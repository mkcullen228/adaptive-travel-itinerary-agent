from pathlib import Path

from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
print(PROJECT_ROOT)
DISRUPTION_PATH = (
    PROJECT_ROOT / "tests/fixtures/p02_disruption_scenario.json"
)

INVESTIGATION_PATH = (
    PROJECT_ROOT / "tests/fixtures/p02_investigation_context.json"
)


def test_p02_disruption_fixture_loads():
    print("\n")
    print(DISRUPTION_PATH)
    scenario = DisruptionScenario.model_validate_json(
        DISRUPTION_PATH.read_text(encoding="utf-8")
    )

    assert scenario.scenario_id == "P-02"
    assert scenario.scenario_type.value == "weather"
    assert scenario.weather_condition.value == "heavy_rain"
    assert scenario.affected_activity_ids == [
        "wwii_memorial",
        "lincoln_memorial",
    ]


def test_p02_investigation_fixture_loads():
    investigation = InvestigationResult.model_validate_json(
        INVESTIGATION_PATH.read_text(encoding="utf-8")
    )

    assert investigation.scenario_id == "P-02"
    assert investigation.weather_result is not None
    assert investigation.weather_result.retrieval_status.value == "success"
    assert investigation.retrieved_evidence == []
