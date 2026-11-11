import pytest
from pathlib import Path
from src.data_sources.document_loader import load_markdown_document


def test_load_washington_monument_document():
    file_path = Path(
        "data/documents/venue_guides/washington_monument_visitor_info.md"
    )

    metadata, content = load_markdown_document(file_path)

    assert metadata["source_id"] == "washington_monument_visitor_info"
    assert metadata["url"].startswith("https://www.nps.gov/wamo/")
    assert metadata["retrieved_at"].tzinfo is not None
    assert "Washington Monument" in content


def test_load_wwii_memorial_document():
    file_path = Path(
        "data/documents/venue_guides/wwii_memorial_visitor_info.md"
    )

    metadata, content = load_markdown_document(file_path)

    assert metadata["source_id"] == "wwii_memorial_visitor_info"
    assert metadata["url"].startswith("https://www.nps.gov/wwii/")
    assert metadata["retrieved_at"].tzinfo is not None
    assert "World War II Memorial" in content
    assert "24 hours" in content


def test_loader_returns_metadata_and_content_separately():
    file_path = Path(
        "data/documents/venue_guides/washington_monument_visitor_info.md"
    )

    metadata, content = load_markdown_document(file_path)

    assert isinstance(metadata, dict)
    assert isinstance(content, str)
    assert content.strip() != ""
    assert "# Source:" not in content
    assert "Retrieved at:" not in content


def test_loader_raises_error_for_missing_file():
    file_path = Path("data/documents/venue_guides/missing_document.md")

    with pytest.raises(FileNotFoundError):
        load_markdown_document(file_path)