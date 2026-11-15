import pytest
from datetime import date, datetime
from pydantic import ValidationError

from src.models.agent_workflow import (
    Constraint,
    ConstraintPriority,
    ConstraintType,
    ConstraintInterpretation,
    ConfirmationStatus,
    RecoveryOption,
    RejectedOption,
    OptionValidation,
    ApprovalStatus,
    ApprovalRecord,
    ConstraintChange, 
    ExecutionEvent
)
from src.models.itinerary import Itinerary
from src.models.validation import (
    ValidationResult,
    ValidationStatus,
)


def test_valid_mandatory_constraint():
    constraint = Constraint(
        constraint_id="C001",
        description="Visit the National Gallery",
        constraint_type=ConstraintType.MANDATORY,
        category="activity",
        priority=ConstraintPriority.HIGH,
        value="National Gallery of Art",
    )

    assert constraint.constraint_type == ConstraintType.MANDATORY
    assert constraint.priority == ConstraintPriority.HIGH


def test_valid_flexible_constraint():
    constraint = Constraint(
        constraint_id="C002",
        description="Prefer indoor activities",
        constraint_type=ConstraintType.FLEXIBLE,
        category="activity_type",
        priority=ConstraintPriority.MEDIUM,
        value="indoor",
    )

    assert constraint.constraint_type == ConstraintType.FLEXIBLE


def test_constraint_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        Constraint(
            constraint_id="C003",
            description="Test constraint",
            constraint_type=ConstraintType.FLEXIBLE,
            category="test",
            priority="urgent",
            value="test",
        )


def test_valid_constraint_interpretation():
    constraint = Constraint(
        constraint_id="C004",
        description="Prefer indoor activities",
        constraint_type=ConstraintType.FLEXIBLE,
        category="activity_type",
        priority=ConstraintPriority.MEDIUM,
        value="indoor",
    )

    interpretation = ConstraintInterpretation(
        original_instruction="I'd prefer to spend most of the afternoon indoors.",
        interpreted_constraint=constraint,
        confidence=0.85,
        requires_confirmation=True,
        confirmation_status=ConfirmationStatus.PENDING,
        interpretation_rationale="The user expressed a preference for indoor activities.",
    )

    assert interpretation.interpreted_constraint == constraint
    assert interpretation.confidence == 0.85
    assert interpretation.confirmation_status == ConfirmationStatus.PENDING


def test_valid_recovery_option():
    itinerary = Itinerary(
        itinerary_id="recovery_001",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[],
    )

    option = RecoveryOption(
        option_id="option_001",
        proposed_itinerary=itinerary,
        rationale="Replaces an unavailable venue with an alternative.",
        preserved_constraints=["C001"],
        violated_constraints=[],
        trade_offs=["Slightly longer walking distance"],
        supporting_evidence_ids=["E001"],
    )

    assert option.proposed_itinerary is itinerary
    assert option.preserved_constraints == ["C001"]
    assert option.violated_constraints == []
    assert option.supporting_evidence_ids == ["E001"]


def test_valid_rejected_option():
    rejected = RejectedOption(
        option_id="option_002",
        rejection_reason="Violates a mandatory timing constraint.",
    )

    assert rejected.option_id == "option_002"
    assert "mandatory timing constraint" in rejected.rejection_reason


def test_valid_option_validation():
    result = ValidationResult(
        status=ValidationStatus.INVALID,
        issues=[],
    )

    option_validation = OptionValidation(
        option_id="option_001",
        validation_result=result,
    )

    assert option_validation.option_id == "option_001"
    assert option_validation.validation_result.status == ValidationStatus.INVALID


def test_valid_approval_record():
    record = ApprovalRecord(
        option_id="option_001",
        status=ApprovalStatus.REVISION_REQUESTED,
        timestamp=datetime.now(),
        user_feedback="Please preserve the afternoon museum visit.",
    )

    assert record.option_id == "option_001"
    assert record.status == ApprovalStatus.REVISION_REQUESTED
    assert record.user_feedback == "Please preserve the afternoon museum visit."


def test_valid_constraint_change():
    change = ConstraintChange(
        constraint_id="C001",
        original_value="indoor",
        proposed_value="outdoor",
        reason="No feasible indoor alternatives are available.",
        approval_status=ApprovalStatus.PENDING,
    )

    assert change.constraint_id == "C001"
    assert change.original_value == "indoor"
    assert change.proposed_value == "outdoor"
    assert change.approval_status == ApprovalStatus.PENDING


def test_valid_execution_event():
    event = ExecutionEvent(
        event_id="event_001",
        stage="investigation",
        event_type="tool_call",
        description="Retrieved current weather forecast.",
        details={
            "tool": "nws_weather",
            "success": True,
            "result_count": 12,
        },
    )

    assert event.event_id == "event_001"
    assert event.stage == "investigation"
    assert event.details["tool"] == "nws_weather"
    assert event.details["success"] is True
    assert event.timestamp.tzinfo is not None
