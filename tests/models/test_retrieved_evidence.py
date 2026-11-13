import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.retrieved_evidence import RetrievedEvidence


def test_valid_retrieved_evidence():
    evidence = RetrievedEvidence(
        chunk_id="washington_monument_1",
        content="Timed-entry tickets are required.",
        subject="Washington Monument",
        source_id="washington_monument",
        source_url="https://www.nps.gov/wamo/index.htm",
        retrieved_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
        similarity_distance=0.25,
        reliability=0.85,
        freshness_score=0.65
    )
    print(evidence)
    assert evidence.chunk_id == "washington_monument_1"
    assert evidence.similarity_distance == 0.25


def test_negative_similarity_distance_is_rejected():
    with pytest.raises(ValidationError):
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required.",
            subject="Washington Monument",
            source_id="washington_monument",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime.now(timezone.utc),
            similarity_distance=-0.1,
            reliability=0.85,
            freshness_score=0.65
        )


def test_missing_source_id_is_rejected():
    with pytest.raises(ValidationError):
        RetrievedEvidence(
            chunk_id="washington_monument_1",
            content="Timed-entry tickets are required.",
            subject="Washington Monument",
            source_url="https://www.nps.gov/wamo/index.htm",
            retrieved_at=datetime.now(timezone.utc),
            similarity_distance=0.25, 
            reliability=0.85,
            freshness_score=0.65
        )


def test_similarity_distance_is_preserved():
    original_distance = 0.3847

    evidence = RetrievedEvidence(
        chunk_id="washington_monument_2",
        content="The observation deck may close during severe weather.",
        subject="Washington Monument",
        source_id="washington_monument",
        source_url="https://www.nps.gov/wamo/index.htm",
        retrieved_at=datetime.now(timezone.utc),
        similarity_distance=original_distance, 
        reliability=0.85,
        freshness_score=0.65
    )

    assert evidence.similarity_distance == original_distance