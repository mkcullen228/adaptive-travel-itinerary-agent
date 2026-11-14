from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RoutingFailure(BaseModel):
    origin_activity_id: str
    destination_activity_id: str
    requested_mode: str
    failure_reason: str
    attempted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
