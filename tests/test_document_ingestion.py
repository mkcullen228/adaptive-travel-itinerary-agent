import requests
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.data_sources.document_ingestion import (
    extract_webpage_content, load_source_registry, 
    ingest_registered_sources, validate_extracted_content)
from src.models.document import IngestionStatus, DocumentIngestionResult


@patch("src.data_sources.document_ingestion.trafilatura.extract")
@patch("src.data_sources.document_ingestion.requests.get")
def test_successful_document_ingestion(mock_get, mock_extract):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html>Visitor information</html>"

    mock_get.return_value = mock_response
    mock_extract.return_value = (
        "Visitor information for the museum. "
        "Opening hours, admission, accessibility, and directions are available. "
        "Visitors can review entrance locations and parking information "
        "before planning their visit. "
    ) * 3

    result = extract_webpage_content(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit"
    )

    assert result.retrieval_status == IngestionStatus.SUCCESS
    assert result.extraction_status == IngestionStatus.SUCCESS
    assert result.http_status_code == 200


@patch("src.data_sources.document_ingestion.requests.get")
def test_http_403_failure(mock_get):
    mock_response = Mock()
    mock_response.status_code = 403

    http_error = requests.exceptions.HTTPError(
        response=mock_response
    )
    mock_response.raise_for_status.side_effect = http_error
    mock_get.return_value = mock_response

    result = extract_webpage_content(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit"
    )

    assert result.retrieval_status == IngestionStatus.FAILED
    assert result.http_status_code == 403
    assert result.extraction_status is None
    assert result.content is None
    assert result.error_message == "HTTP error 403"


@patch("src.data_sources.document_ingestion.requests.get")
def test_network_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout(
        "Request timed out"
    )

    result = extract_webpage_content(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit"
    )

    assert result.retrieval_status == IngestionStatus.FAILED
    assert result.http_status_code is None
    assert result.extraction_status is None
    assert result.content is None
    assert "Network error" in result.error_message


@patch("src.data_sources.document_ingestion.trafilatura.extract")
@patch("src.data_sources.document_ingestion.requests.get")
def test_extraction_failure(mock_get, mock_extract):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html></html>"

    mock_get.return_value = mock_response
    mock_extract.return_value = None

    result = extract_webpage_content(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit"
    )

    assert result.retrieval_status == IngestionStatus.SUCCESS
    assert result.http_status_code == 200
    assert result.extraction_status == IngestionStatus.FAILED
    assert result.content is None
    assert result.error_message=="Extracted content did not meet minimum quality requirements."


def test_load_source_registry():
    sources = load_source_registry()

    assert isinstance(sources, list)
    assert len(sources) > 0
    assert sources[0]["source_id"] == "natural_history_visitor_info"


@patch("src.data_sources.document_ingestion.save_ingestion_results")
@patch("src.data_sources.document_ingestion.save_document")
@patch("src.data_sources.document_ingestion.extract_webpage_content")
@patch("src.data_sources.document_ingestion.load_source_registry")
def test_ingest_registered_sources(
    mock_registry,
    mock_extract,
    mock_save,
    mock_save_results
):
    mock_registry.return_value = [
        {
            "source_id": "source_one",
            "url": "https://example.com/one"
        },
        {
            "source_id": "source_two",
            "url": "https://example.com/two"
        }
    ]

    mock_extract.side_effect = [
        Mock(source_id="source_one"),
        Mock(source_id="source_two")
    ]

    results = ingest_registered_sources()

    assert len(results) == 2
    assert mock_extract.call_count == 2
    assert mock_save.call_count == 2

    mock_save_results.assert_called_once_with(results)


def test_save_document_overwrites_existing_file(tmp_path, monkeypatch):
    import src.data_sources.document_ingestion as ingestion

    monkeypatch.setattr(
        ingestion.Path,
        "resolve",
        lambda self: tmp_path / "src" / "data_sources" / "document_ingestion.py"
    )

    result = DocumentIngestionResult(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit",
        retrieval_status=IngestionStatus.SUCCESS,
        http_status_code=200,
        extraction_status=IngestionStatus.SUCCESS,
        retrieved_at=datetime.now(timezone.utc),
        content="Updated visitor information"
    )

    document_path = (
        tmp_path / "data" / "documents" / "venue_guides"
        / "natural_history_visitor_info.md"
    )
    document_path.parent.mkdir(parents=True)
    document_path.write_text("Old visitor information", encoding="utf-8")

    ingestion.save_document(result)

    saved_content = document_path.read_text(encoding="utf-8")

    assert "Updated visitor information" in saved_content
    assert "Old visitor information" not in saved_content


def test_save_document_preserves_file_after_failure(tmp_path, monkeypatch):
    import src.data_sources.document_ingestion as ingestion

    monkeypatch.setattr(
        ingestion.Path,
        "resolve",
        lambda self: tmp_path / "src" / "data_sources" / "document_ingestion.py"
    )

    document_path = (
        tmp_path / "data" / "documents" / "venue_guides"
        / "natural_history_visitor_info.md"
    )
    document_path.parent.mkdir(parents=True)
    document_path.write_text("Previously saved information", encoding="utf-8")

    result = DocumentIngestionResult(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit",
        retrieval_status=IngestionStatus.FAILED,
        http_status_code=403,
        retrieved_at=datetime.now(timezone.utc),
        error_message="HTTP error 403"
    )

    ingestion.save_document(result)

    saved_content = document_path.read_text(encoding="utf-8")

    assert saved_content == "Previously saved information"


def test_save_ingestion_results(tmp_path, monkeypatch):
    import json
    import src.data_sources.document_ingestion as ingestion

    monkeypatch.setattr(
        ingestion.Path,
        "resolve",
        lambda self: tmp_path / "src" / "data_sources" / "document_ingestion.py"
    )

    results = [
        DocumentIngestionResult(
            source_id="natural_history_visitor_info",
            url="https://example.com/visit",
            retrieval_status=IngestionStatus.SUCCESS,
            http_status_code=200,
            extraction_status=IngestionStatus.SUCCESS,
            retrieved_at=datetime.now(timezone.utc),
            content="Updated visitor information"
        ),
        DocumentIngestionResult(
            source_id="american_history_visitor_info",
            url="https://example.com/history",
            retrieval_status=IngestionStatus.FAILED,
            http_status_code=403,
            retrieved_at=datetime.now(timezone.utc),
            error_message="HTTP error 403"
        )
    ]

    ingestion.save_ingestion_results(results)

    document_path = (
        tmp_path / "data" / "documents" / "ingestion_results.json"
    )

    saved_content = json.loads(
        document_path.read_text(encoding="utf-8")
    )

    assert len(saved_content) == 2
    assert saved_content[0]["retrieval_status"] == "success"
    assert saved_content[1]["retrieval_status"] == "failed"
    assert saved_content[1]["http_status_code"] == 403
    assert saved_content[1]["extraction_status"] is None


def test_content_validation_accepts_relevant_content():
    content = (
        "Visitor information for the museum. "
        "Opening hours and accessibility details are available. "
        "Visitors can review directions, parking information, "
        "entrance locations, admission requirements, and other "
        "important details before planning their visit. "
    ) * 3

    assert validate_extracted_content(content) is True


def test_content_validation_rejects_short_content():
    content = "Museum visitor hours"

    assert validate_extracted_content(content) is False


def test_content_validation_rejects_irrelevant_content():
    content = " ".join(["General information about our organization."] * 30)

    assert validate_extracted_content(content) is False