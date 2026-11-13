import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.disruption import (DisruptionScenario, DisruptionType, 
                                   DisruptionSeverity, WeatherCondition)


@pytest.fixture
def valid_weather_disruption():
    return {
        "scenario_id": "weather_001", 
        "scenario_type": DisruptionType.WEATHER,
        "description": "Heavy rain affects outdoor activities.",
        "affected_activity_ids": ["wwii_memorial", "lincoln_memorial"],
        "affected_travel_leg_ids": [],
        "severity": DisruptionSeverity.HIGH,
        "weather_condition": WeatherCondition.HEAVY_RAIN,
        "affected_time_start": datetime(2026, 11, 7, 10, 0),
        "affected_time_end": datetime(2026, 11, 7, 12, 0),
    }

@pytest.fixture
def valid_travel_disruption():
    return {
        "scenario_id": "delay_001", 
        "scenario_type": DisruptionType.TRAVEL_DELAY,
        "description": "Walking route is temporarily disrupted.",
        "affected_activity_ids": [],
        "affected_travel_leg_ids": ["natural_history_wwii_memorial"],
        "severity": DisruptionSeverity.HIGH,
        "additional_duration_minutes": 10
    }


def test_valid_weather_disruption(valid_weather_disruption):
    scenario = DisruptionScenario(**valid_weather_disruption)

    assert scenario.scenario_type == DisruptionType.WEATHER
    assert len(scenario.affected_activity_ids) == 2


def test_valid_travel_delay(valid_travel_disruption):
    scenario = DisruptionScenario(**valid_travel_disruption)

    assert scenario.scenario_type == DisruptionType.TRAVEL_DELAY
    assert scenario.additional_duration_minutes == 10
    assert len(scenario.affected_activity_ids) == 0
    assert len(scenario.affected_travel_leg_ids) == 1


def test_invalid_transportation_issue():
    with pytest.raises(ValidationError):
        scenario = DisruptionScenario(
            scenario_type="transportation_issue",
            description="Walking route is temporarily disrupted.",
            affected_activity_ids=[],
            affected_travel_leg_ids=["natural_history_wwii_memorial"],
            severity=DisruptionSeverity.MODERATE
        )


def test_invalid_severity():
    with pytest.raises(ValidationError):
        scenario = DisruptionScenario(
            scenario_id="delay_001",
            scenario_type=DisruptionType.TRAVEL_DELAY,
            description="Walking route is temporarily disrupted.",
            affected_activity_ids=[],
            affected_travel_leg_ids=["natural_history_wwii_memorial"],
            severity="extreme"
        )


def test_disruption_defaults_to_empty_lists():
    scenario = DisruptionScenario(
        scenario_id="delay_001",
        scenario_type=DisruptionType.TRAVEL_DELAY,
        description="Walking route is temporarily disrupted.",
        severity=DisruptionSeverity.HIGH,
        additional_duration_minutes=10
    )

    assert scenario.affected_activity_ids == []
    assert scenario.affected_travel_leg_ids == []
    assert scenario.source_references == []


def test_travel_delay_requires_delay_amount(valid_travel_disruption):
    data = valid_travel_disruption.copy()
    data.pop("additional_duration_minutes")

    with pytest.raises(ValidationError):
        DisruptionScenario(**data)


def test_travel_delay_rejects_both_delay_amounts(valid_travel_disruption):
    data = valid_travel_disruption.copy()
    data["additional_duration_percent"] = 25

    with pytest.raises(ValidationError):
        DisruptionScenario(**data)


def test_weather_rejects_travel_delay(valid_weather_disruption):
    data = valid_weather_disruption.copy()
    data["additional_duration_minutes"] = 10

    with pytest.raises(ValidationError):
        DisruptionScenario(**data)


def test_travel_rejects_weather_delay(valid_travel_disruption):
    data = valid_travel_disruption.copy()
    data["affected_time_start"] = datetime(2026, 11, 7, 12, 0)
    data["affected_time_end"] = datetime(2026, 11, 7, 13, 0)
    data['weather_condition'] = WeatherCondition.HEAVY_RAIN,

    with pytest.raises(ValidationError):
        DisruptionScenario(**data)


def test_weather_rejects_start_after_end(valid_weather_disruption):
    data = valid_weather_disruption.copy()
    data["affected_time_start"] = datetime(2026, 11, 7, 13, 0)
    data["affected_time_end"] = datetime(2026, 11, 7, 12, 0)

    with pytest.raises(ValidationError):
        DisruptionScenario(**data)


def test_venue_unavailability_requires_affected_activity():
    with pytest.raises(ValidationError):
        DisruptionScenario(
            scenario_id="closure_001",
            scenario_type=DisruptionType.VENUE_UNAVAILABLE,
            description="National Gallery is unavailable.",
            affected_activity_ids=[],
            severity=DisruptionSeverity.HIGH
        )


def test_valid_venue_unavailability():
    scenario = DisruptionScenario(
        scenario_id="closure_001",
        scenario_type=DisruptionType.VENUE_UNAVAILABLE,
        description="National Gallery is unavailable.",
        affected_activity_ids=["national_gallery"],
        severity=DisruptionSeverity.HIGH
    )

    assert scenario.scenario_type == DisruptionType.VENUE_UNAVAILABLE
    assert scenario.affected_activity_ids == ["national_gallery"]