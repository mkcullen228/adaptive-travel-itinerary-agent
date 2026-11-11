import pytest
from pydantic import ValidationError

from src.models.travel import TravelEstimate, TravelLeg

@pytest.fixture
def valid_travel_walking_estimate_data():
    return {
        "mode": "walking", 
        "duration_minutes": 12,
        "duration_seconds": 711.1,
        "distance_meters": 367,
        "source": "OpenRouteService",
    }

@pytest.fixture
def valid_travel_driving_estimate_data():
    return {
        "mode": "driving", 
        "duration_minutes": 10,
        "duration_seconds": 542,
        "distance_meters": 367.3,
        "source": "OpenRouteService",
    }


def test_valid_travel_estimate(valid_travel_walking_estimate_data):
    t = TravelEstimate(**valid_travel_walking_estimate_data)

    assert t.mode == "walking"
    assert t.duration_minutes == 12
    assert t.duration_seconds == 711.1
    assert t.distance_meters == 367
    assert t.source == "OpenRouteService"


def test_negative_duration_min_is_rejected(valid_travel_walking_estimate_data):
    data = valid_travel_walking_estimate_data.copy()
    data["duration_minutes"] = -1

    with pytest.raises(ValidationError):
        TravelEstimate(**data)


def test_negative_duration_sec_is_rejected(valid_travel_walking_estimate_data):
    data = valid_travel_walking_estimate_data.copy()
    data["duration_seconds"] = -1

    with pytest.raises(ValidationError):
        TravelEstimate(**data)


def test_negative_meters_is_rejected(valid_travel_walking_estimate_data):
    data = valid_travel_walking_estimate_data.copy()
    data["distance_meters"] = -1

    with pytest.raises(ValidationError):
        TravelEstimate(**data)


def test_travel_leg_supports_multiple_estimates(valid_travel_walking_estimate_data, valid_travel_driving_estimate_data):
    # Create a travel leg with walking and driving estimates
    # Assert that both estimates are present
    t3 = TravelLeg(
        origin_activity_id="activity_001",
        destination_activity_id="activity_002",
        estimates=[
            TravelEstimate(**valid_travel_walking_estimate_data), 
            TravelEstimate(**valid_travel_driving_estimate_data)], 
        selected_mode="walking"
        )

    assert len(t3.estimates) == 2
    assert t3.estimates[0].mode == "walking"
    assert t3.estimates[0].duration_minutes == 12
    assert t3.estimates[0].duration_seconds == 711.1
    assert t3.estimates[0].distance_meters == 367
    assert t3.estimates[0].source == "OpenRouteService"

    assert t3.estimates[1].mode == "driving"
    assert t3.estimates[1].duration_minutes == 10
    assert t3.estimates[1].duration_seconds == 542
    assert t3.estimates[1].distance_meters == 367.3
    assert t3.estimates[1].source == "OpenRouteService"


def test_travel_leg_supports_empty_estimates():
    # Create a travel leg with walking and driving estimates
    # Assert that both estimates are present
    t3 = TravelLeg(
        origin_activity_id="activity_001",
        destination_activity_id="activity_002",
        estimates=[], 
        selected_mode="walking"
        )

    assert len(t3.estimates) == 0
    assert t3.selected_mode == "walking"


def test_travel_leg_requires_selected_mode():
    with pytest.raises(ValidationError):
        TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[]
        )