
from datetime import datetime, timezone

from src.models.investigation import InvestigationResult
from src.models.weather import WeatherDataResult, WeatherRetrievalStatus
from src.models.validation import ValidationResult, ValidationStatus


def test_valid_investigation_result():
    weather = WeatherDataResult(
        latitude=38.8977,
        longitude=-77.0365,
        retrieved_at=datetime.now(timezone.utc),
        forecast_source_url="https://api.weather.gov/gridpoints/LWX/...",
        alerts_source_url="https://api.weather.gov/alerts/active",
        retrieval_status=WeatherRetrievalStatus.SUCCESS,
    )

    validation = ValidationResult(
        status=ValidationStatus.VALID,
        issues=[],
    )

    result = InvestigationResult(
        investigation_id="investigation_001",
        scenario_id="scenario_001",
        weather_result=weather,
        routing_validation=validation,
    )

    assert result.investigation_id == "investigation_001"
    assert result.scenario_id == "scenario_001"
    assert result.weather_result.retrieval_status == WeatherRetrievalStatus.SUCCESS
    assert result.routing_validation.status == ValidationStatus.VALID


def test_investigation_result_allows_missing_optional_results():
    result = InvestigationResult(
        investigation_id="investigation_002",
        scenario_id="scenario_002",
    )

    assert result.weather_result is None
    assert result.routing_validation is None


def test_investigation_result_defaults_evidence_lists_to_empty():
    result = InvestigationResult(
        investigation_id="investigation_003",
        scenario_id="scenario_003",
    )

    assert result.retrieved_evidence == []
    assert result.evidence_assessments == []
    assert result.investigation_warnings == []


def test_investigation_result_generates_created_at():
    before = datetime.now(timezone.utc)

    result = InvestigationResult(
        investigation_id="investigation_004",
        scenario_id="scenario_004",
    )

    after = datetime.now(timezone.utc)

    assert before <= result.created_at <= after
    assert result.created_at.tzinfo is not None
