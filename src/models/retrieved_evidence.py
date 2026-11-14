from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from src.models.source_reference import VerificationStatus


class RetrievedEvidence(BaseModel):
    chunk_id: str
    content: str
    subject: str
    source_id: str
    source_url: HttpUrl
    retrieved_at: datetime
    similarity_distance: float = Field(ge=0)
    reliability: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    verification_status: VerificationStatus
