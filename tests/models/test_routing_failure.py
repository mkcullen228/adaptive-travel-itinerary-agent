import pytest
from datetime import timezone
from pydantic import ValidationError

from src.models.routing_failure import RoutingFailure

@pytest.fixture
def valid_routing_failure_data():
    return {
        "origin_activity_id": "activity_1",
        "destination_activity_id": "activity_2",
        "requested_mode": "walking",
        "failure_reason": "Route not found",
        "attempted_at": "2024-06-06T12:00:00Z",
    }

def test_valid_routing_failure(valid_routing_failure_data):
    routing_failure = RoutingFailure(**valid_routing_failure_data)

    assert routing_failure.origin_activity_id == "activity_1"
    assert routing_failure.destination_activity_id == "activity_2"
    assert routing_failure.requested_mode == "walking"
    assert routing_failure.failure_reason == "Route not found"
    assert routing_failure.attempted_at.year == 2024
    assert routing_failure.attempted_at.month == 6
    assert routing_failure.attempted_at.day == 6
    assert routing_failure.attempted_at.hour == 12
    assert routing_failure.attempted_at.minute == 0
    assert routing_failure.attempted_at.second == 0
    assert routing_failure.attempted_at.tzinfo is not None
    assert routing_failure.attempted_at.tzinfo == timezone.utc


def test_routing_failure_generates_timestamp():
    routing_failure = RoutingFailure(
        origin_activity_id="activity_1",
        destination_activity_id="activity_2",
        requested_mode="walking",
        failure_reason="Route not found",
    )

    assert routing_failure.attempted_at is not None
    assert routing_failure.attempted_at.tzinfo == timezone.utc
