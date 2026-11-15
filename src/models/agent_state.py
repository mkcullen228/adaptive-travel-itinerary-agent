from datetime import datetime
from enum import Enum
from typing import TypedDict

from src.models.agent_workflow import (
    Constraint,
    ConstraintInterpretation,
    RecoveryOption,
    RejectedOption,
)
from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult



class WorkflowStage(str, Enum):
    INITIALIZATION = "initialization"
    INVESTIGATION = "investigation"
    RECOVERY_PLANNING = "recovery_planning"
    VALIDATION = "validation"
    APPROVAL = "approval"
    FINALIZATION = "finalization"
    COMPLETED = "completed"


class WorkflowStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_VALID_RECOVERY = "no_valid_recovery"


class TravelAgentState(TypedDict):
    # Workflow identity
    investigation_id: str
    created_at: datetime
    current_stage: WorkflowStage
    status: WorkflowStatus

    # Original inputs
    original_itinerary: Itinerary
    disruption_scenario: DisruptionScenario
    
    # User instructions and constraints
    user_instructions: str
    mandatory_constraints: list[Constraint]
    flexible_preferences: list[Constraint]
    interpreted_constraints: list[ConstraintInterpretation]
    pending_clarifications: list[str]

    # Investigation
    investigation_result: InvestigationResult | None

    # Recovery planning
    recovery_options: list[RecoveryOption]
    selected_option_id: str | None
    rejected_options: list[RejectedOption]
    revision_count: int
    planning_rationale: str
