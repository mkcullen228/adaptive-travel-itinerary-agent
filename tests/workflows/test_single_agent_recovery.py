
from types import SimpleNamespace

from src.models.agent_state import WorkflowStage, WorkflowStatus
from src.models.agent_workflow import RecoveryStrategy
from src.models.validation import ValidationStatus
from src.workflows.single_agent_recovery import (
    build_single_agent_recovery_graph,
)
from src.workflows.state_initialization import initialize_agent_state

from tests.models.test_agent_workflow import make_recovery_planning_input


def make_state():
    planning_input = make_recovery_planning_input()

    state = initialize_agent_state(
        itinerary=planning_input.original_itinerary,
        disruption=planning_input.disruption_scenario,
        user_instructions=planning_input.user_instructions,
    )
    state["investigation_result"] = planning_input.investigation_result

    return state


def make_fake_client(response_content):
    def chat(**kwargs):
        return SimpleNamespace(
            message=SimpleNamespace(content=response_content),
            model=kwargs["model"],
            prompt_eval_count=100,
            eval_count=200,
        )

    return SimpleNamespace(chat=chat)


def test_single_agent_recovery_runs_one_generation_call():
    planning_input = make_recovery_planning_input()
    response_content = (
        # Reuse the existing valid structured-response fixture
        '{"option_id": "test_option", '
        '"strategy": "minimal_disruption", '
        '"proposed_itinerary": {'
        '"itinerary_id": "test_itinerary", '
        '"destination": "Washington, DC", '
        '"itinerary_date": "2026-11-07", '
        '"activities": [], "travel_legs": []}, '
        '"proposal_status": "complete", '
        '"rationale": "No activities need to change.", '
        '"preserved_constraints": [], '
        '"violated_constraints": [], '
        '"trade_offs": [], '
        '"supporting_evidence_ids": [], '
        '"assumptions": [], "uncertainties": []}'
    )

    calls = []

    def chat(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            message=SimpleNamespace(content=response_content),
            model=kwargs["model"],
            prompt_eval_count=100,
            eval_count=200,
        )

    state = make_state()

    graph = build_single_agent_recovery_graph(
        strategy=RecoveryStrategy.MINIMAL_DISRUPTION,
        client=SimpleNamespace(chat=chat),
    )

    result = graph.invoke(state)

    assert len(calls) == 1
    assert result["llm_call_count"] == 1
    assert result["selected_option_id"] == "test_option"
    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["current_stage"] == WorkflowStage.COMPLETED
    assert result["itinerary_validation_result"].status == (
        ValidationStatus.VALID
    )
    assert result["recovery_generation_metadata"]["input_tokens"] == 100
    assert result["recovery_generation_metadata"]["output_tokens"] == 200
    assert result["final_itinerary"] is None


def test_single_agent_requires_investigation_result():
    state = make_state()
    state["investigation_result"] = None

    graph = build_single_agent_recovery_graph()

    try:
        graph.invoke(state)
        assert False, "Expected missing investigation result to raise."
    except ValueError as exc:
        assert "investigation result is required" in str(exc)
