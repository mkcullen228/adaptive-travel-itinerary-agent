
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTESERVICE_API_KEY")

if not api_key:
    raise ValueError("OpenRouteService API key not found.")

url = "https://api.heigit.org/openrouteservice/v2/directions/foot-walking"

headers = {
    "Authorization": api_key,
    "Content-Type": "application/json"
}

# Coordinates are [longitude, latitude]
payload = {
    "coordinates": [
        [-77.0199045, 38.8913116],  # National Gallery of Art
        [-77.0300205, 38.8912397]  # National Museum of American History
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

    duration_seconds = summary["duration"]
    distance_meters = summary["distance"]

    print(f"Walking duration: {duration_seconds / 60:.1f} minutes")
    print(f"Walking distance: {distance_meters:.0f} meters")

except requests.exceptions.HTTPError as error:
    print(f"API returned an HTTP error: {error.response.status_code}")
    print(error.response.text[:500])

except requests.exceptions.RequestException as error:
    print(f"Connection error: {error}")
