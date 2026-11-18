from datetime import datetime, timezone
from uuid import uuid4

from src.models.agent_state import (
    TravelAgentState,
    WorkflowStage,
    WorkflowStatus,
)
from src.models.agent_workflow import ApprovalStatus, Constraint
from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario


def initialize_agent_state(
    itinerary: Itinerary,
    disruption: DisruptionScenario | None = None,
    venue_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    user_instructions: str = "",
    mandatory_constraints: list[Constraint] | None = None,
    flexible_preferences: list[Constraint] | None = None,
) -> TravelAgentState:
    """Create the initial state for a normal itinerary or recovery workflow."""

    return {
        # Workflow identity
        "investigation_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc),
        "current_stage": WorkflowStage.INITIALIZATION,
        "status": WorkflowStatus.IN_PROGRESS,

        # Original inputs
        "original_itinerary": itinerary,
        "disruption_scenario": disruption,
        "venue_id": venue_id,
        "latitude": latitude,
        "longitude": longitude,

        # User instructions and constraints
        "user_instructions": user_instructions,
        "mandatory_constraints": list(mandatory_constraints or []),
        "flexible_preferences": list(flexible_preferences or []),
        "interpreted_constraints": [],
        "pending_clarifications": [],

        # Investigation
        "investigation_result": None,
        "evidence_brief": None,
        "research_generation_metadata": None,

        # Recovery planning
        "recovery_options": [],
        "selected_option_id": None,
        "rejected_options": [],
        "revision_count": 0,
        "planning_rationale": "",
        "recovery_planning_input": None,
        "recovery_generation_metadata": None,
        "planning_generation_metadata": None,

        # Validation, approval, and finalization
        "itinerary_validation_result": None,
        "validation_results": [],
        "approval_status": ApprovalStatus.NOT_REQUIRED,
        "approval_history": [],
        "approved_constraint_changes": [],
        "final_itinerary": None,
        "final_report": None,

        "audit_report": None,
        "audit_generation_metadata": None,

        # Execution and audit
        "execution_trace": [],
        "tool_call_counts": {},
        "total_tool_call_count": 0,
        "llm_call_count": 0,
        "warnings": [],
        "error_details": [],

        "research_raw_response": None,
        "planning_raw_response": None,
        "audit_raw_response": None,
        "multi_agent_generation_metadata": None,
        "workflow_started_at": None,
    }
