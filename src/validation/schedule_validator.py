from src.models.itinerary import Itinerary
from src.models.validation import (ValidationResult, ValidationIssue, 
                                   ValidationStatus, IssueType)
from itertools import pairwise
from datetime import timedelta


def check_activity_overlaps(itinerary: Itinerary) -> ValidationResult:
    """Check whether scheduled activities overlap.

    Sorts activities chronologically and compares consecutive activities
    to identify overlapping time windows. Activities that end exactly
    when the next activity begins are considered valid.

    Args:
        itinerary: The itinerary containing scheduled activities.

    Returns:
        ValidationResult: VALID if no overlaps are found; otherwise
        INVALID with the identified overlap issues.
    """

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
    status = (ValidationStatus.INVALID if issues_lst else ValidationStatus.VALID)

    return ValidationResult(status=status, issues=issues_lst)


def get_selected_travel_estimate(
    itinerary: Itinerary,
    origin_activity_id: str,
    destination_activity_id: str) -> TravelEstimate | None:
    """Retrieve the travel estimate matching the selected mode.

    Searches the itinerary's travel legs for the specified origin and
    destination activities, then returns the estimate matching the
    selected transportation mode.

    Args:
        itinerary: The itinerary containing travel legs and estimates.
        origin_activity_id: ID of the activity where travel begins.
        destination_activity_id: ID of the activity where travel ends.

    Returns:
        TravelEstimate | None: The matching estimate, or None if no
        matching travel leg or selected-mode estimate exists.
    """

    for leg in itinerary.travel_legs:
        if (origin_activity_id == leg.origin_activity_id
            and destination_activity_id == leg.destination_activity_id):
            for e in leg.estimates: 
                if leg.selected_mode == e.mode:
                    return e

    return None



from datetime import timedelta
from itertools import pairwise

from src.models.validation import (
    ValidationStatus,
    IssueType,
    ValidationIssue,
    ValidationResult,
)


def check_travel_time_feasibility(itinerary: Itinerary) -> ValidationResult:
    """Determine whether sufficient time exists between activities for travel.

    Compares the selected travel estimate between consecutive activities
    against the available time between the end of one activity and the
    start of the next.

    Missing travel estimates result in INCOMPLETE validation because
    feasibility cannot be determined without the required information.

    Args:
        itinerary: The itinerary containing activities and travel legs.

    Returns:
        ValidationResult: INVALID if travel time is insufficient,
        INCOMPLETE if required estimates are missing, or VALID if all
        travel transitions are feasible.
    """
    issues_lst = []

    # Sort activities chronologically
    sorted_activities = sorted(
        itinerary.activities,
        key=lambda activity: activity.start_time
    )

    # Compare each consecutive pair of activities
    for current_act, next_act in pairwise(sorted_activities):

        # Retrieve the travel estimate matching the selected mode
        estimate = get_selected_travel_estimate(
            itinerary,
            current_act.activity_id,
            next_act.activity_id
        )

        # Missing estimate means feasibility cannot be determined
        if estimate is None:
            validation_issue = ValidationIssue(
                issue_type=IssueType.MISSING_TRAVEL_ESTIMATE,
                description=(
                    "Missing selected travel estimate between "
                    "consecutive activities."
                ),
                activity_ids=[
                    current_act.activity_id,
                    next_act.activity_id
                ]
            )
            issues_lst.append(validation_issue)
            continue

        # Calculate arrival time after completing the current activity
        arrival_time = current_act.end_time + timedelta(
            minutes=estimate.duration_minutes
        )

        # Check whether travel can be completed before the next activity
        if arrival_time > next_act.start_time:
            validation_issue = ValidationIssue(
                issue_type=IssueType.INSUFFICIENT_TRAVEL_TIME,
                description=(
                    "Insufficient time to travel between consecutive "
                    "activities using the selected transportation mode."
                ),
                activity_ids=[
                    current_act.activity_id,
                    next_act.activity_id
                ]
            )
            issues_lst.append(validation_issue)

    # Determine overall validation status
    if any(
        issue.issue_type == IssueType.INSUFFICIENT_TRAVEL_TIME
        for issue in issues_lst
    ):
        status = ValidationStatus.INVALID

    elif any(
        issue.issue_type == IssueType.MISSING_TRAVEL_ESTIMATE
        for issue in issues_lst
    ):
        status = ValidationStatus.INCOMPLETE

    else:
        status = ValidationStatus.VALID

    return ValidationResult(status=status, issues=issues_lst)


def check_travel_time_feasibility(itinerary: Itinerary) -> ValidationResult:

    # Sort activities chronologically.
    activities = sorted(itinerary.activities, key=lambda u: u.start_time)

    # Iterate through consecutive activity pairs.
    issues_lst = []
    for current_act, next_act in pairwise(activities):
        # Use get_selected_travel_estimate() to find the relevant travel estimate.
        estimate = get_selected_travel_estimate(itinerary, current_act.activity_id, next_act.activity_id)

        # If no estimate exists, create a MISSING_TRAVEL_ESTIMATE issue.
        if estimate is None:
            validation_issue = ValidationIssue(
                issue_type=IssueType.MISSING_TRAVEL_ESTIMATE,
                description="No travel estimate exists for the selected mode.",
                activity_ids=[
                    current_act.activity_id,
                    next_act.activity_id
                ]
            )
            issues_lst.append(validation_issue)
        else:
            # If an estimate exists, calculate whether there is enough time to travel.
            arrival_time = current_act.end_time + timedelta(minutes=estimate.duration_minutes)
            if arrival_time > next_act.start_time:
                # If there isn't enough time, create an INSUFFICIENT_TRAVEL_TIME issue.
                validation_issue = ValidationIssue(
                    issue_type=IssueType.INSUFFICIENT_TRAVEL_TIME,
                    description="Not enough travel time between activities",
                    activity_ids=[
                        current_act.activity_id,
                        next_act.activity_id
                    ]
                )
                issues_lst.append(validation_issue)

    if any(issue.issue_type == IssueType.INSUFFICIENT_TRAVEL_TIME for issue in issues_lst):
        status = ValidationStatus.INVALID
    elif any(issue.issue_type == IssueType.MISSING_TRAVEL_ESTIMATE for issue in issues_lst):
        status = ValidationStatus.INCOMPLETE
    else:
        status = ValidationStatus.VALID
    
    return ValidationResult(
        status=status,
        issues=issues_lst
    )


def check_travel_leg_integrity(itinerary: Itinerary) -> ValidationResult:
    """Check the structural integrity of itinerary travel legs.

    Identifies travel legs that reference nonexistent activities and
    duplicate directed travel-leg pairs.

    Args:
        itinerary: The itinerary containing activities and travel legs.

    Returns:
        ValidationResult: INVALID if orphaned or duplicate travel legs
        are found; otherwise VALID.
    """

    issues_lst = []

    # Build a set of valid activity IDs.
    activity_ids = {
        activity.activity_id for activity in itinerary.activities
    }

    # Check for orphaned travel legs.
    for leg in itinerary.travel_legs:

        if (leg.origin_activity_id not in activity_ids
            or leg.destination_activity_id not in activity_ids):

            validation_issue = ValidationIssue(
                issue_type=IssueType.ORPHANED_TRAVEL_LEG,
                description="The travel leg references an activity that does not exist in the itinerary.",
                activity_ids=[
                    leg.origin_activity_id,
                    leg.destination_activity_id
                ]
            )
            issues_lst.append(validation_issue)

    # Check for duplicate travel legs.
    seen_pairs = set()

    for leg in itinerary.travel_legs:

        pair = (
            leg.origin_activity_id,
            leg.destination_activity_id
        )

        if pair in seen_pairs:
            validation_issue = ValidationIssue(
                issue_type=IssueType.DUPLICATE_TRAVEL_LEG,
                description="Duplicate travel leg found for the same origin and destination.",
                activity_ids=[
                    leg.origin_activity_id,
                    leg.destination_activity_id
                ]
            )
            issues_lst.append(validation_issue)

        else:
            seen_pairs.add(pair)

    # Determine validation status.
    status = (
        ValidationStatus.INVALID
        if issues_lst
        else ValidationStatus.VALID
    )

    return ValidationResult(status=status, issues=issues_lst)


def validate_itinerary(itinerary: Itinerary) -> ValidationResult:
    """Perform comprehensive validation of an itinerary.

    Combines activity overlap, travel-time feasibility, and travel-leg
    integrity checks into a single validation result.

    INVALID takes precedence over INCOMPLETE, which takes precedence
    over VALID, ensuring that all identified issues are retained while
    the overall status reflects the most severe finding.

    Args:
        itinerary: The itinerary to validate.

    Returns:
        ValidationResult: Combined validation status and all identified
        issues.
    """

    result1 = check_travel_time_feasibility(itinerary)
    result2 = check_activity_overlaps(itinerary)
    result3 = check_travel_leg_integrity(itinerary)

    results = [result1, result2, result3]
    issues = result1.issues + result2.issues + result3.issues
    # for r in results:
    #     issues.append(r.issues)

    if any(r.status == ValidationStatus.INVALID for r in results): 
        status = ValidationStatus.INVALID
    elif any(r.status == ValidationStatus.INCOMPLETE for r in results): 
        status = ValidationStatus.INCOMPLETE
    else:
        status = ValidationStatus.VALID
  
    return ValidationResult(status=status, issues=issues)
