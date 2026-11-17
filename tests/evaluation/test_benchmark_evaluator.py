
from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.agent_workflow import RecoveryOption, RecoveryStrategy
from src.models.disruption import DisruptionScenario

from src.evaluation.benchmark_evaluator import evaluate_benchmark_case


def make_activity(activity_id, name, hour, minute=0):
    return Activity(
        activity_id=activity_id,
        name=name,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, hour, minute),
        duration_minutes=60,
    )


def make_itinerary(activities):
    return Itinerary(
        itinerary_id="test",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities,
    )


def test_benchmark_evaluator_returns_all_evaluation_sections():
    original = make_itinerary([
        make_activity("activity_1", "National Gallery", 9, 0),
    ])

    proposed = make_itinerary([
        make_activity("activity_1", "National Gallery", 9, 0),
    ])

    scenario = DisruptionScenario.model_construct(
        scenario_id="TEST-01",
        affected_activity_ids=[],
    )

    proposal = RecoveryOption.model_construct(
        option_id="OPTION-01",
        proposed_itinerary=proposed,
        rationale="The National Gallery is scheduled for 9:00 AM.",
    )

    result = evaluate_benchmark_case(
        original,
        scenario,
        proposal,
    )

    expected_sections = {
        "scenario_id",
        "proposal_id",
        "deterministic_validation",
        "recovery_consistency",
        "schedule_comparison",
        "schedule_robustness",
        "narrative_consistency",
    }

    assert set(result.keys()) == expected_sections


def test_benchmark_evaluator_does_not_modify_inputs():
    original = make_itinerary([
        make_activity("activity_1", "National Gallery", 9, 0),
    ])

    proposed = make_itinerary([
        make_activity("activity_1", "National Gallery", 9, 0),
    ])

    original_before = original.model_dump(mode="json")
    proposed_before = proposed.model_dump(mode="json")

    scenario = DisruptionScenario.model_construct(
        scenario_id="TEST-01",
        affected_activity_ids=[],
    )

    proposal = RecoveryOption.model_construct(
        option_id="OPTION-01",
        proposed_itinerary=proposed,
        rationale="The National Gallery is scheduled for 9:00 AM.",
    )

    evaluate_benchmark_case(original, scenario, proposal)

    assert original.model_dump(mode="json") == original_before
    assert proposed.model_dump(mode="json") == proposed_before
