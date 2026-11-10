import re
import requests


def normalize_location(location: str) -> str:
    location = location.lower()
    location = location.strip()
    location = location.replace("district of columbia", "dc")
    location = re.sub(r'[^\w\s]', '', location)
    location = re.sub(r'\s+', ' ', location)
    return location


def collect_attraction_location(attraction_name, attraction_location=""):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": f"{attraction_name}, {attraction_location}",
        "format": "jsonv2",
        "limit": 5
    }

    headers = {
        "User-Agent": "TravelItineraryRecoveryAgent/1.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        results = response.json()
        
        if not results:
            print("No matching locations found.")
            return []

        return results

    except requests.exceptions.RequestException as e:
        print(f"Location request failed: {e}")
        return []


def coordinates_valid(candidate):
    try:
        lat = float(candidate.get('lat'))
        valid_lat = -90 <= lat <= 90
    except (TypeError, ValueError):
        valid_lat = False

    try:
        lon = float(candidate.get('lon'))
        valid_lon = -180 <= lon <= 180
    except(TypeError, ValueError):
        valid_lon = False

    return {
        "latitude_valid": valid_lat,
        "longitude_valid": valid_lon
    }


def validate_location_candidate(candidate, expected_name, expected_location, expected_type):
    name_match = candidate.get('name', '').lower() == expected_name.lower()

    expected_location = normalize_location(expected_location)
    candidate_location = normalize_location(candidate.get('display_name', ''))

    location_match = expected_location in candidate_location
    
    loc_name_dict = {
        "name_match": name_match,
        "location_match": location_match,
        }

    loc_dict = coordinates_valid(candidate)

    feature_type_match = candidate.get("type", "") == expected_type.lower()
    feature_type_dict = {"feature_type_match": feature_type_match}


    validation_dict = {
        **loc_name_dict,
        **loc_dict,
        **feature_type_dict, 
        "valid": (
            loc_name_dict["name_match"]
            and loc_name_dict["location_match"]
            and loc_dict["latitude_valid"]
            and loc_dict["longitude_valid"]
            and feature_type_dict["feature_type_match"]
            )
        }

    return validation_dict


results = collect_attraction_location(
    "National Museum of Natural History",
    "Washington, DC"
)
print(results)

print(f"Number of candidates returned: {len(results)}")

for candidate in results:
    validation = validate_location_candidate(
        candidate,
        "National Museum of Natural History",
        "Washington, DC", 
        "museum"
    )

    print("\nCandidate:", candidate.get("name"))
    print("Feature type:", candidate.get("type"))
    print("Coordinates:", candidate.get("lat"), candidate.get("lon"))
    print("Validation:", validation)
