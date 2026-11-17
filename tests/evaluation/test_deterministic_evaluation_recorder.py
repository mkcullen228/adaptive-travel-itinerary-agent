
import json

import pytest

from src.evaluation.deterministic_evaluation_recorder import (
    build_deterministic_evaluation_record,
    save_deterministic_evaluation,
    load_deterministic_evaluation,
)


@pytest.fixture
def generation_metadata():
    return {
        "benchmark_id": "P-02-ITERATION-5-CORRECTED",
        "scenario_id": "P-02",
        "model_name": "qwen3.5:4b",
        "strategy": "best_overall_feasibility",
        "prompt_version": "shared_generator_v1",
        "baseline_path": "data/itineraries/baseline.json",
        "investigation_path": "tests/fixtures/investigation.json",
        "disruption_path": "tests/fixtures/disruption.json",
        "latency_seconds": 59.36,
        "input_tokens": 3541,
        "output_tokens": 1794,
        "structured_output_valid": True,
    }


@pytest.fixture
def evaluation_result():
    return {
        "scenario_id": "P-02",
        "proposal_id": "proposal-001",
        "deterministic_validation": {"status": "valid", "issues": []},
        "recovery_consistency": {"all_affected_activities_addressed": False},
        "schedule_comparison": {"removed_activities": []},
        "schedule_robustness": {"status": "complete"},
        "narrative_consistency": {"status": "inconsistent"},
    }


def test_build_deterministic_evaluation_record(
    generation_metadata,
    evaluation_result,
):
    record = build_deterministic_evaluation_record(
        evaluation_result=evaluation_result,
        generation_metadata=generation_metadata,
        raw_response_path="data/raw/P-02.json",
        generation_metadata_path="data/raw/P-02.metadata.json",
    )

    assert record["evaluation_version"] == "deterministic_eval_v1"
    assert record["benchmark"]["benchmark_id"] == (
        "P-02-ITERATION-5-CORRECTED"
    )
    assert record["benchmark"]["proposal_id"] == "proposal-001"
    assert record["generation"]["model_name"] == "qwen3.5:4b"
    assert record["results"]["narrative_consistency"]["status"] == (
        "inconsistent"
    )
    assert record["source_artifacts"]["raw_response_path"] == (
        "data/raw/P-02.json"
    )


def test_save_and_load_deterministic_evaluation(
    tmp_path,
    generation_metadata,
    evaluation_result,
):
    record = build_deterministic_evaluation_record(
        evaluation_result,
        generation_metadata,
        "data/raw/P-02.json",
        "data/raw/P-02.metadata.json",
    )

    output_path = tmp_path / "P-02.json"

    saved_path = save_deterministic_evaluation(output_path, record)
    loaded_record = load_deterministic_evaluation(saved_path)

    assert saved_path == output_path
    assert loaded_record == record


def test_existing_evaluation_result_is_not_overwritten(
    tmp_path,
    generation_metadata,
    evaluation_result,
):
    record = build_deterministic_evaluation_record(
        evaluation_result,
        generation_metadata,
        "data/raw/P-02.json",
        "data/raw/P-02.metadata.json",
    )

    output_path = tmp_path / "P-02.json"
    original_content = '{"original": true}'
    output_path.write_text(original_content, encoding="utf-8")

    with pytest.raises(FileExistsError):
        save_deterministic_evaluation(output_path, record)

    assert output_path.read_text(encoding="utf-8") == original_content


def test_load_missing_evaluation_result_raises_error(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_deterministic_evaluation(missing_path)


def test_saved_evaluation_is_valid_json(
    tmp_path,
    generation_metadata,
    evaluation_result,
):
    record = build_deterministic_evaluation_record(
        evaluation_result,
        generation_metadata,
        "data/raw/P-02.json",
        "data/raw/P-02.metadata.json",
    )

    output_path = tmp_path / "P-02.json"
    save_deterministic_evaluation(output_path, record)

    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded["evaluation_version"] == "deterministic_eval_v1"
