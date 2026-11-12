from datetime import datetime, timezone

from src.models.evidence import EvidenceStatus
from src.models.retrieved_evidence import RetrievedEvidence
from src.validation.evidence_assessment import assess_claim_evidence


def test_directly_supported_claim():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required to enter the monument.",
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
        )
    ]

    assessment = assess_claim_evidence(
        claim="Timed-entry tickets are required.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert "washington_monument_visitor_info" in assessment.supporting_source_ids


def test_unrelated_evidence_does_not_support_claim():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="The monument grounds are open daily.",
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
        )
    ]

    assessment = assess_claim_evidence(
        claim="Timed-entry tickets are required.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.UNSUPPORTED
    assert assessment.supporting_source_ids == []


def test_partially_supported_claim():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required to enter the monument.",
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
        )
    ]

    assessment = assess_claim_evidence(
        claim="Timed-entry tickets are required and visitors must arrive 30 minutes early.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.PARTIALLY_SUPPORTED


def test_conflicting_evidence():
    evidence = [
        RetrievedEvidence(
            chunk_id="source_1_chunk_1",
            content="The monument closes at 5 PM.",
            subject="Washington Monument",
            source_id="source_1",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
        ),
        RetrievedEvidence(
            chunk_id="source_2_chunk_1",
            content="The monument closes at 6 PM.",
            subject="Washington Monument",
            source_id="source_2",
            source_url="https://example.com/visitor-info",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
        ),
    ]

    assessment = assess_claim_evidence(
        claim="The monument closes at 5 PM.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.CONFLICTING
    assert assessment.supporting_source_ids == ["source_1"]
    assert assessment.conflicting_source_ids == ["source_2"]
    assert "source_2 reports 6PM" in assessment.explanation
    assert "claim states 5PM" in assessment.explanation


def test_agreeing_evidence():
    evidence = [
        RetrievedEvidence(
            chunk_id="source_1_chunk_1",
            content="The monument closes at 5 PM.",
            subject="Washington Monument",
            source_id="source_1",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
        ),
        RetrievedEvidence(
            chunk_id="source_2_chunk_1",
            content="The monument closes at 5 PM.",
            subject="Washington Monument",
            source_id="source_2",
            source_url="https://example.com/visitor-info",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
        ),
    ]

    assessment = assess_claim_evidence(
        claim="The monument closes at 5 PM.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert set(assessment.supporting_source_ids) == {"source_1", "source_2"}


def test_different_venue_does_not_create_conflict():
    evidence = [
        RetrievedEvidence(
            chunk_id="source_1_chunk_1",
            content="The monument closes at 5 PM.",
            subject="Washington Monument",
            source_id="source_1",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
        ),
        RetrievedEvidence(
            chunk_id="source_2_chunk_1",
            content="The museum closes at 6 PM.",
            subject="ational Museum of American History",
            source_id="source_2",
            source_url="https://example.com/museum",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
        ),
    ]

    assessment = assess_claim_evidence(
        claim="The monument closes at 5 PM.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert assessment.supporting_source_ids == ["source_1"]
