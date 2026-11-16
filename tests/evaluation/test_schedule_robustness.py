
from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.travel import TravelEstimate, TravelLeg
from src.evaluation.schedule_robustness import (
    calculate_schedule_robustness
)


def make_activity(activity_id, hour, minute=0):
    return Activity(
        activity_id=activity_id,
        name=activity_id,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, hour, minute),
        duration_minutes=60
    )


def make_itinerary(activities, travel_minutes=None):
    if travel_minutes is None:
        travel_minutes = 5

    travel_legs = []

    for current, following in zip(
        activities, activities[1:]
    ):
        travel_legs.append(
            TravelLeg(
                origin_activity_id=current.activity_id,
                destination_activity_id=following.activity_id,
                estimates=[
                    TravelEstimate(
                        mode="walking",
                        duration_minutes=travel_minutes,
                        duration_seconds=travel_minutes * 60,
                        distance_meters=500,
                        source="test"
                    )
                ],
                selected_mode="walking"
            )
        )

    return Itinerary(
        itinerary_id="test",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities,
        travel_legs=travel_legs
    )


def test_calculates_schedule_slack():
    itinerary = make_itinerary(
        [
            make_activity("activity_a", 9),
            make_activity("activity_b", 10, 20)
        ],
        travel_minutes=5
    )

    result = calculate_schedule_robustness(itinerary)

    assert result["minimum_slack_minutes"] == 15
    assert result["average_slack_minutes"] == 15
    assert result["infeasible_leg_count"] == 0


def test_identifies_low_slack():
    itinerary = make_itinerary(
        [
            make_activity("activity_a", 9),
            make_activity("activity_b", 10, 7)
        ],
        travel_minutes=5
    )

    result = calculate_schedule_robustness(itinerary)

    assert result["minimum_slack_minutes"] == 2
    assert result["low_slack_leg_count"] == 1


def test_identifies_infeasible_transition():
    itinerary = make_itinerary(
        [
            make_activity("activity_a", 9),
            make_activity("activity_b", 10, 3)
        ],
        travel_minutes=5
    )

    result = calculate_schedule_robustness(itinerary)

    assert result["minimum_slack_minutes"] == -2
    assert result["infeasible_leg_count"] == 1


def test_missing_travel_estimate():
    activities = [
        make_activity("activity_a", 9),
        make_activity("activity_b", 10)
    ]

    itinerary = Itinerary(
        itinerary_id="test",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities
    )

    result = calculate_schedule_robustness(itinerary)

    assert result["status"] == "incomplete"
    assert result["missing_estimate_count"] == 1
    assert result["minimum_slack_minutes"] is None


def test_multiple_legs_calculate_average_slack():
    activities = [
        make_activity("activity_a", 9),
        make_activity("activity_b", 10, 20),
        make_activity("activity_c", 12)
    ]

    itinerary = make_itinerary(activities, travel_minutes=5)

    result = calculate_schedule_robustness(itinerary)

    assert result["minimum_slack_minutes"] == 15
    assert result["average_slack_minutes"] == 25
