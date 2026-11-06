import pytest
from pydantic import ValidationError

from src.models.travel import TravelEstimate, TravelLeg


def test_valid_travel_estimate():
    # Arrange: create a valid estimate
    t1 = TravelEstimate(
        mode="walking",
        duration_minutes=12,
        source="manual_test_data"
    )

    # Assert: check the expected values
    assert t1.mode == "walking"
    assert t1.duration_minutes == 12
    assert t1.source == "manual_test_data"


def test_negative_duration_is_rejected():
    # Create an estimate with a negative duration
    # Assert that Pydantic raises ValidationError

    with pytest.raises(ValidationError):
        TravelEstimate(
            mode="walking",
            duration_minutes=-5,
            source="manual_test_data"
        )


def test_travel_leg_supports_multiple_estimates():
    # Create a travel leg with walking and driving estimates
    # Assert that both estimates are present
    t3 = TravelLeg(
        origin_activity_id="activity_001",
        destination_activity_id="activity_002",
        estimates=[
        TravelEstimate(
            mode="walking",
            duration_minutes=12,
            source="manual_test_data",
            ), 
        TravelEstimate(
            mode="driving",
            duration_minutes=8,
            source="manual_test_data",
            )]
        )

    assert len(t3.estimates) == 2
    assert t3.estimates[0].mode == "walking"
    assert t3.estimates[0].duration_minutes == 12
    assert t3.estimates[1].mode == "driving"
    assert t3.estimates[1].duration_minutes == 8

def test_travel_leg_supports_empty_estimates():
    # Create a travel leg with walking and driving estimates
    # Assert that both estimates are present
    t3 = TravelLeg(
        origin_activity_id="activity_001",
        destination_activity_id="activity_002",
        estimates=[]
        )

    assert len(t3.estimates) == 0
