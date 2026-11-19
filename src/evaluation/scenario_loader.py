
import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from src.models.evidence import EvidenceStatus
from src.models.retrieved_evidence import RetrievedEvidence


class ScenarioBaseCase(BaseModel):
    itinerary_id: str
    unavailable_venue: str
    recovery_target: str
    recovery_action: str
    mandatory_activity_name: str


class ExpectedResearcherOutput(BaseModel):
    status: EvidenceStatus
    supporting_source_ids: list[str] = Field(default_factory=list)
    conflicting_source_ids: list[str] = Field(default_factory=list)
    source_quality_warnings: list[str] = Field(default_factory=list)
    source_ids_reviewed: list[str] = Field(default_factory=list)


class ExpectedPlannerBehavior(BaseModel):
    may_recommend_recovery: bool
    must_preserve_mandatory_visit: bool
    must_not_add_duplicate_visit: bool
    must_not_claim_unverified_availability: bool
    must_communicate_unresolved_questions: bool
    must_request_verification: bool = False
    must_avoid_high_confidence: bool = False
    must_request_current_verification: bool = False
    must_identify_conflicting_information: bool = False
    must_request_conflict_resolution: bool = False


class EvidenceQualityScenario(BaseModel):
    scenario_id: str
    scenario_name: str
    description: str
    evaluation_reference_time: str
    base_case: ScenarioBaseCase
    retrieved_evidence: list[RetrievedEvidence] = Field(
        default_factory=list
    )
    expected_researcher_output: ExpectedResearcherOutput
    expected_planner_behavior: ExpectedPlannerBehavior

    @model_validator(mode="after")
    def validate_expected_source_ids(self):
        available_ids = {
            evidence.source_id for evidence in self.retrieved_evidence
        }

        expected_ids = (
            self.expected_researcher_output.supporting_source_ids
            + self.expected_researcher_output.conflicting_source_ids
            + self.expected_researcher_output.source_ids_reviewed
        )

        invalid_ids = set(expected_ids) - available_ids

        if invalid_ids:
            raise ValueError(
                "Expected Researcher output references source IDs "
                f"not present in retrieved evidence: {sorted(invalid_ids)}"
            )

        return self


def load_scenario(path: Path) -> EvidenceQualityScenario:
    """Load and validate one evidence-quality scenario."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return EvidenceQualityScenario.model_validate(data)


def load_scenarios(
    directory: Path,
    scenario_ids: list[str] | None = None,
) -> list[EvidenceQualityScenario]:
    """Load all scenarios, or only the requested scenario IDs."""
    scenario_paths = sorted(directory.glob("E*.json"))

    if scenario_ids is not None:
        requested_ids = set(scenario_ids)
        scenario_paths = [
            path
            for path in scenario_paths
            if path.stem.split("_")[0] in requested_ids
        ]

    scenarios = [load_scenario(path) for path in scenario_paths]

    loaded_ids = [scenario.scenario_id for scenario in scenarios]

    if len(loaded_ids) != len(set(loaded_ids)):
        raise ValueError("Duplicate scenario IDs found.")

    if scenario_ids is not None:
        missing_ids = set(scenario_ids) - set(loaded_ids)
        if missing_ids:
            raise ValueError(
                f"Requested scenarios were not found: {sorted(missing_ids)}"
            )

    return scenarios
