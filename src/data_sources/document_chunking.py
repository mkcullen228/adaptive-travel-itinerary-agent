from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.data_sources.document_loader import load_markdown_document


def create_text_splitter() -> RecursiveCharacterTextSplitter:
    """Create a recursive text splitter with configured chunk settings."""

    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=75,
        separators=["\n\n", "\n", ". ", " ", ""]
    )


def chunk_document(content: str, metadata: dict) -> list[Document]:
    """Split document content into chunks and preserve source metadata."""

    splitter = create_text_splitter()

    chunks = splitter.split_text(content)

    documents = []

    for index, chunk in enumerate(chunks):
        document = Document(
            page_content=chunk,
            metadata={
                **metadata,
                "chunk_index": index, 
                "chunking_config": "recursive_v1"
            }
        )

        documents.append(document)

    return documents


def load_and_chunk_document(file_path: Path) -> list[Document]:
    """Load a Markdown document and split it into metadata-preserving chunks."""
    metadata, content = load_markdown_document(file_path)
    return chunk_document(content, metadata)