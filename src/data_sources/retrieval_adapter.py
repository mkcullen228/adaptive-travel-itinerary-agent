from datetime import datetime

from src.models.retrieved_evidence import RetrievedEvidence
from src.validation.data_quality import calculate_freshness_score

def convert_search_results_to_evidence(
    results: dict,
) -> list[RetrievedEvidence]:
    evidence_items = []

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    result_lengths = {
        len(ids),
        len(documents),
        len(metadatas),
        len(distances),
    }

    if len(result_lengths) != 1:
        raise ValueError(
            "ChromaDB search results contain mismatched list lengths."
        )


    for chunk_id, content, metadata, distance in zip(
        ids, documents, metadatas, distances
    ):
        retrieved_at = datetime.fromisoformat(metadata["retrieved_at"])
        freshness_score = calculate_freshness_score(retrieved_at)

        evidence = RetrievedEvidence(
            chunk_id=chunk_id,
            content=content,
            source_id=metadata["source_id"],
            source_url=metadata["url"],
            subject=metadata["subject"],
            retrieved_at=retrieved_at,
            similarity_distance=distance,
            reliability=metadata["reliability"],
            freshness_score=freshness_score,
        )

        evidence_items.append(evidence)

    return evidence_items
