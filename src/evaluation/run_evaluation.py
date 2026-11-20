import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.evaluation.auditor_evaluator import (
    evaluate_auditor_output,
)
from src.evaluation.evidence_quality_evaluator import (
    evaluate_researcher_output,
)
from src.evaluation.input_loader import load_evaluation_inputs
from src.evaluation.planner_evaluator import evaluate_planner_output
from src.evaluation.scenario_loader import load_scenarios
from src.models.agent_state import WorkflowStatus
from src.recovery.generation import DEFAULT_MODEL
from src.workflows.multi_agent_recovery import (
    build_multi_agent_recovery_graph,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCENARIO_DIRECTORY = (
    PROJECT_ROOT / "data/evaluations/evidence_quality/scenarios"
)

DEFAULT_RESULTS_DIRECTORY = (
    PROJECT_ROOT / "data/evaluations/evidence_quality/results"
)


def _metadata_totals(state: dict) -> dict:
    """Aggregate per-agent metadata without relying on workflow totals."""

    agent_metadata = {
        "researcher": state.get("research_generation_metadata"),
        "planner": state.get("planning_generation_metadata"),
        "auditor": state.get("audit_generation_metadata"),
    }

    total_latency = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    for metadata in agent_metadata.values():
        if not metadata:
            continue

        total_latency += metadata.get("latency_seconds") or 0
        total_input_tokens += metadata.get("input_tokens") or 0
        total_output_tokens += metadata.get("output_tokens") or 0

    return {
        "agents": agent_metadata,
        "total_latency_seconds": total_latency,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "llm_call_count": state.get("llm_call_count", 0),
    }


def _auditor_validation_input(validation_result):
    """
    Adapt the workflow's ValidationResult for the current Auditor evaluator.

    The workflow model uses `issues`; the Auditor evaluator currently
    expects a dictionary containing a `failures` list.
    """

    if validation_result is None:
        return None

    failures = []

    for issue in validation_result.issues:
        issue_type = getattr(issue.issue_type, "value", issue.issue_type)
        description = issue.description

        failures.append(
            f"Schedule issue ({issue_type}): {description}"
        )

    return {"failures": failures}


def run_scenario(
    scenario_id: str,
    model_name: str = DEFAULT_MODEL,
    output_directory: Path = DEFAULT_RESULTS_DIRECTORY,
    graph=None,
) -> dict:
    """Run and evaluate one evidence-quality scenario."""

    scenario, initial_state = load_evaluation_inputs(scenario_id)

    if graph is None:
        graph = build_multi_agent_recovery_graph(
            model_name=model_name,
        )

    started_at = datetime.now(timezone.utc)
    run_id = str(uuid4())

    final_state = graph.invoke(initial_state)

    workflow_status = final_state.get("status")

    completed = (
        workflow_status == WorkflowStatus.COMPLETED
        or getattr(workflow_status, "value", workflow_status)
        == WorkflowStatus.COMPLETED.value
    )

    researcher_evaluation = None
    planner_evaluation = None
    auditor_evaluation = None
    evaluation_skip_reason = None

    if completed:
        evidence_brief = final_state.get("evidence_brief")
        recovery_options = final_state.get("recovery_options") or []

        if evidence_brief is None:
            evaluation_skip_reason = (
                "Workflow completed without a Researcher evidence brief."
            )

        elif not recovery_options:
            evaluation_skip_reason = (
                "Workflow completed without a Planner recovery option."
            )

        else:
            original_itinerary = final_state["original_itinerary"]
            recovery_option = recovery_options[0]

            # Researcher evaluation
            researcher_evaluation = evaluate_researcher_output(
                scenario,
                evidence_brief,
            )

            # Planner evaluation
            planner_evaluation = evaluate_planner_output(
                scenario,
                original_itinerary,
                recovery_option,
            )

            # Auditor evaluation
            audit_report = final_state.get("audit_report")

            if audit_report is not None:
                validation_result = final_state.get(
                    "itinerary_validation_result"
                )

                deterministic_validation = (
                    _auditor_validation_input(validation_result)
                )

                auditor_evaluation = evaluate_auditor_output(
                    scenario=scenario,
                    original_itinerary=original_itinerary,
                    proposed_itinerary=recovery_option.proposed_itinerary,
                    audit_report=audit_report,
                    deterministic_validation=deterministic_validation,
                )

    result = {
        "run_id": run_id,
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "model_name": model_name,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "workflow_status": (
            workflow_status.value
            if hasattr(workflow_status, "value")
            else str(workflow_status)
        ),
        "current_stage": (
            final_state["current_stage"].value
            if hasattr(final_state.get("current_stage"), "value")
            else str(final_state.get("current_stage"))
        ),
        "error_details": final_state.get("error_details", []),
        "metadata": _metadata_totals(final_state),

        "researcher_evaluation": (
            researcher_evaluation.model_dump(mode="json")
            if researcher_evaluation is not None
            else None
        ),

        "planner_evaluation": (
            planner_evaluation.model_dump(mode="json")
            if planner_evaluation is not None
            else None
        ),

        "auditor_evaluation": (
            auditor_evaluation.model_dump(mode="json")
            if auditor_evaluation is not None
            else None
        ),

        "evaluation_skip_reason": evaluation_skip_reason,

        "audit_report": (
            final_state["audit_report"].model_dump(mode="json")
            if final_state.get("audit_report") is not None
            else None
        ),

        "deterministic_validation": (
            final_state["itinerary_validation_result"].model_dump(
                mode="json"
            )
            if final_state.get("itinerary_validation_result") is not None
            else None
        ),

        "raw_responses": {
            "researcher": final_state.get("research_raw_response"),
            "planner": final_state.get("planning_raw_response"),
            "auditor": final_state.get("audit_raw_response"),
        },
    }

    # Preserve the existing Researcher + Planner pass definition.
    # Include Auditor when an Auditor evaluation is available.
    result["overall_evaluation_passed"] = (
        researcher_evaluation is not None
        and planner_evaluation is not None
        and researcher_evaluation.passed
        and planner_evaluation.passed
        and (
            auditor_evaluation is None
            or auditor_evaluation.passed
        )
    )

    output_directory.mkdir(parents=True, exist_ok=True)

    output_path = (
        output_directory
        / f"{scenario.scenario_id}_{run_id}.json"
    )

    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result["result_path"] = str(output_path)

    return result


def run_scenarios(
    scenario_ids: list[str],
    model_name: str = DEFAULT_MODEL,
    output_directory: Path = DEFAULT_RESULTS_DIRECTORY,
) -> list[dict]:
    """Run multiple scenarios independently."""

    return [
        run_scenario(
            scenario_id=scenario_id,
            model_name=model_name,
            output_directory=output_directory,
        )
        for scenario_id in scenario_ids
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Run evidence-quality experiments."
    )

    selection = parser.add_mutually_exclusive_group(required=True)

    selection.add_argument(
        "--scenario",
        choices=["E1", "E2", "E3", "E4", "E5"],
    )

    selection.add_argument(
        "--all",
        action="store_true",
        help="Run all five evidence scenarios.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model name used by the multi-agent workflow.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIRECTORY,
        help="Directory for individual JSON result artifacts.",
    )

    args = parser.parse_args()

    if args.all:
        scenarios = load_scenarios(SCENARIO_DIRECTORY)
        scenario_ids = [
            scenario.scenario_id for scenario in scenarios
        ]
    else:
        scenario_ids = [args.scenario]

    results = run_scenarios(
        scenario_ids=scenario_ids,
        model_name=args.model,
        output_directory=args.output_dir,
    )

    for result in results:
        print(
            f"{result['scenario_id']}: "
            f"status={result['workflow_status']}, "
            f"evaluation_passed={result['overall_evaluation_passed']}, "
            f"saved={result['result_path']}"
        )


if __name__ == "__main__":
    main()
