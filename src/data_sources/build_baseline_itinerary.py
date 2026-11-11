import json
from pathlib import Path
from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary


activities = [
    Activity(
        activity_id="national_gallery",
        name="National Gallery of Art",
        location="6th Street and Constitution Avenue NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 9, 0),
        duration_minutes=90,
        mandatory=False,
        indoor=True,
    ),
    Activity(
        activity_id="american_history",
        name="National Museum of American History",
        location="1300 Constitution Ave. NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 50),
        duration_minutes=90,
        mandatory=False,
        indoor=True,
    ),
    Activity(
        activity_id="natural_history",
        name="National Museum of Natural History",
        location="10th St. & Constitution Ave. NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 13, 20),
        duration_minutes=90,
        mandatory=True,
        indoor=True,
    ),
    Activity(
        activity_id="wwii_memorial",
        name="World War II Memorial",
        location="1750 Independence Ave. SW, Washington, DC",
        start_time=datetime(2026, 11, 7, 15, 10),
        duration_minutes=30,
        mandatory=False,
        indoor=False,
    ),
    Activity(
        activity_id="lincoln_memorial",
        name="Lincoln Memorial",
        location="2 Lincoln Memorial Circle NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 15, 50),
        duration_minutes=30,
        mandatory=False,
        indoor=False,
    ),
]


baseline_itinerary = Itinerary(
    itinerary_id="dc_baseline_2026_11_07",
    destination="Washington, DC",
    itinerary_date=date(2026, 11, 7),
    activities=activities,
)


def save_baseline_itinerary(itinerary: Itinerary):
    output_path = Path("data/itineraries/dc_baseline_2026_11_07.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            itinerary.model_dump(mode="json"),
            file,
            indent=2
        )


if __name__ == "__main__":
    print(baseline_itinerary)
    print(f"\nNumber of activities: {len(baseline_itinerary.activities)}")
    print(
        "\nMandatory activities:",
        [activity.name for activity in baseline_itinerary.activities if activity.mandatory]
    )
    print(f"Travel legs: {len(baseline_itinerary.travel_legs)}")

    save_baseline_itinerary(baseline_itinerary)
    print("\nBaseline itinerary saved.")
