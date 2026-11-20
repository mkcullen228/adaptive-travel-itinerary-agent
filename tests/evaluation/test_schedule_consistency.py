
from datetime import date, datetime

from src.evaluation.schedule_consistency import (
    evaluate_schedule_consistency,
)
from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.travel import TravelEstimate, TravelLeg


def make_activity(activity_id, name, start_hour, duration_minutes):
    return Activity(
        activity_id=activity_id,
        name=name,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, start_hour, 0),
        duration_minutes=duration_minutes,
    )


def make_travel_leg(
    origin_id,
    destination_id,
    duration_minutes=10,
    selected_mode="walking",
):
    return TravelLeg(
        origin_activity_id=origin_id,
        destination_activity_id=destination_id,
        estimates=[
            TravelEstimate(
                mode="walking",
                duration_minutes=duration_minutes,
                duration_seconds=duration_minutes * 60,
                distance_meters=500,
                source="test_fixture",
            )
        ],
        selected_mode=selected_mode,
    )


def make_itinerary(activities, travel_legs=None):
    return Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities,
        travel_legs=travel_legs or [],
    )


def test_valid_schedule_passes():
    activities = [
        make_activity("a", "Activity A", 9, 50),
        make_activity("b", "Activity B", 10, 60),
    ]

    itinerary = make_itinerary(
        activities,
        [
            make_travel_leg("a", "b", duration_minutes=10),
        ],
    )

    result = evaluate_schedule_consistency(itinerary)

    assert result.passed is True
    assert result.no_activity_overlaps is True
    assert result.travel_legs_complete is True
    assert result.selected_travel_estimates_available is True
    assert result.travel_time_fits_schedule is True


def test_overlapping_activities_fail():
    activities = [
        make_activity("a", "Activity A", 9, 90),
        make_activity("b", "Activity B", 10, 60),
    ]

    itinerary = make_itinerary(activities)

    result = evaluate_schedule_consistency(itinerary)

    assert result.passed is False
    assert result.no_activity_overlaps is False


def test_missing_travel_leg_fails():
    activities = [
        make_activity("a", "Activity A", 9, 60),
        make_activity("b", "Activity B", 10, 60),
    ]

    itinerary = make_itinerary(activities)

    result = evaluate_schedule_consistency(itinerary)

    assert result.passed is False
    assert result.travel_legs_complete is False


def test_missing_selected_mode_estimate_fails():
    activities = [
        make_activity("a", "Activity A", 9, 60),
        make_activity("b", "Activity B", 10, 60),
    ]

    leg = TravelLeg(
        origin_activity_id="a",
        destination_activity_id="b",
        estimates=[
            TravelEstimate(
                mode="driving",
                duration_minutes=5,
                duration_seconds=300,
                distance_meters=1000,
                source="test_fixture",
            )
        ],
        selected_mode="walking",
    )

    itinerary = make_itinerary(activities, [leg])

    result = evaluate_schedule_consistency(itinerary)

    assert result.passed is False
    assert result.selected_travel_estimates_available is False


def test_travel_time_exceeding_available_gap_fails():
    activities = [
        make_activity("a", "Activity A", 9, 60),
        make_activity("b", "Activity B", 10, 60),
    ]

    itinerary = make_itinerary(
        activities,
        [
            make_travel_leg("a", "b", duration_minutes=15),
        ],
    )

    result = evaluate_schedule_consistency(itinerary)

    assert result.passed is False
    assert result.travel_time_fits_schedule is False
