from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from src.data_sources.document_chunking import load_and_chunk_document

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformer:
    """Load the selected local sentence embedding model."""
    return SentenceTransformer(MODEL_NAME)

def embed_documents(documents: list) -> list:
    """Generate embeddings for a collection of document chunks."""
    model = load_embedding_model()

    texts = [document.page_content for document in documents]

    embeddings = model.encode(texts)

    return embeddings


def embed_query(query: str):
    """Generate an embedding for a search query."""
    model = load_embedding_model()
    return model.encode(query)


if __name__ == "__main__":
    model = load_embedding_model()

    sample_text = (
        "Timed-entry tickets are required for the Washington Monument "
        "observation level."
    )

    embedding = model.encode(sample_text)

    print("Embedding dimensions:", embedding.shape)
    print("First five values:", embedding[:5])

    document_paths = [
    Path("data/documents/venue_guides/washington_monument_visitor_info.md"),
    Path("data/documents/venue_guides/wwii_memorial_visitor_info.md"),
    ]

    documents = []

    for file_path in document_paths:
        documents.extend(load_and_chunk_document(file_path))

    embeddings = embed_documents(documents)

    print("Number of document chunks:", len(documents))
    print("Embedding matrix shape:", embeddings.shape)