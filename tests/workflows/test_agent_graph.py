from langgraph.graph import StateGraph, START, END

from src.models.agent_state import TravelAgentState
from src.models.agent_workflow import ExecutionEvent
from src.workflows.agent_graph import build_agent_graph
import src.workflows.agent_graph as agent_graph
from src.workflows.state_initialization import initialize_agent_state
from tests.workflows.test_state_initialization import make_test_inputs  


def investigation_node(state: TravelAgentState):
    event = ExecutionEvent(
        event_id="event_001",
        stage="investigation",
        event_type="investigation",
        description="Investigation completed.",
    )

    return {
        "execution_trace": [event],
        "warnings": ["Weather data is incomplete."],
    }


def validation_node(state: TravelAgentState):
    event = ExecutionEvent(
        event_id="event_002",
        stage="validation",
        event_type="validation",
        description="Itinerary validation completed.",
    )

    return {
        "execution_trace": [event],
        "warnings": ["Weather data is incomplete."],
    }


def build_test_graph():
    graph = StateGraph(TravelAgentState)

    graph.add_node("investigation", investigation_node)
    graph.add_node("validation", validation_node)

    graph.add_edge(START, "investigation")
    graph.add_edge("investigation", "validation")
    graph.add_edge("validation", END)

    return graph.compile()


def test_langgraph_applies_state_reducers():
    graph = build_test_graph()

    initial_state = {
        "execution_trace": [],
        "warnings": [],
    }

    result = graph.invoke(initial_state)

    assert len(result["execution_trace"]) == 2
    assert [event.event_id for event in result["execution_trace"]] == [
        "event_001",
        "event_002",
    ]

    assert result["warnings"] == [
        "Weather data is incomplete."
    ]


def test_investigation_node_calls_workflow_with_correct_inputs(monkeypatch):
    # Arrange
    itinerary = object()
    scenario = object()
    expected_result = object()

    captured_inputs = {}

    def mock_run_investigation(**kwargs):
        captured_inputs.update(kwargs)
        return expected_result

    monkeypatch.setattr(
        agent_graph,
        "run_investigation",
        mock_run_investigation,
    )

    state = {
        "original_itinerary": itinerary,
        "disruption_scenario": scenario,
        "venue_id": "washington_monument",
        "latitude": 38.8895,
        "longitude": -77.0353,
    }

    # Act
    result = agent_graph.investigation_node(state)

    # Assert
    assert captured_inputs == {
        "itinerary": itinerary,
        "scenario": scenario,
        "venue_id": "washington_monument",
        "latitude": 38.8895,
        "longitude": -77.0353,
    }

    assert result == {
        "investigation_result": expected_result,
    }


def test_agent_graph_runs_investigation_node(monkeypatch):
    # Arrange
    itinerary, disruption = make_test_inputs()

    expected_result = object()

    def mock_run_investigation(**kwargs):
        return expected_result

    monkeypatch.setattr(
        agent_graph,
        "run_investigation",
        mock_run_investigation,
    )

    initial_state = initialize_agent_state(
        itinerary=itinerary,
        disruption=disruption,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
    )

    graph = build_agent_graph()

    # Act
    result = graph.invoke(initial_state)

    # Assert
    assert result["investigation_result"] is expected_result
    assert result["original_itinerary"] is itinerary
    assert result["disruption_scenario"] is disruption
