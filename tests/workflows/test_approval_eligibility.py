from src.models.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from src.workflows.multi_agent_recovery import is_approval_eligible


def test_valid_proposal_is_eligible_for_approval():
    result = ValidationResult(status=ValidationStatus.VALID)

    assert is_approval_eligible(result) is True


def test_incomplete_proposal_is_eligible_for_approval():
    result = ValidationResult(
        status=ValidationStatus.INCOMPLETE,
        issues=[
            ValidationIssue(
                issue_type="missing_travel_estimate",
                description="Walking travel time has not been verified.",
            )
        ],
    )

    assert is_approval_eligible(result) is True


def test_invalid_proposal_is_not_eligible_for_approval():
    result = ValidationResult(
        status=ValidationStatus.INVALID,
        issues=[
            ValidationIssue(
                issue_type="mandatory_activity_not_preserved",
                description="A mandatory activity is missing.",
            )
        ],
    )

    assert is_approval_eligible(result) is False


def test_missing_validation_result_is_not_eligible():
    assert is_approval_eligible(None) is False


def test_incomplete_validation_details_are_preserved():
    issue = ValidationIssue(
        issue_type="missing_travel_estimate",
        description="Walking travel time has not been verified.",
    )
    result = ValidationResult(
        status=ValidationStatus.INCOMPLETE,
        issues=[issue],
    )

    assert is_approval_eligible(result) is True
    assert result.status == ValidationStatus.INCOMPLETE
    assert result.issues[0].description == (
        "Walking travel time has not been verified."
    )

