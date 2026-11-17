
from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EvaluationLevel(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class OverallResult(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


class LLMEvaluationRecord(BaseModel):
    evaluation_id: str
    model_name: str
    model_version: str
    scenario_id: str
    iteration: int = Field(ge=1)

    strategy: str | None = None
    prompt_version: str
    rubric_version: str = "2.0"

    criterion_results: dict[str, EvaluationLevel]

    overall_result: OverallResult
    failure_observations: list[str] = Field(default_factory=list)

    structured_output_valid: bool | None = None
    latency_seconds: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)

    raw_response_path: str | None = None

    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    deterministic_validation: dict | None = None
    schedule_comparison: dict | None = None
    schedule_robustness: dict | None = None
    recovery_consistency: dict | None = None
