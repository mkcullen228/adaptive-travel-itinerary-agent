from datetime import date, datetime
from src.models.activity import Activity
from src.models.itinerary import Itinerary

def test_valid_itinerary():
    t = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 13, 30),
                duration_minutes=90,
            ),
        ]
    )
    # Assert the number of activities
    assert len(t.activities) == 2


def test_valid_itinerary_empty_activities():
    t = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[]
    )
    # Assert the name and duration
    assert len(t.activities) == 0


def test_valid_itinerary_dates():
    t = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[]
    )
    # Assert the name and duration
    assert type(t.itinerary_date) is date
