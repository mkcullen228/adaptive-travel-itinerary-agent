
from pathlib import Path

from src.evaluation.scenario_loader import (
    EvidenceQualityScenario,
    load_scenarios,
)
from src.models.agent_state import TravelAgentState
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.itinerary import Itinerary
from src.workflows.state_initialization import initialize_agent_state


PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASELINE_PATH = (
    PROJECT_ROOT / "data/itineraries/dc_baseline_2026_11_07.json"
)
DISRUPTION_PATH = (
    PROJECT_ROOT / "tests/fixtures/p01_disruption_scenario.json"
)
INVESTIGATION_PATH = (
    PROJECT_ROOT / "tests/fixtures/p01_investigation_context.json"
)
SCENARIO_DIRECTORY = (
    PROJECT_ROOT / "data/evaluations/evidence_quality/scenarios"
)


def load_evaluation_inputs(
    scenario_id: str,
) -> tuple[EvidenceQualityScenario, TravelAgentState]:
    """Load shared P-01 inputs and overlay one evidence scenario."""

    scenarios = load_scenarios(
        SCENARIO_DIRECTORY,
        scenario_ids=[scenario_id],
    )
    scenario = scenarios[0]


    itinerary = Itinerary.model_validate_json(
        BASELINE_PATH.read_text(encoding="utf-8")
    )
    disruption = DisruptionScenario.model_validate_json(
        DISRUPTION_PATH.read_text(encoding="utf-8")
    )
    base_investigation = InvestigationResult.model_validate_json(
        INVESTIGATION_PATH.read_text(encoding="utf-8")
    )

    if scenario.base_case.itinerary_id != "P-01":
        raise ValueError(
            "Expected evidence scenario to reference P-01."
        )

    if itinerary.itinerary_id != "dc_baseline_2026_11_07":
        raise ValueError(
            "Unexpected canonical P-01 itinerary."
        )

    if scenario.base_case.unavailable_venue not in {
        activity.name for activity in itinerary.activities
    }:
        raise ValueError(
            "Unavailable venue is not present in the original itinerary."
        )

    if scenario.base_case.mandatory_activity_name not in {
        activity.name
        for activity in itinerary.activities
        if activity.mandatory
    }:
        raise ValueError(
            "Expected mandatory activity is not present in the itinerary."
        )

    if disruption.scenario_id != "P-01":
        raise ValueError("Expected the P-01 disruption fixture.")

    investigation_warnings = [
        warning
        for warning in base_investigation.investigation_warnings
        if "replacement venue availability" not in warning.lower()
    ]

    investigation_result = InvestigationResult(
        investigation_id=f"p01_evidence_quality_{scenario.scenario_id}",
        scenario_id=disruption.scenario_id,
        retrieved_evidence=scenario.retrieved_evidence,
        evidence_assessments=[],
        investigation_warnings=investigation_warnings,
    )

    state = initialize_agent_state(
        itinerary=itinerary,
        disruption=disruption,
        user_instructions=(
            "Recover the itinerary after the confirmed "
            "National Gallery of Art unavailability. "
            "Preserve the existing mandatory National Museum "
            "of Natural History visit. Do not add a duplicate visit."
        ),
    )
    state["investigation_result"] = investigation_result

    return scenario, state
