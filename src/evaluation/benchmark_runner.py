import json
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.benchmark_config import (
    BenchmarkConfig,
    load_benchmark_config,
    resolve_project_path,
)
from src.models.agent_workflow import (
    DisruptionScenario,
    InvestigationResult,
    RecoveryPlanningInput,
)
from src.models.itinerary import Itinerary
from src.recovery.generation import generate_recovery_option
from src.validation.schedule_validator import validate_itinerary


def load_json_model(path: Path, model_class):
    """Load a JSON file and validate it against a Pydantic model."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    return model_class.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def build_planning_input(config: BenchmarkConfig) -> RecoveryPlanningInput:
    """Load benchmark inputs and construct the recovery planning request."""

    baseline_path = resolve_project_path(config.baseline_path)
    investigation_path = resolve_project_path(config.investigation_path)
    disruption_path = resolve_project_path(config.disruption_path)

    baseline = load_json_model(baseline_path, Itinerary)
    investigation = load_json_model(
        investigation_path,
        InvestigationResult,
    )
    disruption = load_json_model(
        disruption_path,
        DisruptionScenario,
    )

    return RecoveryPlanningInput(
        original_itinerary=baseline,
        investigation_result=investigation,
        disruption_scenario=disruption,
        user_instructions=config.user_instructions,
        strategy=config.strategy,
        additional_instructions=config.additional_instructions,
    )


def build_run_metadata(
    config: BenchmarkConfig,
    result,
    config_path: Path,
    validation_result,
) -> dict:
    """Create a metadata record for the generation run."""

    return {
        "benchmark_id": config.benchmark_id,
        "scenario_id": config.scenario_id,
        "model_name": result.model_name,
        "strategy": config.strategy.value,
        "prompt_version": config.prompt_version,
        "config_path": str(config_path),
        "baseline_path": str(resolve_project_path(config.baseline_path)),
        "investigation_path": str(
            resolve_project_path(config.investigation_path)
        ),
        "disruption_path": str(resolve_project_path(config.disruption_path)),
        "latency_seconds": result.latency_seconds,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "structured_output_valid": True,
        "proposal_status": result.recovery_option.proposal_status,
        "deterministic_validation_status": validation_result.status,
        "deterministic_validation_issues": [
            issue.model_dump(mode="json")
            for issue in validation_result.issues
        ],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def run_benchmark(config_path: str | Path):
    """Execute one configured benchmark generation run."""

    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = resolve_project_path(config_path)
    config_path = config_path.resolve()

    config = load_benchmark_config(config_path)

    output_path = resolve_project_path(config.output_path)
    metadata_path = output_path.with_name(
        f"{output_path.stem}.metadata.json"
    )

    # Check before making an LLM call so an existing run is not overwritten
    # and model resources are not spent unnecessarily.
    if output_path.exists():
        raise FileExistsError(
            f"Output already exists; refusing to overwrite: {output_path}"
        )

    if metadata_path.exists():
        raise FileExistsError(
            f"Metadata file already exists; refusing to overwrite: "
            f"{metadata_path}"
        )

    planning_input = build_planning_input(config)

    result = generate_recovery_option(
        planning_input=planning_input,
        model_name=config.model_name,
    )

    validation_result = validate_itinerary(
        result.recovery_option.proposed_itinerary
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the original model response, not a re-serialized version of the
    # parsed Pydantic object. This preserves the exact response for review.
    output_path.write_text(
        result.raw_response,
        encoding="utf-8",
    )

    metadata = build_run_metadata(
        config,
        result,
        config_path,
        validation_result,
    )

    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Benchmark completed: {config.benchmark_id}")
    print(f"Scenario: {config.scenario_id}")
    print(f"Model: {result.model_name}")
    print(f"Latency: {result.latency_seconds:.2f} seconds")
    print(f"Input tokens: {result.input_tokens}")
    print(f"Output tokens: {result.output_tokens}")
    print(f"Raw response: {output_path}")
    print(f"Run metadata: {metadata_path}")

    print(f"Proposal status: {result.recovery_option.proposal_status}")
    print(f"Deterministic validation: {validation_result.status}")
    print(
        f"Validation issues: {len(validation_result.issues)}"
    )

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a configured itinerary recovery benchmark."
    )
    parser.add_argument(
        "config",
        help="Path to a benchmark JSON configuration file.",
    )
    args = parser.parse_args()

    run_benchmark(args.config)
