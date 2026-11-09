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


class ValidationIssue(BaseModel):
    issue_type: IssueType
    description: str
    activity_ids: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    status: ValidationStatus
    issues: List[ValidationIssue] = Field(default_factory=list)


ex = ValidationResult(
    status=ValidationStatus.INVALID,
    issues=[
        ValidationIssue(
            issue_type=IssueType.INSUFFICIENT_TRAVEL_TIME,
            description="Walking time exceeds the available gap between activities.",
            activity_ids=["activity_001", "activity_002"]
        ), 
        ValidationIssue(
            issue_type=IssueType.ACTIVITY_OVERLAP,
            description="Activity starts before the required travel time has elapsed.",
            activity_ids=["activity_002", "activity_003"]
        )
    ]
)

print(ex)