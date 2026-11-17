import json
from pathlib import Path

from src.models.itinerary import Itinerary


def test_baseline_itinerary_loads():
    dataset_path = Path(
        "data/itineraries/dc_baseline_2026_11_07.json"
    )

    with dataset_path.open(encoding="utf-8") as file:
        data = json.load(file)

    itinerary = Itinerary.model_validate(data)

    assert itinerary.itinerary_id == "dc_baseline_2026_11_07"
    assert itinerary.destination == "Washington, DC"
    assert len(itinerary.activities) == 5

    mandatory_activities = [
        activity for activity in itinerary.activities
        if activity.mandatory
    ]

    assert len(mandatory_activities) == 1
    assert mandatory_activities[0].activity_id == "natural_history"
    
    assert len(itinerary.travel_legs) == 4
    assert len(itinerary.travel_legs) == 4

    assert [
        (leg.origin_activity_id, leg.destination_activity_id)
        for leg in itinerary.travel_legs
    ] == [
        ("national_gallery", "american_history"),
        ("american_history", "natural_history"),
        ("natural_history", "wwii_memorial"),
        ("wwii_memorial", "lincoln_memorial"),
    ]

    assert all(leg.estimates == [] for leg in itinerary.travel_legs)
   