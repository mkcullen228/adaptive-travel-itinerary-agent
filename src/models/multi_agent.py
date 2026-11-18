
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from src.models.evidence import EvidenceStatus


class AuditAssessment(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    INCONCLUSIVE = "inconclusive"


class EvidenceFinding(BaseModel):
    """Researcher's interpretation of one evidence-based claim."""

    claim: str
    status: EvidenceStatus
    supporting_source_ids: list[str] = Field(default_factory=list)
    conflicting_source_ids: list[str] = Field(default_factory=list)
    explanation: str
    source_quality_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_references(self):
        if self.status == EvidenceStatus.UNSUPPORTED:
            if self.supporting_source_ids or self.conflicting_source_ids:
                raise ValueError(
                    "Unsupported findings cannot identify supporting "
                    "or conflicting sources."
                )

        if self.status == EvidenceStatus.SUPPORTED:
            if not self.supporting_source_ids:
                raise ValueError(
                    "Supported findings must identify supporting sources."
                )
            if self.conflicting_source_ids:
                raise ValueError(
                    "Supported findings cannot identify conflicting sources."
                )

        if self.status == EvidenceStatus.CONFLICTING:
            if not self.supporting_source_ids or not self.conflicting_source_ids:
                raise ValueError(
                    "Conflicting findings must identify both supporting "
                    "and conflicting sources."
                )

        return self


class EvidenceBrief(BaseModel):
    """Structured output from the Context and Disruption Researcher."""

    findings: list[EvidenceFinding] = Field(default_factory=list)
    disruption_implications: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    source_ids_reviewed: list[str] = Field(default_factory=list)
    overall_uncertainties: list[str] = Field(default_factory=list)


class AuditReport(BaseModel):
    """Structured output from the Validation and Evidence Auditor."""

    assessment: AuditAssessment
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    conflicting_claims: list[str] = Field(default_factory=list)
    omitted_uncertainties: list[str] = Field(default_factory=list)
    rationale_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
