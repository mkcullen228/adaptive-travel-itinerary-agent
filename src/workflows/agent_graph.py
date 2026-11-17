from langgraph.graph import StateGraph, START, END

from src.models.agent_state import (
    TravelAgentState,
    WorkflowStage,
    WorkflowStatus,
)
from src.workflows.investigation_workflow import run_investigation
from src.workflows.routing_workflow import process_itinerary_routes


def route_workflow(state: TravelAgentState) -> str:
    """Select the workflow path based on whether a disruption exists."""
    if state["disruption_scenario"] is None:
        return "normal"

    return "disruption"


def normal_itinerary_node(state: TravelAgentState):
    """Process routing and deterministic validation for a normal itinerary."""

    # Preserve the original itinerary as an immutable workflow input.
    itinerary = state["original_itinerary"].model_copy(deep=True)

    updated_itinerary, validation_result = process_itinerary_routes(
        itinerary
    )

    return {
        "final_itinerary": updated_itinerary,
        "itinerary_validation_result": validation_result,
        "current_stage": WorkflowStage.COMPLETED,
        "status": WorkflowStatus.COMPLETED,
    }


def investigation_node(state: TravelAgentState):
    result = run_investigation(
        itinerary=state["original_itinerary"],
        scenario=state["disruption_scenario"],
        venue_id=state["venue_id"],
        latitude=state["latitude"],
        longitude=state["longitude"],
    )

    return {
        "investigation_result": result,
    }


def build_agent_graph():
    graph = StateGraph(TravelAgentState)

    graph.add_node("normal_itinerary", normal_itinerary_node)
    graph.add_node("investigation", investigation_node)

    graph.add_conditional_edges(
        START,
        route_workflow,
        {
            "normal": "normal_itinerary",
            "disruption": "investigation",
        },
    )

    graph.add_edge("normal_itinerary", END)
    graph.add_edge("investigation", END)

    return graph.compile()
