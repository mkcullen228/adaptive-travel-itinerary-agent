from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from enum import Enum


class VerificationStatus(str, Enum):
    """Describes the verification state of information from a source."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    STALE = "stale"


class SourceReference(BaseModel):
    """Stores provenance and quality information for a data source.

    Tracks the source identity, retrieval timestamp, reliability score,
    and verification status of supporting information.

    source_id: str - Unique identifier for the source
    source_name: str - Name of the organization or source
    source_type: str - Government, official venue, API, etc.
    url: str - Link to the source
    retrieved_at: datetime - When the information was retrieved
    reliability: float - Reliability score from 0 to 1
    verification_status: enum - Whether the information has been verified
    """

    source_id: str
    source_name: str
    source_type: str
    url: HttpUrl
    retrieved_at: datetime
    reliability: float = Field(ge=0, le=1)
    verification_status: VerificationStatus
