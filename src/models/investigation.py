from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.models.weather import WeatherDataResult
from src.models.retrieved_evidence import RetrievedEvidence
from src.models.evidence import EvidenceAssessment
from src.models.validation import ValidationResult


class InvestigationResult(BaseModel):
    investigation_id: str
    scenario_id: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    weather_result: WeatherDataResult | None = None
    retrieved_evidence: list[RetrievedEvidence] = Field(
        default_factory=list
    )
    evidence_assessments: list[EvidenceAssessment] = Field(
        default_factory=list
    )
    routing_validation: ValidationResult | None = None

    investigation_warnings: list[str] = Field(
        default_factory=list
    )
