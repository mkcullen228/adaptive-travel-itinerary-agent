from langgraph.graph import StateGraph, START, END

from src.models.agent_state import TravelAgentState
from src.workflows.investigation_workflow import run_investigation

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

    graph.add_node("investigation", investigation_node)

    graph.add_edge(START, "investigation")
    graph.add_edge("investigation", END)

    return graph.compile()
