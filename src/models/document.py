from pydantic import BaseModel
from datetime import datetime
from enum import Enum


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
