
from itertools import pairwise

from src.models.itinerary import Itinerary
from src.validation.schedule_validator import (
    get_selected_travel_estimate
)


def calculate_schedule_robustness(
    itinerary: Itinerary,
    low_slack_threshold_minutes: int = 5
) -> dict:
    """
    Calculate available schedule slack between consecutive activities.

    Slack = Available time gap - Selected travel estimate.

    Negative slack indicates an infeasible transition.
    Missing estimates are reported separately and excluded
    from aggregate slack calculations.

    Time comparisons use local wall-clock times, consistent
    with the MVP's single-destination itinerary scope.
    """

    if low_slack_threshold_minutes < 0:
        raise ValueError(
            "Low slack threshold cannot be negative."
        )

    activities = sorted(
        itinerary.activities,
        key=lambda activity: activity.start_time
    )

    leg_results = []
    measured_slacks = []

    for current_activity, next_activity in pairwise(activities):

        # Retrieve the selected transportation estimate.
        estimate = get_selected_travel_estimate(
            itinerary,
            current_activity.activity_id,
            next_activity.activity_id
        )

        # Calculate available time using local wall-clock times.
        current_end = current_activity.end_time.replace(
            tzinfo=None
        )
        next_start = next_activity.start_time.replace(
            tzinfo=None
        )

        available_gap = int(
            (next_start - current_end).total_seconds() / 60
        )

        # Cannot calculate slack without a travel estimate.
        if estimate is None:
            leg_results.append({
                "origin_activity_id": current_activity.activity_id,
                "destination_activity_id": next_activity.activity_id,
                "available_gap_minutes": available_gap,
                "travel_duration_minutes": None,
                "slack_minutes": None,
                "selected_mode": None,
                "travel_source": None,
                "status": "missing_estimate"
            })
            continue

        slack = available_gap - estimate.duration_minutes
        measured_slacks.append(slack)

        if slack < 0:
            status = "infeasible"
        elif slack < low_slack_threshold_minutes:
            status = "low_slack"
        else:
            status = "feasible"

        leg_results.append({
            "origin_activity_id": current_activity.activity_id,
            "destination_activity_id": next_activity.activity_id,
            "available_gap_minutes": available_gap,
            "travel_duration_minutes": estimate.duration_minutes,
            "slack_minutes": slack,
            "selected_mode": estimate.mode,
            "travel_source": estimate.source,
            "status": status
        })

    # Aggregate metrics only from legs with known estimates.
    if measured_slacks:
        minimum_slack = min(measured_slacks)
        average_slack = round(
            sum(measured_slacks) / len(measured_slacks), 2
        )
    else:
        minimum_slack = None
        average_slack = None

    return {
        "status": (
            "incomplete"
            if any(
                leg["status"] == "missing_estimate"
                for leg in leg_results
            )
            else "complete"
        ),
        "minimum_slack_minutes": minimum_slack,
        "average_slack_minutes": average_slack,
        "low_slack_leg_count": sum(
            slack < low_slack_threshold_minutes
            for slack in measured_slacks
            if slack >= 0
        ),
        "infeasible_leg_count": sum(
            slack < 0 for slack in measured_slacks
        ),
        "missing_estimate_count": sum(
            leg["status"] == "missing_estimate"
            for leg in leg_results
        ),
        "legs": leg_results
    }
