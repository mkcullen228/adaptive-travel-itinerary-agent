
import json
from types import SimpleNamespace
from unittest.mock import Mock

from src.models.multi_agent import AuditReport, EvidenceBrief
from src.recovery.audit import (
    audit_recovery_proposal,
    build_audit_messages,
)
from src.recovery.generation import RecoveryGenerationResult
from tests.models.test_agent_workflow import (
        make_recovery_planning_input,
    )


def make_audit_report_json():
    return json.dumps({
        "assessment": "partially_supported",
        "supported_claims": [
            "The confirmed venue disruption is addressed."
        ],
        "unsupported_claims": [
            "The remaining venues are available."
        ],
        "conflicting_claims": [],
        "omitted_uncertainties": [
            "Availability of the remaining venues is unverified."
        ],
        "rationale_findings": [
            "The proposal should distinguish confirmed facts from assumptions."
        ],
        "recommendations": [
            "Retain the availability uncertainty in the final report."
        ],
    })


def test_build_audit_messages_includes_all_review_context():
    planning_input = make_recovery_planning_input()
    evidence_brief = EvidenceBrief()
    recovery_option = Mock()
    recovery_option.model_dump.return_value = {
        "option_id": "option_1",
        "rationale": "Test rationale",
    }

    deterministic_validation = {
        "status": "incomplete",
        "issues": ["Missing travel estimate"],
    }

    messages = build_audit_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=recovery_option,
        deterministic_validation=deterministic_validation,
    )

    assert len(messages) == 2
    assert "Validation and Evidence Auditor" in messages[0]["content"]
    assert "Test rationale" in messages[1]["content"]
    assert "Missing travel estimate" in messages[1]["content"]


def test_audit_recovery_proposal_returns_structured_result():
    planning_input = make_recovery_planning_input()
    evidence_brief = EvidenceBrief()
    recovery_option = Mock()
    recovery_option.model_dump.return_value = {
        "option_id": "option_1",
        "rationale": "Test rationale",
    }

    raw_response = make_audit_report_json()

    client = Mock()
    client.chat.return_value = SimpleNamespace(
        message=SimpleNamespace(content=raw_response),
        model="qwen3.5:4b",
        prompt_eval_count=500,
        eval_count=200,
    )

    result = audit_recovery_proposal(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=recovery_option,
        deterministic_validation={"status": "valid", "issues": []},
        client=client,
    )

    assert isinstance(result.audit_report, AuditReport)
    assert result.audit_report.assessment == "partially_supported"
    assert result.raw_response == raw_response
    assert result.model_name == "qwen3.5:4b"
    assert result.input_tokens == 500
    assert result.output_tokens == 200

    client.chat.assert_called_once()
    call_kwargs = client.chat.call_args.kwargs
    assert call_kwargs["think"] is False
    assert call_kwargs["options"] == {"temperature": 0}
    assert call_kwargs["format"] == AuditReport.model_json_schema()


def test_audit_rejects_invalid_structured_response():
    planning_input = make_recovery_planning_input()
    evidence_brief = EvidenceBrief()
    recovery_option = Mock()
    recovery_option.model_dump.return_value = {}

    client = Mock()
    client.chat.return_value = SimpleNamespace(
        message=SimpleNamespace(content='{"assessment": "unknown"}'),
        model="qwen3.5:4b",
    )

    import pytest

    with pytest.raises(ValueError):
        audit_recovery_proposal(
            planning_input=planning_input,
            evidence_brief=evidence_brief,
            recovery_option=recovery_option,
            client=client,
        )
