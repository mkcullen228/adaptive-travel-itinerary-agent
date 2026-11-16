
from pathlib import Path

from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario
from src.models.agent_workflow import RecoveryOption
from src.evaluation.recovery_consistency import (
    evaluate_recovery_consistency,
)


ROOT = Path(__file__).resolve().parents[2]

BASELINE_PATH = (
    ROOT / "data/itineraries/dc_baseline_2026_11_07_p02.json"
)

SCENARIO_PATH = (
    ROOT / "tests/fixtures/p02_disruption_scenario.json"
)

ITERATION_1_PATH = (
    ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/P-02/iteration_1.md"
)

ITERATION_2_PATH = (
    ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/P-02/iteration_2.md"
)


def load_inputs(response_path):
    original = Itinerary.model_validate_json(
        BASELINE_PATH.read_text(encoding="utf-8")
    )

    scenario = DisruptionScenario.model_validate_json(
        SCENARIO_PATH.read_text(encoding="utf-8")
    )

    proposal = RecoveryOption.model_validate_json(
        response_path.read_text(encoding="utf-8")
    )

    return original, scenario, proposal


def test_p02_iteration_1_detects_affected_activities_unchanged():
    original, scenario, proposal = load_inputs(ITERATION_1_PATH)

    result = evaluate_recovery_consistency(
        original, scenario, proposal
    )

    assert result["all_mandatory_activities_preserved"] is True
    assert result["all_affected_activities_addressed"] is False
    assert result["unresolved_affected_activity_ids"] == [
        "wwii_memorial",
        "lincoln_memorial",
    ]


def test_p02_iteration_2_detects_narrative_schedule_mismatch():
    original, scenario, proposal = load_inputs(ITERATION_2_PATH)

    result = evaluate_recovery_consistency(
        original, scenario, proposal
    )

    assert result["all_mandatory_activities_preserved"] is True
    assert result["all_affected_activities_addressed"] is False
    assert result["unresolved_affected_activity_ids"] == [
        "wwii_memorial",
        "lincoln_memorial",
    ]
