
from pydantic import BaseModel

from src.models.multi_agent import AuditReport
from src.models.itinerary import Itinerary


class AuditorEvaluationResult(BaseModel):
    scenario_id: str
    mandatory_activity_accuracy: bool
    evidence_conflict_recognition: bool
    evidence_limitation_recognition: bool
    schedule_accuracy: bool
    uncertainty_coverage: bool
    passed: bool
    failures: list[str]


def _report_text(audit_report: AuditReport) -> str:
    """Combine Auditor findings into searchable text."""

    fields = (
        audit_report.supported_claims
        + audit_report.unsupported_claims
        + audit_report.conflicting_claims
        + audit_report.omitted_uncertainties
        + audit_report.rationale_findings
        + audit_report.recommendations
    )

    return " ".join(fields).casefold()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _auditor_acknowledges_evidence_limitations(
    scenario,
    audit_text: str,
) -> bool:
    """Check whether the Auditor acknowledges relevant evidence limitations."""

    evidence = scenario.retrieved_evidence

    if not evidence:
        required_terms = (
            "no evidence",
            "no retrieved",
            "missing evidence",
            "absence of evidence",
            "lack of evidence",
            "lack of retrieved evidence",
            "no source data",
            "absence of retrieved sources",
        )
        return _contains_any(audit_text, required_terms)

    verification_statuses = {
        str(
            getattr(
                item.verification_status,
                "value",
                item.verification_status,
            )
        ).lower()
        for item in evidence
    }

    has_stale_evidence = (
        "stale" in verification_statuses
        or any(item.freshness_score < 0.5 for item in evidence)
    )

    has_low_quality_evidence = (
        "unverified" in verification_statuses
        or any(item.reliability < 0.5 for item in evidence)
    )

    if has_stale_evidence:
        stale_terms = (
            "stale",
            "outdated",
            "historical",
            "not current",
            "cannot confirm current",
            "current availability",
        )
        if not _contains_any(audit_text, stale_terms):
            return False

    if has_low_quality_evidence:
        quality_terms = (
            "low reliability",
            "unverified",
            "verification",
            "reliability",
            "verify",
        )
        if not _contains_any(audit_text, quality_terms):
            return False

    return True


def _acknowledges_conflicting_evidence(audit_text: str) -> bool:
    """Require an affirmative acknowledgment that evidence sources disagree."""

    conflict_terms = (
        "conflicting evidence",
        "conflicting information",
        "sources conflict",
        "sources disagree",
        "sources contradict",
        "contradictory evidence",
        "contradictory information",
        "inconsistent source information",
        "disagreement between sources",
        "evidence is inconsistent",
    )

    if not _contains_any(audit_text, conflict_terms):
        return False

    negated_terms = (
        "no conflicting evidence",
        "no material conflicting claims",
        "no conflicting information",
        "sources do not conflict",
        "sources do not disagree",
        "no contradiction",
        "not conflicting",
    )

    if _contains_any(audit_text, negated_terms):
        return False

    return True


def _validation_failure_texts(
    deterministic_validation: dict | None,
) -> list[str]:
    """Read validation issues from either supported input shape."""

    if not deterministic_validation:
        return []

    failures = deterministic_validation.get("failures", [])
    issues = deterministic_validation.get("issues", [])

    result = []

    for item in failures + issues:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            issue_type = str(item.get("issue_type", ""))
            description = str(item.get("description", ""))
            result.append(f"{issue_type}: {description}")
        else:
            result.append(str(item))

    return result


def _auditor_acknowledges_validation_failures(
    deterministic_validation: dict | None,
    audit_text: str,
) -> bool:
    """Check that material deterministic validation failures are acknowledged."""

    validation_failures = _validation_failure_texts(
        deterministic_validation
    )

    if not validation_failures:
        return True

    for failure in validation_failures:
        failure_text = failure.casefold()

        if (
            "schedule time" in failure_text
            or "time mismatch" in failure_text
            or "rationale schedule" in failure_text
        ):
            acknowledged = (
                _contains_any(
                    audit_text,
                    ("schedule time", "time mismatch", "rationale schedule"),
                )
                and _contains_any(
                    audit_text,
                    (
                        "mismatch",
                        "inconsistent",
                        "incorrect",
                        "does not match",
                        "does not align",
                    ),
                )
            )

        elif (
            "travel estimate" in failure_text
            or "walking estimate" in failure_text
            or "travel time" in failure_text
        ):
            acknowledged = _contains_any(
                audit_text,
                (
                    "travel estimate",
                    "walking estimate",
                    "travel time data",
                    "missing travel",
                    "travel time is unavailable",
                    "travel time is not available",
                    "travel time cannot be verified",
                ),
            )

        elif "overlap" in failure_text:
            acknowledged = _contains_any(
                audit_text,
                (
                    "overlap",
                    "overlapping activities",
                    "schedule conflict",
                    "activities conflict",
                ),
            )

        else:
            acknowledged = _contains_any(
                audit_text,
                (
                    "validation failure",
                    "validation issue",
                    "schedule issue",
                    "validation concern",
                ),
            )

        if not acknowledged:
            return False

    return True


def _auditor_covers_uncertainties(
    scenario,
    audit_text: str,
    deterministic_validation: dict | None,
) -> bool:
    """
    Check whether the Auditor communicates the uncertainties relevant
    to the scenario and any deterministic validation failures.

    This checks for meaningful acknowledgment rather than identical wording.
    """

    audit_text = audit_text.casefold()
    expected = scenario.expected_planner_behavior

    # Missing or incomplete evidence should remain an explicit uncertainty.
    if expected.must_communicate_unresolved_questions:
        unresolved_terms = (
            "unresolved",
            "uncertain",
            "uncertainty",
            "cannot confirm",
            "cannot verify",
            "requires verification",
            "requiring verification",
            "requires further verification",
            "needs verification",
            "further verification",
            "additional information",
            "additional evidence",
            "not independently verified",
            "not independently confirmed",
            "no retrieved sources",
            "no evidence records",
            "no evidence",
            "has not been assessed",
            "has not been verified",
            "has not been confirmed",
            "without verifying",
            "unverified",
            "speculative",
            "provisional",
        )

        if not _contains_any(audit_text, unresolved_terms):
            return False

    # General verification requirements apply to missing or insufficient
    # evidence. They do not necessarily require current/up-to-date evidence.
    if getattr(expected, "must_request_verification", False):
        verification_request_terms = (
            "pending verification",
            "requires verification",
            "requiring verification",
            "requires further verification",
            "needs verification",
            "needs to be verified",
            "should be verified",
            "must be verified",
            "verification is needed",
            "verification is required",
            "verify the",
            "verify whether",
            "verify availability",
            "verify travel",
            "further verification",
        )

        if not _contains_any(audit_text, verification_request_terms):
            return False

    # High-confidence conclusions should not be drawn from insufficient
    # or unreliable evidence.
    if getattr(expected, "must_avoid_high_confidence", False):
        confidence_terms = (
            "low confidence",
            "limited confidence",
            "low reliability",
            "not conclusive",
            "not sufficient to confirm",
            "cannot establish",
            "cannot be established",
            "cannot be guaranteed",
            "cannot be confirmed",
            "should not be treated as confirmed",
            "requires verification",
            "requiring verification",
            "requires further verification",
            "needs further verification",
            "overstates certainty",
            "unsupported by evidence",
            "partially unsupported",
            "not supported by evidence",
            "lacks supporting evidence",
            "lacks explicit evidentiary support",
            "insufficient evidence",
            "has not been assessed",
            "has not been verified",
            "unverified",
            "unverified assumption",
            "not independently verified",
            "not independently confirmed",
            "speculative",
            "provisional",
        )

        if not _contains_any(audit_text, confidence_terms):
            return False

    # Stale evidence cannot establish current availability.
    # Keep this requirement separate from general verification.
    if getattr(expected, "must_request_current_verification", False):
        current_verification_terms = (
            "current verification",
            "verify current",
            "confirm current",
            "cannot verify current",
            "cannot confirm current",
            "current availability",
            "up-to-date information",
            "updated information",
            "not independently verified",
            "not independently confirmed",
            "does not apply to the target date",
            "remaining activity availability has not been independently confirmed",
        )

        if not _contains_any(audit_text, current_verification_terms):
            return False

    # Conflicting evidence must remain unresolved until reconciled.
    if getattr(expected, "must_identify_conflicting_information", False):
        conflict_resolution_terms = (
            "conflicting evidence",
            "conflicting information",
            "sources disagree",
            "sources conflict",
            "contradictory evidence",
            "contradictory information",
            "resolve the conflict",
            "conflict must be resolved",
            "requires clarification",
        )

        if not _contains_any(audit_text, conflict_resolution_terms):
            return False

    # Deterministic validation issues must also be communicated.
    validation_failures = _validation_failure_texts(
        deterministic_validation
    )

    if validation_failures:
        if not _contains_any(
            audit_text,
            (
                "incomplete",
                "cannot be verified",
                "cannot confirm",
                "unresolved",
                "validation issue",
                "schedule issue",
                "travel estimate",
                "missing travel",
                "schedule time",
                "time mismatch",
                "overlap",
            ),
        ):
            return False

    return True


def evaluate_auditor_output(
    scenario,
    original_itinerary: Itinerary,
    proposed_itinerary: Itinerary,
    audit_report: AuditReport,
    deterministic_validation: dict | None = None,
) -> AuditorEvaluationResult:
    """Evaluate Auditor findings against known scenario facts."""

    failures = []

    mandatory_name = (
        scenario.base_case.mandatory_activity_name.casefold()
    )

    original_mandatory = [
        activity
        for activity in original_itinerary.activities
        if activity.name.casefold() == mandatory_name
        and activity.mandatory
    ]

    proposed_matches = [
        activity
        for activity in proposed_itinerary.activities
        if activity.name.casefold() == mandatory_name
    ]

    # The original itinerary must contain exactly one mandatory activity.
    # The proposal must preserve that same activity exactly once.
    mandatory_preserved = (
        len(original_mandatory) == 1
        and len(proposed_matches) == 1
        and proposed_matches[0].activity_id
        == original_mandatory[0].activity_id
        and proposed_matches[0].mandatory
    )

    audit_text = _report_text(audit_report)

    # Check both the actual proposal and whether the Auditor describes it
    # accurately.
    incorrect_removal_claims = (
        "mandatory activity was removed",
        "mandatory visit was removed",
        "mandatory activity is missing",
        "mandatory visit is missing",
        "mandatory activity was not preserved",
    )

    auditor_claims_removed = _contains_any(
        audit_text,
        incorrect_removal_claims,
    )

    mandatory_activity_accuracy = (
        mandatory_preserved and not auditor_claims_removed
    )

    if not mandatory_preserved:
        failures.append(
            "The proposed itinerary did not preserve exactly one instance "
            "of the original mandatory activity."
        )
    elif auditor_claims_removed:
        failures.append(
            "Auditor incorrectly reported that the preserved mandatory "
            "activity was removed or missing."
        )

    # E4 requires an affirmative acknowledgment of contradictory evidence.
    evidence_conflict_recognition = True

    if (
        scenario.expected_researcher_output.status.value == "conflicting"
    ):
        evidence_conflict_recognition = (
            _acknowledges_conflicting_evidence(audit_text)
        )

        if not evidence_conflict_recognition:
            failures.append(
                "Auditor did not accurately acknowledge conflicting "
                "evidence identified by the Researcher."
            )

    evidence_limitation_recognition = (
        _auditor_acknowledges_evidence_limitations(
            scenario=scenario,
            audit_text=audit_text,
        )
    )

    if not evidence_limitation_recognition:
        failures.append(
            "Auditor did not adequately acknowledge evidence quality "
            "limitations or missing evidence."
        )

    schedule_accuracy = _auditor_acknowledges_validation_failures(
        deterministic_validation=deterministic_validation,
        audit_text=audit_text,
    )

    if not schedule_accuracy:
        failures.append(
            "Auditor did not acknowledge one or more deterministic "
            "schedule validation failures."
        )

    uncertainty_coverage = _auditor_covers_uncertainties(
        scenario=scenario,
        audit_text=audit_text,
        deterministic_validation=deterministic_validation,
    )

    if not uncertainty_coverage:
        failures.append(
            "Auditor did not adequately communicate the relevant "
            "uncertainties or unresolved issues."
        )

    checks = [
        mandatory_activity_accuracy,
        evidence_conflict_recognition,
        evidence_limitation_recognition,
        schedule_accuracy,
        uncertainty_coverage,
    ]

    return AuditorEvaluationResult(
        scenario_id=scenario.scenario_id,
        mandatory_activity_accuracy=mandatory_activity_accuracy,
        evidence_conflict_recognition=evidence_conflict_recognition,
        evidence_limitation_recognition=evidence_limitation_recognition,
        schedule_accuracy=schedule_accuracy,
        uncertainty_coverage=uncertainty_coverage,
        passed=all(checks),
        failures=failures,
    )
