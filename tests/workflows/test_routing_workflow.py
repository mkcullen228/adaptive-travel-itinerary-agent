from unittest.mock import patch
from datetime import date, datetime

from src.workflows.routing_workflow import process_travel_leg
from src.models.activity import Activity
from src.models.travel import TravelLeg, TravelEstimate
from src.models.itinerary import Itinerary
from src.models.validation import ValidationStatus
from src.models.routing_failure import RoutingFailure
from src.workflows.routing_workflow import get_activity_coordinates, process_itinerary_routes


@patch("src.workflows.routing_workflow.get_walking_route")
def test_process_travel_leg(mock_get_walking_route):
    mock_get_walking_route.return_value = {
        "duration_seconds": 683.5,
        "distance_meters": 949.3,
    }

    travel_leg = TravelLeg(
        origin_activity_id="activity_1",
        destination_activity_id="activity_2",
        estimates=[],
        selected_mode="walking",
    )

    origin_coordinates = (-77.019, 38.891)
    destination_coordinates = (-77.030, 38.891)

    updated_travel_leg, routing_failure = process_travel_leg(
        travel_leg,
        origin_coordinates,
        destination_coordinates,
    )

    mock_get_walking_route.assert_called_once_with(
        origin_coordinates,
        destination_coordinates,
    )

    assert len(updated_travel_leg.estimates) == 1
    assert updated_travel_leg.estimates[0].mode == "walking"
    assert updated_travel_leg.estimates[0].duration_minutes == 12
    assert updated_travel_leg.estimates[0].duration_seconds == 683.5
    assert updated_travel_leg.estimates[0].distance_meters == 949.3
    assert routing_failure is None


@patch("src.workflows.routing_workflow.get_walking_route")
def test_process_travel_leg_routing_failure(mock_get_walking_route):
    mock_get_walking_route.side_effect = RuntimeError(
        "OpenRouteService returned HTTP 429"
    )

    travel_leg = TravelLeg(
        origin_activity_id="activity_1",
        destination_activity_id="activity_2",
        estimates=[],
        selected_mode="walking",
    )

    updated_travel_leg, routing_failure = process_travel_leg(
        travel_leg,
        (-77.019, 38.891),
        (-77.030, 38.891),
    )

    assert updated_travel_leg.estimates == []
    assert routing_failure is not None
    assert routing_failure.origin_activity_id == "activity_1"
    assert routing_failure.destination_activity_id == "activity_2"
    assert routing_failure.requested_mode == "walking"
    assert "HTTP 429" in routing_failure.failure_reason


def test_get_activity_coordinates():
    coordinates = get_activity_coordinates("national_gallery")

    assert isinstance(coordinates, tuple)
    assert len(coordinates) == 2
    assert -180 <= coordinates[0] <= 180
    assert -90 <= coordinates[1] <= 90


@patch("src.workflows.routing_workflow.process_travel_leg")
def test_process_itinerary_routes_continues_after_failure(mock_process):
    mock_process.side_effect = [
        (
            TravelLeg(
                origin_activity_id="national_gallery",
                destination_activity_id="american_history",
                estimates=[],
                selected_mode="walking",
            ),
            None,
        ),
        (
            TravelLeg(
                origin_activity_id="american_history",
                destination_activity_id="natural_history",
                estimates=[],
                selected_mode="walking",
            ),
            RoutingFailure(
                origin_activity_id="american_history",
                destination_activity_id="natural_history",
                requested_mode="walking",
                failure_reason="HTTP 429",
            ),
        ),
    ]

    itinerary = Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[],
        travel_legs=[
            TravelLeg(
                origin_activity_id="national_gallery",
                destination_activity_id="american_history",
                estimates=[],
                selected_mode="walking",
            ),
            TravelLeg(
                origin_activity_id="american_history",
                destination_activity_id="natural_history",
                estimates=[],
                selected_mode="walking",
            ),
        ],
    )

    updated_itinerary, validation_result = process_itinerary_routes(itinerary)

    assert mock_process.call_count == 2
    assert len(updated_itinerary.routing_failures) == 1
    assert updated_itinerary.routing_failures[0].failure_reason == "HTTP 429"
    assert len(updated_itinerary.travel_legs) == 2


def test_process_itinerary_routes_all_valid():
    itinerary = Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[Activity(
                        activity_id="national_gallery",
                        name="National Gallery of Art",
                        location="Washington, DC",
                        start_time=datetime(2026, 11, 7, 10, 0),
                        duration_minutes=90,
                    ),
                    Activity(
                        activity_id="american_history",
                        name="National Museum of American History",
                        location="Washington, DC",
                        start_time=datetime(2026, 11, 7, 12, 00),
                        duration_minutes=90,
                    ),
                    ],
        travel_legs=[
            TravelLeg(
                origin_activity_id="national_gallery",
                destination_activity_id="american_history",
                estimates=[
                    TravelEstimate(
                        mode="walking",
                        duration_minutes=15,
                        duration_seconds=913,
                        distance_meters=1200,
                        source="manual_test_data",
                        ), ],
                selected_mode="walking",
            ),
        ],
    )

    updated_itinerary, validation_result = process_itinerary_routes(itinerary)
    assert len(updated_itinerary.routing_failures) == 0
    assert len(updated_itinerary.travel_legs) == 1
    assert validation_result.status == ValidationStatus.VALID
    assert validation_result.issues == []


@patch("src.workflows.routing_workflow.process_travel_leg")
def test_process_itinerary_routes_all_incomplete(mock_process):
    travel_leg = TravelLeg(
        origin_activity_id="national_gallery",
        destination_activity_id="american_history",
        estimates=[],
        selected_mode="walking",
    )

    mock_process.return_value = (travel_leg, None)

    itinerary = Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="national_gallery",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
            Activity(
                activity_id="american_history",
                name="National Museum of American History",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 12, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs=[travel_leg],
    )

    updated_itinerary, validation_result = process_itinerary_routes(itinerary)

    mock_process.assert_called_once()

    assert len(updated_itinerary.routing_failures) == 0
    assert len(updated_itinerary.travel_legs) == 1
    assert updated_itinerary.travel_legs[0].estimates == []
    assert validation_result.status == ValidationStatus.INCOMPLETE


def test_process_itinerary_routes_all_invalid():
    itinerary = Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[Activity(
                        activity_id="national_gallery",
                        name="National Gallery of Art",
                        location="Washington, DC",
                        start_time=datetime(2026, 11, 7, 10, 0),
                        duration_minutes=90,
                    ),
                    Activity(
                        activity_id="american_history",
                        name="National Museum of American History",
                        location="Washington, DC",
                        start_time=datetime(2026, 11, 7, 11, 35),
                        duration_minutes=90,
                    ),
                    ],
        travel_legs=[
            TravelLeg(
                origin_activity_id="national_gallery",
                destination_activity_id="american_history",
                estimates=[
                    TravelEstimate(
                        mode="walking",
                        duration_minutes=15,
                        duration_seconds=913,
                        distance_meters=1200,
                        source="manual_test_data",
                        ), ],
                selected_mode="walking",
            ),
        ],
    )

    updated_itinerary, validation_result = process_itinerary_routes(itinerary)
    assert len(updated_itinerary.routing_failures) == 0
    assert len(updated_itinerary.travel_legs) == 1
    assert validation_result.status == ValidationStatus.INVALID
    assert any(
        issue.issue_type.value == "insufficient_travel_time"
        for issue in validation_result.issues
        )
