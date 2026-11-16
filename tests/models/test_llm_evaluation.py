from src.models.llm_evaluation import (
    EvaluationLevel,
    LLMEvaluationRecord,
    OverallResult
)


def test_not_applicable_evaluation_level():
    assert EvaluationLevel.NOT_APPLICABLE.value == "not_applicable"


def test_default_rubric_version():
    record = LLMEvaluationRecord(
        evaluation_id="test-001",
        model_name="qwen3.5:4b",
        model_version="4b",
        scenario_id="P-01",
        iteration=1,
        prompt_version="p01-v1",
        criterion_results={
            "mandatory_constraint_preservation": EvaluationLevel.PASS
        },
        overall_result=OverallResult.PASS
    )

    assert record.rubric_version == "2.0"
