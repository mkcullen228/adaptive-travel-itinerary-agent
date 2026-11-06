import pytest
from pydantic import ValidationError
from datetime import datetime

from src.models.activity import Activity


def test_valid_activity():
    # Create a museum activity
    t = Activity(
        activity_id="activity_001",
        name="Activity Name",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=124,
        mandatory=False,
        indoor=True
    )
    
    # Assert the name and duration
    assert t.name == "Activity Name"
    assert t.duration_minutes == 124


def test_activity_end_time():
    # Create an activity starting at 10:00
    # Duration is 90 minutes
    # Assert end time is 11:30
    t = Activity(
        activity_id="activity_001",
        name="Activity Name",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=False,
        indoor=True
    )

    assert t.end_time == datetime(2026, 11, 7, 11, 30)


def test_negative_activity_duration_rejected():
    # Create an activity with a negative duration
    # Assert ValidationError
    with pytest.raises(ValidationError):
        Activity(
            activity_id="activity_001",
            name="Activity Name",
            location="Washington, DC",
            start_time=datetime(2026, 11, 7, 10, 0),
            duration_minutes=-500,
            mandatory=False,
            indoor=True
        )


def test_zero_activity_duration_rejected():
    # Create an activity with a negative duration
    # Assert ValidationError
    with pytest.raises(ValidationError):
        Activity(
            activity_id="activity_001",
            name="Activity Name",
            location="Washington, DC",
            start_time=datetime(2026, 11, 7, 10, 0),
            duration_minutes=0,
            mandatory=False,
            indoor=True
        )


def test_activity_default_values():
    # Create an activity without mandatory or indoor
    # Assert the default values
    t = Activity(
            activity_id="activity_001",
            name="Activity Name",
            location="Washington, DC",
            start_time=datetime(2026, 11, 7, 10, 0),
            duration_minutes=90,
    )

    assert t.mandatory is False
    assert t.indoor is True
