
from pathlib import Path

import pytest

from src.evaluation.scenario_loader import load_scenarios
from src.evaluation.evidence_quality_evaluator import (
    evaluate_researcher_output,
)
from src.models.evidence import EvidenceStatus
from src.models.multi_agent import EvidenceBrief, EvidenceFinding


SCENARIO_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluations"
    / "evidence_quality"
    / "scenarios"
)


def make_expected_brief(scenario):
    expected = scenario.expected_researcher_output

    finding = EvidenceFinding(
        claim="The existing Natural History Museum visit can be "
              "rescheduled or extended.",
        status=expected.status,
        supporting_source_ids=expected.supporting_source_ids,
        conflicting_source_ids=expected.conflicting_source_ids,
        explanation="Constructed expected assessment for testing.",
        source_quality_warnings=expected.source_quality_warnings,
    )

    return EvidenceBrief(
        findings=[finding],
        source_ids_reviewed=expected.source_ids_reviewed,
    )


@pytest.mark.parametrize(
    "scenario_id",
    ["E1", "E2", "E3", "E4", "E5"],
)
def test_expected_researcher_output_passes(scenario_id):
    scenarios = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=[scenario_id],
    )
    scenario = scenarios[0]

    brief = make_expected_brief(scenario)

    result = evaluate_researcher_output(scenario, brief)

    assert result.passed is True
    assert result.failures == []


def test_incorrect_evidence_status_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E1"],
    )[0]

    brief = make_expected_brief(scenario)
    brief.findings[0].status = EvidenceStatus.PARTIALLY_SUPPORTED

    result = evaluate_researcher_output(scenario, brief)

    assert result.passed is False
    assert result.status_passed is False


def test_invalid_source_id_fails_provenance():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E1"],
    )[0]

    brief = make_expected_brief(scenario)
    brief.findings[0].supporting_source_ids = ["unknown_source"]

    result = evaluate_researcher_output(scenario, brief)

    assert result.passed is False
    assert result.provenance_passed is False


def test_missing_source_quality_warning_fails():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E2"],
    )[0]

    brief = make_expected_brief(scenario)
    brief.findings[0].source_quality_warnings = []

    result = evaluate_researcher_output(scenario, brief)

    assert result.passed is False
    assert result.source_quality_warnings_passed is False


def test_multiple_findings_fail():
    scenario = load_scenarios(
        SCENARIO_DIR,
        scenario_ids=["E1"],
    )[0]

    brief = make_expected_brief(scenario)
    brief.findings.append(brief.findings[0].model_copy())

    result = evaluate_researcher_output(scenario, brief)

    assert result.passed is False
    assert result.finding_count_passed is False
