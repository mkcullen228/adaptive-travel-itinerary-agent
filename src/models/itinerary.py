from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List
from src.models.activity import Activity
from src.models.travel import TravelLeg


class Itinerary(BaseModel):
    itinerary_id: str
    destination: str
    itinerary_date: date
    activities: List[Activity]
    travel_legs: List[TravelLeg] = Field(default_factory=list)


itinerary_a = Itinerary(
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
