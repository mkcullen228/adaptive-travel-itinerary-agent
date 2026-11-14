from datetime import datetime, timezone

from src.models.evidence import EvidenceStatus
from src.models.source_reference import VerificationStatus
from src.models.retrieved_evidence import RetrievedEvidence
from src.models.evidence import EvidenceAssessment, EvidenceRelevance, EvidenceCoverage
from src.validation.evidence_assessment import (
    assess_claim_evidence, extract_meaningful_terms, assess_evidence_relevance, 
    assess_evidence_coverage, assess_source_quality)


def create_test_evidence(verification_status):
    return RetrievedEvidence(
        chunk_id="test_0",
        content="Visitors need a ticket.",
        subject="Washington Monument",
        source_id="test_source",
        source_url="https://example.com",
        retrieved_at=datetime.now(timezone.utc),
        similarity_distance=0.2,
        reliability=0.95,
        freshness_score=1.0,
        verification_status=verification_status,
    )


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
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    assessment = assess_claim_evidence(
        claim="Timed-entry tickets are required.",
        evidence=evidence,
    )
    print(assessment)

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
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
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
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
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
            reliability=0.85,
            freshness_score=0.65,
            verification_status=VerificationStatus.VERIFIED
        ),
        RetrievedEvidence(
            chunk_id="source_2_chunk_1",
            content="The monument closes at 6 PM.",
            subject="Washington Monument",
            source_id="source_2",
            source_url="https://example.com/visitor-info",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
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
            reliability=0.85,
            freshness_score=0.65,
            verification_status=VerificationStatus.VERIFIED
        ),
        RetrievedEvidence(
            chunk_id="source_2_chunk_1",
            content="The monument closes at 5 PM.",
            subject="Washington Monument",
            source_id="source_2",
            source_url="https://example.com/visitor-info",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
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
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
        ),
        RetrievedEvidence(
            chunk_id="source_2_chunk_1",
            content="The museum closes at 6 PM.",
            subject="National Museum of American History",
            source_id="source_2",
            source_url="https://example.com/museum",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.30,
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
        ),
    ]

    assessment = assess_claim_evidence(
        claim="The monument closes at 5 PM.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert assessment.supporting_source_ids == ["source_1"]


def test_general_accessibility_does_not_support_restroom_claim():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_visitor_info_4",
            content=(
                "The Washington Monument is accessible to "
                "visitors with disabilities. Visitors requiring "
                "additional accommodations are encouraged to "
                "contact the National Park Service in advance."
            ),
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.477,
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    assessment = assess_claim_evidence(
        claim=(
            "The Washington Monument has "
            "wheelchair-accessible restrooms."
        ),
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.UNSUPPORTED
    assert assessment.supporting_source_ids == []


def test_partial_evidence_assessment_dimensions():
    assessment = EvidenceAssessment(
        claim="The venue is open and offers wheelchair-accessible restrooms.",
        status=EvidenceStatus.PARTIALLY_SUPPORTED,
        relevance=EvidenceRelevance.RELEVANT,
        coverage=EvidenceCoverage.PARTIAL,
        source_quality_assessed=False,
        consistency_assessed=False,
        supporting_source_ids=["source_1"],
        explanation="The evidence supports opening hours but not restroom accessibility.",
        verification_status=VerificationStatus.VERIFIED
    )

    assert assessment.relevance == EvidenceRelevance.RELEVANT
    assert assessment.coverage == EvidenceCoverage.PARTIAL
    assert assessment.source_quality_assessed is False
    assert assessment.consistency_assessed is False

def test_extract_meaningful_terms():
    terms = extract_meaningful_terms(
        "The Washington Monument has accessible visitor restrooms."
    )

    assert terms == {
        "washington",
        "monument",
        "accessible",
        "visitor",
        "restrooms",
    }

def test_assess_evidence_relevance_relevant():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required to enter the monument.",
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
            reliability=0.85,
            freshness_score=0.65, 
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    relevance = assess_evidence_relevance(
        claim="Timed-entry tickets are required to enter the monument.",
        evidence=evidence,
    )

    assert relevance == EvidenceRelevance.RELEVANT


def test_assess_evidence_relevance_partiallyrelevant():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required to enter the monument.",
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
            reliability=0.85,
            freshness_score=0.65,
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    relevance = assess_evidence_relevance(
        claim="Timed-entry tickets are required and visitors must arrive 30 minutes early.",
        evidence=evidence,
    )

    assert relevance == EvidenceRelevance.PARTIALLY_RELEVANT


def test_assess_evidence_relevance_irrelevant():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required to enter the monument.",
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.25,
            reliability=0.85,
            freshness_score=0.65,
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    relevance = assess_evidence_relevance(
        claim="Shows start each hour",
        evidence=evidence,
    )

    assert relevance == EvidenceRelevance.IRRELEVANT


def test_relevant_evidence_does_not_necessarily_support_claim():
    evidence = [
        RetrievedEvidence(
            chunk_id="washington_monument_4",
            content=(
                "The Washington Monument is accessible to "
                "visitors with disabilities."
            ),
            subject="Washington Monument",
            source_id="washington_monument_visitor_info",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
            similarity_distance=0.477,
            reliability=0.85,
            freshness_score=0.65,
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    assessment = assess_claim_evidence(
        claim="The Washington Monument has wheelchair-accessible restrooms.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.UNSUPPORTED
    assert assessment.relevance == EvidenceRelevance.RELEVANT
    assert assessment.coverage == EvidenceCoverage.NONE
    assert assessment.supporting_source_ids == []


def test_evidence_coverage_complete():
    coverage = assess_evidence_coverage(
        supported_statements=["Tickets are required."],
        unsupported_statements=[],
    )
    assert coverage == EvidenceCoverage.COMPLETE


def test_evidence_coverage_partial():
    coverage = assess_evidence_coverage(
        supported_statements=["Tickets are required."],
        unsupported_statements=["Visitors must arrive early."],
    )
    assert coverage == EvidenceCoverage.PARTIAL


def test_evidence_coverage_none():
    coverage = assess_evidence_coverage(
        supported_statements=[],
        unsupported_statements=["Tickets are required."],
    )
    assert coverage == EvidenceCoverage.NONE


def test_verified_source_has_no_warnings():
    evidence = [create_test_evidence(VerificationStatus.VERIFIED)]

    assert assess_source_quality(evidence) == []


def test_unverified_source_generates_warning():
    evidence = [create_test_evidence(VerificationStatus.UNVERIFIED)]

    warnings = assess_source_quality(evidence)

    assert len(warnings) == 1
    assert "not been independently verified" in warnings[0]


def test_stale_source_generates_warning():
    evidence = [create_test_evidence(VerificationStatus.STALE)]

    warnings = assess_source_quality(evidence)

    assert len(warnings) == 1
    assert "stale" in warnings[0]


def test_conflicting_source_generates_warning():
    evidence = [create_test_evidence(VerificationStatus.CONFLICTING)]

    warnings = assess_source_quality(evidence)

    assert len(warnings) == 1
    assert "conflicting verification status" in warnings[0]


def test_assess_claim_evidence_with_source_quality_warnings():
    evidence = [create_test_evidence(VerificationStatus.VERIFIED)]

    assessment = assess_claim_evidence(
       claim="Visitors need a ticket.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert assessment.source_quality_assessed is True
    assert assessment.source_quality_warnings == assess_source_quality(evidence)


def test_assess_claim_evidence_recognizes_paraphrase():
    evidence = [
        create_test_evidence(VerificationStatus.UNVERIFIED).model_copy(
            update={
                "content": (
                    "You can't get to the top of the Washington "
                    "Monument without a ticket."
                )
            }
        )
    ]

    assessment = assess_claim_evidence(
        claim="Visitors must have a ticket to reach the top of the Washington Monument.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED


def test_assess_claim_evidence_rejects_unrelated_keyword_overlap():
    evidence = [
        create_test_evidence(VerificationStatus.UNVERIFIED).model_copy(
            update={
                "content": (
                    "Visitors need a ticket to access the Washington Monument."
                )
            }
        )
    ]

    assessment = assess_claim_evidence(
        claim="The Washington Monument closes at 10 PM.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.UNSUPPORTED


def test_ticket_requirement_without_matching_destination_is_unsupported():
    evidence = [
        create_test_evidence(VerificationStatus.UNVERIFIED).model_copy(
            update={
                "content": "Visitors need a ticket to enter the museum."
            }
        )
    ]

    assessment = assess_claim_evidence(
        claim="Visitors must have a ticket to reach the top of the Washington Monument.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.UNSUPPORTED


def test_assess_claim_evidence_includes_unverified_source_warning():
    evidence = [
        create_test_evidence(VerificationStatus.UNVERIFIED)
    ]

    assessment = assess_claim_evidence(
        claim="Visitors need a ticket.",
        evidence=evidence,
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert assessment.source_quality_assessed is True
    assert any(
        "not been independently verified" in warning
        for warning in assessment.source_quality_warnings
    )
