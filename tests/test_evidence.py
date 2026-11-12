import pytest
from src.models.evidence import EvidenceAssessment, EvidenceStatus


def test_supported_evidence():
    assessment = EvidenceAssessment(
        claim="Timed-entry tickets are required.",
        status=EvidenceStatus.SUPPORTED,
        supporting_source_ids=["washington_monument"],
        explanation="The official visitor guide confirms timed-entry tickets are required."
    )

    assert assessment.status == EvidenceStatus.SUPPORTED
    assert len(assessment.supporting_source_ids) == 1


def test_partially_supported_evidence():
    assessment = EvidenceAssessment(
        claim="The monument is accessible and has accessible restrooms.",
        status=EvidenceStatus.PARTIALLY_SUPPORTED,
        supporting_source_ids=["washington_monument"],
        explanation="Accessibility accommodations are documented, but restroom accessibility is not confirmed."
    )

    assert assessment.status == EvidenceStatus.PARTIALLY_SUPPORTED


def test_unsupported_evidence():
    assessment = EvidenceAssessment(
        claim="Wheelchair-accessible restrooms are available.",
        status=EvidenceStatus.UNSUPPORTED,
        explanation="The retrieved information does not address restroom accessibility."
    )

    assert assessment.status == EvidenceStatus.UNSUPPORTED
    assert assessment.supporting_source_ids == []


def test_conflicting_evidence():
    assessment = EvidenceAssessment(
        claim="The monument is open today.",
        status=EvidenceStatus.CONFLICTING,
        supporting_source_ids=["official_venue_source"],
        conflicting_source_ids=["third_party_source"],
        explanation="The sources provide contradictory operating information."
    )

    assert assessment.status == EvidenceStatus.CONFLICTING
    assert len(assessment.supporting_source_ids) == 1
    assert len(assessment.conflicting_source_ids) == 1


def test_unsupported_evidence_rejects_supporting_sources():
    with pytest.raises(
        ValueError,
        match="Unsupported evidence cannot have supporting source IDs."
        ):
        EvidenceAssessment(
            claim="Wheelchair-accessible restrooms are available.",
            status=EvidenceStatus.UNSUPPORTED,
            supporting_source_ids=["washington_monument"],
            explanation="The retrieved information does not address restroom accessibility."
        )


def test_supported_evidence_requires_supporting_sources():
    with pytest.raises(
        ValueError,
        match="Supported evidence must have at least one supporting source ID."
    ):
        EvidenceAssessment(
            claim="Timed-entry tickets are required.",
            status=EvidenceStatus.SUPPORTED,
            supporting_source_ids=[],
            explanation="The claim has no identified supporting source."
        )


def test_partially_supported_evidence_allows_supporting_sources():
    assessment = EvidenceAssessment(
        claim="The monument is accessible and has accessible restrooms.",
        status=EvidenceStatus.PARTIALLY_SUPPORTED,
        supporting_source_ids=["washington_monument"],
        explanation="Accessibility accommodations are documented, but restroom accessibility is not confirmed."
    )

    assert assessment.status == EvidenceStatus.PARTIALLY_SUPPORTED
    assert assessment.supporting_source_ids == ["washington_monument"]


def test_conflicting_evidence_allows_multiple_sources():
    assessment = EvidenceAssessment(
        claim="The monument is open today.",
        status=EvidenceStatus.CONFLICTING,
        supporting_source_ids=[
            "official_venue_source",
            "another_official_source",
        ],
        conflicting_source_ids=[
            "third_party_source",
            "another_third_party_source",
        ],
        explanation="The sources provide contradictory operating information."
    )

    assert assessment.status == EvidenceStatus.CONFLICTING
    assert len(assessment.supporting_source_ids) == 2
