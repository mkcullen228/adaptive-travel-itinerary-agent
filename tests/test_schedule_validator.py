from datetime import datetime, date

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.validation import ValidationStatus
from src.validation.schedule_validator import check_activity_overlaps


def test_activities_without_overlap():
    # Create two activities that do not overlap
    # Create an itinerary containing them
    # Run the validator
    # Assert that the result is VALID
    t1 = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 30),
                duration_minutes=90,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ]
    )

    r = check_activity_overlaps(t1)
    assert r.status == "valid"


def test_activities_with_overlap():
    # Create two activities that overlap
    # Create an itinerary containing them
    # Run the validator
    # Assert that the result is INVALID
    # Assert that the issue identifies both activity IDs

    t1 = Itinerary(
            itinerary_id="Fun Day Out",
            destination="Washington, DC", 
            itinerary_date=date(2026, 11, 7),
            activities=[
                Activity(
                    activity_id="activity_002",
                    name="Smithsonian's National Air and Space Museum",
                    location="Washington, DC",
                    start_time=datetime(2026, 11, 7, 11, 0),
                    duration_minutes=90,
                ),
                Activity(
                    activity_id="activity_001",
                    name="National Gallery of Art",
                    location="Washington, DC",
                    start_time=datetime(2026, 11, 7, 10, 0),
                    duration_minutes=90,
                ),
            ]
        )
    
    r = check_activity_overlaps(t1)
    assert r.status == "invalid"
    assert len(r.issues) == 1
    assert r.issues[0].activity_ids == [
        "activity_001",
        "activity_002"
    ]
    assert r.issues[0].issue_type == "activity_overlap"


def test_activities_starting_at_same_time():
    # Create two activities starting at 10:00
    # Run the validator
    # Assert INVALID
    t1 = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ]
    )
        
    r = check_activity_overlaps(t1)
    assert r.status == "invalid"
    assert len(r.issues) == 1
    assert set(r.issues[0].activity_ids) == {
        "activity_001",
        "activity_002"
    }
    assert r.issues[0].issue_type == "activity_overlap"