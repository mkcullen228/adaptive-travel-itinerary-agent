
from pathlib import Path

from src.models.agent_workflow import (
    RecoveryPlanningInput,
    RecoveryStrategy,
)
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.itinerary import Itinerary

from src.recovery.generation import generate_recovery_option
from src.validation.schedule_validator import validate_itinerary


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_NAME = "qwen3.5:4b"

BASELINE_PATH = (
    PROJECT_ROOT
    / "data/itineraries/dc_baseline_2026_11_07_p02_routes_expanded.json"
)

INVESTIGATION_PATH = (
    PROJECT_ROOT / "tests/fixtures/p02_investigation_context.json"
)

DISRUPTION_PATH = (
    PROJECT_ROOT / "tests/fixtures/p02_disruption_scenario.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/P-02/iteration_5_shared_generator.json"
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

    return original_itinerary, investigation_result, disruption_scenario


def run_benchmark():
    (
        original_itinerary,
        investigation_result,
        disruption_scenario,
    ) = load_test_inputs()

    print("Starting P-02 benchmark using shared generator...", flush=True)

    planning_input = RecoveryPlanningInput(
        original_itinerary=original_itinerary,
        disruption_scenario=disruption_scenario,
        investigation_result=investigation_result,
        user_instructions=(
            "Recover the itinerary from the heavy-rain disruption "
            "while preserving mandatory constraints."
        ),
        strategy=RecoveryStrategy.BEST_OVERALL_FEASIBILITY,
        additional_instructions=(
            "Preserve all unaffected original activities provisionally. "
            "Address the outdoor activities affected by heavy rain. "
            "You may reschedule outdoor activities to times before "
            "12:00 PM if the schedule and available walking estimates "
            "support feasibility. Alternatively, you may replace "
            "affected outdoor activities with indoor alternatives, "
            "but only when retrieved evidence supports their availability. "
            "Do not invent venue availability, activity details, or "
            "travel estimates. Do not assume that moving an activity "
            "earlier is feasible when required travel estimates are missing. "
            "If neither recovery approach can be established as feasible, "
            "return a partial proposal and explain what remains unresolved. "
            "Preserve the mandatory Natural History Museum visit. "
            "Explain schedule changes and remaining uncertainties. "
            "All activity start times must use Washington, DC local time. "
            "Preserve the original itinerary's timezone convention. "
            "Do not convert activity times to UTC or append Z to timestamps. "
            "Use only the supplied directed walking estimates. "
            "Do not assume that a route estimate is interchangeable "
            "with its reverse direction. "
            "Do not invent or infer travel estimates for missing routes."
        ),
    )

    result = generate_recovery_option(
        planning_input=planning_input,
        model_name=MODEL_NAME,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
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

    print(f"\nRaw response saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run_benchmark()
