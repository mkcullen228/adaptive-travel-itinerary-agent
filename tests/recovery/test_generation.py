import json
from types import SimpleNamespace
from unittest.mock import Mock
from pydantic import ValidationError

import pytest

from src.models.agent_workflow import (
    RecoveryOption,
    RecoveryStrategy,
)
from src.models.multi_agent import EvidenceBrief, EvidenceFinding
from src.models.evidence import EvidenceStatus
from src.recovery.generation import (
    build_recovery_messages,
    generate_recovery_option,
)

from tests.models.test_agent_workflow import make_recovery_planning_input


@pytest.fixture
def planning_input():
    planning_input = make_recovery_planning_input()
    planning_input.additional_instructions = (
        "Preserve the mandatory museum visit."
    )
    return planning_input


@pytest.fixture
def valid_recovery_response(planning_input):
    return RecoveryOption(
        option_id="test-option-001",
        strategy=planning_input.strategy,
        proposed_itinerary=planning_input.original_itinerary,
        proposal_status="partial",
        rationale="Test recovery proposal.",
        uncertainties=["Venue availability remains unverified."],
    ).model_dump_json()


def make_fake_client(raw_response):
    response = SimpleNamespace(
        message=SimpleNamespace(content=raw_response),
        model="qwen3.5:4b",
        prompt_eval_count=100,
        eval_count=200,
    )

    client = Mock()
    client.chat.return_value = response
    return client


def test_build_messages_includes_strategy_and_additional_instructions(
    planning_input,
):
    messages = build_recovery_messages(planning_input)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    assert "Prioritize preserving the original itinerary" in (
        messages[0]["content"]
    )

    assert "Preserve the mandatory museum visit." in (
        messages[1]["content"]
    )


def test_generation_calls_client_with_expected_settings(
    planning_input,
    valid_recovery_response,
):
    client = make_fake_client(valid_recovery_response)

    result = generate_recovery_option(
        planning_input=planning_input,
        client=client,
    )

    client.chat.assert_called_once()

    call_args = client.chat.call_args.kwargs

    assert call_args["model"] == "qwen3.5:4b"
    assert call_args["think"] is False
    assert call_args["options"] == {"temperature": 0}
    assert call_args["format"] == RecoveryOption.model_json_schema()

    assert result.recovery_option.option_id == "test-option-001"


def test_generation_returns_raw_response_and_metadata(
    planning_input,
    valid_recovery_response,
):
    client = make_fake_client(valid_recovery_response)

    result = generate_recovery_option(
        planning_input=planning_input,
        client=client,
    )

    assert result.raw_response == valid_recovery_response
    assert result.model_name == "qwen3.5:4b"
    assert result.input_tokens == 100
    assert result.output_tokens == 200
    assert result.latency_seconds >= 0


def test_generation_rejects_invalid_structured_response(
    planning_input,
):
    client = make_fake_client('{"invalid": "response"}')

    with pytest.raises(ValidationError):
        generate_recovery_option(
            planning_input=planning_input,
            client=client,
        )


def test_generation_uses_selected_strategy_instruction(
    planning_input,
    valid_recovery_response,
):
    planning_input.strategy = RecoveryStrategy.BEST_OVERALL_FEASIBILITY

    client = make_fake_client(valid_recovery_response)

    result = generate_recovery_option(
        planning_input=planning_input,
        client=client,
    )

    messages = client.chat.call_args.kwargs["messages"]

    assert "Prioritize producing the most feasible recovery" in (
        messages[0]["content"]
    )
    assert result.recovery_option is not None



def test_build_recovery_messages_without_evidence_brief():
    planning_input = make_recovery_planning_input()

    messages = build_recovery_messages(planning_input)

    assert len(messages) == 2
    assert "ADDITIONAL RESEARCHER EVIDENCE BRIEF" not in (
        messages[1]["content"]
    )


def test_build_recovery_messages_includes_evidence_brief():
    planning_input = make_recovery_planning_input()

    brief = EvidenceBrief(
        findings=[
            EvidenceFinding(
                claim="The National Gallery is unavailable.",
                status=EvidenceStatus.SUPPORTED,
                supporting_source_ids=["source_1"],
                explanation="The supplied evidence confirms closure.",
            )
        ],
        source_ids_reviewed=["source_1"],
        unresolved_questions=["Remaining venue availability is unknown."],
    )

    messages = build_recovery_messages(
        planning_input,
        evidence_brief=brief,
    )

    assert "ADDITIONAL RESEARCHER EVIDENCE BRIEF" in (
        messages[1]["content"]
    )
    assert "source_1" in messages[1]["content"]
    assert "Remaining venue availability is unknown." in (
        messages[1]["content"]
    )
