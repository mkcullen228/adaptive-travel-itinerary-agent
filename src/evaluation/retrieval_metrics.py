def calculate_precision_at_k(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: list[str],
    k: int = 3,
) -> float:
    """Calculate the proportion of the top-k retrieved chunks that are relevant."""
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    retrieved = retrieved_chunk_ids[:k]

    if not retrieved:
        return 0.0

    relevant = set(relevant_chunk_ids)
    relevant_retrieved = sum(
        chunk_id in relevant for chunk_id in retrieved
    )

    return relevant_retrieved / len(retrieved)


def calculate_recall_at_k(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: list[str],
    k: int = 3,
) -> float:
    """Calculate the proportion of known relevant chunks found in the top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    relevant = set(relevant_chunk_ids)

    if not relevant:
        raise ValueError("At least one relevant chunk is required.")

    retrieved = set(retrieved_chunk_ids[:k])

    return len(retrieved.intersection(relevant)) / len(relevant)


def calculate_mrr(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: list[str],
) -> float:
    """Calculate the reciprocal rank of the first relevant retrieved chunk."""
    relevant = set(relevant_chunk_ids)

    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in relevant:
            return 1 / rank

    return 0.0