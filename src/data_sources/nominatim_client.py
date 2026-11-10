import re
import requests
from enum import Enum


class LocationMatchStatus(str, Enum):
    NO_CANDIDATE_MATCHES = "no_candidate_matches"
    NO_VALID_MATCHES = "no_valid_matches"
    UNIQUE_VALID_MATCH = "unique_valid_match"
    MULTIPLE_VALID_MATCHES = "multiple_valid_matches"


def collect_attraction_location(attraction_name, attraction_location):
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


def normalize_location(location: str) -> str:
    location = location.lower()
    location = location.strip()
    location = location.replace("district of columbia", "dc")
    location = re.sub(r'[^\w\s]', '', location)
    location = re.sub(r'\s+', ' ', location)
    return location


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


def coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon):
    try:
        lat = float(candidate.get('lat'))
        latitude_within_area = min_lat <= lat <= max_lat
    except(TypeError, ValueError):
        latitude_within_area = False
            
    try:
        lon = float(candidate.get('lon'))   
        longitude_within_area = min_lon <= lon <= max_lon 
    except(TypeError, ValueError):
        longitude_within_area = False  
          
    return {
        "latitude_within_area": latitude_within_area,
        "longitude_within_area": longitude_within_area
    }


def validate_location_candidate(candidate, expected_name, expected_location, expected_types, 
                                min_lat, max_lat, min_lon, max_lon, aliases=None):

    # Name Match
    candidate_name = normalize_location(candidate.get("name", ""))

    aliases = aliases or []
    accepted_names = [expected_name] + aliases
    accepted_names = [normalize_location(name) for name in accepted_names]

    name_match = candidate_name in accepted_names

    expected_location = normalize_location(expected_location)
    candidate_location = normalize_location(candidate.get('display_name', ''))

    # Location Match
    location_match = expected_location in candidate_location
    
    loc_name_dict = {
        "name_match": name_match,
        "location_match": location_match,
        }

    loc_dict = coordinates_valid(candidate)

    feature_type_match = (candidate.get("type", "").lower() in [t.lower() for t in expected_types])
    feature_type_dict = {"feature_type_match": feature_type_match}

    coord_dict = coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon)

    validation_dict = {
        **loc_name_dict,
        **loc_dict,
        **feature_type_dict,
        **coord_dict, 
        "valid": (
            loc_name_dict["name_match"]
            and loc_name_dict["location_match"]
            and loc_dict["latitude_valid"]
            and loc_dict["longitude_valid"]
            and feature_type_dict["feature_type_match"]
            and coord_dict['latitude_within_area']
            and coord_dict['longitude_within_area']
            )
        }

    return validation_dict


def select_location_candidate(candidates, expected_name, expected_location, expected_types, 
                              min_lat, max_lat, min_lon, max_lon, aliases=None):
    """
    Evaluates location candidates for potential inclusion in the curated
    attraction dataset.

    Returns the candidate evaluations, validation results, and selection
    status. Automatically selects a candidate only when exactly one
    candidate passes all validation checks. Multiple valid candidates
    require manual review.
    """

    selected_candidate = None
    valid_candidates = []
    candidate_evaluations = []

    if len(candidates) == 0: 
        status = LocationMatchStatus.NO_CANDIDATE_MATCHES
        return {'status': status, 
                'selected_candidate':selected_candidate, 
                'valid_candidates':valid_candidates, 
                'candidate_evaluations': candidate_evaluations}

    for candidate in candidates:
        r = validate_location_candidate(candidate, expected_name, expected_location, expected_types, 
                                        min_lat, max_lat, min_lon, max_lon, aliases)

        failed_checks = [key for key, value in r.items() if key != "valid" and value is False]
        
        # Keep full vaidation
        candidate_evaluations.append({
                'candidate': candidate, 
                'validation': r, 
                'failure_reasons': failed_checks
            })
        # Assess Validation Results
        if r["valid"] is True:
            # Keep Candidate
            valid_candidates.append(candidate)

    if len(valid_candidates) == 0: 
        status = LocationMatchStatus.NO_VALID_MATCHES
    elif len(valid_candidates) == 1:
        status = LocationMatchStatus.UNIQUE_VALID_MATCH
        selected_candidate = valid_candidates[0]
    else:
        status = LocationMatchStatus.MULTIPLE_VALID_MATCHES

    return {'status': status, 
            'selected_candidate':selected_candidate, 
            'valid_candidates': valid_candidates, 
            'candidate_evaluations': candidate_evaluations}

