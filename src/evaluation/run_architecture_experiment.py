
import argparse
import json

from datetime import datetime, timezone
from pathlib import Path

import ollama

from src.evaluation.benchmark_config import (
    load_benchmark_config,
    resolve_project_path,
)
from src.evaluation.benchmark_runner import build_planning_input
from src.evaluation.benchmark_evaluator import evaluate_benchmark_case
from src.evaluation.deterministic_evaluation_recorder import (
    build_deterministic_evaluation_record,
    save_deterministic_evaluation,
)
from src.models.agent_state import WorkflowStatus
from src.workflows.single_agent_recovery import (
    build_single_agent_recovery_graph,
)
from src.workflows.state_initialization import initialize_agent_state


class RecordingClient:
    """Pass requests to Ollama while retaining its raw response."""

    def __init__(self, client):
        self.client = client
        self.response = None

    def chat(self, **kwargs):
        self.response = self.client.chat(**kwargs)
        return self.response


def run_single_agent_experiment(config_path: str | Path):
    """Run and evaluate one single-agent architecture experiment."""

    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = resolve_project_path(config_path)

    config_path = config_path.resolve()
    config = load_benchmark_config(config_path)

    raw_response_path = resolve_project_path(config.output_path)

    metadata_path = raw_response_path.with_name(
        f"{raw_response_path.stem}.metadata.json"
    )

    evaluation_path = raw_response_path.with_name(
        f"{raw_response_path.stem}.evaluation.json"
    )

    # Check every output before spending resources on a model call.
    output_paths = [
        raw_response_path,
        metadata_path,
        evaluation_path,
    ]

    for path in output_paths:
        if path.exists():
            raise FileExistsError(
                f"Output already exists; refusing to overwrite: {path}"
            )

    # Load the same original inputs used by the existing benchmark.
    planning_input = build_planning_input(config)

    state = initialize_agent_state(
        itinerary=planning_input.original_itinerary,
        disruption=planning_input.disruption_scenario,
        user_instructions=planning_input.user_instructions,
        mandatory_constraints=planning_input.mandatory_constraints,
        flexible_preferences=planning_input.flexible_preferences,
    )

    # Reuse the frozen investigation snapshot; do not rerun retrieval.
    state["investigation_result"] = planning_input.investigation_result

    recording_client = RecordingClient(ollama)

    graph = build_single_agent_recovery_graph(
        strategy=config.strategy,
        model_name=config.model_name,
        client=recording_client,
        additional_instructions=config.additional_instructions,
    )

    result_state = graph.invoke(state)

    if result_state["status"] != WorkflowStatus.COMPLETED:
        raise RuntimeError(
            f"Single-agent workflow did not complete: "
            f"{result_state['status']}"
        )

    if recording_client.response is None:
        raise RuntimeError("No raw model response was captured.")

    if not result_state["recovery_options"]:
        raise RuntimeError("The workflow did not produce a recovery option.")

    proposal = result_state["recovery_options"][0]
    validation_result = result_state["itinerary_validation_result"]
    generation_metadata = result_state["recovery_generation_metadata"]

    if validation_result is None or generation_metadata is None:
        raise RuntimeError(
            "The workflow did not return validation or generation metadata."
        )

    raw_response = recording_client.response.message.content

    if not raw_response:
        raise RuntimeError("The captured model response is empty.")

    # Preserve the original response exactly as returned by Ollama.
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_response_path.write_text(raw_response, encoding="utf-8")

    metadata = {
        "benchmark_id": config.benchmark_id,
        "scenario_id": config.scenario_id,
        "architecture": "single_agent",
        "model_name": generation_metadata["model_name"],
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
        "latency_seconds": generation_metadata["latency_seconds"],
        "input_tokens": generation_metadata["input_tokens"],
        "output_tokens": generation_metadata["output_tokens"],
        "llm_call_count": result_state["llm_call_count"],
        "tool_call_count": result_state["total_tool_call_count"],
        "structured_output_valid": True,
        "proposal_id": proposal.option_id,
        "proposal_status": proposal.proposal_status.value,
        "deterministic_validation_status": validation_result.status.value,
        "deterministic_validation_issues": [
            issue.model_dump(mode="json")
            for issue in validation_result.issues
        ],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    # Apply the same deterministic evaluator used by the other benchmarks.
    evaluation_result = evaluate_benchmark_case(
        original=planning_input.original_itinerary,
        scenario=planning_input.disruption_scenario,
        proposal=proposal,
    )

    evaluation_record = build_deterministic_evaluation_record(
        evaluation_result=evaluation_result,
        generation_metadata=metadata,
        raw_response_path=raw_response_path,
        generation_metadata_path=metadata_path,
    )

    save_deterministic_evaluation(
        evaluation_path,
        evaluation_record,
    )

    print("\nSingle-agent experiment completed.")
    print(f"Benchmark: {config.benchmark_id}")
    print(f"Scenario: {config.scenario_id}")
    print(f"Model: {generation_metadata['model_name']}")
    print(f"LLM calls: {result_state['llm_call_count']}")
    print(f"Latency: {generation_metadata['latency_seconds']:.2f} seconds")
    print(f"Input tokens: {generation_metadata['input_tokens']}")
    print(f"Output tokens: {generation_metadata['output_tokens']}")
    print(f"Proposal status: {proposal.proposal_status.value}")
    print(f"Validation: {validation_result.status.value}")
    print(f"Raw response: {raw_response_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Evaluation: {evaluation_path}")

    return result_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a single-agent architecture experiment."
    )
    parser.add_argument(
        "config",
        help="Path to the experiment configuration JSON.",
    )

    args = parser.parse_args()
    run_single_agent_experiment(args.config)
