import os
import json
import tempfile
from pathlib import Path


from src.models.llm_evaluation import LLMEvaluationRecord


def load_evaluation_results(file_path: Path) -> dict:
    """Load existing evaluation results or initialize an empty structure."""

    if not file_path.exists():
        return {
            "evaluation_version": "1.0",
            "models": []
        }

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def append_evaluation_record(
    file_path: Path,
    record: LLMEvaluationRecord,
    model_type: str = "local"
) -> None:
    """Append an evaluation record to the matching model and scenario."""

    results = load_evaluation_results(file_path)

    # Find or create the model entry
    model = next(
        (
            item for item in results["models"]
            if item["model_name"] == record.model_name
        ),
        None
    )

    if model is None:
        model = {
            "model_name": record.model_name,
            "model_type": model_type,
            "scenarios": []
        }
        results["models"].append(model)

    # Find or create the scenario entry
    scenario = next(
        (
            item for item in model["scenarios"]
            if item["scenario_id"] == record.scenario_id
        ),
        None
    )

    if scenario is None:
        scenario = {
            "scenario_id": record.scenario_id,
            "iterations": []
        }
        model["scenarios"].append(scenario)

    # Prevent duplicate evaluation IDs across all models and scenarios
    existing_ids = {
        iteration["evaluation_id"]
        for model_entry in results["models"]
        for scenario_entry in model_entry["scenarios"]
        for iteration in scenario_entry["iterations"]
    }

    if record.evaluation_id in existing_ids:
        raise ValueError(
            f"Evaluation ID already exists: {record.evaluation_id}"
        )

    scenario["iterations"].append(record.model_dump(mode="json"))

    # Serialize results before touching the existing file
    serialized_results = json.dumps(results, indent=2)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp",
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(serialized_results)

        # Replace the original only after the temporary write succeeds
        os.replace(temp_path, file_path)
        temp_path = None

    finally:
        # Clean up temporary file if replacement fails
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)