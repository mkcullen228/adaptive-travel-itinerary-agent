from datetime import date, datetime

from src.models.agent_state import (
    TravelAgentState,
    WorkflowStage,
    WorkflowStatus,
)
from src.models.agent_workflow import ApprovalStatus
from src.models.disruption import (
    DisruptionScenario,
    DisruptionType,
    DisruptionSeverity,
)
from src.models.itinerary import Itinerary


def make_test_itinerary():
    return Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=[],
    )


def make_test_disruption():
    return DisruptionScenario(
        scenario_id="test_disruption",
        scenario_type=DisruptionType.TRAVEL_DELAY,
        description="Walking route is delayed",
        severity=DisruptionSeverity.MODERATE,
        additional_duration_minutes=15,
    )


def test_agent_state_initialization():
    itinerary = make_test_itinerary()
    disruption = make_test_disruption()

    state: TravelAgentState = {
        "investigation_id": "test_investigation",
        "created_at": datetime.now(),
        "current_stage": WorkflowStage.INITIALIZATION,
        "status": WorkflowStatus.IN_PROGRESS,
        "original_itinerary": itinerary,
        "disruption_scenario": disruption,
        "user_instructions": "",
        "mandatory_constraints": [],
        "flexible_preferences": [],
        "interpreted_constraints": [],
        "pending_clarifications": [],
        "investigation_result": None,
        "recovery_options": [],
        "selected_option_id": None,
        "rejected_options": [],
        "revision_count": 0,
        "planning_rationale": "",
        "validation_results": [],
        "approval_status": ApprovalStatus.NOT_REQUIRED,
        "approval_history": [],
        "approved_constraint_changes": [],
        "final_itinerary": None,
        "final_report": None,
    }

    assert state["investigation_id"] == "test_investigation"
    assert state["current_stage"] == WorkflowStage.INITIALIZATION
    assert state["status"] == WorkflowStatus.IN_PROGRESS
    assert state["original_itinerary"] is itinerary
    assert state["disruption_scenario"] is disruption
    assert state["user_instructions"] == ""
    assert state["mandatory_constraints"] == []
    assert state["flexible_preferences"] == []
    assert state["interpreted_constraints"] == []
    assert state["pending_clarifications"] == []
    assert state["investigation_result"] is None
    assert state["recovery_options"] == []
    assert state["selected_option_id"] is None
    assert state["rejected_options"] == []
    assert state["revision_count"] == 0
    assert state["planning_rationale"] == ""
    assert state["validation_results"] == []
    assert state["approval_status"] == ApprovalStatus.NOT_REQUIRED
    assert state["approval_history"] == []
    assert state["approved_constraint_changes"] == []
    assert state["final_itinerary"] is None
    assert state["final_report"] is None
