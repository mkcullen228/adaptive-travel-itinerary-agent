from enum import Enum
from typing import List

from pydantic import BaseModel, Field, model_validator


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting"


class EvidenceRelevance(str, Enum):
    RELEVANT = "relevant"
    PARTIALLY_RELEVANT = "partially_relevant"
    IRRELEVANT = "irrelevant"


class EvidenceCoverage(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NONE = "none"


class EvidenceAssessment(BaseModel):
    claim: str
    status: EvidenceStatus
    relevance: EvidenceRelevance
    coverage: EvidenceCoverage
    source_quality_assessed: bool = False
    consistency_assessed: bool = False
    supporting_source_ids: List[str] = Field(default_factory=list)
    conflicting_source_ids: List[str] = Field(default_factory=list)
    explanation: str
    

    @model_validator(mode="after")
    def validate_supporting_sources(self):
        if self.status == EvidenceStatus.UNSUPPORTED:
            if self.supporting_source_ids:
                raise ValueError(
                    "Unsupported evidence cannot have supporting source IDs."
                )

            if self.conflicting_source_ids:
                raise ValueError(
                    "Unsupported evidence cannot have conflicting source IDs."
                )

        if self.status == EvidenceStatus.SUPPORTED:
            if not self.supporting_source_ids:
                raise ValueError(
                    "Supported evidence must have at least one "
                    "supporting source ID."
                )
            if self.conflicting_source_ids:
                raise ValueError(
                    "Supported evidence cannot have conflicting source IDs."
                )

        if self.status == EvidenceStatus.CONFLICTING:
            if not self.supporting_source_ids or not self.conflicting_source_ids:
                raise ValueError(
                    "Conflicting evidence must identify both supporting "
                    "and conflicting sources."
                )

        return self

