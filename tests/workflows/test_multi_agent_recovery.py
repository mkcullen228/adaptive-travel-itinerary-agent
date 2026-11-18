import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from src.models.agent_state import WorkflowStage, WorkflowStatus
from src.models.multi_agent import EvidenceBrief, AuditReport
from src.models.agent_workflow import RecoveryOption
from src.models.validation import ValidationResult

from src.workflows.multi_agent_recovery import (
    build_multi_agent_recovery_graph,
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
    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["current_stage"] == WorkflowStage.COMPLETED

    # Completing the workflow does not imply user approval or execution.
    assert result["final_itinerary"] is None
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
