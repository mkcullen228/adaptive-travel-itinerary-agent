import pytest

from src.data_sources.nominatim_client import (coordinates_valid, validate_location_candidate)

def test_valid_coordinates():
    candidate = {
        "lat": "38.8913116",
        "lon": "-77.0199045"
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is True


def test_coordinates_lat_invalid():
    candidate = {
        "lat": "98.8913116",
        "lon": "-77.0199045"
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is False
    assert result["longitude_valid"] is True


def test_coordinates_missing_lon():
    candidate = {
        "lat": "35.8913116",
    }

    result = coordinates_valid(candidate)
    print(result)

    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is False


def test_coordinates_missing_lat():
    candidate = {
        "lon": "-77.0199045"
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is False
    assert result["longitude_valid"] is True


def test_incorrect_feature_type():
    candidate = {
        "name": "National Museum of Natural History",
        "display_name": "National Museum of Natural History, Washington, District of Columbia",
        "lat": "38.8912450",
        "lon": "-77.0259701",
        "type": "restaurant"
    }

    result = validate_location_candidate(
        candidate,
        "National Museum of Natural History",
        "Washington, DC",
        "museum"
    )

    assert result["name_match"] is True
    assert result["location_match"] is True
    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is True
    assert result["feature_type_match"] is False
    assert result["valid"] is False