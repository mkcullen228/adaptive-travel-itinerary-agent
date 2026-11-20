
import argparse
import json
from pathlib import Path

from src.evaluation.auditor_evaluator import evaluate_auditor_output
from src.evaluation.evidence_quality_evaluator import (
    evaluate_researcher_output,
)
from src.evaluation.input_loader import load_evaluation_inputs
from src.evaluation.planner_evaluator import evaluate_planner_output
from src.models.agent_workflow import RecoveryOption
from src.models.multi_agent import EvidenceBrief, AuditReport


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_DIRECTORY = (
    PROJECT_ROOT / "data/evaluations/evidence_quality/results"
)

DEFAULT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "data/evaluations/evidence_quality/reevaluated"
)


def evaluate_saved_run(result_path: Path) -> dict:
    """Re-evaluate one saved run without invoking any LLMs."""

    saved_result = json.loads(
        result_path.read_text(encoding="utf-8")
    )

    scenario_id = saved_result["scenario_id"]

    scenario, initial_state = load_evaluation_inputs(scenario_id)

    raw_responses = saved_result.get("raw_responses", {})

    researcher_raw = raw_responses.get("researcher")
    planner_raw = raw_responses.get("planner")
    auditor_raw = raw_responses.get("auditor")

    if not researcher_raw or not planner_raw:
        raise ValueError(
            f"{result_path.name}: missing Researcher or Planner "
            "raw response."
        )

    evidence_brief = EvidenceBrief.model_validate_json(
        researcher_raw
    )

    recovery_option = RecoveryOption.model_validate_json(
        planner_raw
    )

    audit_report = (
        AuditReport.model_validate_json(auditor_raw)
        if auditor_raw
        else None
    )

    researcher_evaluation = evaluate_researcher_output(
        scenario,
        evidence_brief,
    )

    planner_evaluation = evaluate_planner_output(
        scenario,
        initial_state["original_itinerary"],
        recovery_option,
        evidence_brief=evidence_brief,
    )

    auditor_evaluation = None

    if audit_report is not None:
        schedule_failures = list(
            planner_evaluation.schedule_consistency_failures
        )

        schedule_failures.extend(
            failure
            for failure in planner_evaluation.failures
            if (
                "schedule time" in failure.casefold()
                or "time mismatch" in failure.casefold()
            )
        )

        deterministic_validation = {
            "failures": schedule_failures
        }

        auditor_evaluation = evaluate_auditor_output(
            scenario=scenario,
            original_itinerary=initial_state["original_itinerary"],
            proposed_itinerary=recovery_option.proposed_itinerary,
            audit_report=audit_report,
            deterministic_validation=deterministic_validation,
        )

    return {
        "original_run_id": saved_result.get("run_id"),
        "original_result_file": result_path.name,
        "scenario_id": scenario_id,
        "model_name": saved_result.get("model_name"),
        "original_metadata": saved_result.get("metadata"),
        "researcher_evaluation": (
            researcher_evaluation.model_dump(mode="json")
        ),
        "planner_evaluation": (
            planner_evaluation.model_dump(mode="json")
        ),
        "auditor_evaluation": (
            auditor_evaluation.model_dump(mode="json")
            if auditor_evaluation is not None
            else None
        ),
        "overall_evaluation_passed": (
            researcher_evaluation.passed
            and planner_evaluation.passed
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Re-evaluate saved evidence-quality runs."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIRECTORY,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )

    args = parser.parse_args()

    result_files = sorted(args.input_dir.glob("*.json"))

    if not result_files:
        raise FileNotFoundError(
            f"No JSON result files found in {args.input_dir}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for result_path in result_files:
        try:
            evaluation = evaluate_saved_run(result_path)

            output_path = (
                args.output_dir
                / f"{result_path.stem}_reevaluated.json"
            )

            output_path.write_text(
                json.dumps(evaluation, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            print(
                f"{evaluation['scenario_id']}: "
                f"passed={evaluation['overall_evaluation_passed']}, "
                f"saved={output_path.name}"
            )

        except Exception as exc:
            print(
                f"ERROR: {result_path.name}: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()
