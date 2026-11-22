from enum import Enum
from datetime import datetime
from typing import Annotated, TypedDict

from src.models.itinerary import Itinerary
from src.models.validation import ValidationResult
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.agent_workflow import (
    Constraint,
    ConstraintInterpretation,
    ExecutionEvent,
    RecoveryOption,
    RejectedOption,
    OptionValidation,
    ApprovalRecord,
    ApprovalStatus,
    ConstraintChange,
    RecoveryPlanningInput,
)
from src.models.multi_agent import EvidenceBrief, AuditReport

from src.workflows.state_reducers import (
    append_execution_events,
    append_unique_strings,
    append_approval_records,
)


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
    venue_id: str | None
    latitude: float | None
    longitude: float | None
    
    # User instructions and constraints
    user_instructions: str
    mandatory_constraints: list[Constraint]
    flexible_preferences: list[Constraint]
    interpreted_constraints: list[ConstraintInterpretation]
    pending_clarifications: list[str]

    # Investigation
    investigation_result: InvestigationResult | None
    
    # Multi-agent research
    evidence_brief: EvidenceBrief | None
    research_generation_metadata: dict[
        str, str | int | float | None
    ] | None

    # Recovery planning
    recovery_options: list[RecoveryOption]
    selected_option_id: str | None
    rejected_options: list[RejectedOption]
    revision_count: int
    planning_rationale: str
    recovery_planning_input: RecoveryPlanningInput | None
    recovery_generation_metadata: dict[
        str, str | int | float | None
    ] | None

    # Planner output metadata
    planning_generation_metadata: dict[
        str, str | int | float | None
    ] | None

    # Validation, approval, and finalization
    validation_results: list[OptionValidation]
    itinerary_validation_result: ValidationResult | None
    approval_status: ApprovalStatus
    approval_history: Annotated[
        list[ApprovalRecord],
        append_approval_records,
    ]
    approved_constraint_changes: list[ConstraintChange]
    final_itinerary: Itinerary | None
    final_report: str | None
    
    # Multi-agent audit
    audit_report: AuditReport | None
    audit_generation_metadata: dict[
        str, str | int | float | None
    ] | None

    # Execution and audit
    tool_call_counts: dict[str, int]
    total_tool_call_count: int
    llm_call_count: int
    execution_trace: Annotated[
        list[ExecutionEvent],
        append_execution_events,
    ]
    warnings: Annotated[
        list[str],
        append_unique_strings,
    ]
    error_details: Annotated[
        list[str],
        append_unique_strings,
    ]

    research_raw_response: str | None
    planning_raw_response: str | None
    audit_raw_response: str | None

    # Multi-agent workflow aggregate metadata
    multi_agent_generation_metadata: dict[
        str, str | int | float | bool | None
    ] | None

    workflow_started_at: float | None
    current_proposal_warnings: list[str]
