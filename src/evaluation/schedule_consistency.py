
from pydantic import BaseModel

from src.models.itinerary import Itinerary


class ScheduleConsistencyResult(BaseModel):
    no_activity_overlaps: bool
    travel_legs_complete: bool
    selected_travel_estimates_available: bool
    travel_time_fits_schedule: bool

    # True only when all required schedule data is available.
    validation_complete: bool

    # PASS, FAIL, or INCOMPLETE.
    status: str

    # Backward-compatible indicator: True only for PASS.
    passed: bool

    # Definite schedule violations.
    failures: list[str]

    # Missing information that prevents full validation.
    unresolved: list[str]


def evaluate_schedule_consistency(
    itinerary: Itinerary,
) -> ScheduleConsistencyResult:
    """
    Validate timing and travel-leg consistency in a proposed itinerary.

    Results distinguish:
    - PASS: Complete data and no schedule violations.
    - FAIL: One or more definite schedule violations.
    - INCOMPLETE: Missing data prevents full validation.

    Checks:
    1. Activities do not overlap.
    2. Every consecutive pair has a travel leg.
    3. Each leg has an estimate for its selected mode.
    4. Selected travel time fits between consecutive activities.
    """

    failures = []
    unresolved = []

    activities = sorted(
        itinerary.activities,
        key=lambda activity: activity.start_time,
    )

    no_activity_overlaps = True
    travel_legs_complete = True
    selected_travel_estimates_available = True
    travel_time_fits_schedule = True

    legs_by_pair = {
        (leg.origin_activity_id, leg.destination_activity_id): leg
        for leg in itinerary.travel_legs
    }

    # Check consecutive activities.
    for previous, current in zip(activities, activities[1:]):
        previous_end = previous.end_time

        # An activity overlap is a definite schedule violation.
        if current.start_time < previous_end:
            no_activity_overlaps = False

            failures.append(
                f"Activities overlap: '{previous.name}' and "
                f"'{current.name}'."
            )

            continue

        pair = (
            previous.activity_id,
            current.activity_id,
        )

        leg = legs_by_pair.get(pair)

        # Missing travel legs make schedule feasibility unresolved.
        if leg is None:
            travel_legs_complete = False

            unresolved.append(
                f"Missing travel leg between '{previous.name}' "
                f"and '{current.name}'."
            )

            continue

        selected_estimate = next(
            (
                estimate
                for estimate in leg.estimates
                if estimate.mode.casefold()
                == leg.selected_mode.casefold()
            ),
            None,
        )

        # Missing selected-mode estimates make feasibility unresolved.
        if selected_estimate is None:
            selected_travel_estimates_available = False

            unresolved.append(
                f"No {leg.selected_mode} estimate exists for travel "
                f"between '{previous.name}' and '{current.name}'."
            )

            continue

        available_minutes = (
            current.start_time - previous_end
        ).total_seconds() / 60

        # An estimate exceeding the available time is a definite violation.
        if selected_estimate.duration_minutes > available_minutes:
            travel_time_fits_schedule = False

            failures.append(
                f"Travel time does not fit between '{previous.name}' "
                f"and '{current.name}': "
                f"{selected_estimate.duration_minutes} minutes required, "
                f"{available_minutes:.1f} minutes available."
            )

    validation_complete = (
        travel_legs_complete
        and selected_travel_estimates_available
    )

    if failures:
        status = "FAIL"
    elif not validation_complete:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    return ScheduleConsistencyResult(
        no_activity_overlaps=no_activity_overlaps,
        travel_legs_complete=travel_legs_complete,
        selected_travel_estimates_available=(
            selected_travel_estimates_available
        ),
        travel_time_fits_schedule=travel_time_fits_schedule,
        validation_complete=validation_complete,
        status=status,
        passed=(status == "PASS"),
        failures=failures,
        unresolved=unresolved,
    )
