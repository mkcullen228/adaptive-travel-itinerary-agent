from datetime import datetime, timezone

from src.models.document import (
    DocumentIngestionResult,
    IngestionStatus
)


def test_successful_document_ingestion():
    result = DocumentIngestionResult(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit",
        retrieval_status=IngestionStatus.SUCCESS,
        http_status_code=200,
        extraction_status=IngestionStatus.SUCCESS,
        retrieved_at=datetime.now(timezone.utc),
        content="Visitor information"
    )

    assert result.retrieval_status == IngestionStatus.SUCCESS
    assert result.extraction_status == IngestionStatus.SUCCESS


def test_failed_document_retrieval():
    result = DocumentIngestionResult(
        source_id="natural_history_visitor_info",
        url="https://example.com/visit",
        retrieval_status=IngestionStatus.FAILED,
        http_status_code=403,
        retrieved_at=datetime.now(timezone.utc),
        error_message="HTTP 403 Forbidden"
    )

    assert result.retrieval_status == IngestionStatus.FAILED
    assert result.extraction_status is None
    assert result.content is None