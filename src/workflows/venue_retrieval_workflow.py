from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
    search_documents,
)
from src.data_sources.embedding_client import embed_query
from src.data_sources.retrieval_adapter import (
    convert_search_results_to_evidence,
)


def retrieve_venue_evidence(
    venue_id: str,
    query: str,
    n_results: int = 3,
):
    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    query_embedding = embed_query(query)

    results = search_documents(
        collection=collection,
        query=query,
        query_embedding=query_embedding,
        n_results=n_results,
        venue_id=venue_id,
    )

    return convert_search_results_to_evidence(results)