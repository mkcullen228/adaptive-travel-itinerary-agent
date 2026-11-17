
import json
import os
import tempfile

from datetime import datetime, timezone
from pathlib import Path


EVALUATION_VERSION = "deterministic_eval_v1"


def build_deterministic_evaluation_record(
    evaluation_result: dict,
    generation_metadata: dict,
    raw_response_path: str | Path,
    generation_metadata_path: str | Path,
    evaluation_version: str = EVALUATION_VERSION,
) -> dict:
    """Combine deterministic results with generation provenance."""

    return {
        "evaluation_version": evaluation_version,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": {
            "benchmark_id": generation_metadata["benchmark_id"],
            "scenario_id": generation_metadata["scenario_id"],
            "proposal_id": evaluation_result["proposal_id"],
        },
        "generation": {
            "model_name": generation_metadata["model_name"],
            "strategy": generation_metadata["strategy"],
            "prompt_version": generation_metadata["prompt_version"],
            "latency_seconds": generation_metadata.get("latency_seconds"),
            "input_tokens": generation_metadata.get("input_tokens"),
            "output_tokens": generation_metadata.get("output_tokens"),
            "structured_output_valid": generation_metadata.get(
                "structured_output_valid"
            ),
        },
        "source_artifacts": {
            "raw_response_path": str(raw_response_path),
            "generation_metadata_path": str(generation_metadata_path),
            "baseline_path": generation_metadata["baseline_path"],
            "investigation_path": generation_metadata["investigation_path"],
            "disruption_path": generation_metadata["disruption_path"],
        },
        "results": {
            "deterministic_validation": evaluation_result[
                "deterministic_validation"
            ],
            "recovery_consistency": evaluation_result[
                "recovery_consistency"
            ],
            "schedule_comparison": evaluation_result["schedule_comparison"],
            "schedule_robustness": evaluation_result["schedule_robustness"],
            "narrative_consistency": evaluation_result[
                "narrative_consistency"
            ],
        },
    }


def save_deterministic_evaluation(
    output_path: str | Path,
    record: dict,
) -> Path:
    """
    Save a deterministic evaluation record without overwriting an
    existing result.

    A temporary file and atomic hard-link creation prevent readers
    from seeing a partially written record and protect existing files.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    serialized = json.dumps(record, indent=2)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(serialized)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # Atomic creation; raises FileExistsError instead of overwriting.
        os.link(temp_path, output_path)

        return output_path

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def load_deterministic_evaluation(
    file_path: str | Path,
) -> dict:
    """Load a saved deterministic evaluation record."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Evaluation result not found: {file_path}"
        )

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)
