import pytest

from src.data_sources.attraction_lookup import (
    get_attraction_by_id,
    load_attractions,
)


def test_load_attractions():
    attractions = load_attractions()

    assert len(attractions) == 10


def test_get_attraction_by_id():
    attraction = get_attraction_by_id("national_gallery")

    assert attraction.name == "National Gallery of Art"
    assert attraction.latitude == pytest.approx(38.8913116)
    assert attraction.longitude == pytest.approx(-77.0199045)


def test_unknown_attraction_id():
    with pytest.raises(ValueError):
        get_attraction_by_id("unknown_attraction")