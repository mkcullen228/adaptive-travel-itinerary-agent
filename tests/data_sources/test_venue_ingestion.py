from datetime import datetime, timezone
from unittest.mock import patch

from src.data_sources.venue_ingestion import ingest_venue_sources
from src.models.document import DocumentIngestionResult, IngestionStatus
from src.models.source_reference import SourceReference, VerificationStatus


@patch("src.data_sources.venue_ingestion.save_ingestion_results")
@patch("src.data_sources.venue_ingestion.save_document")
@patch("src.data_sources.venue_ingestion.extract_webpage_content")
@patch("src.data_sources.venue_ingestion.get_sources_by_venue")
def test_ingest_venue_sources_success(
    mock_get_sources,
    mock_extract,
    mock_save_document,
    mock_save_results
):
    mock_get_sources.return_value = [
        SourceReference(
            source_id="nps_washington_monument",
            source_name="National Park Service",
            source_type="official_website",
            url="https://www.nps.gov/wamo/index.htm",
            reliability=0.95,
            verification_status=VerificationStatus.VERIFIED
        )
    ]

    mock_extract.return_value = DocumentIngestionResult(
        source_id="nps_washington_monument",
        url="https://www.nps.gov/wamo/index.htm",
        retrieval_status=IngestionStatus.SUCCESS,
        http_status_code=200,
        extraction_status=IngestionStatus.SUCCESS,
        retrieved_at=datetime.now(timezone.utc),
        content="Washington Monument visitor information."
    )

    results = ingest_venue_sources("washington_monument")

    assert len(results) == 1
    assert results[0].venue_id == "washington_monument"
    assert results[0].reliability == 0.95
    assert results[0].verification_status == VerificationStatus.VERIFIED
    assert results[0].retrieval_status == IngestionStatus.SUCCESS

    mock_extract.assert_called_once()
    mock_save_document.assert_called_once()
    mock_save_results.assert_called_once()


@patch("src.data_sources.venue_ingestion.save_ingestion_results")
@patch("src.data_sources.venue_ingestion.save_document")
@patch("src.data_sources.venue_ingestion.extract_webpage_content")
@patch("src.data_sources.venue_ingestion.get_sources_by_venue")
def test_ingest_venue_sources_failure(
    mock_get_sources,
    mock_extract,
    mock_save_document,
    mock_save_results
):
    mock_get_sources.return_value = [
        SourceReference(
            source_id="nps_washington_monument",
            source_name="National Park Service",
            source_type="official_website",
            url="https://www.nps.gov/wamo/index.htm",
            reliability=0.95,
            verification_status=VerificationStatus.UNVERIFIED
        )
    ]

    mock_extract.return_value = DocumentIngestionResult(
        source_id="nps_washington_monument",
        url="https://www.nps.gov/wamo/index.htm",
        retrieval_status=IngestionStatus.FAILED,
        http_status_code=403,
        retrieved_at=datetime.now(timezone.utc),
        error_message="HTTP error 403"
    )

    results = ingest_venue_sources("washington_monument")

    assert len(results) == 1
    assert results[0].retrieval_status == IngestionStatus.FAILED
    assert results[0].venue_id == "washington_monument"
    assert results[0].reliability == 0.95
    assert results[0].verification_status == VerificationStatus.UNVERIFIED
    assert results[0].content is None

    mock_extract.assert_called_once()
    mock_save_document.assert_called_once()
    mock_save_results.assert_called_once()


@patch("src.data_sources.venue_ingestion.save_ingestion_results")
@patch("src.data_sources.venue_ingestion.save_document")
@patch("src.data_sources.venue_ingestion.extract_webpage_content")
@patch("src.data_sources.venue_ingestion.get_sources_by_venue")
def test_ingest_venue_sources_multiple(
    mock_get_sources,
    mock_extract,
    mock_save_document,
    mock_save_results
):
    mock_get_sources.return_value = [
        SourceReference(
            source_id="source_one",
            source_name="Official Source One",
            source_type="official_website",
            url="https://example.com/one",
            reliability=0.95,
            verification_status=VerificationStatus.UNVERIFIED
        ),
        SourceReference(
            source_id="source_two",
            source_name="Official Source Two",
            source_type="official_website",
            url="https://example.com/two",
            reliability=0.90,
            verification_status=VerificationStatus.UNVERIFIED
        )
    ]

    mock_extract.side_effect = [
        DocumentIngestionResult(
            source_id="source_one",
            url="https://example.com/one",
            retrieval_status=IngestionStatus.SUCCESS,
            http_status_code=200,
            extraction_status=IngestionStatus.SUCCESS,
            retrieved_at=datetime.now(timezone.utc),
            content="Source one content"
        ),
        DocumentIngestionResult(
            source_id="source_two",
            url="https://example.com/two",
            retrieval_status=IngestionStatus.SUCCESS,
            http_status_code=200,
            extraction_status=IngestionStatus.SUCCESS,
            retrieved_at=datetime.now(timezone.utc),
            content="Source two content"
        )
    ]

    results = ingest_venue_sources("test_venue")

    assert len(results) == 2
    assert results[0].source_id == "source_one"
    assert results[1].source_id == "source_two"
    assert mock_extract.call_count == 2
    assert mock_save_document.call_count == 2
    mock_save_results.assert_called_once()


@patch("src.data_sources.venue_ingestion.save_ingestion_results")
@patch("src.data_sources.venue_ingestion.save_document")
@patch("src.data_sources.venue_ingestion.extract_webpage_content")
@patch("src.data_sources.venue_ingestion.get_sources_by_venue")
def test_ingest_venue_sources_continues_after_exception(
    mock_get_sources,
    mock_extract,
    mock_save_document,
    mock_save_results
):
    mock_get_sources.return_value = [
        SourceReference(
            source_id="source_one",
            source_name="Official Source One",
            source_type="official_website",
            url="https://example.com/one",
            reliability=0.95,
            verification_status=VerificationStatus.UNVERIFIED
        ),
        SourceReference(
            source_id="source_two",
            source_name="Official Source Two",
            source_type="official_website",
            url="https://example.com/two",
            reliability=0.90,
            verification_status=VerificationStatus.UNVERIFIED
        )
    ]

    mock_extract.side_effect = [
        ValueError("Unexpected parsing error"),
        DocumentIngestionResult(
            source_id="source_two",
            url="https://example.com/two",
            retrieval_status=IngestionStatus.SUCCESS,
            http_status_code=200,
            extraction_status=IngestionStatus.SUCCESS,
            retrieved_at=datetime.now(timezone.utc),
            content="Source two content"
        )
    ]

    results = ingest_venue_sources("test_venue")

    assert len(results) == 2

    assert results[0].retrieval_status == IngestionStatus.FAILED
    assert "Unexpected parsing error" in results[0].error_message

    assert results[1].retrieval_status == IngestionStatus.SUCCESS
    assert results[1].source_id == "source_two"

    assert mock_extract.call_count == 2
    assert mock_save_document.call_count == 2
    mock_save_results.assert_called_once()