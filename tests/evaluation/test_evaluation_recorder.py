import json
import pytest
import shutil
from pathlib import Path

from src.evaluation.evaluation_recorder import (
    load_evaluation_results
)

from src.models.llm_evaluation import (
    LLMEvaluationRecord,
    EvaluationLevel,
    OverallResult
)

from src.evaluation.evaluation_recorder import (
    append_evaluation_record
)


def test_load_missing_evaluation_file(tmp_path):
    file_path = tmp_path / "evaluation_results.json"

    results = load_evaluation_results(file_path)

    assert results == {
        "evaluation_version": "1.0",
        "models": []
    }


def test_load_existing_evaluation_file(tmp_path):
    file_path = tmp_path / "evaluation_results.json"

    existing_results = {
        "evaluation_version": "1.0",
        "models": [
            {
                "model_name": "qwen3.5:4b",
                "model_type": "local",
                "scenarios": []
            }
        ]
    }

    file_path.write_text(
        json.dumps(existing_results),
        encoding="utf-8"
    )

    results = load_evaluation_results(file_path)

    assert results == existing_results
    assert len(results["models"]) == 1
    assert results["models"][0]["model_name"] == "qwen3.5:4b"


def test_append_evaluation_record(tmp_path):
    file_path = tmp_path / "evaluation_results.json"

    record = LLMEvaluationRecord(
        evaluation_id="TEST-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS,
            "evidence_grounding": EvaluationLevel.PARTIAL
        },
        overall_result=OverallResult.PARTIAL
    )

    append_evaluation_record(file_path, record)

    results = load_evaluation_results(file_path)

    assert len(results["models"]) == 1
    assert results["models"][0]["model_name"] == "qwen3.5:4b"

    scenario = results["models"][0]["scenarios"][0]

    assert scenario["scenario_id"] == "P-01"
    assert len(scenario["iterations"]) == 1
    assert scenario["iterations"][0]["evaluation_id"] == "TEST-001"


def test_duplicate_evaluation_id_is_rejected(tmp_path):
    file_path = tmp_path / "evaluation_results.json"

    record = LLMEvaluationRecord(
        evaluation_id="TEST-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    append_evaluation_record(file_path, record)

    with pytest.raises(ValueError, match="Evaluation ID already exists"):
        append_evaluation_record(file_path, record)

    results = load_evaluation_results(file_path)

    assert len(results["models"][0]["scenarios"][0]["iterations"]) == 1


def test_append_multiple_iterations_to_same_scenario(tmp_path):
    file_path = tmp_path / "evaluation_results.json"

    record_1 = LLMEvaluationRecord(
        evaluation_id="TEST-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    record_2 = LLMEvaluationRecord(
        evaluation_id="TEST-002",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=2,
        prompt_version="v2",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PARTIAL
        },
        overall_result=OverallResult.PARTIAL
    )

    append_evaluation_record(file_path, record_1)
    append_evaluation_record(file_path, record_2)

    results = load_evaluation_results(file_path)

    assert len(results["models"]) == 1
    assert len(results["models"][0]["scenarios"]) == 1

    iterations = results["models"][0]["scenarios"][0]["iterations"]

    assert len(iterations) == 2
    assert iterations[0]["evaluation_id"] == "TEST-001"
    assert iterations[1]["evaluation_id"] == "TEST-002"


def test_malformed_json_is_not_overwritten(tmp_path):
    file_path = tmp_path / "evaluation_results.json"
    original_content = '{"evaluation_version": "1.0",'

    file_path.write_text(original_content, encoding="utf-8")

    record = LLMEvaluationRecord(
        evaluation_id="TEST-003",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=3,
        prompt_version="v3",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    with pytest.raises(json.JSONDecodeError):
        append_evaluation_record(file_path, record)

    assert file_path.read_text(encoding="utf-8") == original_content


def test_duplicate_evaluation_id_across_scenarios_is_rejected(tmp_path):
    file_path = tmp_path / "evaluation_results.json"

    record_1 = LLMEvaluationRecord(
        evaluation_id="TEST-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    record_2 = LLMEvaluationRecord(
        evaluation_id="TEST-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-02",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    append_evaluation_record(file_path, record_1)

    with pytest.raises(ValueError, match="Evaluation ID already exists"):
        append_evaluation_record(file_path, record_2)

    results = load_evaluation_results(file_path)

    assert len(results["models"][0]["scenarios"]) == 1


def test_failed_atomic_replace_preserves_original_file(
    tmp_path, monkeypatch
):
    file_path = tmp_path / "evaluation_results.json"

    original_content = json.dumps({
        "evaluation_version": "1.0",
        "models": []
    })

    file_path.write_text(original_content, encoding="utf-8")

    record = LLMEvaluationRecord(
        evaluation_id="TEST-004",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    def fail_replace(source, destination):
        raise OSError("Simulated replacement failure")

    monkeypatch.setattr(
        "src.evaluation.evaluation_recorder.os.replace",
        fail_replace
    )

    with pytest.raises(OSError, match="Simulated replacement failure"):
        append_evaluation_record(file_path, record)

    assert file_path.read_text(encoding="utf-8") == original_content

    # Temporary file should also have been cleaned up
    assert list(tmp_path.glob("*.tmp")) == []


def test_recorder_preserves_existing_p01_results(tmp_path):
    project_root = Path(__file__).resolve().parents[2]

    original_file = (
        project_root
        / "data/evaluations/llm_benchmarks/evaluation_results.json"
    )

    assert original_file.exists()

    # Work with a copy, never the original benchmark file
    test_file = tmp_path / "evaluation_results.json"
    shutil.copy2(original_file, test_file)

    original_results = load_evaluation_results(test_file)

    record = LLMEvaluationRecord(
        evaluation_id="INTEGRATION-TEST-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=4,
        prompt_version="integration-test",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS,
            "evidence_grounding": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    append_evaluation_record(test_file, record)

    updated_results = load_evaluation_results(test_file)

    # Existing model and scenario structure is preserved
    assert len(updated_results["models"]) == len(original_results["models"])

    original_model = original_results["models"][0]
    updated_model = updated_results["models"][0]

    assert updated_model["model_name"] == original_model["model_name"]

    original_scenario = original_model["scenarios"][0]
    updated_scenario = updated_model["scenarios"][0]

    assert updated_scenario["scenario_id"] == "P-01"
    assert len(updated_scenario["iterations"]) == (
        len(original_scenario["iterations"]) + 1
    )

    assert updated_scenario["iterations"][-1]["evaluation_id"] == (
        "INTEGRATION-TEST-001"
    )
