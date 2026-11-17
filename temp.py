
import json
from pathlib import Path

from src.models.itinerary import Itinerary
from src.models.agent_workflow import RecoveryOption
from src.models.disruption import DisruptionScenario

from src.evaluation.benchmark_evaluator import evaluate_benchmark_case
from src.evaluation.deterministic_evaluation_recorder import (
    build_deterministic_evaluation_record,
    save_deterministic_evaluation,
)

root = Path.cwd()

raw_dir = (
    root
    / "data/evaluations/llm_benchmarks/raw_responses/"
    / "qwen_3_5_4b/consolidated"
)

output_dir = (
    root
    / "data/evaluations/deterministic_results/qwen_3_5_4b"
)

benchmarks = {
    "P-01": {
        "baseline": "data/itineraries/dc_baseline_2026_11_07.json",
        "proposal": "P-01.json",
        "scenario": "tests/fixtures/p01_disruption_scenario.json",
    },
    "P-02-iteration-5-corrected": {
        "baseline": (
            "data/itineraries/"
            "dc_baseline_2026_11_07_p02_routes_expanded.json"
        ),
        "proposal": "P-02-iteration-5-corrected.json",
        "scenario": "tests/fixtures/p02_disruption_scenario.json",
    },
}

for benchmark_id, paths in benchmarks.items():
    raw_path = raw_dir / paths["proposal"]
    metadata_path = raw_path.with_name(
        f"{raw_path.stem}.metadata.json"
    )

    generation_metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    original = Itinerary.model_validate_json(
        (root / paths["baseline"]).read_text(encoding="utf-8")
    )

    proposal = RecoveryOption.model_validate_json(
        raw_path.read_text(encoding="utf-8")
    )

    scenario = DisruptionScenario.model_validate_json(
        (root / paths["scenario"]).read_text(encoding="utf-8")
    )

    evaluation_result = evaluate_benchmark_case(
        original=original,
        scenario=scenario,
        proposal=proposal,
    )

    record = build_deterministic_evaluation_record(
        evaluation_result=evaluation_result,
        generation_metadata=generation_metadata,
        raw_response_path=raw_path.relative_to(root),
        generation_metadata_path=metadata_path.relative_to(root),
    )

    output_path = output_dir / f"{benchmark_id}.json"

    save_deterministic_evaluation(output_path, record)

    print(f"\nSaved: {output_path.relative_to(root)}")
    print(
        "Validation:",
        evaluation_result["deterministic_validation"]["status"],
    )
    print(
        "Recovery addressed:",
        evaluation_result["recovery_consistency"][
            "all_affected_activities_addressed"
        ],
    )
    print(
        "Robustness:",
        evaluation_result["schedule_robustness"]["status"],
    )
    print(
        "Narrative:",
        evaluation_result["narrative_consistency"]["status"],
    )
