
from pydantic import BaseModel

from src.evaluation.scenario_loader import EvidenceQualityScenario
from src.models.agent_workflow import (
    RecoveryOption,
    RecoveryProposalStatus,
)
from src.models.itinerary import Itinerary


class PlannerEvaluationResult(BaseModel):
    scenario_id: str
    mandatory_visit_preserved: bool
    no_duplicate_visit: bool
    evidence_provenance_passed: bool
    uncertainty_communicated: bool
    availability_caveat_passed: bool
    verification_requested: bool
    conflict_acknowledged: bool
    cautious_proposal_status: bool
    passed: bool
    failures: list[str]


def evaluate_planner_output(
    scenario: EvidenceQualityScenario,
    original_itinerary: Itinerary,
    recovery_option: RecoveryOption,
) -> PlannerEvaluationResult:
    """Evaluate a Planner's RecoveryOption against scenario expectations."""

    expected = scenario.expected_planner_behavior
    mandatory_name = scenario.base_case.mandatory_activity_name.casefold()

    failures = []

    original_mandatory = [
        activity
        for activity in original_itinerary.activities
        if activity.name.casefold() == mandatory_name
        and activity.mandatory
    ]

    proposed_matches = [
        activity
        for activity in recovery_option.proposed_itinerary.activities
        if activity.name.casefold() == mandatory_name
    ]

    # Check that the original mandatory activity is retained.
    mandatory_visit_preserved = (
        len(original_mandatory) == 1
        and len(proposed_matches) == 1
        and proposed_matches[0].activity_id
        == original_mandatory[0].activity_id
        and proposed_matches[0].mandatory
    )

    if expected.must_preserve_mandatory_visit and not mandatory_visit_preserved:
        failures.append(
            "The original mandatory Natural History Museum visit "
            "was not preserved."
        )

    # Check that the proposal does not introduce duplicate visits.
    no_duplicate_visit = len(proposed_matches) == 1

    if expected.must_not_add_duplicate_visit and not no_duplicate_visit:
        failures.append(
            "The proposal contains a duplicate or missing "
            "Natural History Museum visit."
        )

    # Validate every cited source against the original investigation evidence.
    available_source_ids = {
        evidence.source_id for evidence in scenario.retrieved_evidence
    }

    invalid_source_ids = (
        set(recovery_option.supporting_evidence_ids) - available_source_ids
    )

    evidence_provenance_passed = not invalid_source_ids

    if not evidence_provenance_passed:
        failures.append(
            "Planner referenced unavailable evidence IDs: "
            f"{sorted(invalid_source_ids)}"
        )

    # Gather the Planner's explanatory text for qualitative checks.
    explanatory_text = " ".join(
        [
            recovery_option.rationale,
            *recovery_option.assumptions,
            *recovery_option.uncertainties,
            *recovery_option.trade_offs,
        ]
    ).casefold()

    uncertainty_communicated = bool(recovery_option.uncertainties)

    if expected.must_communicate_unresolved_questions:
        if not uncertainty_communicated:
            failures.append(
                "Planner did not communicate unresolved uncertainties."
            )

    # For evidence conditions weaker than SUPPORTED, require a
    # non-complete proposal and an explicit caveat.
    requires_caution = (
        scenario.expected_researcher_output.status.value != "supported"
    )

    availability_caveat_passed = True

    if expected.must_not_claim_unverified_availability and requires_caution:
        availability_caveat_passed = (
            recovery_option.proposal_status
            != RecoveryProposalStatus.COMPLETE
            and bool(recovery_option.uncertainties
                    or recovery_option.assumptions)
        )

        if not availability_caveat_passed:
            failures.append(
                "Planner treated an insufficiently supported recovery "
                "option as complete or omitted its caveats."
            )

    # Verification requests must be communicated in the Planner's text.
    verification_requested = True

    if (
        expected.must_request_verification
        or expected.must_request_current_verification
        or expected.must_request_conflict_resolution
    ):
        verification_terms = (
            "verify",
            "verification",
            "confirm",
            "confirmation",
            "check",
        )

        verification_requested = any(
            term in explanatory_text for term in verification_terms
        )

        if not verification_requested:
            failures.append(
                "Planner did not communicate a need for verification."
            )

    # Conflicting evidence must be explicitly acknowledged.
    conflict_acknowledged = True

    if expected.must_identify_conflicting_information:
        conflict_acknowledged = "conflict" in explanatory_text

        if not conflict_acknowledged:
            failures.append(
                "Planner did not acknowledge conflicting evidence."
            )

    # The model has no confidence field. Use proposal status as a
    # conservative proxy for whether the proposal is treated as complete.
    cautious_proposal_status = True

    if expected.must_avoid_high_confidence:
        cautious_proposal_status = (
            recovery_option.proposal_status
            != RecoveryProposalStatus.COMPLETE
        )

        if not cautious_proposal_status:
            failures.append(
                "Planner marked a proposal complete despite the "
                "scenario requiring cautious handling."
            )

    checks = [
        not expected.must_preserve_mandatory_visit
        or mandatory_visit_preserved,
        not expected.must_not_add_duplicate_visit
        or no_duplicate_visit,
        evidence_provenance_passed,
        not expected.must_communicate_unresolved_questions
        or uncertainty_communicated,
        availability_caveat_passed,
        verification_requested,
        conflict_acknowledged,
        cautious_proposal_status,
    ]

    return PlannerEvaluationResult(
        scenario_id=scenario.scenario_id,
        mandatory_visit_preserved=mandatory_visit_preserved,
        no_duplicate_visit=no_duplicate_visit,
        evidence_provenance_passed=evidence_provenance_passed,
        uncertainty_communicated=uncertainty_communicated,
        availability_caveat_passed=availability_caveat_passed,
        verification_requested=verification_requested,
        conflict_acknowledged=conflict_acknowledged,
        cautious_proposal_status=cautious_proposal_status,
        passed=all(checks),
        failures=failures,
    )
