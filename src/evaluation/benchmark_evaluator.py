
from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario
from src.models.agent_workflow import RecoveryOption

from src.validation.schedule_validator import validate_itinerary

from src.evaluation.recovery_consistency import (
    evaluate_recovery_consistency,
)
from src.evaluation.schedule_comparison import compare_itineraries
from src.evaluation.schedule_robustness import (
    calculate_schedule_robustness,
)
from src.evaluation.narrative_consistency import (
    evaluate_narrative_consistency,
)


def evaluate_benchmark_case(
    original: Itinerary,
    scenario: DisruptionScenario,
    proposal: RecoveryOption,
) -> dict:
    """
    Run all deterministic evaluators against one recovery proposal.

    This function does not call an LLM, modify the input objects,
    or persist evaluation results.
    """

    proposed = proposal.proposed_itinerary

    validation_result = validate_itinerary(proposed)

    return {
        "scenario_id": scenario.scenario_id,
        "proposal_id": proposal.option_id,
        "deterministic_validation": (
            validation_result.model_dump(mode="json")
        ),
        "recovery_consistency": evaluate_recovery_consistency(
            original,
            scenario,
            proposal,
        ),
        "schedule_comparison": compare_itineraries(
            original,
            proposed,
        ),
        "schedule_robustness": calculate_schedule_robustness(
            proposed,
        ),
        "narrative_consistency": evaluate_narrative_consistency(
            original,
            proposal,
        ),
    }
