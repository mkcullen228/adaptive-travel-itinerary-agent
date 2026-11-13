import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.data_sources.retrieval_adapter import (convert_search_results_to_evidence)


def create_mock_results():
    return {
        "ids": [["washington_monument_1"]],
        "documents": [["Timed-entry tickets are required."]],
        "metadatas": [[{
            "source_id": "washington_monument_visitor_info",
            "subject": "Washington Monument",
            "url": "https://www.nps.gov/wamo/index.htm",
            "retrieved_at": "2026-11-11T20:18:05.637606+00:00",
            "reliability": 0.85,
            "freshness_score": 0.65,
        }]],
        "distances": [[0.3847]],
        
    }


def test_converts_search_results_to_evidence():
    results = create_mock_results()

    evidence = convert_search_results_to_evidence(results)

    assert len(evidence) == 1
    assert evidence[0].chunk_id == "washington_monument_1"
    assert evidence[0].content == "Timed-entry tickets are required."
    assert evidence[0].source_id == "washington_monument_visitor_info"
    assert evidence[0].subject == "Washington Monument"


def test_converts_retrieved_at_to_datetime():
    results = create_mock_results()

    evidence = convert_search_results_to_evidence(results)

    assert evidence[0].retrieved_at == datetime(
        2026, 11, 11, 20, 18, 5, 637606, tzinfo=timezone.utc
    )


def test_preserves_similarity_distance():
    results = create_mock_results()

    evidence = convert_search_results_to_evidence(results)

    assert evidence[0].similarity_distance == 0.3847


def test_converts_multiple_results():
    results = create_mock_results()
    results["ids"][0].append("washington_monument_2")
    results["documents"][0].append("The monument is generally open daily.")
    results["metadatas"][0].append(results["metadatas"][0][0])
    results["distances"][0].append(0.52)

    evidence = convert_search_results_to_evidence(results)

    assert len(evidence) == 2
    assert evidence[1].chunk_id == "washington_monument_2"


def test_rejects_mismatched_result_lengths():
    results = create_mock_results()
    results["distances"][0].append(0.52)

    with pytest.raises(ValueError, match="mismatched list lengths"):
        convert_search_results_to_evidence(results)


def test_preserves_reliability_and_calculates_freshness(monkeypatch):
    results = create_mock_results()

    expected_retrieved_at = datetime(
        2026, 11, 11, 20, 18, 5, 637606, tzinfo=timezone.utc
    )

    def mock_freshness_score(retrieved_at):
        assert retrieved_at == expected_retrieved_at
        return 0.75

    monkeypatch.setattr(
        "src.data_sources.retrieval_adapter.calculate_freshness_score",
        mock_freshness_score,
    )

    evidence = convert_search_results_to_evidence(results)

    assert evidence[0].reliability == 0.85
    assert evidence[0].freshness_score == 0.75
