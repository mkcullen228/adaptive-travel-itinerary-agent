
from datetime import date, datetime

import pytest

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.evaluation.schedule_comparison import compare_itineraries


def make_activity(activity_id, hour, minute=0):
    return Activity(
        activity_id=activity_id,
        name=activity_id,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, hour, minute),
        duration_minutes=60
    )


def make_itinerary(activities):
    return Itinerary(
        itinerary_id="test",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities
    )


def test_unchanged_itineraries():
    original = make_itinerary([
        make_activity("museum_a", 9),
        make_activity("museum_b", 11)
    ])

    proposed = make_itinerary([
        make_activity("museum_a", 9),
        make_activity("museum_b", 11)
    ])

    result = compare_itineraries(original, proposed)

    assert result["retained_activities"] == [
        "museum_a", "museum_b"
    ]
    assert result["removed_activities"] == []
    assert result["added_activities"] == []
    assert result["rescheduled_activities"] == []


def test_activity_removed():
    original = make_itinerary([
        make_activity("museum_a", 9),
        make_activity("museum_b", 11)
    ])

    proposed = make_itinerary([
        make_activity("museum_b", 11)
    ])

    result = compare_itineraries(original, proposed)

    assert result["removed_activities"] == ["museum_a"]


def test_activity_added():
    original = make_itinerary([
        make_activity("museum_a", 9)
    ])

    proposed = make_itinerary([
        make_activity("museum_a", 9),
        make_activity("memorial", 11)
    ])

    result = compare_itineraries(original, proposed)

    assert result["added_activities"] == ["memorial"]


def test_activity_rescheduled():
    original = make_itinerary([
        make_activity("museum_a", 9)
    ])

    proposed = make_itinerary([
        make_activity("museum_a", 10, 30)
    ])

    result = compare_itineraries(original, proposed)

    assert result["rescheduled_activities"] == [{
        "activity_id": "museum_a",
        "original_start": "2026-11-07T09:00:00",
        "proposed_start": "2026-11-07T10:30:00",
        "change_minutes": 90
    }]


def test_original_itinerary_is_not_modified():
    original = make_itinerary([
        make_activity("museum_a", 9)
    ])

    original_start = original.activities[0].start_time

    proposed = make_itinerary([
        make_activity("museum_a", 10)
    ])

    compare_itineraries(original, proposed)

    assert original.activities[0].start_time == original_start


def test_duplicate_activity_ids_are_rejected():
    original = make_itinerary([
        make_activity("museum_a", 9),
        make_activity("museum_a", 11)
    ])

    proposed = make_itinerary([
        make_activity("museum_a", 9)
    ])

    with pytest.raises(ValueError, match="duplicate activity IDs"):
        compare_itineraries(original, proposed)


def test_timezone_aware_and_naive_times_compare_as_local_times():
    original = make_itinerary([
        make_activity("museum_a", 9)
    ])

    proposed_activity = Activity(
        activity_id="museum_a",
        name="museum_a",
        location="Washington, DC",
        start_time=datetime.fromisoformat(
            "2026-11-07T09:00:00-05:00"
        ),
        duration_minutes=60
    )

    proposed = make_itinerary([proposed_activity])

    result = compare_itineraries(original, proposed)

    assert result["retained_activities"] == ["museum_a"]
    assert result["rescheduled_activities"] == []
