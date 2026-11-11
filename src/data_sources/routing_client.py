import os
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

        return {
            "duration_seconds": summary["duration"],
            "distance_meters": summary["distance"]
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

