
from datetime import datetime
from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario, DisruptionType
from src.models.agent_workflow import RecoveryOption


def _local_time(value: datetime) -> datetime:
    """Compare local wall-clock times for a single-destination itinerary."""
    return value.replace(tzinfo=None)


def evaluate_recovery_consistency(
    original: Itinerary,
    scenario: DisruptionScenario,
    proposal: RecoveryOption,
) -> dict:
    proposed = proposal.proposed_itinerary

    original_by_id = {
        activity.activity_id: activity
        for activity in original.activities
    }
    proposed_by_id = {
        activity.activity_id: activity
        for activity in proposed.activities
    }

    affected_results = []

    for activity_id in scenario.affected_activity_ids:
        original_activity = original_by_id.get(activity_id)
        proposed_activity = proposed_by_id.get(activity_id)

        if original_activity is None:
            affected_results.append({
                "activity_id": activity_id,
                "status": "missing_from_original",
            })
            continue

        if proposed_activity is None:
            status = "removed"
        elif (
            scenario.scenario_type == DisruptionType.WEATHER
            and scenario.affected_time_start is not None
            and scenario.affected_time_end is not None
        ):
            start = _local_time(proposed_activity.start_time)
            end = _local_time(proposed_activity.end_time)
            disruption_start = _local_time(scenario.affected_time_start)
            disruption_end = _local_time(scenario.affected_time_end)

            overlaps = (
                start < disruption_end
                and end > disruption_start
            )

            if overlaps:
                status = "retained_during_disruption"
            elif start != _local_time(original_activity.start_time):
                status = "rescheduled_outside_disruption"
            else:
                status = "unchanged_outside_disruption"
        else:
            status = "retained"

        affected_results.append({
            "activity_id": activity_id,
            "status": status,
        })

    mandatory_results = []

    for activity in original.activities:
        if not activity.mandatory:
            continue

        proposed_activity = proposed_by_id.get(activity.activity_id)

        mandatory_results.append({
            "activity_id": activity.activity_id,
            "preserved": proposed_activity is not None,
        })

    removed = [
        activity_id
        for activity_id in original_by_id
        if activity_id not in proposed_by_id
    ]

    added = [
        activity_id
        for activity_id in proposed_by_id
        if activity_id not in original_by_id
    ]

    rescheduled = []

    for activity_id in original_by_id.keys() & proposed_by_id.keys():
        original_time = _local_time(
            original_by_id[activity_id].start_time
        )
        proposed_time = _local_time(
            proposed_by_id[activity_id].start_time
        )

        if original_time != proposed_time:
            rescheduled.append(activity_id)

    unresolved_affected = [
        item["activity_id"]
        for item in affected_results
        if item["status"] in {
            "retained_during_disruption",
            "missing_from_original",
        }
    ]

    return {
        "affected_activities": affected_results,
        "mandatory_activities": mandatory_results,
        "removed_activity_ids": removed,
        "added_activity_ids": added,
        "rescheduled_activity_ids": sorted(rescheduled),
        "unresolved_affected_activity_ids": unresolved_affected,
        "all_mandatory_activities_preserved": all(
            item["preserved"] for item in mandatory_results
        ),
        "all_affected_activities_addressed": (
            len(unresolved_affected) == 0
            and len(affected_results) > 0
        ),
    }
