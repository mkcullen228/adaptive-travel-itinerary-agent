from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from src.models.source_reference import VerificationStatus


class IngestionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class DocumentIngestionResult(BaseModel):
    source_id: str
    url: str
    retrieval_status: IngestionStatus
    http_status_code: int | None = None
    extraction_status: IngestionStatus | None = None
    retrieved_at: datetime
    error_message: str | None = None
    content: str | None = None

    # Venue source metadata
    venue_id: str | None = None
    subject: str | None = None
    reliability: float | None = Field(default=None, ge=0, le=1)
    verification_status: VerificationStatus | None = None
