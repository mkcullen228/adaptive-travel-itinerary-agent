import numpy as np
from unittest.mock import MagicMock
from src.data_sources.vector_store import delete_source_documents, search_documents


def test_delete_source_documents_filters_by_source_id():
    mock_collection = MagicMock()

    delete_source_documents(
        collection=mock_collection,
        source_id="nps_washington_monument"
    )

    mock_collection.delete.assert_called_once_with(
        where={"source_id": "nps_washington_monument"}
    )


def test_search_documents_filters_by_venue():
    collection = MagicMock()
    query_embedding = np.array([0.1, 0.2, 0.3])

    search_documents(
        collection=collection,
        query="Washington Monument tickets",
        query_embedding=query_embedding,
        n_results=3,
        venue_id="washington_monument",
    )

    collection.query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2, 0.3]],
        n_results=3,
        include=["documents", "metadatas", "distances"],
        where={"venue_id": "washington_monument"},
    )
