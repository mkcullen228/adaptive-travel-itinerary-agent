import pytest

from src.data_sources.nominatim_client import coordinates_valid

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