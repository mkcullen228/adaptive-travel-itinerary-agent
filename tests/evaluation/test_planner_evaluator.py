
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import result

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
from src.models.travel import TravelEstimate, TravelLeg


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
                start_time=datetime(2026, 11, 7, 9, 0),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_american_history",
                name="American History",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 50),
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
    adjust_mandatory_visit=True,
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

    if adjust_mandatory_visit:
        for index, activity in enumerate(activities):
            if activity.name == "National Museum of Natural History":
                activities[index] = activity.model_copy(
                    update={
                        "start_time": datetime(2026, 11, 7, 11, 0)
                    }
                )

    return RecoveryOption(
        option_id="recovery_001",
        strategy=RecoveryStrategy.MINIMAL_DISRUPTION,
        proposed_itinerary=Itinerary(
            itinerary_id="P-01_recovered",
            destination="Washington, DC",
            itinerary_date=date(2026, 11, 7),
            activities=activities,
            travel_legs=[
                TravelLeg(
                    origin_activity_id=first.activity_id,
                    destination_activity_id=second.activity_id,
                    estimates=[
                        TravelEstimate(
                            mode="walking",
                            duration_minutes=10,
                            duration_seconds=600,
                            distance_meters=500,
                            source="test_fixture",
                        )
                    ],
                    selected_mode="walking",
                )
                for first, second in zip(
                    sorted(
                        activities,
                        key=lambda activity: activity.start_time,
                    ),
                    sorted(
                        activities,
                        key=lambda activity: activity.start_time,
                    )[1:],
                )
            ],
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


def make_evidence_brief(status, source_ids_reviewed):
    return SimpleNamespace(
        findings=[
            SimpleNamespace(status=status)
        ],
        source_ids_reviewed=source_ids_reviewed,
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

    rationale = (
        "The recovery option is supported by the available evidence. "
        "However, the revised itinerary remains provisional pending "
        "confirmation of the remaining activities."
        if scenario_id == "E1"
        else (
            "The recovery option requires verification of availability "
            "and resolution of any evidence conflict. The revised "
            "itinerary remains provisional pending confirmation of "
            "the remaining activities."
        )
    )

    option = make_recovery_option(
        original,
        scenario,
        proposal_status=status,
        rationale=rationale,
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
        rationale="The option may be possible."
    )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.conflict_acknowledged is False


def test_moving_unaffected_activity_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E3"],
    )[0]

    original = make_original_itinerary()

    option = make_recovery_option(original, scenario)

    # Move an unaffected activity from its original time.
    for index, activity in enumerate(
        option.proposed_itinerary.activities
    ):
        if activity.name == "American History":
            option.proposed_itinerary.activities[index] = (
                activity.model_copy(
                    update={
                        "start_time": datetime(2026, 11, 7, 9, 0)
                    }
                )
            )

    result = evaluate_planner_output(scenario, original, option)

    assert result.passed is False
    assert result.unaffected_activities_preserved is False
