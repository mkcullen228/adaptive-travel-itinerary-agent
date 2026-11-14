import math

from src.models.travel import TravelEstimate, TravelLeg
from src.models.routing_failure import RoutingFailure
from src.models.itinerary import Itinerary
from src.models.validation import ValidationResult
from src.data_sources.routing_client import get_walking_route
from src.data_sources.attraction_lookup import get_attraction_by_id
from src.validation.schedule_validator import validate_itinerary


def process_travel_leg(
    travel_leg: TravelLeg,
    origin_coordinates: tuple[float, float],
    destination_coordinates: tuple[float, float],
) -> tuple[TravelLeg, RoutingFailure | None]:

    try:
        route = get_walking_route(
            origin_coordinates,
            destination_coordinates,
        )

        estimate = TravelEstimate(
            mode="walking",
            duration_seconds=route["duration_seconds"],
            duration_minutes=math.ceil(route["duration_seconds"] / 60),
            distance_meters=route["distance_meters"],
            source="OpenRouteService",
        )

        travel_leg.estimates = [estimate]

        return travel_leg, None

    except RuntimeError as error:
        failure = RoutingFailure(
            origin_activity_id=travel_leg.origin_activity_id,
            destination_activity_id=travel_leg.destination_activity_id,
            requested_mode=travel_leg.selected_mode,
            failure_reason=str(error),
        )

        return travel_leg, failure


def get_activity_coordinates(activity_id: str) -> tuple[float, float]:
    attraction = get_attraction_by_id(activity_id)

    return (
        attraction.longitude,
        attraction.latitude,
    )


def process_itinerary_routes(itinerary: Itinerary,) -> tuple[Itinerary, ValidationResult]:
    routing_failures = []

    for travel_leg in itinerary.travel_legs:
        try:
            origin_coordinates = get_activity_coordinates(
                travel_leg.origin_activity_id
            )
            destination_coordinates = get_activity_coordinates(
                travel_leg.destination_activity_id
            )

            updated_leg, routing_failure = process_travel_leg(
                travel_leg,
                origin_coordinates,
                destination_coordinates,
            )

            if routing_failure:
                routing_failures.append(routing_failure)

        except ValueError as error:
            routing_failures.append(
                RoutingFailure(
                    origin_activity_id=travel_leg.origin_activity_id,
                    destination_activity_id=travel_leg.destination_activity_id,
                    requested_mode=travel_leg.selected_mode,
                    failure_reason=str(error),
                )
            )

    itinerary.routing_failures = routing_failures
    validation_result = validate_itinerary(itinerary)

    return itinerary, validation_result
