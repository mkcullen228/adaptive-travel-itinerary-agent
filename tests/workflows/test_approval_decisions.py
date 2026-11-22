
from types import SimpleNamespace

import pytest

from src.models.agent_state import WorkflowStage, WorkflowStatus
from src.models.agent_workflow import ApprovalStatus
from src.models.validation import (
    IssueType,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from src.workflows.multi_agent_recovery import apply_approval_decision
from tests.workflows.test_single_agent_recovery import make_state


def make_approval_state(validation_status=ValidationStatus.VALID):
    state = make_state()

    original_itinerary = state["original_itinerary"]
    proposed_itinerary = original_itinerary.model_copy()

    option = SimpleNamespace(
        option_id="test-option",
        proposed_itinerary=proposed_itinerary,
    )

    issues = []
    warnings = []

    if validation_status == ValidationStatus.INCOMPLETE:
        issues = [
            ValidationIssue(
                issue_type=IssueType.MISSING_TRAVEL_ESTIMATE,
                description="Walking time to the venue is unverified.",
                activity_ids=[],
            )
        ]
        warnings = [
            "The recovery proposal is incomplete.",
            "Walking time to the venue is unverified.",
        ]

    state.update({
        "recovery_options": [option],
        "selected_option_id": "test-option",
        "itinerary_validation_result": ValidationResult(
            status=validation_status,
            issues=issues,
        ),
        "approval_status": ApprovalStatus.PENDING,
        "status": WorkflowStatus.AWAITING_APPROVAL,
        "current_stage": WorkflowStage.APPROVAL,
        "warnings": warnings,
    })

    return state, proposed_itinerary


def test_approve_valid_proposal_sets_final_itinerary():
    state, proposed_itinerary = make_approval_state()

    result = apply_approval_decision(
        state,
        decision=ApprovalStatus.APPROVED,
    )

    assert result["approval_status"] == ApprovalStatus.APPROVED
    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["current_stage"] == WorkflowStage.COMPLETED
    assert result["final_itinerary"] is proposed_itinerary
    assert result["approval_history"][-1].status == ApprovalStatus.APPROVED
    assert result["approval_history"][-1].option_id == "test-option"


def test_approve_incomplete_proposal_preserves_validation_details():
    state, proposed_itinerary = make_approval_state(
        ValidationStatus.INCOMPLETE
    )

    original_issues = list(
        state["itinerary_validation_result"].issues
    )
    original_warnings = list(state["warnings"])

    result = apply_approval_decision(
        state,
        decision=ApprovalStatus.APPROVED,
    )

    assert result["approval_status"] == ApprovalStatus.APPROVED
    assert result["final_itinerary"] is proposed_itinerary

    # Approval must not erase the fact that validation was incomplete.
    assert (
        result["itinerary_validation_result"].status
        == ValidationStatus.INCOMPLETE
    )
    assert (
        result["itinerary_validation_result"].issues
        == original_issues
    )
    assert result["warnings"] == original_warnings


def test_reject_proposal_does_not_set_final_itinerary():
    state, _ = make_approval_state()

    result = apply_approval_decision(
        state,
        decision=ApprovalStatus.REJECTED,
        user_feedback="This recovery does not meet my needs.",
    )

    assert result["approval_status"] == ApprovalStatus.REJECTED
    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["current_stage"] == WorkflowStage.COMPLETED
    assert result["final_itinerary"] is None
    assert (
        result["approval_history"][-1].user_feedback
        == "This recovery does not meet my needs."
    )


def test_revision_request_records_feedback_and_returns_to_planning():
    state, _ = make_approval_state()

    result = apply_approval_decision(
        state,
        decision=ApprovalStatus.REVISION_REQUESTED,
        user_feedback="Please preserve the afternoon museum visit.",
    )

    assert (
        result["approval_status"]
        == ApprovalStatus.REVISION_REQUESTED
    )
    assert result["status"] == WorkflowStatus.IN_PROGRESS
    assert result["current_stage"] == WorkflowStage.RECOVERY_PLANNING
    assert result["final_itinerary"] is None
    assert result["revision_count"] == state["revision_count"] + 1
    assert (
        result["approval_history"][-1].user_feedback
        == "Please preserve the afternoon museum visit."
    )


def test_invalid_proposal_cannot_be_approved():
    state, _ = make_approval_state(ValidationStatus.INVALID)

    with pytest.raises(ValueError, match="not eligible for approval"):
        apply_approval_decision(
            state,
            decision=ApprovalStatus.APPROVED,
        )


def test_decision_requires_pending_approval():
    state, _ = make_approval_state()
    state["approval_status"] = ApprovalStatus.APPROVED

    with pytest.raises(ValueError, match="not awaiting approval"):
        apply_approval_decision(
            state,
            decision=ApprovalStatus.APPROVED,
        )
