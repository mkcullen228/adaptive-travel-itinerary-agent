
import json
from pathlib import Path

from src.models.itinerary import Itinerary
from src.models.agent_workflow import RecoveryOption
from src.models.disruption import DisruptionScenario
from src.models.llm_evaluation import (
    LLMEvaluationRecord,
    EvaluationLevel,
    OverallResult,
)

from src.evaluation.schedule_comparison import compare_itineraries
from src.evaluation.schedule_robustness import calculate_schedule_robustness
from src.evaluation.recovery_consistency import evaluate_recovery_consistency
from src.evaluation.evaluation_recorder import append_evaluation_record
from src.validation.schedule_validator import validate_itinerary


# --------------------------------------------------
# 1. Define project paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

baseline_path = (
    ROOT
    / "data/itineraries/dc_baseline_2026_11_07_p02_routes_expanded.json"
)

proposal_path = (
    ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/P-02/iteration_3.md"
)

disruption_path = (
    ROOT / "tests/fixtures/p02_disruption_scenario.json"
)

results_path = (
    ROOT
    / "data/evaluations/llm_benchmarks/evaluation_results.json"
)


# --------------------------------------------------
# 2. Load baseline, proposal, and disruption scenario
# --------------------------------------------------

with baseline_path.open(encoding="utf-8") as file:
    baseline = Itinerary.model_validate_json(file.read())

with proposal_path.open(encoding="utf-8") as file:
    proposal = RecoveryOption.model_validate_json(file.read())

with disruption_path.open(encoding="utf-8") as file:
    disruption = DisruptionScenario.model_validate_json(file.read())


# --------------------------------------------------
# 3. Calculate evaluation metrics
# --------------------------------------------------

comparison = compare_itineraries(
    baseline,
    proposal.proposed_itinerary
)

validation = validate_itinerary(
    proposal.proposed_itinerary
)

schedule_robustness = calculate_schedule_robustness(
    proposal.proposed_itinerary
)

recovery_consistency = evaluate_recovery_consistency(
    baseline,
    disruption,
    proposal
)


# --------------------------------------------------
# 4. Create the LLM evaluation record
# --------------------------------------------------

record = LLMEvaluationRecord(
    evaluation_id="P02-QWEN-003",
    model_name="qwen3.5:4b",
    model_version="4b",
    scenario_id="P-02",
    iteration=3,
    strategy="best_overall_feasibility",
    prompt_version="p02-v1",
    rubric_version="2.1",

    structured_output_valid=True,

    deterministic_validation=validation.model_dump(mode="json"),
    schedule_comparison=comparison,
    schedule_robustness=schedule_robustness,
    recovery_consistency=recovery_consistency,

    criterion_results={
        "mandatory_constraint_preservation": EvaluationLevel.PASS,
        "flexible_constraint_adherence": EvaluationLevel.PARTIAL,
        "disruption_handling": EvaluationLevel.FAIL,
        "schedule_change_accuracy": EvaluationLevel.FAIL,
        "narrative_itinerary_consistency": EvaluationLevel.FAIL,
        "evidence_grounding": EvaluationLevel.PARTIAL,
        "uncertainty_handling": EvaluationLevel.PASS,
        "unsupported_assumptions": EvaluationLevel.PARTIAL,
    },

    overall_result=OverallResult.PARTIAL,

    failure_observations=[
        "Both weather-affected outdoor activities remain scheduled during the disruption window.",
        "The rationale incorrectly claims the activities were moved before noon.",
        "The proposed WWII Memorial visit overlaps the mandatory Natural History Museum visit by 20 minutes.",
        "The proposed schedule does not provide sufficient time for the Natural History to WWII Memorial walking leg.",
        "No verified indoor replacement activities were available in the investigation context.",
        "The proposal changes activity times but does not successfully resolve the weather disruption."
    ],

    raw_response_path=str(proposal_path)
)


# --------------------------------------------------
# 5. Save evaluation record
# --------------------------------------------------

append_evaluation_record(
    results_path,
    record
)


# --------------------------------------------------
# 6. Display evaluation summary
# --------------------------------------------------

print("\nP-02 ITERATION 3 EVALUATION RECORD SAVED")
print("----------------------------------------")
print(f"Evaluation ID: {record.evaluation_id}")
print(f"Model: {record.model_name}")
print(f"Strategy: {record.strategy}")
print(f"Overall result: {record.overall_result.value}")


print("\nDETERMINISTIC VALIDATION")
print("------------------------")
print(validation.model_dump_json(indent=2))


print("\nRECOVERY CONSISTENCY")
print("--------------------")
print(json.dumps(recovery_consistency, indent=2))


print("\nSCHEDULE COMPARISON")
print("-------------------")
print(json.dumps(comparison, indent=2))


print("\nSCHEDULE ROBUSTNESS")
print("-------------------")
print(json.dumps(schedule_robustness, indent=2))


print("\nQUALITY SCORES")
print("--------------")

for criterion, score in record.criterion_results.items():
    print(f"{criterion}: {score.value}")


print("\nFAILURE OBSERVATIONS")
print("--------------------")

for observation in record.failure_observations:
    print(f"- {observation}")
