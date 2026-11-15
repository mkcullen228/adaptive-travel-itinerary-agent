from src.models.llm_evaluation import (
    EvaluationLevel,
    OverallResult,
    LLMEvaluationRecord,
)


def test_valid_evaluation_record():
    record = LLMEvaluationRecord(
        evaluation_id="QWEN-P01-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="v1",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS,
            "evidence_grounding": EvaluationLevel.PARTIAL,
        },
        overall_result=OverallResult.PARTIAL,
    )

    assert record.scenario_id == "P-01"
    assert record.overall_result == OverallResult.PARTIAL


def test_evaluation_metrics_can_be_missing():
    record = LLMEvaluationRecord(
        evaluation_id="QWEN-P01-002",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=2,
        prompt_version="v2",
        criterion_results={
            "constraint_adherence": EvaluationLevel.PASS,
        },
        overall_result=OverallResult.PASS,
    )

    assert record.latency_seconds is None
    assert record.estimated_cost is None


def test_invalid_iteration_is_rejected():
    from pydantic import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        LLMEvaluationRecord(
            evaluation_id="INVALID",
            model_name="qwen3.5:4b",
            model_version="4b",
            scenario_id="P-01",
            iteration=0,
            prompt_version="v1",
            criterion_results={},
            overall_result=OverallResult.FAIL,
        )
