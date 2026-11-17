
from src.models.agent_workflow import RecoveryPlanningInput
from src.models.multi_agent import EvidenceBrief
from src.recovery.generation import (
    DEFAULT_MODEL,
    RecoveryGenerationResult,
    generate_recovery_option,
)


def plan_recovery(
    planning_input: RecoveryPlanningInput,
    evidence_brief: EvidenceBrief,
    model_name: str = DEFAULT_MODEL,
    client=None,
) -> RecoveryGenerationResult:
    """Generate a recovery proposal using the Researcher's evidence brief."""

    return generate_recovery_option(
        planning_input=planning_input,
        model_name=model_name,
        client=client,
        evidence_brief=evidence_brief,
    )
