import json
import ollama
from pathlib import Path

from src.models.agent_workflow import RecoveryOption
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.itinerary import Itinerary
from src.validation.schedule_validator import validate_itinerary

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
    print("Starting Qwen P-01 benchmark...", flush=True)
    user_prompt = build_user_prompt(
        original_itinerary,
        investigation_result,
        disruption_scenario,
    )
    print("Sending request to Ollama...", flush=True)
    response = ollama.chat(
        model=MODEL_NAME,
        think=False,
        messages=[
            {
                "role": "system",
                "content": (
                    RECOVERY_SYSTEM_PROMPT
                    + "\n\n"
                    + MINIMAL_DISRUPTION_INSTRUCTION
                ),
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        format=RecoveryOption.model_json_schema(),
        options={"temperature": 0},
    )
    print("Received response from Ollama.", flush=True)
    raw_response = response.message.content
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(raw_response, encoding="utf-8")

    validated_option = RecoveryOption.model_validate_json(raw_response)

    validation_result = validate_itinerary(
        validated_option.proposed_itinerary
    )

    print("\nDETERMINISTIC VALIDATION:")
    print(validation_result.model_dump_json(indent=2))

    print("\nSTRUCTURED OUTPUT VALIDATION: PASSED")
    print("\nMODEL RESPONSE:")
    print(validated_option.model_dump_json(indent=2))

    print(f"\nRaw response saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run_benchmark()
