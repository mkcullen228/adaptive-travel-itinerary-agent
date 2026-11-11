import math
import json
from pathlib import Path
from itertools import pairwise

from src.models.itinerary import Itinerary
from src.models.travel import TravelLeg, TravelEstimate
from src.data_sources.attraction_lookup import get_attraction_by_id
from src.data_sources.routing_client import get_walking_route


def build_travel_legs(itinerary: Itinerary) -> list[TravelLeg]:
    """Build walking travel legs between consecutive itinerary activities."""

    sorted_activities = sorted(
        itinerary.activities,
        key=lambda activity: activity.start_time
    )

    travel_legs = []

    for origin_activity, destination_activity in pairwise(sorted_activities):

        # Get IDs
        origin_attraction = get_attraction_by_id(origin_activity.activity_id)
        destination_attraction = get_attraction_by_id(destination_activity.activity_id)

        # OpenRouteService expects coordinates as (longitude, latitude)
        origin_coordinates = (origin_attraction.longitude, origin_attraction.latitude)
        destination_coordinates = (destination_attraction.longitude, destination_attraction.latitude)

        route_result = get_walking_route(origin_coordinates, destination_coordinates)
        duration_minutes = math.ceil(route_result["duration_seconds"] / 60)

        travel_estimate = TravelEstimate(
            mode="walking",
            duration_minutes=duration_minutes,
            duration_seconds=route_result["duration_seconds"],
            distance_meters=route_result["distance_meters"],
            source="OpenRouteService"
        )

        travel_leg = TravelLeg(
            origin_activity_id=origin_activity.activity_id,
            destination_activity_id=destination_activity.activity_id,
            estimates=[travel_estimate],
            selected_mode="walking"
        )

        travel_legs.append(travel_leg)

    return travel_legs


def add_travel_legs_to_itinerary(itinerary: Itinerary) -> Itinerary:
    """Add walking travel estimates to an itinerary."""

    itinerary.travel_legs = build_travel_legs(itinerary)

    return itinerary


def save_itinerary_with_travel_legs(itinerary: Itinerary) -> None:
    """Save an itinerary, including its travel legs, to JSON."""

    output_path = Path("data/itineraries/dc_baseline_2026_11_07.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(itinerary.model_dump(mode="json"), file, indent=4)


if __name__ == "__main__":
    from src.data_sources.build_baseline_itinerary import baseline_itinerary

    updated_itinerary = add_travel_legs_to_itinerary(baseline_itinerary)
    save_itinerary_with_travel_legs(updated_itinerary)

    print(f"Saved {len(updated_itinerary.travel_legs)} travel legs.")