from pathlib import Path

from src.data_sources.document_loader import load_markdown_document
from src.data_sources.document_chunking import load_and_chunk_document
from src.data_sources.embedding_client import embed_documents
from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
    store_documents,
    delete_source_documents,
)

VENUE_GUIDES_PATH = Path("data/documents/venue_guides")


def get_venue_documents(venue_id: str) -> list[Path]:
    """Find successfully ingested documents belonging to a venue."""

    matching_documents = []

    for file_path in VENUE_GUIDES_PATH.glob("*.md"):
        metadata, _ = load_markdown_document(file_path)

        if metadata.get("venue_id") == venue_id:
            matching_documents.append(file_path)

    return matching_documents


def index_venue_documents(venue_id: str) -> int:
    """Chunk, embed, and index documents belonging to a venue."""

    document_paths = get_venue_documents(venue_id)

    if not document_paths:
        return 0

    documents = []

    for file_path in document_paths:
        documents.extend(load_and_chunk_document(file_path))

    if not documents:
        return 0

    embeddings = embed_documents(documents)

    if len(embeddings) != len(documents):
        raise ValueError(
            "Number of embeddings must match number of documents."
        )

    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    # Remove previously indexed chunks for each source.
    for source_id in {doc.metadata["source_id"] for doc in documents}:
        delete_source_documents(collection, source_id)

    # Store the updated chunks.
    store_documents(collection, documents, embeddings)

    return len(documents)
