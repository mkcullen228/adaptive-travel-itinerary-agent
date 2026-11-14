import chromadb
import pytest
import numpy as np

from src.data_sources.vector_store import store_documents, delete_source_documents
from langchain_core.documents import Document


@pytest.fixture
def test_collection(tmp_path):
    client = chromadb.PersistentClient(
        path=str(tmp_path / "test_vector_store")
    )

    collection = client.get_or_create_collection(
        name="test_venue_indexing",
        metadata={"hnsw:space": "cosine"}
    )

    yield collection

    client.delete_collection("test_venue_indexing")


def test_store_documents_in_chromadb(test_collection):
    documents = [
        Document(
            page_content="Visitors need tickets to enter the Washington Monument.",
            metadata={
                "source_id": "nps_washington_monument",
                "venue_id": "washington_monument",
                "chunk_index": 0,
            },
        ),
        Document(
            page_content="The Washington Monument has timed entry.",
            metadata={
                "source_id": "nps_washington_monument",
                "venue_id": "washington_monument",
                "chunk_index": 1,
            },
        ),
    ]

    embeddings = np.array([
        [0.1, 0.2, 0.3],
        [0.2, 0.3, 0.4],
    ])

    store_documents(test_collection, documents, embeddings)

    assert test_collection.count() == 2

    results = test_collection.get(
        where={"source_id": "nps_washington_monument"},
        include=["documents", "metadatas"],
    )

    assert len(results["ids"]) == 2
    assert results["metadatas"][0]["venue_id"] == "washington_monument"


def test_reindexing_updates_existing_chunks_without_duplicates(test_collection):
    documents = [
        Document(
            page_content="Original Washington Monument visitor information.",
            metadata={
                "source_id": "nps_washington_monument",
                "venue_id": "washington_monument",
                "chunk_index": 0,
            },
        )
    ]

    original_embeddings = np.array([[0.1, 0.2, 0.3]])

    store_documents(test_collection, documents, original_embeddings)

    updated_documents = [
        Document(
            page_content="Updated Washington Monument visitor information.",
            metadata={
                "source_id": "nps_washington_monument",
                "venue_id": "washington_monument",
                "chunk_index": 0,
            },
        )
    ]

    updated_embeddings = np.array([[0.4, 0.5, 0.6]])

    store_documents(test_collection, updated_documents, updated_embeddings)

    assert test_collection.count() == 1

    results = test_collection.get(
        ids=["nps_washington_monument_0"],
        include=["documents", "embeddings"],
    )

    assert results["documents"][0] == (
        "Updated Washington Monument visitor information."
    )
    assert np.allclose(
        results["embeddings"][0],
        updated_embeddings[0],
    )


def test_reindexing_removes_obsolete_chunks(test_collection):
    source_id = "nps_washington_monument"

    original_documents = [
        Document(
            page_content=f"Original chunk {i}",
            metadata={
                "source_id": source_id,
                "venue_id": "washington_monument",
                "chunk_index": i,
            },
        )
        for i in range(3)
    ]

    original_embeddings = np.array([
        [0.1, 0.2, 0.3],
        [0.2, 0.3, 0.4],
        [0.3, 0.4, 0.5],
    ])

    store_documents(
        test_collection,
        original_documents,
        original_embeddings,
    )

    assert test_collection.count() == 3

    # Simulate re-indexing after the source document shrinks.
    delete_source_documents(test_collection, source_id)

    updated_documents = [
        Document(
            page_content=f"Updated chunk {i}",
            metadata={
                "source_id": source_id,
                "venue_id": "washington_monument",
                "chunk_index": i,
            },
        )
        for i in range(2)
    ]

    updated_embeddings = np.array([
        [0.4, 0.5, 0.6],
        [0.5, 0.6, 0.7],
    ])

    store_documents(
        test_collection,
        updated_documents,
        updated_embeddings,
    )

    assert test_collection.count() == 2

    results = test_collection.get(
        ids=[
            "nps_washington_monument_0",
            "nps_washington_monument_1",
            "nps_washington_monument_2",
        ],
        include=["documents"],
    )

    assert set(results["ids"]) == {
        "nps_washington_monument_0",
        "nps_washington_monument_1",
    }


def test_deleting_source_preserves_other_venues(test_collection):
    documents = [
        Document(
            page_content="Washington Monument visitor information.",
            metadata={
                "source_id": "nps_washington_monument",
                "venue_id": "washington_monument",
                "chunk_index": 0,
            },
        ),
        Document(
            page_content="World War II Memorial visitor information.",
            metadata={
                "source_id": "nps_wwii_memorial",
                "venue_id": "wwii_memorial",
                "chunk_index": 0,
            },
        ),
    ]

    embeddings = np.array([
        [0.1, 0.2, 0.3],
        [0.2, 0.3, 0.4],
    ])

    store_documents(test_collection, documents, embeddings)

    assert test_collection.count() == 2

    delete_source_documents(
        test_collection,
        "nps_washington_monument"
    )

    assert test_collection.count() == 1

    results = test_collection.get(include=["metadatas"])

    assert results["metadatas"][0]["source_id"] == "nps_wwii_memorial"
    assert results["metadatas"][0]["venue_id"] == "wwii_memorial"
