import pytest

from src.evaluation.retrieval_metrics import (
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr,
)


def test_precision_at_k():
    retrieved = ["chunk_1", "chunk_2", "chunk_3"]
    relevant = ["chunk_2", "chunk_3"]

    assert calculate_precision_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)


def test_recall_at_k():
    retrieved = ["chunk_1", "chunk_2", "chunk_3"]
    relevant = ["chunk_2", "chunk_3"]

    assert calculate_recall_at_k(retrieved, relevant, k=3) == 1.0


def test_mrr():
    retrieved = ["chunk_1", "chunk_2", "chunk_3"]
    relevant = ["chunk_2", "chunk_3"]

    assert calculate_mrr(retrieved, relevant) == 0.5


def test_mrr_returns_zero_when_no_relevant_chunk_is_retrieved():
    retrieved = ["chunk_1", "chunk_4", "chunk_5"]
    relevant = ["chunk_2"]

    assert calculate_mrr(retrieved, relevant) == 0.0


def test_recall_requires_relevant_chunks():
    with pytest.raises(ValueError):
        calculate_recall_at_k(["chunk_1"], [], k=3)


def test_precision_requires_positive_k():
    with pytest.raises(ValueError):
        calculate_precision_at_k(["chunk_1"], ["chunk_1"], k=0)