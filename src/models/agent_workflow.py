from enum import Enum
from pydantic import BaseModel, Field

from src.models.itinerary import Itinerary


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
    proposed_itinerary: Itinerary
    rationale: str
    preserved_constraints: list[str] = Field(default_factory=list)
    violated_constraints: list[str] = Field(default_factory=list)
    trade_offs: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class RejectedOption(BaseModel):
    option_id: str
    rejection_reason: str
