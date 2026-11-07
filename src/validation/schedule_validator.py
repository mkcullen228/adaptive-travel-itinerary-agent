from src.models.itinerary import Itinerary
from src.models.validation import (
    ValidationResult,
    ValidationIssue,
    ValidationStatus,
    IssueType
)


def check_activity_overlaps(itinerary: Itinerary) -> ValidationResult:
    """Check whether consecutive activities overlap."""

    # Sort activities by start_time
    activities = sorted(itinerary.activities, key=lambda u: u.start_time)
    
    # Create an empty list to collect issues
    issues_lst = []

    # Compare each activity with the next activity
    for i in range(len(activities) - 1):
        current_activity = activities[i]
        next_activity = activities[i + 1]
        
        # If they overlap, create a ValidationIssue
        if current_activity.end_time > next_activity.start_time:
            issues_lst.append(
                ValidationIssue(
                    issue_type=IssueType.ACTIVITY_OVERLAP,
                    description="The second activity starts before the first activity has ended.",
                    activity_ids=[current_activity.activity_id, next_activity.activity_id]
                    )
                )

    # 5. Return a ValidationResult
    status = (
        ValidationStatus.INVALID if issues_lst else ValidationStatus.VALID
    )

    return ValidationResult(
        status=status,
        issues=issues_lst
    )
