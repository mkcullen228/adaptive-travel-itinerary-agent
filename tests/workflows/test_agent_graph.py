import json
from pathlib import Path
from langgraph.graph import StateGraph, START, END

from src.models.itinerary import Itinerary
from src.models.agent_state import (
    TravelAgentState,
    WorkflowStage,
    WorkflowStatus,
)
from src.models.agent_workflow import ExecutionEvent
from src.models.validation import ValidationResult, ValidationStatus
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
    expected_investigation = object()
    expected_audit_report = object()

    def mock_run_investigation(**kwargs):
        return expected_investigation

    def mock_build_multi_agent_recovery_graph():
        def mock_recovery_node(state):
            # Confirm the investigation result reaches recovery.
            assert (
                state["investigation_result"]
                is expected_investigation
            )

            return {
                "audit_report": expected_audit_report,
                "current_stage": WorkflowStage.COMPLETED,
                "status": WorkflowStatus.COMPLETED,
            }

        return mock_recovery_node

    monkeypatch.setattr(
        agent_graph,
        "run_investigation",
        mock_run_investigation,
    )

    monkeypatch.setattr(
        agent_graph,
        "build_multi_agent_recovery_graph",
        mock_build_multi_agent_recovery_graph,
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
    assert result["investigation_result"] is expected_investigation
    assert result["audit_report"] is expected_audit_report

    assert result["original_itinerary"] is itinerary
    assert result["disruption_scenario"] is disruption

    # Recovery generation must not finalize the itinerary.
    assert result["final_itinerary"] is None

    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["current_stage"] == WorkflowStage.COMPLETED


def test_normal_itinerary_node_processes_copy(monkeypatch):
    itinerary, _ = make_test_inputs()
    expected_validation = ValidationResult(
        status=ValidationStatus.VALID
    )
    captured = {}

    def mock_process_itinerary_routes(received_itinerary):
        captured["itinerary"] = received_itinerary
        return received_itinerary, expected_validation

    monkeypatch.setattr(
        agent_graph,
        "process_itinerary_routes",
        mock_process_itinerary_routes,
    )

    state = initialize_agent_state(itinerary=itinerary)

    result = agent_graph.normal_itinerary_node(state)

    assert captured["itinerary"] is not itinerary
    assert result["final_itinerary"] is captured["itinerary"]
    assert result["itinerary_validation_result"] is expected_validation
    assert itinerary.travel_legs == []


def test_agent_graph_runs_normal_itinerary_path(monkeypatch):
    itinerary, _ = make_test_inputs()

    expected_validation = ValidationResult(
        status=ValidationStatus.VALID
    )

    def mock_process_itinerary_routes(received_itinerary):
        return received_itinerary, expected_validation

    monkeypatch.setattr(
        agent_graph,
        "process_itinerary_routes",
        mock_process_itinerary_routes,
    )

    initial_state = initialize_agent_state(itinerary=itinerary)

    graph = build_agent_graph()
    result = graph.invoke(initial_state)

    assert result["final_itinerary"] is not itinerary
    assert result["itinerary_validation_result"] == expected_validation
    assert result["disruption_scenario"] is None
    assert result["status"].value == "completed"


def test_normal_itinerary_end_to_end_with_mocked_routing(monkeypatch):
    # Load the actual baseline itinerary.
    dataset_path = Path(
        "data/itineraries/dc_baseline_2026_11_07.json"
    )

    with dataset_path.open(encoding="utf-8") as file:
        data = json.load(file)

    itinerary = Itinerary.model_validate(data)

    # Confirm the baseline starts without routing estimates.
    assert len(itinerary.travel_legs) == 4
    assert all(leg.estimates == [] for leg in itinerary.travel_legs)

    # Mock only the external routing request.
    routing_calls = []

    def mock_get_walking_route(origin_coordinates, destination_coordinates):
        routing_calls.append(
            (origin_coordinates, destination_coordinates)
        )

        return {
            "duration_seconds": 300,
            "distance_meters": 400,
        }

    monkeypatch.setattr(
        "src.workflows.routing_workflow.get_walking_route",
        mock_get_walking_route,
    )

    # Initialize and execute the actual graph.
    initial_state = initialize_agent_state(itinerary=itinerary)

    graph = build_agent_graph()
    result = graph.invoke(initial_state)

    # Confirm all four routes were requested.
    assert len(routing_calls) == 4

    # Confirm the processed itinerary contains four walking estimates.
    processed_itinerary = result["final_itinerary"]

    assert len(processed_itinerary.travel_legs) == 4

    for leg in processed_itinerary.travel_legs:
        assert len(leg.estimates) == 1
        assert leg.estimates[0].mode == "walking"
        assert leg.estimates[0].duration_minutes == 5
        assert leg.estimates[0].source == "OpenRouteService"

    # Confirm deterministic validation ran successfully.
    validation = result["itinerary_validation_result"]

    assert validation.status.value == "valid"
    assert validation.issues == []

    # Confirm the workflow completed.
    assert result["status"].value == "completed"

    # Confirm the original itinerary was not modified.
    assert all(leg.estimates == [] for leg in itinerary.travel_legs)
