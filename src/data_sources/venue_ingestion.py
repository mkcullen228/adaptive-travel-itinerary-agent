from datetime import datetime, timezone

from src.models.document import IngestionStatus
from src.models.document import DocumentIngestionResult
from src.data_sources.venue_source_loader import get_sources_by_venue
from src.data_sources.document_ingestion import (
    extract_webpage_content,
    save_document,
    save_ingestion_results,
)


def ingest_venue_sources(venue_id: str) -> list[DocumentIngestionResult]:
    sources = get_sources_by_venue(venue_id)
    results = []

    for source in sources:
        try:
            result = extract_webpage_content(
                source_id=source.source_id,
                url=str(source.url)
            )
        except Exception as error:
            result = DocumentIngestionResult(
                source_id=source.source_id,
                url=str(source.url),
                retrieval_status=IngestionStatus.FAILED,
                retrieved_at=datetime.now(timezone.utc),
                error_message=f"Unexpected ingestion error: {error}"
            )

        result_data = result.model_dump()

        result_data.update({
            "venue_id": venue_id,
            "subject": source.source_name,
            "reliability": source.reliability,
            "verification_status": source.verification_status
        })

        result = DocumentIngestionResult(**result_data)

        save_document(result)
        results.append(result)

    save_ingestion_results(results)
    return results
