
import json
from pathlib import Path
from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.travel import TravelLeg
from src.data_sources.build_travel_legs import (
    add_travel_legs_to_itinerary,
)


activities = [
    Activity(
        activity_id="national_gallery",
        attraction_id="national_gallery",
        name="National Gallery of Art",
        location="6th Street and Constitution Avenue NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 9, 0),
        duration_minutes=90,
        mandatory=False,
        indoor=True,
    ),
    Activity(
        activity_id="american_history",
        attraction_id="american_history",
        name="National Museum of American History",
        location="1300 Constitution Ave. NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 50),
        duration_minutes=90,
        mandatory=False,
        indoor=True,
    ),
    Activity(
        activity_id="natural_history",
        attraction_id="natural_history",
        name="National Museum of Natural History",
        location="10th St. & Constitution Ave. NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 13, 20),
        duration_minutes=90,
        mandatory=True,
        indoor=True,
    ),
    Activity(
        activity_id="wwii_memorial",
        attraction_id="wwii_memorial",
        name="World War II Memorial",
        location="1750 Independence Ave. SW, Washington, DC",
        start_time=datetime(2026, 11, 7, 15, 10),
        duration_minutes=30,
        mandatory=False,
        indoor=False,
    ),
    Activity(
        activity_id="lincoln_memorial",
        attraction_id="lincoln_memorial",
        name="Lincoln Memorial",
        location="2 Lincoln Memorial Circle NW, Washington, DC",
        start_time=datetime(2026, 11, 7, 15, 50),
        duration_minutes=30,
        mandatory=False,
        indoor=False,
    ),
]


# Initial travel-leg relationships.
# Walking estimates are populated by the routing implementation below.
travel_legs = [
    TravelLeg(
        origin_activity_id="national_gallery",
        destination_activity_id="american_history",
        estimates=[],
        selected_mode="walking",
    ),
    TravelLeg(
        origin_activity_id="american_history",
        destination_activity_id="natural_history",
        estimates=[],
        selected_mode="walking",
    ),
    TravelLeg(
        origin_activity_id="natural_history",
        destination_activity_id="wwii_memorial",
        estimates=[],
        selected_mode="walking",
    ),
    TravelLeg(
        origin_activity_id="wwii_memorial",
        destination_activity_id="lincoln_memorial",
        estimates=[],
        selected_mode="walking",
    ),
]


baseline_itinerary = Itinerary(
    itinerary_id="dc_baseline_2026_11_07",
    destination="Washington, DC",
    itinerary_date=date(2026, 11, 7),
    activities=activities,
    travel_legs=travel_legs,
)


def save_baseline_itinerary(itinerary: Itinerary) -> None:
    """Save the baseline itinerary, including walking estimates."""

    output_path = Path(
        "data/itineraries/dc_baseline_2026_11_07.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            itinerary.model_dump(mode="json"),
            file,
            indent=2,
        )


if __name__ == "__main__":
    print("Generating baseline itinerary...")

    print(f"Number of activities: {len(baseline_itinerary.activities)}")

    print(
        "Mandatory activities:",
        [
            activity.name
            for activity in baseline_itinerary.activities
            if activity.mandatory
        ],
    )

    # Populate walking estimates using the existing routing implementation.
    # This makes routing requests before the canonical JSON is overwritten.
    updated_itinerary = add_travel_legs_to_itinerary(
        baseline_itinerary
    )

    # Validate the generated travel legs before saving.
    expected_leg_count = len(updated_itinerary.activities) - 1

    if len(updated_itinerary.travel_legs) != expected_leg_count:
        raise RuntimeError(
            f"Expected {expected_leg_count} travel legs, "
            f"but generated {len(updated_itinerary.travel_legs)}."
        )

    for leg in updated_itinerary.travel_legs:
        if not leg.estimates:
            raise RuntimeError(
                f"Missing walking estimate for "
                f"{leg.origin_activity_id} -> "
                f"{leg.destination_activity_id}."
            )

        if not any(
            estimate.mode == "walking"
            for estimate in leg.estimates
        ):
            raise RuntimeError(
                f"No walking estimate for "
                f"{leg.origin_activity_id} -> "
                f"{leg.destination_activity_id}."
            )

    print(f"Generated travel legs: {len(updated_itinerary.travel_legs)}")

    for leg in updated_itinerary.travel_legs:
        estimate = next(
            estimate
            for estimate in leg.estimates
            if estimate.mode == "walking"
        )

        print(
            f"{leg.origin_activity_id} -> "
            f"{leg.destination_activity_id}: "
            f"{estimate.duration_minutes} minutes, "
            f"{estimate.distance_meters:.1f} meters"
        )

    save_baseline_itinerary(updated_itinerary)

    print("\nBaseline itinerary saved successfully.")
