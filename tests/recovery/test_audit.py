
import json
from types import SimpleNamespace
from unittest.mock import Mock

from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.multi_agent import AuditReport, EvidenceBrief
from tests.models.test_agent_workflow import (
        make_recovery_planning_input,
    )

from src.recovery.audit import (
    audit_recovery_proposal,
    build_audit_messages,
    compare_mandatory_activities,
)
from src.recovery.generation import RecoveryGenerationResult


def make_test_itinerary(mandatory=True):
    activity = Activity(
        activity_id="natural_history",
        name="National Museum of Natural History",
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=mandatory,
    )

    return Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[activity],
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


def test_build_audit_messages_requires_mandatory_activity_comparison():
    planning_input = make_recovery_planning_input()
    evidence_brief = EvidenceBrief()

    recovery_option = Mock()
    recovery_option.model_dump.return_value = {
        "option_id": "option_1",
        "proposed_itinerary": {
            "activities": [
                {
                    "activity_id": "natural_history",
                    "name": "National Museum of Natural History",
                    "mandatory": True,
                }
            ]
        },
    }

    messages = build_audit_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=recovery_option,
    )

    system_prompt = messages[0]["content"]

    assert "Mandatory activity verification" in system_prompt
    assert "activity IDs, names, and mandatory flags" in system_prompt
    assert "remains in the proposed itinerary" in system_prompt


def test_compare_mandatory_activities_identifies_preserved_activity():
    original = make_test_itinerary()
    proposed = make_test_itinerary()

    result = compare_mandatory_activities(original, proposed)

    assert len(result) == 1
    assert result[0]["activity_id"] == "natural_history"
    assert result[0]["preserved"] is True


def test_compare_mandatory_activities_identifies_removed_activity():
    original = make_test_itinerary()

    proposed = original.model_copy(update={"activities": []})

    result = compare_mandatory_activities(original, proposed)

    assert len(result) == 1
    assert result[0]["activity_id"] == "natural_history"
    assert result[0]["preserved"] is False
    assert result[0]["proposed_activity_id"] is None


def test_compare_mandatory_activities_detects_mandatory_flag_change():
    original = make_test_itinerary()

    proposed_activity = original.activities[0].model_copy(
        update={"mandatory": False}
    )
    proposed = original.model_copy(
        update={"activities": [proposed_activity]}
    )

    result = compare_mandatory_activities(original, proposed)

    assert len(result) == 1
    assert result[0]["preserved"] is False
    assert result[0]["proposed_activity_id"] == "natural_history"
    assert result[0]["proposed_mandatory"] is False


def test_build_audit_messages_includes_mandatory_activity_comparison():
    planning_input = make_recovery_planning_input()
    original = make_test_itinerary()
    planning_input.original_itinerary = original

    evidence_brief = EvidenceBrief()

    recovery_option = Mock()
    recovery_option.proposed_itinerary = make_test_itinerary()
    recovery_option.model_dump.return_value = {
        "option_id": "option_1",
        "rationale": "Preserve the mandatory museum visit.",
    }

    messages = build_audit_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=recovery_option,
    )

    audit_context = json.loads(messages[1]["content"].split(
        "supplied context.\n\nReturn an AuditReport. "
        "Do not modify or replace the proposal.\n\n"
    )[1])

    comparison = audit_context["mandatory_activity_comparison"]

    assert len(comparison) == 1
    assert comparison[0]["activity_id"] == "natural_history"
    assert comparison[0]["preserved"] is True


def test_audit_prompt_requires_explicit_validation_review():
    planning_input = make_recovery_planning_input()
    evidence_brief = EvidenceBrief()

    recovery_option = Mock()
    recovery_option.model_dump.return_value = {
        "option_id": "option_1",
        "rationale": "Test rationale",
    }

    validation = {
        "status": "incomplete",
        "issues": [
            "No walking estimate exists between "
            "'National Museum of American History' and "
            "'National Museum of Natural History'."
        ],
    }

    messages = build_audit_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=recovery_option,
        deterministic_validation=validation,
    )

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    assert "Deterministic validation review" in system_prompt
    assert "affected activity pair" in system_prompt
    assert "schedule feasibility" in system_prompt
    assert "National Museum of American History" in user_prompt
    assert "National Museum of Natural History" in user_prompt
