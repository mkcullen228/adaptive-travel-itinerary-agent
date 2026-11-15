from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario, DisruptionType
from src.models.investigation import InvestigationResult

from src.data_sources.weather_client import get_weather_data
from src.data_sources.embedding_client import embed_query

from src.validation.evidence_assessment import assess_claim_evidence
from src.validation.schedule_validator import validate_itinerary

from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
    search_documents,
)
from src.data_sources.retrieval_adapter import (
    convert_search_results_to_evidence,
)


def retrieve_venue_evidence(
    venue_id: str,
    query: str,
    n_results: int = 3,
):
    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    query_embedding = embed_query(query)

    results = search_documents(
        collection=collection,
        query=query,
        query_embedding=query_embedding,
        n_results=n_results,
        venue_id=venue_id,
    )

    return convert_search_results_to_evidence(results)


def build_retrieval_query(
    scenario: DisruptionScenario,
) -> str | None:

    if scenario.scenario_type == DisruptionType.WEATHER:
        return (
            f"{scenario.weather_condition.value} weather, "
            "visitor guidance, weather-related closures, "
            "and safety restrictions. "
            f"Additional context: {scenario.description}"
        )

    if scenario.scenario_type == DisruptionType.VENUE_UNAVAILABLE:
        return (
            "Venue closures, operating hours, temporary "
            "closures, and visitor access restrictions. "
            f"Additional context: {scenario.description}"
        )

    if scenario.scenario_type == DisruptionType.TRAVEL_DELAY:
        return None

    return None


def build_evidence_claim(
    scenario: DisruptionScenario,
) -> str | None:

    if scenario.scenario_type == DisruptionType.WEATHER:
        return (
            "The venue has weather-related closures "
            "or visitor safety restrictions."
        )

    if scenario.scenario_type == DisruptionType.VENUE_UNAVAILABLE:
        return scenario.description

    return None


def run_investigation(
    itinerary: Itinerary,
    scenario: DisruptionScenario,
    venue_id: str,
    latitude: float,
    longitude: float,
) -> InvestigationResult:

    # Weather Collection
    weather_result = None
    investigation_warnings = []

    if scenario.scenario_type.value == "weather":
        weather_result = get_weather_data(latitude, longitude)

        if weather_result.retrieval_status.value != "success":
            investigation_warnings.append(
                "Weather data retrieval was incomplete or failed."
            )

    # Retrieval
    retrieved_evidence = []

    retrieval_query = build_retrieval_query(scenario)

    if retrieval_query is not None:
        try:
            retrieved_evidence = retrieve_venue_evidence(
                venue_id=venue_id,
                query=retrieval_query,
            )

            if not retrieved_evidence:
                investigation_warnings.append(
                    "No relevant venue documents were retrieved."
                )

        except Exception as error:
            investigation_warnings.append(
                f"Venue document retrieval failed: {error}"
            )

    # Evidence
    evidence_assessments = []

    evidence_claim = build_evidence_claim(scenario)

    if evidence_claim is not None and retrieved_evidence:
        assessment = assess_claim_evidence(
            claim=evidence_claim,
            evidence=retrieved_evidence,
        )

        evidence_assessments.append(assessment)

    routing_validation = validate_itinerary(itinerary)

    return InvestigationResult(
        investigation_id=f"investigation_{scenario.scenario_id}",
        scenario_id=scenario.scenario_id,
        weather_result=weather_result,
        retrieved_evidence=retrieved_evidence,
        evidence_assessments=evidence_assessments,
        routing_validation=routing_validation,
        investigation_warnings=investigation_warnings,
    )
