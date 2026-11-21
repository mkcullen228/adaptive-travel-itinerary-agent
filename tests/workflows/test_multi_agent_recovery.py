from unittest import result

import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta

from src.models.retrieved_evidence import RetrievedEvidence
from src.models.source_reference import VerificationStatus
from src.models.activity import Activity
from src.models.agent_state import WorkflowStage, WorkflowStatus
from src.models.multi_agent import EvidenceBrief, AuditReport
from src.models.agent_workflow import (
    ApprovalRecord,
    Constraint,
    ConstraintPriority,
    ConstraintType,
    ApprovalStatus,
    RecoveryOption,
)
from src.models.validation import (
    IssueType,
    ValidationStatus,
)

from src.workflows.multi_agent_recovery import (
    apply_approval_decision,
    build_multi_agent_recovery_graph,
    validate_mandatory_activity_preservation,
)
from tests.workflows.test_single_agent_recovery import make_state


def test_multi_agent_graph_has_expected_nodes():
    graph = build_multi_agent_recovery_graph(client=Mock())

    assert graph is not None


def test_multi_agent_graph_stops_when_research_fails(monkeypatch):
    initialized_recovery_state = make_state()
    def fail_research(*args, **kwargs):
        raise ValueError("Research failed")

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.research_evidence",
        fail_research,
    )

    graph = build_multi_agent_recovery_graph(client=Mock())
    result = graph.invoke(initialized_recovery_state)

    assert result["status"] == WorkflowStatus.FAILED
    assert result["current_stage"] == WorkflowStage.INVESTIGATION
    assert result["llm_call_count"] == 1
    assert result["evidence_brief"] is None
    assert result["audit_report"] is None
    assert any("Research failed" in item for item in result["error_details"])
    assert result["research_raw_response"] is None
    assert result["planning_raw_response"] is None
    assert result["audit_raw_response"] is None
    


def test_multi_agent_graph_completes_all_three_agents(monkeypatch):
    initialized_recovery_state = make_state()
    evidence_brief = EvidenceBrief()
    audit_report = AuditReport(
        assessment="partially_supported",
        supported_claims=[],
        unsupported_claims=[],
        conflicting_claims=[],
        omitted_uncertainties=[],
        rationale_findings=[],
        recommendations=[],
    )

    recovery_option = Mock()
    recovery_option.option_id = "test-option"
    recovery_option.supporting_evidence_ids = []
    recovery_option.rationale = "Test recovery rationale"
    recovery_option.proposed_itinerary = (
        initialized_recovery_state["original_itinerary"]
    )

    research_result = SimpleNamespace(
        evidence_brief=evidence_brief,
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

    research_mock = Mock(return_value=research_result)
    planning_mock = Mock(return_value=planning_result)
    audit_mock = Mock(return_value=audit_result)

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.research_evidence",
        research_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.plan_recovery",
        planning_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.audit_recovery_proposal",
        audit_mock,
    )

    graph = build_multi_agent_recovery_graph(client=Mock())
    result = graph.invoke(initialized_recovery_state)

    research_mock.assert_called_once()
    planning_mock.assert_called_once()
    audit_mock.assert_called_once()

    assert planning_mock.call_args.kwargs["evidence_brief"] == evidence_brief
    assert audit_mock.call_args.kwargs["evidence_brief"] == evidence_brief
    assert audit_mock.call_args.kwargs["deterministic_validation"] is not None

    assert result["evidence_brief"] == evidence_brief
    assert result["audit_report"] == audit_report

    assert result["research_generation_metadata"]["input_tokens"] == 100
    assert result["planning_generation_metadata"]["input_tokens"] == 200
    assert result["audit_generation_metadata"]["input_tokens"] == 150

    assert result["llm_call_count"] == 3
    assert result["status"] == WorkflowStatus.AWAITING_APPROVAL
    assert result["current_stage"] == WorkflowStage.APPROVAL
    assert result["approval_status"] == ApprovalStatus.PENDING

    # Completing the three agents does not imply user approval or execution.
    assert result["final_itinerary"] is None

    # Explicit approval should finalize the proposed itinerary.
    approved_result = apply_approval_decision(
        result,
        decision=ApprovalStatus.APPROVED,
    )

    assert approved_result["approval_status"] == ApprovalStatus.APPROVED
    assert approved_result["status"] == WorkflowStatus.COMPLETED
    assert approved_result["current_stage"] == WorkflowStage.COMPLETED
    assert approved_result["final_itinerary"] is (
        result["recovery_options"][0].proposed_itinerary
    )

    # Rejection should not create a final itinerary.
    rejected_result = apply_approval_decision(
        result,
        decision=ApprovalStatus.REJECTED,
        user_feedback="The proposed recovery does not meet my needs.",
    )

    assert rejected_result["approval_status"] == ApprovalStatus.REJECTED
    assert rejected_result["status"] == WorkflowStatus.COMPLETED
    assert rejected_result["final_itinerary"] is None
    assert result["research_raw_response"] is not None
    assert result["planning_raw_response"] is not None
    assert result["audit_raw_response"] is not None

    metadata = result["multi_agent_generation_metadata"]

    assert metadata["agent_count"] == 3
    assert metadata["total_llm_calls"] == 3
    assert metadata["total_latency_seconds"] == pytest.approx(
        research_result.latency_seconds
        + planning_result.latency_seconds
        + audit_result.latency_seconds
    )
    assert metadata["total_input_tokens"] == (
        research_result.input_tokens
        + planning_result.input_tokens
        + audit_result.input_tokens
    )
    assert metadata["total_output_tokens"] == (
        research_result.output_tokens
        + planning_result.output_tokens
        + audit_result.output_tokens
    )
    assert metadata["input_tokens_complete"] is True
    assert metadata["output_tokens_complete"] is True
    assert metadata["total_workflow_latency_seconds"] is not None
    assert metadata["total_workflow_latency_seconds"] > 0
    assert result["workflow_started_at"] is not None
    


def test_multi_agent_graph_rejects_unavailable_evidence_source(
    monkeypatch,
):
    initialized_recovery_state = make_state()

    evidence_brief = EvidenceBrief()

    research_result = SimpleNamespace(
        evidence_brief=evidence_brief,
        raw_response='{"findings": []}',
        model_name="qwen3.5:4b",
        latency_seconds=1.0,
        input_tokens=100,
        output_tokens=50,
    )

    recovery_option = Mock()
    recovery_option.supporting_evidence_ids = [
        "test_investigation"
    ]

    planning_result = SimpleNamespace(
        recovery_option=recovery_option,
        raw_response='{"option_id": "test-option"}',
        model_name="qwen3.5:4b",
        latency_seconds=2.0,
        input_tokens=200,
        output_tokens=100,
    )

    research_mock = Mock(return_value=research_result)
    planning_mock = Mock(return_value=planning_result)
    audit_mock = Mock()

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.research_evidence",
        research_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.plan_recovery",
        planning_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.audit_recovery_proposal",
        audit_mock,
    )

    graph = build_multi_agent_recovery_graph(client=Mock())
    result = graph.invoke(initialized_recovery_state)

    assert result["status"] == WorkflowStatus.FAILED
    assert result["current_stage"] == WorkflowStage.RECOVERY_PLANNING
    assert research_mock.call_count == 1
    audit_mock.assert_not_called()

    assert any(
        "test_investigation" in item
        for item in result["error_details"]
    )


def test_multi_agent_graph_accepts_valid_evidence_source(
    monkeypatch,
):
    initialized_recovery_state = make_state()

    retrieved_evidence = RetrievedEvidence(
        chunk_id="chunk_001",
        content="The National Gallery is closed on November 7.",
        subject="National Gallery availability",
        source_id="source_001",
        source_url="https://example.com/venue-status",
        retrieved_at=datetime.now(timezone.utc),
        similarity_distance=0.1,
        reliability=0.95,
        freshness_score=0.95,
        verification_status=VerificationStatus.VERIFIED,
    )

    initialized_recovery_state["investigation_result"].retrieved_evidence = [
        retrieved_evidence
    ]

    evidence_brief = EvidenceBrief()

    audit_report = AuditReport(
        assessment="partially_supported",
        supported_claims=[],
        unsupported_claims=[],
        conflicting_claims=[],
        omitted_uncertainties=[],
        rationale_findings=[],
        recommendations=[],
    )

    recovery_option = Mock()
    recovery_option.supporting_evidence_ids = ["source_001"]
    recovery_option.option_id = "test-option"
    recovery_option.rationale = "Test recovery rationale"
    recovery_option.proposed_itinerary = (
        initialized_recovery_state["original_itinerary"]
    )

    research_result = SimpleNamespace(
        evidence_brief=evidence_brief,
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

    research_mock = Mock(return_value=research_result)
    planning_mock = Mock(return_value=planning_result)
    audit_mock = Mock(return_value=audit_result)

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.research_evidence",
        research_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.plan_recovery",
        planning_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.audit_recovery_proposal",
        audit_mock,
    )

    graph = build_multi_agent_recovery_graph(client=Mock())
    result = graph.invoke(initialized_recovery_state)

    assert result["current_stage"] == WorkflowStage.APPROVAL
    assert result["approval_status"] == ApprovalStatus.PENDING
    assert len(result["recovery_options"]) == 1

    assert result["recovery_options"][0].supporting_evidence_ids == [
        "source_001"
    ]

    research_mock.assert_called_once()
    planning_mock.assert_called_once()
    audit_mock.assert_called_once()


def test_auditor_receives_validation_issues_and_schedule_findings(
    monkeypatch,
):
    initialized_recovery_state = make_state()

    # make_state() uses an empty itinerary fixture.
    # Create a real activity specifically for this workflow test.
    activity = Activity(
        activity_id="test_activity",
        name="Test Museum",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=False,
        indoor=True,
    )

    original_itinerary = initialized_recovery_state[
        "original_itinerary"
    ].model_copy(
        update={"activities": [activity]}
    )

    initialized_recovery_state["original_itinerary"] = original_itinerary

    # This is a travel-delay scenario, so the activity is not affected
    # by the disruption itself.
    initialized_recovery_state[
        "disruption_scenario"
    ].affected_activity_ids = []

    changed_activity = activity.model_copy(
        update={
            "start_time": activity.start_time + timedelta(minutes=15)
        }
    )

    proposed_itinerary = original_itinerary.model_copy(
        update={"activities": [changed_activity]}
    )

    recovery_option = Mock()
    recovery_option.option_id = "test-option"
    recovery_option.supporting_evidence_ids = []
    recovery_option.rationale = "Test recovery rationale"
    recovery_option.proposed_itinerary = proposed_itinerary

    evidence_brief = EvidenceBrief()

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
        evidence_brief=evidence_brief,
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
    result = graph.invoke(initialized_recovery_state)

    assert result["status"] == WorkflowStatus.AWAITING_APPROVAL
    audit_mock.assert_called_once()

    deterministic_validation = (
        audit_mock.call_args.kwargs["deterministic_validation"]
    )

    # Original validation issues remain available at the top level.
    expected_validation = (
        result["itinerary_validation_result"].model_dump(mode="json")
    )

    assert deterministic_validation["issues"] == (
        expected_validation["issues"]
    )

    # The changed activity should be identified for Auditor review.
    schedule_findings = deterministic_validation[
        "schedule_preservation_findings"
    ]

    assert len(schedule_findings) == 1
    assert schedule_findings[0]["activity_id"] == "test_activity"
    assert schedule_findings[0]["original_start_time"] == (
        activity.start_time.isoformat()
    )
    assert schedule_findings[0]["proposed_start_time"] == (
        changed_activity.start_time.isoformat()
    )


def test_auditor_receives_no_schedule_finding_for_unchanged_activities(
    monkeypatch,
):
    initialized_recovery_state = make_state()
    original_itinerary = initialized_recovery_state["original_itinerary"]

    recovery_option = Mock()
    recovery_option.option_id = "test-option"
    recovery_option.supporting_evidence_ids = []
    recovery_option.rationale = "Test recovery rationale"
    recovery_option.proposed_itinerary = original_itinerary

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
    result = graph.invoke(initialized_recovery_state)

    assert result["status"] == WorkflowStatus.AWAITING_APPROVAL

    deterministic_validation = (
        audit_mock.call_args.kwargs["deterministic_validation"]
    )

    assert deterministic_validation["schedule_preservation_findings"] == []


def test_schedule_findings_exclude_disrupted_activity(
    monkeypatch,
):
    initialized_recovery_state = make_state()
    original_itinerary = initialized_recovery_state["original_itinerary"]

    affected_ids = set(
        initialized_recovery_state["disruption_scenario"].affected_activity_ids
    )

    # Keep unaffected activities unchanged and remove the disrupted activity.
    proposed_activities = [
        activity
        for activity in original_itinerary.activities
        if activity.activity_id not in affected_ids
    ]

    proposed_itinerary = original_itinerary.model_copy(
        update={"activities": proposed_activities}
    )

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
    result = graph.invoke(initialized_recovery_state)

    assert result["status"] == WorkflowStatus.AWAITING_APPROVAL

    deterministic_validation = (
        audit_mock.call_args.kwargs["deterministic_validation"]
    )

    schedule_findings = deterministic_validation[
        "schedule_preservation_findings"
    ]

    assert all(
        finding["activity_id"] not in affected_ids
        for finding in schedule_findings
    )


def test_mandatory_activity_must_be_preserved():
    activity = Activity(
        activity_id="activity_001",
        name="National Gallery of Art",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=True,
        indoor=True,
    )

    original = make_state()["original_itinerary"].model_copy(
        update={"activities": [activity]}
    )
    proposed = original.model_copy(update={"activities": []})

    result = validate_mandatory_activity_preservation(
        original,
        proposed,
        [],
    )

    assert result.status == ValidationStatus.INVALID
    assert result.issues[0].issue_type == (
        IssueType.MANDATORY_ACTIVITY_NOT_PRESERVED
    )


def test_mandatory_activity_flag_cannot_be_relaxed():
    activity = Activity(
        activity_id="activity_001",
        name="National Gallery of Art",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=True,
        indoor=True,
    )

    relaxed_activity = activity.model_copy(
        update={"mandatory": False}
    )

    original = make_state()["original_itinerary"].model_copy(
        update={"activities": [activity]}
    )
    proposed = original.model_copy(
        update={"activities": [relaxed_activity]}
    )

    result = validate_mandatory_activity_preservation(
        original,
        proposed,
        [],
    )

    assert result.status == ValidationStatus.INVALID


def test_mandatory_activity_constraint_accepts_exact_normalized_name():
    activity = Activity(
        activity_id="activity_001",
        name="National Gallery of Art",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=False,
        indoor=True,
    )

    itinerary = make_state()["original_itinerary"].model_copy(
        update={"activities": [activity]}
    )

    constraint = Constraint(
        constraint_id="constraint_001",
        description="Visit the National Gallery",
        constraint_type=ConstraintType.MANDATORY,
        category="activity",
        priority=ConstraintPriority.HIGH,
        value="  national gallery of art  ",
    )

    result = validate_mandatory_activity_preservation(
        itinerary,
        itinerary,
        [constraint],
    )

    assert result.status == ValidationStatus.VALID
    assert result.issues == []


def test_missing_mandatory_activity_constraint_is_invalid():
    itinerary = make_state()["original_itinerary"]

    constraint = Constraint(
        constraint_id="constraint_001",
        description="Visit the National Gallery",
        constraint_type=ConstraintType.MANDATORY,
        category="activity",
        priority=ConstraintPriority.HIGH,
        value="National Gallery of Art",
    )

    result = validate_mandatory_activity_preservation(
        itinerary,
        itinerary,
        [constraint],
    )

    assert result.status == ValidationStatus.INVALID
    assert "no exact match" in result.issues[0].description


def test_ambiguous_mandatory_activity_constraint_is_invalid():
    first = Activity(
        activity_id="activity_001",
        name="National Gallery of Art",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=60,
        mandatory=False,
        indoor=True,
    )

    second = Activity(
        activity_id="activity_002",
        name="National Gallery of Art",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 12, 0),
        duration_minutes=60,
        mandatory=False,
        indoor=True,
    )

    itinerary = make_state()["original_itinerary"].model_copy(
        update={"activities": [first, second]}
    )

    constraint = Constraint(
        constraint_id="constraint_001",
        description="Visit the National Gallery",
        constraint_type=ConstraintType.MANDATORY,
        category="activity",
        priority=ConstraintPriority.HIGH,
        value="National Gallery of Art",
    )

    result = validate_mandatory_activity_preservation(
        itinerary,
        itinerary,
        [constraint],
    )

    assert result.status == ValidationStatus.INVALID
    assert "ambiguous" in result.issues[0].description


def test_multi_agent_graph_does_not_submit_invalid_proposal_for_approval(
    monkeypatch,
):
    initialized_state = make_state()

    mandatory_activity = Activity(
        activity_id="mandatory_001",
        name="National Gallery of Art",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=True,
        indoor=True,
    )

    original_itinerary = initialized_state["original_itinerary"].model_copy(
        update={"activities": [mandatory_activity]}
    )

    initialized_state["original_itinerary"] = original_itinerary

    # The proposal removes the mandatory activity.
    proposed_itinerary = original_itinerary.model_copy(
        update={"activities": []}
    )

    recovery_option = Mock()
    recovery_option.option_id = "invalid-option"
    recovery_option.supporting_evidence_ids = []
    recovery_option.rationale = "Test proposal that removes a mandatory activity."
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
        raw_response='{"option_id": "invalid-option"}',
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
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.audit_recovery_proposal",
        Mock(return_value=audit_result),
    )

    graph = build_multi_agent_recovery_graph(client=Mock())
    result = graph.invoke(initialized_state)

    assert result["itinerary_validation_result"].status == (
        ValidationStatus.INVALID
    )
    assert result["status"] == WorkflowStatus.NO_VALID_RECOVERY
    assert result["current_stage"] == WorkflowStage.COMPLETED
    assert result["approval_status"] == ApprovalStatus.NOT_REQUIRED
    assert result["final_itinerary"] is None


def test_revision_feedback_is_passed_to_planner(monkeypatch):
    initialized_state = make_state()

    feedback = (
        "Keep the National Gallery visit and avoid moving "
        "the afternoon activities."
    )

    initialized_state["approval_history"] = [
        ApprovalRecord(
            option_id="previous-option",
            status=ApprovalStatus.REVISION_REQUESTED,
            timestamp=datetime.now(timezone.utc),
            user_feedback=feedback,
        )
    ]
    initialized_state["approval_status"] = ApprovalStatus.REVISION_REQUESTED
    initialized_state["revision_count"] = 1
    initialized_state["status"] = WorkflowStatus.IN_PROGRESS
    initialized_state["current_stage"] = WorkflowStage.RECOVERY_PLANNING

    recovery_option = Mock()
    recovery_option.option_id = "revised-option"
    recovery_option.supporting_evidence_ids = []
    recovery_option.rationale = "Revised recovery proposal"
    recovery_option.proposed_itinerary = initialized_state[
        "original_itinerary"
    ]

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
        raw_response='{"option_id": "revised-option"}',
        model_name="qwen3.5:4b",
        latency_seconds=2.0,
        input_tokens=200,
        output_tokens=100,
    )

    audit_result = SimpleNamespace(
        audit_report=AuditReport(
            assessment="partially_supported",
            supported_claims=[],
            unsupported_claims=[],
            conflicting_claims=[],
            omitted_uncertainties=[],
            rationale_findings=[],
            recommendations=[],
        ),
        raw_response='{"assessment": "partially_supported"}',
        model_name="qwen3.5:4b",
        latency_seconds=1.5,
        input_tokens=150,
        output_tokens=75,
    )

    planning_mock = Mock(return_value=planning_result)

    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.research_evidence",
        Mock(return_value=research_result),
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.plan_recovery",
        planning_mock,
    )
    monkeypatch.setattr(
        "src.workflows.multi_agent_recovery.audit_recovery_proposal",
        Mock(return_value=audit_result),
    )
    graph = build_multi_agent_recovery_graph(
        client=Mock(),
        additional_instructions="Prefer minimal changes.",
    )

    graph.invoke(initialized_state)

    planning_input = planning_mock.call_args.kwargs["planning_input"]

    assert planning_input.revision_count == 1
    assert feedback in planning_input.additional_instructions
    assert "Prefer minimal changes." in planning_input.additional_instructions