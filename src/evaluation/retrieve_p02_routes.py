
import json
import math
from pathlib import Path

from src.data_sources.routing_client import get_walking_route


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ATTRACTIONS_PATH = (
    PROJECT_ROOT / "data/attractions/washington_dc.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/evaluations/llm_benchmarks/"
    / "p02_additional_routes.json"
)

ROUTES_TO_RETRIEVE = [
    ("national_gallery", "wwii_memorial"),
    ("american_history", "wwii_memorial"),
    ("national_gallery", "lincoln_memorial"),
    ("wwii_memorial", "american_history"),
]


def load_attractions():
    with ATTRACTIONS_PATH.open(encoding="utf-8") as file:
        attractions = json.load(file)

    return {
        attraction["attraction_id"]: attraction
        for attraction in attractions
    }


def retrieve_routes():
    attractions = load_attractions()
    results = []

    for origin_id, destination_id in ROUTES_TO_RETRIEVE:
        origin = attractions[origin_id]
        destination = attractions[destination_id]

        # Routing client expects (longitude, latitude).
        origin_coordinates = (
            origin["longitude"],
            origin["latitude"],
        )

        destination_coordinates = (
            destination["longitude"],
            destination["latitude"],
        )

        print(
            f"Retrieving: {origin['name']} -> "
            f"{destination['name']}",
            flush=True,
        )

        route = get_walking_route(
            origin_coordinates,
            destination_coordinates,
        )

        duration_seconds = route["duration_seconds"]

        estimate = {
            "mode": "walking",
            "duration_minutes": math.ceil(
                duration_seconds / 60
            ),
            "duration_seconds": duration_seconds,
            "distance_meters": route["distance_meters"],
            "source": "OpenRouteService",
        }

        results.append({
            "origin_activity_id": origin_id,
            "destination_activity_id": destination_id,
            "estimates": [estimate],
            "selected_mode": "walking",
        })

        print(f"  Estimate: {estimate}")

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved route estimates to: {OUTPUT_PATH}")


if __name__ == "__main__":
    retrieve_routes()
