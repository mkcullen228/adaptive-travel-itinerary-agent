from langchain_text_splitters import NLTKTextSplitter
from langchain_core.documents import Document

from pathlib import Path
from src.data_sources.document_loader import load_markdown_document


def create_experimental_splitter() -> NLTKTextSplitter:
    return NLTKTextSplitter(
        chunk_size=500,
        chunk_overlap=75,
    )


def chunk_document_experimental(content: str, metadata: dict) -> list[Document]:

    splitter = create_experimental_splitter()
    chunks = splitter.split_text(content)

    documents = []

    for index, chunk in enumerate(chunks):
        documents.append(
            Document(
                page_content=chunk,
                metadata={
                    **metadata,
                    "chunk_index": index,
                    "chunking_config": "sentence_aware_v1"
                }
            )
        )

    return documents


def load_and_chunk_document_experimental(file_path: Path) -> list[Document]:

    metadata, content = load_markdown_document(file_path)

    return chunk_document_experimental(content, metadata)


if __name__ == "__main__":
    file_path = Path(
        "data/documents/venue_guides/washington_monument_visitor_info.md"
    )

    chunks = load_and_chunk_document_experimental(file_path)

    for chunk in chunks:
        print(f"\n{'=' * 60}")
        print(f"Chunk ID: {chunk.metadata['chunk_index']}")
        print(chunk.page_content)