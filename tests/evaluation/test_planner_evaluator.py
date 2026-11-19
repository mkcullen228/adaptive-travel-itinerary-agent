
from datetime import date, datetime
from pathlib import Path

import pytest

from src.evaluation.scenario_loader import load_scenarios
from src.evaluation.planner_evaluator import evaluate_planner_output
from src.models.activity import Activity
from src.models.agent_workflow import (
    RecoveryOption,
    RecoveryProposalStatus,
    RecoveryStrategy,
)
from src.models.itinerary import Itinerary


SCENARIO_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluations"
    / "evidence_quality"
    / "scenarios"
)


def make_original_itinerary():
    return Itinerary(
        itinerary_id="P-01",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_gallery",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
            Activity(
                activity_id="activity_natural_history",
                name="National Museum of Natural History",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 12, 0),
                duration_minutes=90,
                mandatory=True,
            ),
        ],
    )


def make_recovery_option(
    original_itinerary,
    scenario,
    proposal_status=RecoveryProposalStatus.REQUIRES_INVESTIGATION,
    uncertainties=None,
    assumptions=None,
    rationale="The recovery option requires verification.",
    supporting_evidence_ids=None,
    duplicate_visit=False,
):
    activities = list(original_itinerary.activities)

    if duplicate_visit:
        activities.append(
            Activity(
                activity_id="activity_natural_history_duplicate",
                name="National Museum of Natural History",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 14, 0),
                duration_minutes=60,
                mandatory=False,
            )
        )

    return RecoveryOption(
        option_id="recovery_001",
        strategy=RecoveryStrategy.MINIMAL_DISRUPTION,
        proposed_itinerary=Itinerary(
            itinerary_id="P-01_recovered",
            destination="Washington, DC",
            itinerary_date=date(2026, 11, 7),
            activities=activities,
        ),
        proposal_status=proposal_status,
        rationale=rationale,
        supporting_evidence_ids=(
            supporting_evidence_ids
            if supporting_evidence_ids is not None
            else scenario.expected_researcher_output.supporting_source_ids
        ),
        uncertainties=(
            uncertainties
            if uncertainties is not None
            else ["Current availability requires verification."]
        ),
        assumptions=assumptions or [],
    )


@pytest.mark.parametrize(
    "scenario_id",
    ["E1", "E2", "E3", "E4", "E5"],
)
def test_valid_recovery_option_passes(scenario_id):
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=[scenario_id],
    )[0]

    original = make_original_itinerary()

    # E1 has supported evidence; the remaining scenarios require caution.
    status = (
        RecoveryProposalStatus.COMPLETE
        if scenario_id == "E1"
        else RecoveryProposalStatus.REQUIRES_INVESTIGATION
    )

    option = make_recovery_option(
        original,
        scenario,
        proposal_status=status,
        rationale=(
            "The recovery option is supported by the available evidence. "
            if scenario_id == "E1"
            else "The recovery option requires verification of availability "
                 "and resolution of any evidence conflict."
        ),
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is True, result.failures


def test_missing_mandatory_visit_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E1"],
    )[0]

    original = make_original_itinerary()
    option = make_recovery_option(original, scenario)

    option.proposed_itinerary.activities = [
        activity
        for activity in option.proposed_itinerary.activities
        if activity.name != "National Museum of Natural History"
    ]

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.mandatory_visit_preserved is False


def test_duplicate_mandatory_visit_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E1"],
    )[0]

    original = make_original_itinerary()
    option = make_recovery_option(
        original,
        scenario,
        duplicate_visit=True,
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.no_duplicate_visit is False


def test_invalid_evidence_source_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E1"],
    )[0]

    original = make_original_itinerary()
    option = make_recovery_option(
        original,
        scenario,
        supporting_evidence_ids=["unknown_source"],
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.evidence_provenance_passed is False


def test_missing_uncertainty_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E5"],
    )[0]

    original = make_original_itinerary()
    option = make_recovery_option(
        original,
        scenario,
        uncertainties=[],
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.uncertainty_communicated is False


def test_complete_proposal_fails_when_evidence_is_missing():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E5"],
    )[0]

    original = make_original_itinerary()
    option = make_recovery_option(
        original,
        scenario,
        proposal_status=RecoveryProposalStatus.COMPLETE,
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.cautious_proposal_status is False


def test_conflicting_evidence_must_be_acknowledged():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E4"],
    )[0]

    original = make_original_itinerary()
    option = make_recovery_option(
        original,
        scenario,
        rationale="The option may be possible.",
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.conflict_acknowledged is False
