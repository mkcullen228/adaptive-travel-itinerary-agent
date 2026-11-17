
import pytest
from pydantic import ValidationError

from src.models.evidence import EvidenceStatus
from src.models.multi_agent import (
    AuditAssessment,
    AuditReport,
    EvidenceBrief,
    EvidenceFinding,
)


def test_supported_finding_requires_supporting_source():
    finding = EvidenceFinding(
        claim="The venue is unavailable.",
        status=EvidenceStatus.SUPPORTED,
        supporting_source_ids=["source_1"],
        explanation="The source confirms the closure.",
    )

    assert finding.supporting_source_ids == ["source_1"]


def test_supported_finding_requires_source_id():
    with pytest.raises(ValidationError):
        EvidenceFinding(
            claim="The venue is unavailable.",
            status=EvidenceStatus.SUPPORTED,
            explanation="The source confirms the closure.",
        )


def test_unsupported_finding_cannot_have_source_ids():
    with pytest.raises(ValidationError):
        EvidenceFinding(
            claim="The venue is unavailable.",
            status=EvidenceStatus.UNSUPPORTED,
            supporting_source_ids=["source_1"],
            explanation="No evidence supports this claim.",
        )


def test_conflicting_finding_requires_both_source_types():
    with pytest.raises(ValidationError):
        EvidenceFinding(
            claim="The venue is open.",
            status=EvidenceStatus.CONFLICTING,
            supporting_source_ids=["source_1"],
            explanation="Sources disagree.",
        )


def test_conflicting_finding_accepts_both_source_types():
    finding = EvidenceFinding(
        claim="The venue is open.",
        status=EvidenceStatus.CONFLICTING,
        supporting_source_ids=["source_1"],
        conflicting_source_ids=["source_2"],
        explanation="Sources disagree.",
    )

    assert finding.status == EvidenceStatus.CONFLICTING


def test_evidence_brief_defaults():
    brief = EvidenceBrief()

    assert brief.findings == []
    assert brief.unresolved_questions == []
    assert brief.source_ids_reviewed == []


def test_audit_report_defaults():
    report = AuditReport(
        assessment=AuditAssessment.INCONCLUSIVE
    )

    assert report.supported_claims == []
    assert report.unsupported_claims == []
    assert report.recommendations == []
