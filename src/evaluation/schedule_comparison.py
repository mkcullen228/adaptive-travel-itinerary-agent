
from src.models.itinerary import Itinerary


def _local_time_difference_minutes(original_start, proposed_start) -> int:
    """
    Compare local wall-clock times.

    Timezone information is removed for comparison because both
    itineraries represent the same destination and local schedule.
    The original datetime values are not modified.
    """
    original_local = original_start.replace(tzinfo=None)
    proposed_local = proposed_start.replace(tzinfo=None)

    return int(
        (proposed_local - original_local).total_seconds() / 60
    )


def compare_itineraries(
    original: Itinerary,
    proposed: Itinerary
) -> dict:
    """
    Compare original and proposed itineraries without modifying either.
    Activities are matched by activity_id.
    """

    original_ids_list = [
        activity.activity_id for activity in original.activities
    ]
    proposed_ids_list = [
        activity.activity_id for activity in proposed.activities
    ]

    if len(original_ids_list) != len(set(original_ids_list)):
        raise ValueError(
            "Original itinerary contains duplicate activity IDs."
        )

    if len(proposed_ids_list) != len(set(proposed_ids_list)):
        raise ValueError(
            "Proposed itinerary contains duplicate activity IDs."
        )

    original_activities = {
        activity.activity_id: activity
        for activity in original.activities
    }

    proposed_activities = {
        activity.activity_id: activity
        for activity in proposed.activities
    }

    original_ids = set(original_activities)
    proposed_ids = set(proposed_activities)

    retained = []
    rescheduled = []

    for activity_id in sorted(original_ids & proposed_ids):
        original_activity = original_activities[activity_id]
        proposed_activity = proposed_activities[activity_id]

        difference = _local_time_difference_minutes(
            original_activity.start_time,
            proposed_activity.start_time
        )

        if difference == 0:
            retained.append(activity_id)
        else:
            rescheduled.append({
                "activity_id": activity_id,
                "original_start": (
                    original_activity.start_time.isoformat()
                ),
                "proposed_start": (
                    proposed_activity.start_time.isoformat()
                ),
                "change_minutes": difference
            })

    return {
        "retained_activities": retained,
        "removed_activities": sorted(original_ids - proposed_ids),
        "added_activities": sorted(proposed_ids - original_ids),
        "rescheduled_activities": rescheduled
    }
