import pytest
from pathlib import Path
from src.data_sources.document_loader import load_markdown_document, extract_required_metadata


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


def test_valid_metadata_is_extracted():
    header = """
        # Source: Washington Monument
        Subject: Washington Monument
        URL: https://www.nps.gov/wamo/index.htm
        Retrieved at: 2026-11-10T23:11:48+00:00
        Reliability: 0.85
    """

    metadata = extract_required_metadata(header)

    assert metadata["source_id"] == "Washington Monument"
    assert metadata["url"] == "https://www.nps.gov/wamo/index.htm"
    assert metadata["retrieved_at"].isoformat() == ("2026-11-10T23:11:48+00:00")
    assert metadata["subject"] == "Washington Monument"
    assert metadata["reliability"] == 0.85


def test_missing_url_raises_value_error():
    header = """
    # Source: Washington Monument
    Subject: Washington Monument
    Retrieved at: 2026-11-10T23:11:48+00:00
    Reliability: 1
    """

    with pytest.raises(
        ValueError,
        match="Missing required document metadata: url"
    ):
        extract_required_metadata(header)


def test_invalid_retrieved_at_raises_value_error():
    header = """
        # Source: Washington Monument
        Subject: Washington Monument
        URL: https://www.nps.gov/wamo/index.htm
        Retrieved at: not-a-valid-date
        Reliability: 0.85
    """

    with pytest.raises(
        ValueError,
        match="Invalid retrieved_at metadata"
    ):
        extract_required_metadata(header)

def test_invalid_subject_raises_value_error():
    header = """
    # Source: Washington Monument
    URL: https://www.nps.gov/wamo/index.htm
    Retrieved at: not-a-valid-date
    Reliability: 0.85
    """

    with pytest.raises(
        ValueError,
        match="Missing required document metadata: subject"):
        extract_required_metadata(header)