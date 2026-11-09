from src.models.itinerary import Itinerary
from src.models.validation import (ValidationResult, ValidationIssue, 
                                   ValidationStatus, IssueType)
from itertools import pairwise
from datetime import timedelta


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
    status = (ValidationStatus.INVALID if issues_lst else ValidationStatus.VALID)

    return ValidationResult(
        status=status,
        issues=issues_lst
    )


def get_selected_travel_estimate(
    itinerary: Itinerary,
    origin_activity_id: str,
    destination_activity_id: str) -> TravelEstimate | None:
    
    for leg in itinerary.travel_legs:
        if (origin_activity_id == leg.origin_activity_id
            and destination_activity_id == leg.destination_activity_id):
            for e in leg.estimates: 
                if leg.selected_mode == e.mode:
                    return e

    return None


def check_travel_time_feasibility(itinerary: Itinerary) -> ValidationResult:

    activities = sorted(itinerary.activities, key=lambda u: u.start_time)
    issues_lst = []

    for current_act, next_act in pairwise(activities):

        # Find the selected estimate using activity IDs
        estimate = get_selected_travel_estimate(itinerary, current_act.activity_id, next_act.activity_id)

        if estimate is None:
            issues_lst
        #   Append a ValidationIssue
        #   Continue to the next pair

        # Calculate arrival time using timedelta

        # If arrival time exceeds next activity start:
        #   Append a ValidationIssue

    # Determine final status based on all issues

    return ValidationResult(
        status=status,
        issues=issues_lst
    )

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


def validate_itinerary(itinerary: Itinerary) -> ValidationResult:

    result1 = check_travel_time_feasibility(itinerary)
    result2 = check_activity_overlaps(itinerary)

    issues = result1.issues + result2.issues

    if result1.status == ValidationStatus.INVALID or result2.status == ValidationStatus.INVALID: 
        status = ValidationStatus.INVALID
    elif result1.status == ValidationStatus.INCOMPLETE or result2.status == ValidationStatus.INCOMPLETE: 
        status = ValidationStatus.INCOMPLETE
    else:
        status = ValidationStatus.VALID
  
    return ValidationResult(
        status=status,
        issues=issues
    ) 


def check_travel_leg_integrity(itinerary: Itinerary) -> ValidationResult:

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

    return ValidationResult(
        status=status,
        issues=issues_lst
    )

