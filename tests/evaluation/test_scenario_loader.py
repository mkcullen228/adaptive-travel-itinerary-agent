from pathlib import Path

import pytest

from src.evaluation.scenario_loader import (
    load_scenario,
    load_scenarios,
)


SCENARIO_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluations"
    / "evidence_quality"
    / "scenarios"
)


def test_load_all_evidence_quality_scenarios():
    scenarios = load_scenarios(SCENARIO_DIR)

    assert len(scenarios) == 5
    assert {scenario.scenario_id for scenario in scenarios} == {
        "E1", "E2", "E3", "E4", "E5"
    }


@pytest.mark.parametrize(
    "scenario_id",
    ["E1", "E2", "E3", "E4", "E5"],
)
def test_load_individual_scenario(scenario_id):
    scenarios = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=[scenario_id],
    )

    assert len(scenarios) == 1
    assert scenarios[0].scenario_id == scenario_id


def test_conflicting_scenario_has_two_evidence_records():
    scenario = load_scenario(
        SCENARIO_DIR / "E4_conflicting.json"
    )

    assert len(scenario.retrieved_evidence) == 2


def test_missing_scenario_has_no_evidence_records():
    scenario = load_scenario(
        SCENARIO_DIR / "E5_missing.json"
    )

    assert scenario.retrieved_evidence == []


def test_unknown_scenario_id_raises_error():
    with pytest.raises(ValueError, match="not found"):
        load_scenarios(
            SCENARIO_DIR,
            scenario_ids=["E99"],
        )
