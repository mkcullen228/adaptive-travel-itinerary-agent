from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.models.disruption import DisruptionScenario
from src.models.itinerary import Itinerary
from src.models.validation import ValidationResult
from src.models.investigation import InvestigationResult


class ConstraintPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConstraintType(str, Enum):
    MANDATORY = "mandatory"
    FLEXIBLE = "flexible"


class ConfirmationStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class RecoveryStrategy(str, Enum):
    MINIMAL_DISRUPTION = "minimal_disruption"
    BEST_OVERALL_FEASIBILITY = "best_overall_feasibility"
    PREFERENCE_ORIENTED = "preference_oriented"


class RecoveryProposalStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    REQUIRES_INVESTIGATION = "requires_investigation"


class Constraint(BaseModel):
    constraint_id: str
    description: str
    constraint_type: ConstraintType
    category: str
    priority: ConstraintPriority
    value: str


class ConstraintInterpretation(BaseModel):
    original_instruction: str
    interpreted_constraint: Constraint
    confidence: float = Field(ge=0, le=1)
    requires_confirmation: bool
    confirmation_status: ConfirmationStatus
    interpretation_rationale: str


class RecoveryOption(BaseModel):
    option_id: str
    strategy: RecoveryStrategy
    proposed_itinerary: Itinerary
    proposal_status: RecoveryProposalStatus
    rationale: str
    preserved_constraints: list[str] = Field(default_factory=list)
    violated_constraints: list[str] = Field(default_factory=list)
    trade_offs: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class RejectedOption(BaseModel):
    option_id: str
    rejection_reason: str


class OptionValidation(BaseModel):
    option_id: str
    validation_result: ValidationResult


class ApprovalRecord(BaseModel):
    option_id: str | None = None
    status: ApprovalStatus
    timestamp: datetime
    user_feedback: str | None = None


class ConstraintChange(BaseModel):
    constraint_id: str
    original_value: str
    proposed_value: str
    reason: str
    approval_status: ApprovalStatus


class ExecutionEvent(BaseModel):
    event_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    stage: str
    event_type: str
    description: str
    details: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )


class RecoveryPlanningInput(BaseModel):
    original_itinerary: Itinerary
    disruption_scenario: DisruptionScenario
    investigation_result: InvestigationResult
    mandatory_constraints: list[Constraint] = Field(default_factory=list)
    flexible_preferences: list[Constraint] = Field(default_factory=list)
    user_instructions: str
    strategy: RecoveryStrategy
    revision_count: int = Field(default=0, ge=0)
    rejected_options: list[RejectedOption] = Field(default_factory=list)
    additional_instructions: str = ""
