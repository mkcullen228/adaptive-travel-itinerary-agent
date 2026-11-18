import json
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.benchmark_config import (
    load_benchmark_config,
    resolve_project_path,
)
from src.evaluation.benchmark_runner import build_planning_input
from src.models.agent_state import WorkflowStatus
from src.workflows.multi_agent_recovery import (
    build_multi_agent_recovery_graph,
)
from src.workflows.state_initialization import initialize_agent_state


def build_initial_state(planning_input):
    """Build the initial graph state from the shared benchmark inputs."""

    state = initialize_agent_state(
        itinerary=planning_input.original_itinerary,
        disruption=planning_input.disruption_scenario,
        user_instructions=planning_input.user_instructions,
        mandatory_constraints=planning_input.mandatory_constraints,
        flexible_preferences=planning_input.flexible_preferences,
    )

    state["investigation_result"] = planning_input.investigation_result

    return state


def run_multi_agent_benchmark(config_path: str | Path):
    """Run one configured multi-agent recovery benchmark."""

    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = resolve_project_path(config_path)

    config_path = config_path.resolve()
    config = load_benchmark_config(config_path)

    output_path = resolve_project_path(config.output_path)

    metadata_path = output_path.with_name(
        f"{output_path.stem}.metadata.json"
    )
    research_path = output_path.with_name(
        f"{output_path.stem}.research.json"
    )
    audit_path = output_path.with_name(
        f"{output_path.stem}.audit.json"
    )

    # Do not spend model resources or overwrite an existing experiment.
    output_paths = [
        output_path,
        metadata_path,
        research_path,
        audit_path,
    ]

    for path in output_paths:
        if path.exists():
            raise FileExistsError(
                f"Output already exists; refusing to overwrite: {path}"
            )

    planning_input = build_planning_input(config)
    initial_state = build_initial_state(planning_input)

    graph = build_multi_agent_recovery_graph(
        strategy=config.strategy,
        model_name=config.model_name,
        additional_instructions=config.additional_instructions,
    )

    result = graph.invoke(initial_state)

    if result["status"] != WorkflowStatus.COMPLETED:
        raise RuntimeError(
            "Multi-agent benchmark did not complete successfully. "
            f"Status: {result['status']}. "
            f"Errors: {result.get('error_details', [])}"
        )

    research_raw = result.get("research_raw_response")
    planning_raw = result.get("planning_raw_response")
    audit_raw = result.get("audit_raw_response")

    if not all([research_raw, planning_raw, audit_raw]):
        raise ValueError(
            "A completed multi-agent run is missing one or more raw responses."
        )

    validation_result = result["itinerary_validation_result"]
    audit_report = result["audit_report"]

    metadata = {
        "benchmark_id": config.benchmark_id,
        "scenario_id": config.scenario_id,
        "model_name": config.model_name,
        "strategy": config.strategy.value,
        "prompt_version": config.prompt_version,
        "config_path": str(config_path),
        "baseline_path": str(resolve_project_path(config.baseline_path)),
        "investigation_path": str(
            resolve_project_path(config.investigation_path)
        ),
        "disruption_path": str(
            resolve_project_path(config.disruption_path)
        ),
        "workflow_status": result["status"].value,
        "current_stage": result["current_stage"].value,
        "llm_call_count": result["llm_call_count"],
        "tool_call_count": result["total_tool_call_count"],
        "research_generation_metadata": result[
            "research_generation_metadata"
        ],
        "planning_generation_metadata": result[
            "planning_generation_metadata"
        ],
        "audit_generation_metadata": result[
            "audit_generation_metadata"
        ],
        "aggregate_generation_metadata": result[
            "multi_agent_generation_metadata"
        ],
        "deterministic_validation_status": validation_result.status.value,
        "deterministic_validation_issues": [
            issue.model_dump(mode="json")
            for issue in validation_result.issues
        ],
        "audit_report": audit_report.model_dump(mode="json"),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve the exact raw model responses for later inspection.
    research_path.write_text(research_raw, encoding="utf-8")
    output_path.write_text(planning_raw, encoding="utf-8")
    audit_path.write_text(audit_raw, encoding="utf-8")

    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Multi-agent benchmark completed: {config.benchmark_id}")
    print(f"Scenario: {config.scenario_id}")
    print(f"Model: {config.model_name}")
    print(f"LLM calls: {result['llm_call_count']}")
    print(
        "LLM latency: "
        f"{metadata['aggregate_generation_metadata']['total_latency_seconds']}"
    )
    print(
        "Workflow latency: "
        f"{metadata['aggregate_generation_metadata']['total_workflow_latency_seconds']}"
    )
    print(
        "Input tokens: "
        f"{metadata['aggregate_generation_metadata']['total_input_tokens']}"
    )
    print(
        "Output tokens: "
        f"{metadata['aggregate_generation_metadata']['total_output_tokens']}"
    )
    print(f"Research response: {research_path}")
    print(f"Planner response: {output_path}")
    print(f"Auditor response: {audit_path}")
    print(f"Run metadata: {metadata_path}")
    print(
        "Deterministic validation: "
        f"{validation_result.status.value}"
    )

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a configured multi-agent recovery benchmark."
    )
    parser.add_argument(
        "config",
        help="Path to a multi-agent benchmark JSON configuration file.",
    )
    args = parser.parse_args()

    run_multi_agent_benchmark(args.config)
