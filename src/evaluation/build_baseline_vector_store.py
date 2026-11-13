from pathlib import Path

from src.data_sources.document_chunking import load_and_chunk_document
from src.data_sources.embedding_client import embed_documents
from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
    store_documents,
)

DOCUMENT_DIRECTORY = Path("data/documents/venue_guides")
BASELINE_COLLECTION = "venue_visitor_information"


def main():
    client = create_vector_store_client()

    collection = get_or_create_collection(
        client,
        collection_name=BASELINE_COLLECTION,
    )

    documents = []

    for file_path in DOCUMENT_DIRECTORY.glob("*.md"):
        chunks = load_and_chunk_document(file_path)
        documents.extend(chunks)

    embeddings = embed_documents(documents)

    store_documents(collection, documents, embeddings)

    print(f"Baseline collection: {BASELINE_COLLECTION}")
    print(f"Documents stored: {len(documents)}")
    print(f"Collection count: {collection.count()}")


if __name__ == "__main__":
    main()
