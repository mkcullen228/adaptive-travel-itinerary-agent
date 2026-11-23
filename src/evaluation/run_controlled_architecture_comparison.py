
import argparse
import hashlib
import json
import time

from datetime import datetime, timezone
from pathlib import Path

import ollama

from src.data_sources.build_travel_legs import (
    add_travel_legs_to_itinerary,
)
from src.evaluation.benchmark_config import (
    load_benchmark_config,
    resolve_project_path,
)
from src.evaluation.benchmark_runner import build_planning_input
from src.evaluation.benchmark_evaluator import evaluate_benchmark_case
from src.models.agent_workflow import RecoveryPlanningInput
from src.recovery.audit import (
    audit_recovery_proposal,
    build_audit_messages,
)
from src.recovery.generation import (
    build_recovery_messages,
    generate_recovery_option,
)
from src.recovery.research import research_evidence


CONTROLLED_PROMPT_VERSION = "shared_standard_planner_v1"
AUDITOR_PROMPT_VERSION = "auditor_schedule_robustness_v2"

def sha256_json(value) -> str:
    """Create a stable SHA-256 hash of JSON-compatible data."""
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def write_json(path: Path, data) -> None:
    """Write JSON without overwriting an existing artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing artifact: {path}"
        )

    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def save_raw_response(path: Path, response: str) -> None:
    """Preserve the exact raw model response."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing response: {path}"
        )

    path.write_text(response, encoding="utf-8")


def agent_metadata(result) -> dict:
    """Extract common metadata from an agent generation result."""
    return {
        "model_name": result.model_name,
        "latency_seconds": result.latency_seconds,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


def sum_complete_tokens(agent_records: list[dict], field: str):
    """Return a token total only when every agent reports token usage."""
    values = [record.get(field) for record in agent_records]

    if not values or any(value is None for value in values):
        return None

    return sum(values)


def schedule_preservation_findings(
    original_itinerary,
    proposed_itinerary,
    affected_activity_ids,
) -> list[dict]:
    """Identify changes to retained activities outside the disruption."""
    original_by_id = {
        activity.activity_id: activity
        for activity in original_itinerary.activities
    }
    proposed_by_id = {
        activity.activity_id: activity
        for activity in proposed_itinerary.activities
    }

    affected_ids = set(affected_activity_ids)
    findings = []

    for activity_id, original in original_by_id.items():
        if activity_id in affected_ids:
            continue

        proposed = proposed_by_id.get(activity_id)

        if proposed is None:
            continue

        changed = (
            original.start_time != proposed.start_time
            or original.duration_minutes != proposed.duration_minutes
        )

        if changed:
            findings.append({
                "activity_id": activity_id,
                "activity_name": original.name,
                "original_start_time": original.start_time.isoformat(),
                "proposed_start_time": proposed.start_time.isoformat(),
                "original_duration_minutes": original.duration_minutes,
                "proposed_duration_minutes": proposed.duration_minutes,
                "reason": (
                    "An existing activity's schedule changed. Review whether "
                    "the change is necessary and supported by the disruption, "
                    "evidence, and travel estimates."
                ),
            })

    return findings


def prepare_frozen_planning_input(
    config,
) -> RecoveryPlanningInput:
    """
    Load the common benchmark inputs and prepare walking estimates once.

    Both architectures receive independent copies of this same frozen input.
    """

    planning_input = build_planning_input(config)

    itinerary_copy = planning_input.original_itinerary.model_copy(
        deep=True
    )

    itinerary_with_routes = add_travel_legs_to_itinerary(
        itinerary_copy
    )

    return planning_input.model_copy(
        update={
            "original_itinerary": itinerary_with_routes,
        },
        deep=True,
    )


def build_initial_artifacts(
    planning_input: RecoveryPlanningInput,
    config,
    output_dir: Path,
) -> dict:
    """Save and describe the shared input snapshot."""

    input_data = planning_input.model_dump(mode="json")

    input_hash = sha256_json(input_data)

    write_json(
        output_dir / "prepared_inputs.json",
        input_data,
    )

    itinerary = planning_input.original_itinerary

    snapshot = {
        "benchmark_id": config.benchmark_id,
        "scenario_id": config.scenario_id,
        "model_name": config.model_name,
        "strategy": config.strategy.value,
        "controlled_prompt_version": CONTROLLED_PROMPT_VERSION,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "planning_input_sha256": input_hash,
        "original_itinerary_sha256": sha256_json(
            itinerary.model_dump(mode="json")
        ),
        "investigation_sha256": sha256_json(
            planning_input.investigation_result.model_dump(mode="json")
        ),
        "disruption_sha256": sha256_json(
            planning_input.disruption_scenario.model_dump(mode="json")
        ),
        "walking_travel_leg_count": len(itinerary.travel_legs),
        "routing_failure_count": len(itinerary.routing_failures),
        "travel_legs": [
            leg.model_dump(mode="json")
            for leg in itinerary.travel_legs
        ],
        "routing_failures": [
            failure.model_dump(mode="json")
            for failure in itinerary.routing_failures
        ],
    }

    write_json(
        output_dir / "input_snapshot_metadata.json",
        snapshot,
    )

    return snapshot


def run_single_agent(
    planning_input: RecoveryPlanningInput,
    model_name: str,
    client,
    run_dir: Path,
    run_id: str,
    input_snapshot: dict,
) -> dict:
    """Run the one-call Planner baseline."""

    start = time.perf_counter()

    # No Researcher brief is supplied to the single-agent baseline.
    result = generate_recovery_option(
        planning_input=planning_input.model_copy(deep=True),
        model_name=model_name,
        client=client,
        evidence_brief=None,
        use_experimental_prompt=False,
    )

    wall_latency = time.perf_counter() - start

    proposal = result.recovery_option

    evaluation = evaluate_benchmark_case(
        original=planning_input.original_itinerary,
        scenario=planning_input.disruption_scenario,
        proposal=proposal,
    )

    messages = build_recovery_messages(
        planning_input=planning_input,
        evidence_brief=None,
        use_experimental_prompt=False,
    )

    planner_metadata = agent_metadata(result)

    metadata = {
        "run_id": run_id,
        "architecture": "single_agent",
        "benchmark_id": input_snapshot["benchmark_id"],
        "scenario_id": input_snapshot["scenario_id"],
        "model_name": result.model_name,
        "strategy": planning_input.strategy.value,
        "controlled_prompt_version": CONTROLLED_PROMPT_VERSION,
        "planner_system_prompt_sha256": hashlib.sha256(
            messages[0]["content"].encode("utf-8")
        ).hexdigest(),
        "planner_user_prompt_sha256": hashlib.sha256(
            messages[1]["content"].encode("utf-8")
        ).hexdigest(),
        "planning_input_sha256": input_snapshot[
            "planning_input_sha256"
        ],
        "llm_call_count": 1,
        "llm_latency_seconds": result.latency_seconds,
        "workflow_wall_latency_seconds": wall_latency,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "planner_metadata": planner_metadata,
        "proposal_id": proposal.option_id,
        "proposal_status": proposal.proposal_status.value,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    save_raw_response(
        run_dir / "planner_response.json",
        result.raw_response,
    )

    write_json(run_dir / "evaluation.json", evaluation)
    write_json(run_dir / "metadata.json", metadata)

    return {
        "metadata": metadata,
        "evaluation": evaluation,
    }



def run_multi_agent(
    planning_input: RecoveryPlanningInput,
    model_name: str,
    client,
    run_dir: Path,
    run_id: str,
    input_snapshot: dict,
) -> dict:
    """Run Researcher, Planner, deterministic evaluation, and Auditor."""

    start = time.perf_counter()

    # Agent 1: Researcher interprets the frozen investigation snapshot.
    research_result = research_evidence(
        investigation=planning_input.investigation_result,
        disruption=planning_input.disruption_scenario,
        model_name=model_name,
        client=client,
    )

    evidence_brief = research_result.evidence_brief

    # Agent 2: Planner receives the same base input and standard system
    # prompt as the single-agent baseline, plus the Researcher's brief.
    planner_result = generate_recovery_option(
        planning_input=planning_input.model_copy(deep=True),
        model_name=model_name,
        client=client,
        evidence_brief=evidence_brief,
        use_experimental_prompt=False,
    )

    proposal = planner_result.recovery_option

    # Apply the same deterministic evaluator used for the baseline.
    evaluation = evaluate_benchmark_case(
        original=planning_input.original_itinerary,
        scenario=planning_input.disruption_scenario,
        proposal=proposal,
    )

    # Give the Auditor both the validation issues and the detailed
    # leg-by-leg schedule calculations.
    validation_context = dict(
        evaluation["deterministic_validation"]
    )

    validation_context["schedule_robustness"] = (
        evaluation.get("schedule_robustness")
    )

    validation_context["schedule_preservation_findings"] = (
        schedule_preservation_findings(
            original_itinerary=planning_input.original_itinerary,
            proposed_itinerary=proposal.proposed_itinerary,
            affected_activity_ids=(
                planning_input.disruption_scenario.affected_activity_ids
            ),
        )
    )

    # Build the exact Auditor messages so the prompt version and hash
    # can be recorded with the experiment.
    audit_messages = build_audit_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=proposal,
        deterministic_validation=validation_context,
    )

    # Agent 3: Auditor reviews the proposal without modifying it.
    audit_result = audit_recovery_proposal(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=proposal,
        deterministic_validation=validation_context,
        model_name=model_name,
        client=client,
    )

    wall_latency = time.perf_counter() - start

    research_metadata = agent_metadata(research_result)
    planner_metadata = agent_metadata(planner_result)
    audit_metadata = agent_metadata(audit_result)

    agent_records = [
        research_metadata,
        planner_metadata,
        audit_metadata,
    ]

    messages = build_recovery_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        use_experimental_prompt=False,
    )

    metadata = {
        "run_id": run_id,
        "architecture": "multi_agent",
        "benchmark_id": input_snapshot["benchmark_id"],
        "scenario_id": input_snapshot["scenario_id"],
        "model_name": planner_result.model_name,
        "strategy": planning_input.strategy.value,
        "controlled_prompt_version": CONTROLLED_PROMPT_VERSION,
        "auditor_prompt_version": AUDITOR_PROMPT_VERSION,
        "planner_system_prompt_sha256": hashlib.sha256(
            messages[0]["content"].encode("utf-8")
        ).hexdigest(),
        "planner_user_prompt_sha256": hashlib.sha256(
            messages[1]["content"].encode("utf-8")
        ).hexdigest(),
        "auditor_system_prompt_sha256": hashlib.sha256(
            audit_messages[0]["content"].encode("utf-8")
        ).hexdigest(),
        "auditor_user_prompt_sha256": hashlib.sha256(
            audit_messages[1]["content"].encode("utf-8")
        ).hexdigest(),
        "planning_input_sha256": input_snapshot[
            "planning_input_sha256"
        ],
        "llm_call_count": 3,
        "llm_latency_seconds": sum(
            record["latency_seconds"]
            for record in agent_records
        ),
        "workflow_wall_latency_seconds": wall_latency,
        "input_tokens": sum_complete_tokens(
            agent_records,
            "input_tokens",
        ),
        "output_tokens": sum_complete_tokens(
            agent_records,
            "output_tokens",
        ),
        "researcher_metadata": research_metadata,
        "planner_metadata": planner_metadata,
        "auditor_metadata": audit_metadata,
        "researcher_assessment": [
            finding.model_dump(mode="json")
            for finding in evidence_brief.findings
        ],
        "auditor_assessment": audit_result.audit_report.model_dump(
            mode="json"
        ),
        "proposal_id": proposal.option_id,
        "proposal_status": proposal.proposal_status.value,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    save_raw_response(
        run_dir / "researcher_response.json",
        research_result.raw_response,
    )

    save_raw_response(
        run_dir / "planner_response.json",
        planner_result.raw_response,
    )

    save_raw_response(
        run_dir / "auditor_response.json",
        audit_result.raw_response,
    )

    write_json(run_dir / "evaluation.json", evaluation)
    write_json(run_dir / "metadata.json", metadata)

    return {
        "metadata": metadata,
        "evaluation": evaluation,
    }


def run_controlled_comparison(
    config_path: str | Path,
    output_dir: str | Path,
    runs: int = 3,
) -> None:
    """Run paired, repeated single-agent and multi-agent comparisons."""

    if runs < 1:
        raise ValueError("runs must be at least 1.")

    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = resolve_project_path(config_path)

    config_path = config_path.resolve()

    output_dir = Path(output_dir)

    if not output_dir.is_absolute():
        output_dir = resolve_project_path(output_dir)

    output_dir = output_dir.resolve()

    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            "Output directory is not empty. Choose a new directory: "
            f"{output_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_benchmark_config(config_path)

    print("Preparing shared benchmark input...")
    planning_input = prepare_frozen_planning_input(config)

    input_snapshot = build_initial_artifacts(
        planning_input=planning_input,
        config=config,
        output_dir=output_dir,
    )

    print(
        "Frozen walking estimates: "
        f"{input_snapshot['walking_travel_leg_count']} successful, "
        f"{input_snapshot['routing_failure_count']} failed."
    )

    print(
        "Shared input SHA-256: "
        f"{input_snapshot['planning_input_sha256']}"
    )

    paired_results = []

    for index in range(1, runs + 1):
        run_id = f"run_{index:02d}"

        # Alternate order to reduce systematic first-run/warm-up effects.
        order = (
            ["single_agent", "multi_agent"]
            if index % 2 == 1
            else ["multi_agent", "single_agent"]
        )

        print(f"\nStarting {run_id}: {' -> '.join(order)}")

        run_results = {}

        for architecture in order:
            run_dir = output_dir / run_id / architecture

            if architecture == "single_agent":
                result = run_single_agent(
                    planning_input=planning_input,
                    model_name=config.model_name,
                    client=ollama,
                    run_dir=run_dir,
                    run_id=run_id,
                    input_snapshot=input_snapshot,
                )
            else:
                result = run_multi_agent(
                    planning_input=planning_input,
                    model_name=config.model_name,
                    client=ollama,
                    run_dir=run_dir,
                    run_id=run_id,
                    input_snapshot=input_snapshot,
                )

            run_results[architecture] = result["metadata"]

            metadata = result["metadata"]

            print(
                f"{architecture}: "
                f"calls={metadata['llm_call_count']}, "
                f"LLM latency={metadata['llm_latency_seconds']:.2f}s, "
                f"wall latency="
                f"{metadata['workflow_wall_latency_seconds']:.2f}s, "
                f"validation="
                f"{result['evaluation']['deterministic_validation']['status']}"
            )

        paired_results.append({
            "run_id": run_id,
            "execution_order": order,
            "single_agent": run_results["single_agent"],
            "multi_agent": run_results["multi_agent"],
        })

    summary = {
        "benchmark_id": config.benchmark_id,
        "scenario_id": config.scenario_id,
        "model_name": config.model_name,
        "strategy": config.strategy.value,
        "controlled_prompt_version": CONTROLLED_PROMPT_VERSION,
        "auditor_prompt_version": AUDITOR_PROMPT_VERSION,
        "runs": runs,
        "input_snapshot": input_snapshot,
        "paired_results": paired_results,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "interpretation_note": (
            "The Planner system prompt and generation settings are shared. "
            "The multi-agent Planner additionally receives the Researcher's "
            "EvidenceBrief. The multi-agent condition also includes separate "
            "Researcher and Auditor calls. This comparison measures the "
            "incremental value and resource cost of those components under "
            "the controlled Planner prompt."
        ),
    }
    write_json(output_dir / "summary.json", summary)

    print("\nControlled architecture comparison completed.")
    print(f"Results directory: {output_dir}")
    print(f"Summary: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run a controlled single-agent versus multi-agent "
            "itinerary recovery comparison."
        )
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to the existing P-01 benchmark JSON config.",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="New directory for this experiment's artifacts.",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of paired iterations. Defaults to 3.",
    )

    args = parser.parse_args()

    run_controlled_comparison(
        config_path=args.config,
        output_dir=args.output_dir,
        runs=args.runs,
    )
