from pathlib import Path
from langchain_core.documents import Document
from src.data_sources.document_chunking import (chunk_document, load_and_chunk_document)


def test_chunk_document_returns_multiple_chunks():
    content = "Visitor information. " * 100

    chunks = chunk_document(content, metadata={"source_id": "test_source"})

    assert len(chunks) > 1


def test_chunks_do_not_exceed_maximum_size():
    content = "Visitor information. " * 100

    chunks = chunk_document(content, metadata={"source_id": "test_source"})
    assert all(len(chunk) <= 500 for chunk in chunks)



def test_chunk_document_returns_list_of_documents():
    content = "Visitor information. " * 100

    chunks = chunk_document(
        content,
        metadata={"source_id": "test_source"}
    )

    assert isinstance(chunks, list)
    assert all(isinstance(chunk, Document) for chunk in chunks)


def test_chunks_do_not_exceed_maximum_size():
    content = "Visitor information. " * 100

    chunks = chunk_document(
        content,
        metadata={"source_id": "test_source"}
    )

    assert all(len(chunk.page_content) <= 500 for chunk in chunks)


def test_chunk_document_preserves_metadata():
    content = "Visitor information. " * 100

    metadata = {
        "source_id": "lincoln_memorial_visitor_info",
        "attraction_id": "lincoln_memorial",
        "url": "https://www.nps.gov/linc/planyourvisit/index.htm"
    }

    chunks = chunk_document(content, metadata)

    for index, chunk in enumerate(chunks):
        assert chunk.metadata["source_id"] == metadata["source_id"]
        assert chunk.metadata["attraction_id"] == metadata["attraction_id"]
        assert chunk.metadata["url"] == metadata["url"]
        assert chunk.metadata["chunk_index"] == index



def test_load_and_chunk_washington_monument():
    file_path = Path(
        "data/documents/venue_guides/washington_monument_visitor_info.md"
    )

    chunks = load_and_chunk_document(file_path)

    assert len(chunks) > 0
    assert all(chunk.metadata["source_id"] == "washington_monument_visitor_info"
               for chunk in chunks)
    assert all(chunk.metadata["url"].startswith("https://www.nps.gov/wamo/")
               for chunk in chunks)


def test_load_and_chunk_wwii_memorial():
    file_path = Path(
        "data/documents/venue_guides/wwii_memorial_visitor_info.md"
    )

    chunks = load_and_chunk_document(file_path)

    assert len(chunks) > 0
    assert all(chunk.metadata["source_id"] == "wwii_memorial_visitor_info"
               for chunk in chunks)
    assert all(chunk.metadata["url"].startswith("https://www.nps.gov/wwii/")
               for chunk in chunks)