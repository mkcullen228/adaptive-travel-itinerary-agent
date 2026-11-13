import os
import math
import requests
from dotenv import load_dotenv


load_dotenv()

def get_walking_route(
    origin_coordinates: tuple[float, float],
    destination_coordinates: tuple[float, float]
    ) -> dict:
    """Retrieve a walking route between two geographic coordinates.
        coordinates passed as (longitude, latitude)
    """

    api_key = os.getenv("OPENROUTESERVICE_API_KEY")

    if not api_key:
        raise ValueError("OpenRouteService API key not found.")

    if (
        not isinstance(origin_coordinates, (tuple, list))
        or len(origin_coordinates) != 2
        or not isinstance(destination_coordinates, (tuple, list))
        or len(destination_coordinates) != 2
    ):
        raise ValueError("Invalid coordinates: expected (longitude, latitude).")

    for longitude, latitude in (origin_coordinates, destination_coordinates):
        if (
            not isinstance(longitude, (int, float))
            or not isinstance(latitude, (int, float))
            or not math.isfinite(longitude)
            or not math.isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError("Invalid coordinates: longitude or latitude is out of range.")


    url = "https://api.heigit.org/openrouteservice/v2/directions/foot-walking"

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "coordinates": [
            list(origin_coordinates),
            list(destination_coordinates)
        ],
        "instructions": False
    }


    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        route_data = response.json()
        summary = route_data["routes"][0]["summary"]

        duration = summary["duration"]
        distance = summary["distance"]

        if (
            not isinstance(duration, (int, float))
            or not isinstance(distance, (int, float))
            or not math.isfinite(duration)
            or not math.isfinite(distance)
            or duration <= 0
            or distance <= 0
        ):
            raise RuntimeError("Invalid route estimate returned by OpenRouteService.")


        return {
            "duration_seconds": duration,
            "distance_meters": distance
        }

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"OpenRouteService returned HTTP {error.response.status_code}"
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Unable to retrieve walking route: {error}"
        ) from error

    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            "Unexpected response format from OpenRouteService."
        ) from error
