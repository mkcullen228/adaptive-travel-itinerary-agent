import chromadb
from pathlib import Path
from datetime import datetime

from src.data_sources.embedding_client import MODEL_NAME, embed_query


VECTOR_STORE_PATH = Path("data/vector_store")
COLLECTION_NAME = "venue_visitor_information"


def create_vector_store_client() -> chromadb.ClientAPI:
    """Create a persistent local ChromaDB client."""
    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(VECTOR_STORE_PATH)
    )


def get_or_create_collection(client: chromadb.ClientAPI, collection_name: str = COLLECTION_NAME):
    return client.get_or_create_collection(
        name=collection_name,
        metadata={
            "embedding_model": MODEL_NAME,
            "hnsw:space": "cosine"
        }
    )


def store_documents(collection, documents: list, embeddings) -> None:
    """Store document chunks, embeddings, and metadata in ChromaDB."""

    if len(documents) != len(embeddings):
        raise ValueError("Number of documents and embeddings must match.")

    ids = []
    metadatas = []

    for document in documents:
        source_id = document.metadata["source_id"]
        chunk_index = document.metadata["chunk_index"]

        ids.append(f"{source_id}_{chunk_index}")

        metadata = {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in document.metadata.items()
        }
        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=[document.page_content for document in documents],
        metadatas=metadatas
    )


def delete_source_documents(collection, source_id: str) -> None:
    """Delete all indexed chunks belonging to a source document."""

    collection.delete(
        where={"source_id": source_id}
    )


def search_documents(collection, query: str, query_embedding, n_results: int = 3) -> dict:
    """Retrieve the most relevant document chunks for a query."""

    return collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )


if __name__ == "__main__":
    from pathlib import Path
    from src.data_sources.document_chunking import load_and_chunk_document
    from src.data_sources.embedding_client import embed_documents

    document_paths = [
        Path("data/documents/venue_guides/washington_monument_visitor_info.md"),
        Path("data/documents/venue_guides/wwii_memorial_visitor_info.md"),
    ]

    documents = []

    for file_path in document_paths:
        documents.extend(load_and_chunk_document(file_path))

    embeddings = embed_documents(documents)

    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    store_documents(collection, documents, embeddings)

    print("Stored records:", collection.count())

    query = "Do I need to reserve a ticket before visiting the observation deck?"
    query = "Can I visit the Washington Monument when it is raining or during bad weather?"
    query = "When can visitors see the fountains at the World War II Memorial?"
    
    query_embedding = embed_query(query)

    results = search_documents(
        collection=collection,
        query=query,
        query_embedding=query_embedding,
        n_results=3
    )

    for index, document in enumerate(results["documents"][0]):
        print(f"\nResult {index + 1}")
        print("Text:", document[:300])
        print("Metadata:", results["metadatas"][0][index])
        print("Cosine distance:", results["distances"][0][index])
