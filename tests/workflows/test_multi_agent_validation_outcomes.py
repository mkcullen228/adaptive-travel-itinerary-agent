
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from src.models.activity import Activity
from src.models.agent_state import WorkflowStage, WorkflowStatus
from src.models.multi_agent import EvidenceBrief, AuditReport
from src.models.validation import ValidationStatus
from src.models.agent_workflow import (
    Constraint,
    ConstraintPriority,
    ConstraintType,
    ApprovalStatus
)
from src.workflows.multi_agent_recovery import (
    build_multi_agent_recovery_graph,
)
from tests.workflows.test_single_agent_recovery import make_state


def run_mocked_recovery(monkeypatch, state, proposed_itinerary):
    """Run the multi-agent graph with mocked agent responses."""

    recovery_option = Mock()
    recovery_option.option_id = "test-option"
    recovery_option.supporting_evidence_ids = []
    recovery_option.rationale = "Test recovery rationale"
    recovery_option.proposed_itinerary = proposed_itinerary

    audit_report = AuditReport(
        assessment="partially_supported",
        supported_claims=[],
        unsupported_claims=[],
        conflicting_claims=[],
        omitted_uncertainties=[],
        rationale_findings=[],
        recommendations=[],
    )

    research_result = SimpleNamespace(
        evidence_brief=EvidenceBrief(),
        raw_response='{"findings": []}',
        model_name="qwen3.5:4b",
        latency_seconds=1.0,
        input_tokens=100,
        output_tokens=50,
    )

    planning_result = SimpleNamespace(
        recovery_option=recovery_option,
        raw_response='{"option_id": "test-option"}',
        model_name="qwen3.5:4b",
        latency_seconds=2.0,
        input_tokens=200,
        output_tokens=100,
    )

    audit_result = SimpleNamespace(
        audit_report=audit_report,
        raw_response='{"assessment": "partially_supported"}',
        model_name="qwen3.5:4b",
        latency_seconds=1.5,
        input_tokens=150,
        output_tokens=75,
    )

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.research_evidence",
        Mock(return_value=research_result),
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.plan_recovery",
        Mock(return_value=planning_result),
    )

    audit_mock = Mock(return_value=audit_result)

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.audit_recovery_proposal",
        audit_mock,
    )

    graph = build_multi_agent_recovery_graph(client=Mock())
    result = graph.invoke(state)

    return result, audit_mock


def test_invalid_mandatory_activity_proposal_is_not_valid_recovery(
    monkeypatch,
):
    state = make_state()

    # The original itinerary is empty. This mandatory constraint
    # therefore has no matching activity in the proposed itinerary.
    state["mandatory_constraints"] = [
        Constraint(
            constraint_id="constraint_001",
            description="Visit the National Gallery",
            constraint_type=ConstraintType.MANDATORY,
            category="activity",
            priority=ConstraintPriority.HIGH,
            value="National Gallery of Art",
        )
    ]

    proposed_itinerary = state["original_itinerary"].model_copy()

    result, audit_mock = run_mocked_recovery(
        monkeypatch,
        state,
        proposed_itinerary,
    )

    assert result["itinerary_validation_result"].status == (
        ValidationStatus.INVALID
    )

    assert result["status"] == WorkflowStatus.NO_VALID_RECOVERY

    assert result["final_itinerary"] is None

    assert any(
        "no exact match" in issue.description
        for issue in result["itinerary_validation_result"].issues
    )

    # Auditor still runs, but its assessment cannot override validation.
    audit_mock.assert_called_once()

    assert result["audit_report"].assessment.value == (
        "partially_supported"
    )


def test_incomplete_proposal_remains_available_with_warnings(
    monkeypatch,
):
    state = make_state()

    first_activity = Activity(
        activity_id="activity_001",
        name="National Gallery",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=60,
        mandatory=False,
        indoor=True,
    )

    second_activity = Activity(
        activity_id="activity_002",
        name="Smithsonian Museum",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 12, 0),
        duration_minutes=60,
        mandatory=False,
        indoor=True,
    )

    # No travel leg or walking estimate is provided between
    # consecutive activities, so feasibility is incomplete.
    proposed_itinerary = state["original_itinerary"].model_copy(
        update={
            "activities": [first_activity, second_activity],
            "travel_legs": [],
        }
    )

    result, audit_mock = run_mocked_recovery(
        monkeypatch,
        state,
        proposed_itinerary,
    )

    assert result["itinerary_validation_result"].status == (
        ValidationStatus.INCOMPLETE
    )
    assert result["status"] == WorkflowStatus.AWAITING_APPROVAL
    assert result["approval_status"] == ApprovalStatus.PENDING
    assert result["current_stage"] == WorkflowStage.APPROVAL
    assert result["final_itinerary"] is None

    assert result["recovery_options"]

    assert any(
        "incomplete" in warning.lower()
        for warning in result["warnings"]
    )

    # Auditor runs, but does not convert INCOMPLETE into VALID.
    audit_mock.assert_called_once()

    assert result["itinerary_validation_result"].status == (
        ValidationStatus.INCOMPLETE
    )
