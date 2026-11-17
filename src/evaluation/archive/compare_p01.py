
import json
from pathlib import Path

from src.models.itinerary import Itinerary
from src.models.agent_workflow import RecoveryOption
from src.models.llm_evaluation import (
    LLMEvaluationRecord,
    EvaluationLevel,
    OverallResult
)

from src.evaluation.schedule_comparison import compare_itineraries
from src.evaluation.evaluation_recorder import append_evaluation_record
from src.evaluation.schedule_robustness import calculate_schedule_robustness
from src.validation.schedule_validator import validate_itinerary


# --------------------------------------------------
# 1. Define project paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

baseline_path = (
    ROOT / "data/itineraries/dc_baseline_2026_11_07.json"
)

proposal_path = (
    ROOT
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/P-01/structured_output_1.md"
)

results_path = (
    ROOT
    / "data/evaluations/llm_benchmarks/evaluation_results.json"
)


# --------------------------------------------------
# 2. Load original itinerary and Qwen proposal
# --------------------------------------------------

with baseline_path.open(encoding="utf-8") as file:
    baseline = Itinerary.model_validate_json(file.read())

with proposal_path.open(encoding="utf-8") as file:
    proposal = RecoveryOption.model_validate_json(file.read())


# --------------------------------------------------
# 3. Compare original and proposed itineraries
# --------------------------------------------------

comparison = compare_itineraries(
    baseline,
    proposal.proposed_itinerary
)


# --------------------------------------------------
# 4. Run deterministic schedule validation
# --------------------------------------------------

validation = validate_itinerary(
    proposal.proposed_itinerary
)

schedule_robustness = calculate_schedule_robustness(
    proposal.proposed_itinerary
)

# --------------------------------------------------
# 5. Create the LLM evaluation record
# --------------------------------------------------

record = LLMEvaluationRecord(
    evaluation_id="P01-QWEN-005",
    model_name="qwen3.5:4b",
    model_version="4b",
    scenario_id="P-01",
    iteration=4,
    strategy="minimal_disruption",
    prompt_version="p01-v1",

    structured_output_valid=True,

    deterministic_validation=validation.model_dump(mode="json"),
    schedule_comparison=comparison,
    schedule_robustness=schedule_robustness,

    criterion_results={
        "mandatory_constraint_preservation": EvaluationLevel.PASS,
        "flexible_constraint_adherence": EvaluationLevel.NOT_APPLICABLE,
        "disruption_handling": EvaluationLevel.PASS,
        "schedule_change_accuracy": EvaluationLevel.FAIL,
        "evidence_grounding": EvaluationLevel.PARTIAL,
        "uncertainty_handling": EvaluationLevel.PASS,
        "unsupported_assumptions": EvaluationLevel.PASS
    },

    overall_result=OverallResult.PARTIAL,

    failure_observations=[
        "All four remaining activities were rescheduled earlier.",
        "The rationale incorrectly described the schedule changes as shifting forward by 50 minutes.",
        "The rationale referred to the removed activity as having a 50-minute duration, while the baseline specifies 90 minutes.",
        "Venue availability and travel estimate accuracy remain unverified."
    ],

    raw_response_path=str(proposal_path)
)


# --------------------------------------------------
# 6. Save evaluation record
# --------------------------------------------------

append_evaluation_record(
    results_path,
    record
)


# --------------------------------------------------
# 7. Display evaluation summary
# --------------------------------------------------

print("\nEVALUATION RECORD SAVED")
print("-----------------------")

print(f"Evaluation ID: {record.evaluation_id}")
print(f"Model: {record.model_name}")
print(f"Scenario: {record.scenario_id}")
print(f"Overall result: {record.overall_result.value}")

print("\nDETERMINISTIC VALIDATION")
print("------------------------")
print(f"Status: {validation.status.value}")

for issue in validation.issues:
    print(f"- {issue.issue_type.value}: {issue.description}")

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

print("\nFailure observations:")
for observation in record.failure_observations:
    print(f"- {observation}")
