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


ROOT = Path(__file__).resolve().parents[2]

baseline_path = (
    ROOT
    / "data/itineraries/dc_baseline_2026_11_07_p02_routes_expanded.json"
)

proposal_path = (
    ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/P-02/iteration_5.md"
)

disruption_path = (
    ROOT / "tests/fixtures/p02_disruption_scenario.json"
)

results_path = (
    ROOT / "data/evaluations/llm_benchmarks/evaluation_results.json"
)


# Load the benchmark baseline, Iteration 5 proposal, and disruption.
with baseline_path.open(encoding="utf-8") as file:
    baseline = Itinerary.model_validate_json(file.read())

with proposal_path.open(encoding="utf-8") as file:
    proposal = RecoveryOption.model_validate_json(file.read())

with disruption_path.open(encoding="utf-8") as file:
    disruption = DisruptionScenario.model_validate_json(file.read())


# Calculate deterministic metrics independently of the LLM's rationale.
comparison = compare_itineraries(
    baseline,
    proposal.proposed_itinerary,
)

validation = validate_itinerary(
    proposal.proposed_itinerary,
)

schedule_robustness = calculate_schedule_robustness(
    proposal.proposed_itinerary,
)

recovery_consistency = evaluate_recovery_consistency(
    baseline,
    disruption,
    proposal,
)


# Human-assigned rubric scores are based on the observed raw response.
# Deterministic schedule and recovery metrics above are calculated by code.
record = LLMEvaluationRecord(
    evaluation_id="P02-QWEN-005",
    model_name="qwen3.5:4b",
    model_version="4b",
    scenario_id="P-02",
    iteration=5,
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
        "Both weather-affected outdoor activities remain scheduled during the noon-to-6 PM disruption window.",
        "The rationale claims both outdoor activities were moved before the onset of rain, but their structured start times are 14:30 and 15:40.",
        "The World War II Memorial is scheduled from 14:30 to 15:00, overlapping the mandatory Natural History Museum visit, which runs until 14:50.",
        "The supplied Natural History Museum-to-World War II Memorial walking estimate is 17 minutes, so the proposed sequence is also infeasible on travel time.",
        "The rationale says the schedule preserves the original sequence and minimizes travel time, but the structured schedule does not establish a feasible recovery.",
        "The proposal includes only four travel legs, while the expanded benchmark baseline contains eight directed travel legs; four supplied alternative route legs are not carried into the proposal.",
        "No verified indoor replacement activities or venue availability were supplied by the investigation context.",
        "The proposal assumes the supplied walking estimates remain accurate at the proposed times without evidence of time-specific validation.",
    ],

    raw_response_path=str(proposal_path),
)


# Append only; the recorder rejects duplicate evaluation IDs and preserves
# existing historical records.
append_evaluation_record(
    results_path,
    record,
)


print("\nP-02 ITERATION 5 EVALUATION RECORD SAVED")
print("----------------------------------------")
print(f"Evaluation ID: {record.evaluation_id}")
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
