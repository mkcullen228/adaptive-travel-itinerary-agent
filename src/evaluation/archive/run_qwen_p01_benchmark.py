import json
import ollama
from pathlib import Path

from src.models.agent_workflow import (
    RecoveryPlanningInput,
    RecoveryStrategy,
)
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.itinerary import Itinerary
from src.validation.schedule_validator import validate_itinerary
from src.recovery.generation import generate_recovery_option

from src.prompts.recovery_planning import RECOVERY_SYSTEM_PROMPT
from src.prompts.strategy_instructions import (
    MINIMAL_DISRUPTION_INSTRUCTION,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_NAME = "qwen3.5:4b"

BASELINE_PATH = (
    PROJECT_ROOT
    / "data/itineraries/dc_baseline_2026_11_07.json"
)

INVESTIGATION_PATH = (
    PROJECT_ROOT
    / "tests/fixtures/p01_investigation_context.json"
)

DISRUPTION_PATH = (
    PROJECT_ROOT
    / "tests/fixtures/p01_disruption_scenario.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    "qwen_3_5_4b/P-01/structured_output_1.md"
)


def load_test_inputs():
    original_itinerary = Itinerary.model_validate_json(
        BASELINE_PATH.read_text(encoding="utf-8")
    )

    investigation_result = InvestigationResult.model_validate_json(
        INVESTIGATION_PATH.read_text(encoding="utf-8")
    )

    disruption_scenario = DisruptionScenario.model_validate_json(
        DISRUPTION_PATH.read_text(encoding="utf-8")
    )

    return (
        original_itinerary,
        investigation_result,
        disruption_scenario,
    )


def build_user_prompt(
    original_itinerary,
    investigation_result,
    disruption_scenario,
):
    planning_context = {
        "original_itinerary": original_itinerary.model_dump(mode="json"),
        "disruption_scenario": disruption_scenario.model_dump(mode="json"),
        "investigation_result": investigation_result.model_dump(mode="json"),
        "strategy": "minimal_disruption",
        "additional_instructions": (
            "Preserve all unaffected original activities provisionally. "
            "Remove the confirmed unavailable National Gallery. "
            "Do not imply that the remaining venues are available. "
            "Do not claim schedule feasibility has been established. "
            "Do not invent replacement activities. "
            "Explain all remaining uncertainties."
        ),
    }

    return (
        "Prepare a recovery proposal using the following planning context.\n\n"
        "Return a complete RecoveryOption object.\n"
        "The original itinerary must remain unchanged.\n\n"
        + json.dumps(planning_context, indent=2)
    )


def run_benchmark():
    (
        original_itinerary,
        investigation_result,
        disruption_scenario,
    ) = load_test_inputs()

    print("Starting P-01 benchmark using shared generator...", flush=True)

    planning_input = RecoveryPlanningInput(
        original_itinerary=original_itinerary,
        disruption_scenario=disruption_scenario,
        investigation_result=investigation_result,
        user_instructions=(
            "Recover the itinerary after the confirmed "
            "National Gallery unavailability."
        ),
        strategy=RecoveryStrategy.MINIMAL_DISRUPTION,
        additional_instructions=(
            "Preserve all unaffected original activities provisionally. "
            "Remove the confirmed unavailable National Gallery. "
            "Do not imply that the remaining venues are available. "
            "Do not claim schedule feasibility has been established. "
            "Do not invent replacement activities. "
            "Explain all remaining uncertainties."
        ),
    )

    result = generate_recovery_option(
        planning_input=planning_input,
        model_name=MODEL_NAME,
    )

    # Use a new output filename so the historical response is preserved.
    shared_output_path = OUTPUT_PATH.with_name(
        "structured_output_shared_generator_1.json"
    )

    shared_output_path.parent.mkdir(parents=True, exist_ok=True)
    shared_output_path.write_text(
        result.raw_response,
        encoding="utf-8",
    )

    validation_result = validate_itinerary(
        result.recovery_option.proposed_itinerary
    )

    print("\nGENERATION METADATA:")
    print(f"Model: {result.model_name}")
    print(f"Latency: {result.latency_seconds:.2f} seconds")
    print(f"Input tokens: {result.input_tokens}")
    print(f"Output tokens: {result.output_tokens}")

    print("\nDETERMINISTIC VALIDATION:")
    print(validation_result.model_dump_json(indent=2))

    print("\nSTRUCTURED OUTPUT VALIDATION: PASSED")
    print("\nMODEL RESPONSE:")
    print(result.recovery_option.model_dump_json(indent=2))

    print(f"\nRaw response saved to: {shared_output_path}")


if __name__ == "__main__":
    run_benchmark()
