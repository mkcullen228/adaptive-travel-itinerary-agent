from datetime import date, datetime, timezone
from unittest import result
from unittest.mock import patch, MagicMock

from src.models.disruption import (
    DisruptionScenario,
    DisruptionType,
    DisruptionSeverity,
    WeatherCondition,
)
from src.models.validation import ValidationStatus
from src.workflows.investigation_workflow import (run_investigation, retrieve_venue_evidence, 
                                                  build_retrieval_query, build_evidence_claim)
from src.models.weather import WeatherDataResult, WeatherRetrievalStatus
from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.retrieved_evidence import RetrievedEvidence
from src.models.evidence import (
    EvidenceAssessment,
    EvidenceStatus,
    EvidenceRelevance,
    EvidenceCoverage,
)
from src.models.source_reference import VerificationStatus


def make_test_itinerary():
    return Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="washington_monument",
                name="Washington Monument",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=60,
                mandatory=True,
                indoor=False,
            )
        ],
    )



@patch("src.workflows.investigation_workflow.get_weather_data")
def test_weather_scenario_retrieves_weather(mock_get_weather):
    scenario = DisruptionScenario(
        scenario_id="weather_001",
        scenario_type=DisruptionType.WEATHER,
        description="Heavy rain during the afternoon.",
        severity=DisruptionSeverity.HIGH,
        weather_condition=WeatherCondition.HEAVY_RAIN,
        affected_time_start="2026-11-07T12:00:00Z",
        affected_time_end="2026-11-07T16:00:00Z",
    )

    mock_get_weather.return_value = WeatherDataResult(
        latitude=38.8895,
        longitude=-77.0353,
        retrieved_at=datetime.now(timezone.utc),
        forecast_source_url="https://api.weather.gov/gridpoints/LWX/...",
        alerts_source_url="https://api.weather.gov/alerts/active",
        retrieval_status=WeatherRetrievalStatus.SUCCESS,
    )

    result = run_investigation(
        itinerary=make_test_itinerary(),
        scenario=scenario,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
    )

    mock_get_weather.assert_called_once_with(38.8895, -77.0353)
    assert result.weather_result == mock_get_weather.return_value


@patch("src.workflows.investigation_workflow.get_weather_data")
def test_non_weather_scenario_skips_weather_retrieval(mock_get_weather):
    scenario = DisruptionScenario(
        scenario_id="delay_001",
        scenario_type=DisruptionType.TRAVEL_DELAY,
        description="Walking route is delayed by 15 minutes.",
        severity=DisruptionSeverity.MODERATE,
        additional_duration_minutes=15,
    )

    run_investigation(
        itinerary=make_test_itinerary(),
        scenario=scenario,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
    )

    mock_get_weather.assert_not_called()


@patch("src.workflows.investigation_workflow.convert_search_results_to_evidence")
@patch("src.workflows.investigation_workflow.search_documents")
@patch("src.workflows.investigation_workflow.embed_query")
@patch("src.workflows.investigation_workflow.get_or_create_collection")
@patch("src.workflows.investigation_workflow.create_vector_store_client")
def test_retrieve_venue_evidence(
    mock_create_client,
    mock_get_collection,
    mock_embed_query,
    mock_search,
    mock_convert,
):
    mock_embed_query.return_value = [0.1, 0.2, 0.3]
    mock_search.return_value = {"ids": [["chunk_1"]]}
    mock_convert.return_value = ["evidence_1"]

    result = retrieve_venue_evidence(
        venue_id="washington_monument",
        query="Washington Monument ticket requirements",
        n_results=3,
    )

    mock_create_client.assert_called_once()
    mock_get_collection.assert_called_once()
    mock_embed_query.assert_called_once_with(
        "Washington Monument ticket requirements"
    )
    mock_search.assert_called_once_with(
        collection=mock_get_collection.return_value,
        query="Washington Monument ticket requirements",
        query_embedding=mock_embed_query.return_value,
        n_results=3,
        venue_id="washington_monument",
    )
    mock_convert.assert_called_once_with(mock_search.return_value)

    assert result == ["evidence_1"]


def test_weather_scenario_builds_weather_query():
    scenario = DisruptionScenario(
        scenario_id="weather_001",
        scenario_type=DisruptionType.WEATHER,
        description="Heavy rain during the afternoon.",
        severity=DisruptionSeverity.HIGH,
        weather_condition=WeatherCondition.HEAVY_RAIN,
        affected_time_start="2026-11-07T12:00:00Z",
        affected_time_end="2026-11-07T16:00:00Z",
    )

    query = build_retrieval_query(scenario)

    assert "heavy_rain" in query
    assert "weather-related closures" in query


def test_venue_unavailability_builds_closure_query():
    scenario = DisruptionScenario(
        scenario_id="venue_001",
        scenario_type=DisruptionType.VENUE_UNAVAILABLE,
        description="Washington Monument is unavailable.",
        severity=DisruptionSeverity.HIGH,
        affected_activity_ids=["washington_monument"],
    )

    query = build_retrieval_query(scenario)

    assert "temporary closures" in query
    assert "visitor access restrictions" in query


def test_travel_delay_skips_venue_retrieval():
    scenario = DisruptionScenario(
        scenario_id="delay_001",
        scenario_type=DisruptionType.TRAVEL_DELAY,
        description="Walking route delayed by 15 minutes.",
        severity=DisruptionSeverity.MODERATE,
        additional_duration_minutes=15,
    )

    assert build_retrieval_query(scenario) is None


def test_weather_scenario_builds_evidence_claim():
    scenario = DisruptionScenario(
        scenario_id="weather_01",
        scenario_type=DisruptionType.WEATHER,
        description="Heavy rain expected during the afternoon.",
        severity="moderate",
        weather_condition="heavy_rain",
        affected_time_start=datetime(2026, 11, 7, 12, 0),
        affected_time_end=datetime(2026, 11, 7, 16, 0),
    )

    claim = build_evidence_claim(scenario)

    assert claim == (
        "The venue has weather-related closures "
        "or visitor safety restrictions."
    )


def test_venue_unavailability_uses_scenario_description():
    scenario = DisruptionScenario(
        scenario_id="venue_01",
        scenario_type=DisruptionType.VENUE_UNAVAILABLE,
        description="Washington Monument is unavailable.",
        severity="high",
        affected_activity_ids=["washington_monument"],
    )

    claim = build_evidence_claim(scenario)

    assert claim == scenario.description


def test_travel_delay_does_not_build_evidence_claim():
    scenario = DisruptionScenario(
        scenario_id="delay_01",
        scenario_type=DisruptionType.TRAVEL_DELAY,
        description="Walking route is delayed.",
        severity="moderate",
        additional_duration_minutes=20,
    )

    claim = build_evidence_claim(scenario)

    assert claim is None


@patch("src.workflows.investigation_workflow.assess_claim_evidence")
@patch("src.workflows.investigation_workflow.retrieve_venue_evidence")
def test_run_investigation_assesses_retrieved_evidence(
    mock_retrieve,
    mock_assess,
):
    scenario = DisruptionScenario(
        scenario_id="venue_01",
        scenario_type=DisruptionType.VENUE_UNAVAILABLE,
        description="Washington Monument is unavailable.",
        severity="high",
        affected_activity_ids=["washington_monument"],
    )

    evidence = [
        RetrievedEvidence(
            chunk_id="nps_washington_monument_0",
            content="Visitors need a ticket to reach the top.",
            subject="National Park Service - Washington Monument",
            source_id="nps_washington_monument",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime.now(timezone.utc),
            similarity_distance=0.25,
            reliability=0.95,
            freshness_score=1.0,
            verification_status=VerificationStatus.UNVERIFIED,
        )
    ]

    expected_assessment = EvidenceAssessment(
        claim=scenario.description,
        status=EvidenceStatus.UNSUPPORTED,
        relevance=EvidenceRelevance.PARTIALLY_RELEVANT,
        coverage=EvidenceCoverage.PARTIAL,
        source_quality_assessed=True,
        source_quality_warnings=["Source has not been verified."],
        consistency_assessed=True,
        supporting_source_ids=[],
        conflicting_source_ids=[],
        explanation="The retrieved document does not establish that the venue is unavailable.",
    )

    mock_retrieve.return_value = evidence
    mock_assess.return_value = expected_assessment

    result = run_investigation(
        itinerary=make_test_itinerary(),
        scenario=scenario,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
    )

    mock_assess.assert_called_once_with(
        claim=scenario.description,
        evidence=evidence,
    )

    assert result.evidence_assessments == [expected_assessment]


@patch("src.workflows.investigation_workflow.retrieve_venue_evidence")
def test_run_investigation_handles_no_retrieved_evidence(mock_retrieve):
    scenario = DisruptionScenario(
        scenario_id="venue_02",
        scenario_type=DisruptionType.VENUE_UNAVAILABLE,
        description="Washington Monument is unavailable.",
        severity="high",
        affected_activity_ids=["washington_monument"],
    )

    mock_retrieve.return_value = []

    result = run_investigation(
        itinerary=make_test_itinerary(),
        scenario=scenario,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
    )

    assert result.retrieved_evidence == []
    assert result.evidence_assessments == []
    assert "No relevant venue documents were retrieved." in result.investigation_warnings


@patch("src.workflows.investigation_workflow.retrieve_venue_evidence")
def test_run_investigation_handles_retrieval_exception(mock_retrieve):
    scenario = DisruptionScenario(
        scenario_id="venue_03",
        scenario_type=DisruptionType.VENUE_UNAVAILABLE,
        description="Washington Monument is unavailable.",
        severity="high",
        affected_activity_ids=["washington_monument"],
    )

    mock_retrieve.side_effect = RuntimeError("Vector store unavailable")

    result = run_investigation(
        itinerary=make_test_itinerary(),
        scenario=scenario,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
    )

    assert result.retrieved_evidence == []
    assert result.evidence_assessments == []
    assert any(
        "Venue document retrieval failed: Vector store unavailable"
        in warning
        for warning in result.investigation_warnings
    )
    assert result.routing_validation is not None
    assert result.routing_validation.status == ValidationStatus.VALID