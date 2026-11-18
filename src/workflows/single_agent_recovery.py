
from datetime import datetime, timezone
from uuid import uuid4

from langgraph.graph import StateGraph, START, END

from src.models.agent_state import (
    TravelAgentState,
    WorkflowStage,
    WorkflowStatus,
)
from src.models.agent_workflow import (
    RecoveryPlanningInput,
    RecoveryStrategy,
    OptionValidation,
    ExecutionEvent,
)
from src.recovery.generation import (
    DEFAULT_MODEL,
    generate_recovery_option,
)
from src.validation.schedule_validator import validate_itinerary


def build_single_agent_recovery_graph(
    strategy: RecoveryStrategy = RecoveryStrategy.BEST_OVERALL_FEASIBILITY,
    model_name: str = DEFAULT_MODEL,
    client=None,
    additional_instructions: str = "",
):
    """Build a single-agent recovery workflow.

    The workflow makes one LLM generation call, then validates
    the resulting proposal deterministically.
    """

    def prepare_recovery_input(state: TravelAgentState):
        disruption = state["disruption_scenario"]
        investigation = state["investigation_result"]

        if disruption is None:
            raise ValueError(
                "A disruption scenario is required for recovery."
            )

        if investigation is None:
            raise ValueError(
                "An investigation result is required for recovery."
            )

        planning_input = RecoveryPlanningInput(
            original_itinerary=state["original_itinerary"],
            disruption_scenario=disruption,
            investigation_result=investigation,
            mandatory_constraints=state["mandatory_constraints"],
            flexible_preferences=state["flexible_preferences"],
            user_instructions=state["user_instructions"],
            strategy=strategy,
            revision_count=state["revision_count"],
            rejected_options=state["rejected_options"],
            additional_instructions=additional_instructions,
        )

        event = ExecutionEvent(
            event_id=str(uuid4()),
            stage="recovery_planning",
            event_type="input_prepared",
            description="Prepared the shared recovery planning input.",
            details={"strategy": strategy.value},
        )

        return {
            "recovery_planning_input": planning_input,
            "current_stage": WorkflowStage.RECOVERY_PLANNING,
            "execution_trace": [event],
        }

    def generate_proposal(state: TravelAgentState):
        planning_input = state["recovery_planning_input"]

        if planning_input is None:
            raise ValueError("Recovery planning input is missing.")

        result = generate_recovery_option(
            planning_input=planning_input,
            model_name=model_name,
            client=client,
        )

        option = result.recovery_option

        metadata = {
            "model_name": result.model_name,
            "latency_seconds": result.latency_seconds,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }

        event = ExecutionEvent(
            event_id=str(uuid4()),
            stage="recovery_planning",
            event_type="proposal_generated",
            description="Generated one recovery proposal.",
            details={
                "option_id": option.option_id,
                "model_name": result.model_name,
                "latency_seconds": result.latency_seconds,
            },
        )

        return {
            "recovery_options": [option],
            "selected_option_id": option.option_id,
            "planning_rationale": option.rationale,
            "recovery_generation_metadata": metadata,
            "llm_call_count": state["llm_call_count"] + 1,
            "current_stage": WorkflowStage.VALIDATION,
            "execution_trace": [event],
        }

    def validate_proposal(state: TravelAgentState):
        option_id = state["selected_option_id"]

        if option_id is None or not state["recovery_options"]:
            raise ValueError("No recovery proposal is available.")

        option = next(
            (
                item
                for item in state["recovery_options"]
                if item.option_id == option_id
            ),
            None,
        )

        if option is None:
            raise ValueError("Selected recovery proposal was not found.")

        validation_result = validate_itinerary(
            option.proposed_itinerary
        )

        option_validation = OptionValidation(
            option_id=option_id,
            validation_result=validation_result,
        )

        event = ExecutionEvent(
            event_id=str(uuid4()),
            stage="validation",
            event_type="proposal_validated",
            description="Completed deterministic itinerary validation.",
            details={
                "option_id": option_id,
                "validation_status": validation_result.status.value,
                "issue_count": len(validation_result.issues),
            },
        )

        return {
            "validation_results": [option_validation],
            "itinerary_validation_result": validation_result,
            "current_stage": WorkflowStage.COMPLETED,
            "status": WorkflowStatus.COMPLETED,
            "execution_trace": [event],
        }

    graph = StateGraph(TravelAgentState)

    graph.add_node("prepare_recovery_input", prepare_recovery_input)
    graph.add_node("generate_proposal", generate_proposal)
    graph.add_node("validate_proposal", validate_proposal)

    graph.add_edge(START, "prepare_recovery_input")
    graph.add_edge("prepare_recovery_input", "generate_proposal")
    graph.add_edge("generate_proposal", "validate_proposal")
    graph.add_edge("validate_proposal", END)

    return graph.compile()
