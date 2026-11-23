
from datetime import date, datetime
from pathlib import Path

from src.evaluation.auditor_evaluator import (
    evaluate_auditor_output,
    _auditor_acknowledges_evidence_limitations,
    _auditor_covers_uncertainties
)
from src.evaluation.scenario_loader import load_scenarios
from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.multi_agent import AuditReport


SCENARIO_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluations"
    / "evidence_quality"
    / "scenarios"
)


def make_activity(
    activity_id="activity_natural_history",
    name="National Museum of Natural History",
    mandatory=True,
    start_hour=11,
    duration_minutes=90,
):
    return Activity(
        activity_id=activity_id,
        name=name,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, start_hour, 0),
        duration_minutes=duration_minutes,
        mandatory=mandatory,
    )


def make_itinerary(activities=None):
    if activities is None:
        activities = [make_activity()]

    return Itinerary(
        itinerary_id="P-01",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities,
    )


def make_report(
    supported_claims=None,
    unsupported_claims=None,
    conflicting_claims=None,
    omitted_uncertainties=None,
    rationale_findings=None,
    recommendations=None,
):
    return AuditReport(
        assessment="partially_supported",
        supported_claims=supported_claims or [],
        unsupported_claims=unsupported_claims or [],
        conflicting_claims=conflicting_claims or [],
        omitted_uncertainties=omitted_uncertainties or [],
        rationale_findings=rationale_findings or [],
        recommendations=recommendations or [],
    )


def load_scenario(scenario_id):
    return load_scenarios(
        SCENARIO_DIR,
        scenario_ids=[scenario_id],
    )[0]


def evaluate(
    scenario,
    original_itinerary,
    proposed_itinerary,
    report,
    deterministic_validation=None,
):
    return evaluate_auditor_output(
        scenario=scenario,
        original_itinerary=original_itinerary,
        proposed_itinerary=proposed_itinerary,
        audit_report=report,
        deterministic_validation=deterministic_validation,
    )


def test_auditor_must_not_claim_preserved_mandatory_visit_was_removed():
    scenario = load_scenario("E3")
    itinerary = make_itinerary()

    report = make_report(
        unsupported_claims=[
            "The mandatory activity was removed from the itinerary."
        ],
        rationale_findings=[
            "The stale evidence cannot confirm current availability."
        ],
        omitted_uncertainties=[
            "Current venue availability remains uncertain."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.mandatory_activity_accuracy is False
    assert result.passed is False
    assert any(
        "mandatory" in failure.casefold()
        for failure in result.failures
    )


def test_auditor_accepts_preserved_mandatory_visit():
    scenario = load_scenario("E3")
    itinerary = make_itinerary()

    report = make_report(
        supported_claims=[
            "The mandatory Natural History Museum visit is preserved."
        ],
        rationale_findings=[
            "The stale evidence cannot confirm current availability."
        ],
        omitted_uncertainties=[
            "Current venue availability remains uncertain."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.mandatory_activity_accuracy is True


def test_evaluator_fails_when_mandatory_visit_is_removed():
    scenario = load_scenario("E1")

    original = make_itinerary()
    proposed = make_itinerary(activities=[])

    report = make_report(
        rationale_findings=[
            "The available evidence supports the proposed recovery."
        ],
        omitted_uncertainties=[
            "Further verification may be needed."
        ],
    )

    result = evaluate(
        scenario,
        original,
        proposed,
        report,
    )

    assert result.mandatory_activity_accuracy is False
    assert result.passed is False


def test_evaluator_fails_when_mandatory_visit_is_duplicated():
    scenario = load_scenario("E1")

    original = make_itinerary()
    proposed = make_itinerary(
        activities=[
            make_activity(),
            make_activity(
                activity_id="duplicate_natural_history",
                start_hour=14,
            ),
        ]
    )

    report = make_report(
        rationale_findings=[
            "The available evidence supports the proposed recovery."
        ],
        omitted_uncertainties=[
            "Further verification may be needed."
        ],
    )

    result = evaluate(
        scenario,
        original,
        proposed,
        report,
    )

    assert result.mandatory_activity_accuracy is False
    assert result.passed is False


def test_auditor_must_acknowledge_conflicting_evidence():
    scenario = load_scenario("E4")
    itinerary = make_itinerary()

    report = make_report(
        supported_claims=[
            "The proposed recovery is supported by the evidence."
        ],
        rationale_findings=[
            "The sources disagree about whether the visit can be extended."
        ],
        omitted_uncertainties=[
            "The conflict requires resolution before availability can be confirmed."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.evidence_conflict_recognition is True


def test_auditor_must_not_pass_on_a_false_no_conflict_statement():
    scenario = load_scenario("E4")
    itinerary = make_itinerary()

    report = make_report(
        conflicting_claims=[
            "No material conflicting claims were found."
        ],
        rationale_findings=[
            "The proposal is supported."
        ],
        omitted_uncertainties=[
            "Further verification is required."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.evidence_conflict_recognition is False
    assert result.passed is False


def test_auditor_must_acknowledge_low_reliability_evidence():
    scenario = load_scenario("E2")
    itinerary = make_itinerary()

    report = make_report(
        rationale_findings=[
            "The source has low reliability and is unverified."
        ],
        omitted_uncertainties=[
            "The information requires verification before relying on it."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.evidence_limitation_recognition is True
    assert result.uncertainty_coverage is True


def test_auditor_must_acknowledge_stale_evidence():
    scenario = load_scenario("E3")
    itinerary = make_itinerary()

    report = make_report(
        rationale_findings=[
            "The stale evidence cannot confirm current availability."
        ],
        omitted_uncertainties=[
            "Current availability remains uncertain and requires verification."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.evidence_limitation_recognition is True
    assert result.uncertainty_coverage is True


def test_auditor_must_acknowledge_missing_evidence():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        rationale_findings=[
            "No retrieved evidence was available to verify the proposed recovery."
        ],
        omitted_uncertainties=[
            "The proposed recovery remains uncertain and requires verification."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.evidence_limitation_recognition is True
    assert result.uncertainty_coverage is True


def test_auditor_fails_when_missing_evidence_is_not_communicated():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        supported_claims=[
            "The proposed recovery is supported."
        ],
    )

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
    )

    assert result.evidence_limitation_recognition is False
    assert result.uncertainty_coverage is False
    assert result.passed is False


def test_auditor_must_acknowledge_schedule_time_mismatch():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        rationale_findings=[
            "No retrieved evidence was available to verify the proposed recovery.",
            "The rationale schedule time does not match the proposed itinerary.",
        ],
        omitted_uncertainties=[
            "The schedule remains inconsistent and requires review.",
            "The proposed recovery remains uncertain and requires verification.",
        ],
    )

    deterministic_validation = {
        "rationale_schedule_times_consistent": False,
        "schedule_consistency_passed": False,
        "failures": [
            "Rationale schedule time for National Museum of American History "
            "is 10:50 AM, but the proposed itinerary schedules it for 9:00 AM."
        ],
    }

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
        deterministic_validation,
    )

    assert result.schedule_accuracy is True
    assert result.uncertainty_coverage is True


def test_auditor_fails_when_schedule_mismatch_is_not_acknowledged():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        supported_claims=[
            "The proposed itinerary preserves the mandatory visit."
        ],
    )

    deterministic_validation = {
        "failures": [
            "Rationale schedule time does not match the proposed itinerary."
        ]
    }

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
        deterministic_validation,
    )

    assert result.schedule_accuracy is False
    assert result.uncertainty_coverage is False
    assert result.passed is False


def test_auditor_must_acknowledge_missing_travel_estimates():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        rationale_findings=[
            "No retrieved evidence was available to verify the proposed recovery.",
            "Walking travel estimates are missing for some activity transitions.",
        ],
        omitted_uncertainties=[
            "Travel time cannot be verified without those estimates.",
            "The proposed recovery remains uncertain and requires verification.",
        ],
    )

    deterministic_validation = {
        "failures": [
            "Missing walking travel estimate between two activities."
        ]
    }

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
        deterministic_validation,
    )

    assert result.schedule_accuracy is True
    assert result.uncertainty_coverage is True


def test_auditor_accepts_native_validation_issues_shape():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        rationale_findings=[
            "No retrieved evidence was available to verify the proposed recovery.",
            "Walking travel estimates are missing for this transition.",
        ],
        omitted_uncertainties=[
            "The travel time remains uncertain and cannot be verified.",
            "The proposed recovery requires further verification.",
        ],
    )

    deterministic_validation = {
        "issues": [
            {
                "issue_type": "missing_travel_estimate",
                "description": "Missing walking travel estimate."
            }
        ]
    }

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
        deterministic_validation,
    )

    assert result.schedule_accuracy is True
    assert result.uncertainty_coverage is True


def test_auditor_recognizes_lack_of_retrieved_evidence():
    scenario = load_scenario("E5")

    audit_text = (
        "The proposal reflects the lack of retrieved evidence sources."
    )

    assert _auditor_acknowledges_evidence_limitations(
        scenario,
        audit_text,
    )


def test_auditor_recognizes_cannot_verify_current_availability():
    scenario = load_scenario("E3")

    audit_text = (
        "The stale source cannot verify current or future "
        "availability for November 7, 2026. The evidence is "
        "not sufficient to confirm availability, so confidence "
        "should remain low pending current verification."
    )

    assert _auditor_covers_uncertainties(
        scenario,
        audit_text,
        deterministic_validation=None,
    )


def test_auditor_recognizes_e2_uncertainty_language():
    scenario = load_scenario("E2")

    audit_text = (
        "The proposal's claim lacks explicit evidentiary support. "
        "The source has a low reliability score (0.35) and "
        "verification status of unverified. The proposed time gaps "
        "cannot be guaranteed to allow sufficient arrival times. "
        "The opening hours assumption is a critical uncertainty "
        "requiring verification. Missing travel estimates mean "
        "schedule feasibility cannot be guaranteed."
    )

    deterministic_validation = {
        "status": "incomplete",
        "issues": [
            {
                "issue_type": "missing_travel_estimate",
                "description": "Missing selected travel estimate between consecutive activities.",
            }
        ],
    }

    assert _auditor_covers_uncertainties(
        scenario,
        audit_text,
        deterministic_validation,
    )


def test_e3_actual_auditor_response_acknowledges_uncertainty_but_not_stale_evidence():
    scenario = load_scenario("E3")
    itinerary = make_itinerary()

    report = make_report(
        supported_claims=[
            "The proposal correctly identifies the National Gallery of Art "
            "as unavailable based on the disruption scenario and removes it "
            "from the itinerary.",
            "The proposal preserves the mandatory visit to the National "
            "Museum of Natural History at its original scheduled time.",
            "The proposal acknowledges that travel estimates have not been "
            "verified and remaining activity availability has not been "
            "independently confirmed."
        ],
        omitted_uncertainties=[
            "The proposal fails to explicitly quantify the feasibility risk "
            "regarding the specific travel duration between American History "
            "and Natural History.",
            "The proposal assumes the National Museum of American History "
            "is open at 09:00 without providing evidence."
        ],
        rationale_findings=[
            "The proposal overstates certainty by stating schedule feasibility "
            "remains provisional while listing constraints as preserved "
            "without verifying travel time.",
            "The deterministic validation issues confirm that travel estimates "
            "are missing for all legs.",
            "The assumption about travel time is not supported by evidence."
        ],
        recommendations=[
            "Explicitly state that feasibility depends on an unverified travel "
            "duration between American History and Natural History.",
            "Clarify that the assumption regarding the National Museum of "
            "American History's availability at 09:00 is speculative.",
            "Do not claim schedule feasibility without addressing missing "
            "travel estimates."
        ]
    )

    deterministic_validation = {
        "status": "incomplete",
        "issues": [
            {
                "issue_type": "missing_travel_estimate",
                "description": (
                    "Missing selected travel estimate between consecutive activities."
                ),
            },
            {
                "issue_type": "missing_travel_estimate",
                "description": (
                    "Missing selected travel estimate between consecutive activities."
                ),
            },
            {
                "issue_type": "missing_travel_estimate",
                "description": (
                    "Missing selected travel estimate between consecutive activities."
                ),
            },
        ],
    }

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
        deterministic_validation,
    )

    assert result.mandatory_activity_accuracy is True
    assert result.evidence_limitation_recognition is False
    assert result.schedule_accuracy is True
    assert result.uncertainty_coverage is True
    assert result.passed is False


def test_e5_actual_auditor_response_recognizes_missing_evidence_and_uncertainty():
    scenario = load_scenario("E5")
    itinerary = make_itinerary()

    report = make_report(
        supported_claims=[
            "The proposal correctly identifies the National Gallery of Art "
            "as unavailable based on the disruption scenario description, "
            "despite the lack of independent evidence verification.",
            "The proposal accurately reflects that the mandatory visit to "
            "the National Museum of Natural History is preserved."
        ],
        unsupported_claims=[
            "The claim that schedule feasibility after removing the unavailable "
            "activity has not been assessed is partially unsupported because "
            "the proposal proceeds with a specific time shift without verifying "
            "whether subsequent activities can still be met.",
            "The assumption that walking time between American History and "
            "Natural History is negligible is unsupported by travel estimate data."
        ],
        omitted_uncertainties=[
            "The proposal fails to explicitly quantify the risk of the National "
            "Museum of Natural History being closed.",
            "The proposal does not address the potential cascading delay if "
            "walking time exceeds the available 90-minute window."
        ],
        rationale_findings=[
            "The proposal rationale acknowledges that no retrieved sources "
            "were available to verify the claim and that schedule feasibility "
            "has not been assessed.",
            "The deterministic validation results indicate three instances "
            "of missing travel estimates.",
            "The proposal treats missing travel estimates as negligible "
            "without acknowledging that schedule feasibility is incomplete."
        ],
        recommendations=[
            "The proposal should explicitly state that recovery actions are "
            "provisional pending verification of travel times.",
            "The rationale must directly reference deterministic validation "
            "issues regarding missing travel estimates.",
            "The proposal should clarify that the scheduled time for the "
            "mandatory activity has changed, introducing additional uncertainty."
        ]
    )

    deterministic_validation = {
        "status": "incomplete",
        "issues": [
            {
                "issue_type": "missing_travel_estimate",
                "description": (
                    "Missing selected travel estimate between consecutive activities."
                ),
            },
            {
                "issue_type": "missing_travel_estimate",
                "description": (
                    "Missing selected travel estimate between consecutive activities."
                ),
            },
            {
                "issue_type": "missing_travel_estimate",
                "description": (
                    "Missing selected travel estimate between consecutive activities."
                ),
            },
        ],
    }

    result = evaluate(
        scenario,
        itinerary,
        itinerary,
        report,
        deterministic_validation,
    )

    assert result.mandatory_activity_accuracy is True
    assert result.evidence_limitation_recognition is True
    assert result.schedule_accuracy is True
    assert result.uncertainty_coverage is True
    assert result.passed is True
