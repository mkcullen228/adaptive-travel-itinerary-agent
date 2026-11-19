
from pydantic import BaseModel

from src.evaluation.scenario_loader import EvidenceQualityScenario


class ResearcherEvaluationResult(BaseModel):
    scenario_id: str
    finding_count: int
    finding_count_passed: bool
    status_passed: bool
    supporting_sources_passed: bool
    conflicting_sources_passed: bool
    source_review_passed: bool
    source_quality_warnings_passed: bool
    provenance_passed: bool
    passed: bool
    failures: list[str]


def evaluate_researcher_output(
    scenario: EvidenceQualityScenario,
    evidence_brief,
) -> ResearcherEvaluationResult:
    """Evaluate a Researcher's EvidenceBrief against a scenario."""

    findings = evidence_brief.findings
    expected = scenario.expected_researcher_output

    failures = []

    # Exactly one finding is expected in this controlled experiment.
    finding_count_passed = len(findings) == 1

    if not finding_count_passed:
        failures.append(
            f"Expected exactly one finding; received {len(findings)}."
        )

    # Use the finding only when exactly one is present.
    finding = findings[0] if finding_count_passed else None

    status_passed = False
    supporting_sources_passed = False
    conflicting_sources_passed = False
    source_review_passed = False
    source_quality_warnings_passed = False

    if finding is not None:
        status_passed = finding.status == expected.status

        if not status_passed:
            failures.append(
                f"Expected status '{expected.status.value}', "
                f"received '{finding.status.value}'."
            )

        supporting_sources_passed = (
            set(finding.supporting_source_ids)
            == set(expected.supporting_source_ids)
        )

        if not supporting_sources_passed:
            failures.append(
                "Supporting source IDs do not match expected IDs."
            )

        conflicting_sources_passed = (
            set(finding.conflicting_source_ids)
            == set(expected.conflicting_source_ids)
        )

        if not conflicting_sources_passed:
            failures.append(
                "Conflicting source IDs do not match expected IDs."
            )

        source_review_passed = (
            set(evidence_brief.source_ids_reviewed)
            == set(expected.source_ids_reviewed)
        )

        if not source_review_passed:
            failures.append(
                "Reviewed source IDs do not match expected IDs."
            )

        # Check whether warnings are present when expected.
        # We intentionally do not require exact wording.
        source_quality_warnings_passed = (
            not expected.source_quality_warnings
            or bool(finding.source_quality_warnings)
        )

        if not source_quality_warnings_passed:
            failures.append(
                "Expected source-quality warnings, but none were reported."
            )

    else:
        failures.append(
            "Researcher output could not be evaluated without "
            "exactly one finding."
        )

    available_source_ids = {
        evidence.source_id for evidence in scenario.retrieved_evidence
    }

    referenced_source_ids = set()

    if finding is not None:
        referenced_source_ids.update(finding.supporting_source_ids)
        referenced_source_ids.update(finding.conflicting_source_ids)

    referenced_source_ids.update(evidence_brief.source_ids_reviewed)

    invalid_source_ids = referenced_source_ids - available_source_ids
    provenance_passed = not invalid_source_ids

    if invalid_source_ids:
        failures.append(
            "Researcher referenced unavailable source IDs: "
            f"{sorted(invalid_source_ids)}"
        )

    checks = [
        finding_count_passed,
        status_passed,
        supporting_sources_passed,
        conflicting_sources_passed,
        source_review_passed,
        source_quality_warnings_passed,
        provenance_passed,
    ]

    return ResearcherEvaluationResult(
        scenario_id=scenario.scenario_id,
        finding_count=len(findings),
        finding_count_passed=finding_count_passed,
        status_passed=status_passed,
        supporting_sources_passed=supporting_sources_passed,
        conflicting_sources_passed=conflicting_sources_passed,
        source_review_passed=source_review_passed,
        source_quality_warnings_passed=source_quality_warnings_passed,
        provenance_passed=provenance_passed,
        passed=all(checks),
        failures=failures,
    )
