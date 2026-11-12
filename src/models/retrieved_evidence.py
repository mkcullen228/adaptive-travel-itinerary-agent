from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class RetrievedEvidence(BaseModel):
    chunk_id: str
    content: str
    subject: str
    source_id: str
    source_url: HttpUrl
    retrieved_at: datetime
    similarity_distance: float = Field(ge=0)
