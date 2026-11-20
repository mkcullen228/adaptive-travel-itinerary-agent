from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"


class IssueType(str, Enum):
    INSUFFICIENT_TRAVEL_TIME = "insufficient_travel_time"
    ACTIVITY_OVERLAP = "activity_overlap"
    MISSING_TRAVEL_ESTIMATE = "missing_travel_estimate"
    ORPHANED_TRAVEL_LEG = "orphaned_travel_leg"
    DUPLICATE_TRAVEL_LEG = "duplicate_travel_leg"
    MANDATORY_ACTIVITY_NOT_PRESERVED = "mandatory_activity_not_preserved"


class ValidationIssue(BaseModel):
    issue_type: IssueType
    description: str
    activity_ids: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    status: ValidationStatus
    issues: List[ValidationIssue] = Field(default_factory=list)
