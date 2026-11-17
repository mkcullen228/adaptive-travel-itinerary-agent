from datetime import date

from src.models.itinerary import Itinerary
from src.models.disruption import (
    DisruptionScenario,
    DisruptionType,
    DisruptionSeverity,
)
from src.models.agent_workflow import Constraint, ConstraintPriority, ConstraintType
from src.workflows.state_initialization import initialize_agent_state


def make_test_inputs():
    itinerary = Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[],
        travel_legs=[],
    )

    disruption = DisruptionScenario(
        scenario_id="test_disruption",
        scenario_type=DisruptionType.TRAVEL_DELAY,
        description="A 15-minute travel delay.",
        severity=DisruptionSeverity.MODERATE,
        additional_duration_minutes=15,
    )

    return itinerary, disruption


def test_initialize_agent_state_defaults():
    itinerary, disruption = make_test_inputs()

    state = initialize_agent_state(
        itinerary, 
        disruption,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,)

    assert state["original_itinerary"] is itinerary
    assert state["disruption_scenario"] is disruption
    assert state["user_instructions"] == ""
    assert state["mandatory_constraints"] == []
    assert state["flexible_preferences"] == []
    assert state["investigation_result"] is None
    assert state["recovery_options"] == []
    assert state["revision_count"] == 0
    assert state["total_tool_call_count"] == 0
    assert state["llm_call_count"] == 0
    assert state["warnings"] == []
    assert state["error_details"] == []


def test_initialize_agent_state_with_user_inputs():
    itinerary, disruption = make_test_inputs()

    mandatory = Constraint(
        constraint_id="constraint_001",
        description="Visit the National Gallery.",
        constraint_type=ConstraintType.MANDATORY,
        category="activity",
        priority=ConstraintPriority.HIGH,
        value="national_gallery",
    )

    flexible = Constraint(
        constraint_id="constraint_002",
        description="Prefer indoor activities.",
        constraint_type=ConstraintType.FLEXIBLE,
        category="preference",
        priority=ConstraintPriority.MEDIUM,
        value="indoor",
    )

    state = initialize_agent_state(
        itinerary=itinerary,
        disruption=disruption,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,
        user_instructions="Keep the afternoon activities indoors if possible.",
        mandatory_constraints=[mandatory],
        flexible_preferences=[flexible],
    )

    assert state["user_instructions"] == (
        "Keep the afternoon activities indoors if possible."
    )
    assert state["mandatory_constraints"] == [mandatory]
    assert state["flexible_preferences"] == [flexible]


def test_initialize_agent_state_creates_independent_states():
    itinerary, disruption = make_test_inputs()

    state_1 = initialize_agent_state(
        itinerary, 
        disruption,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,)
    state_2 = initialize_agent_state(
        itinerary, 
        disruption,
        venue_id="washington_monument",
        latitude=38.8895,
        longitude=-77.0353,)

    assert state_1["investigation_id"] != state_2["investigation_id"]

    # Each workflow should have independent collections.
    assert state_1["warnings"] is not state_2["warnings"]
    assert state_1["execution_trace"] is not state_2["execution_trace"]
    assert state_1["tool_call_counts"] is not state_2["tool_call_counts"]

    # Updating one state should not affect the other.
    state_1["warnings"].append("Test warning")
    state_1["tool_call_counts"]["weather"] = 1

    assert state_2["warnings"] == []
    assert state_2["tool_call_counts"] == {}
