
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
        model_name="qwen3.5:4b",
        latency_seconds=1.0,
        input_tokens=100,
        output_tokens=50,
    )

    planning_result = SimpleNamespace(
        recovery_option=recovery_option,
        model_name="qwen3.5:4b",
        latency_seconds=2.0,
        input_tokens=200,
        output_tokens=100,
    )

    audit_result = SimpleNamespace(
        audit_report=audit_report,
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
