import json
import requests
import trafilatura
from pathlib import Path
from datetime import datetime, timezone

from src.models.document import (DocumentIngestionResult, IngestionStatus)


def extract_webpage_content(source_id: str, url: str) -> DocumentIngestionResult:

    retrieved_at = datetime.now(timezone.utc)

    try:
        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "TravelItineraryRecoveryAgent/1.0"
            }
        )
        response.raise_for_status()

    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code

        return DocumentIngestionResult(
            source_id=source_id,
            url=url,
            retrieval_status=IngestionStatus.FAILED,
            http_status_code=status_code,
            retrieved_at=retrieved_at,
            error_message=f"HTTP error {status_code}"
        )

    except requests.exceptions.RequestException as error:
        return DocumentIngestionResult(
            source_id=source_id,
            url=url,
            retrieval_status=IngestionStatus.FAILED,
            retrieved_at=retrieved_at,
            error_message=f"Network error: {error}"
        )

    extracted_content = trafilatura.extract(response.text)

    if not extracted_content or not validate_extracted_content(extracted_content):
        return DocumentIngestionResult(
            source_id=source_id,
            url=url,
            retrieval_status=IngestionStatus.SUCCESS,
            http_status_code=response.status_code,
            extraction_status=IngestionStatus.FAILED,
            retrieved_at=retrieved_at,
            error_message="Extracted content did not meet minimum quality requirements.",
            content=None
        )

    return DocumentIngestionResult(
        source_id=source_id,
        url=url,
        retrieval_status=IngestionStatus.SUCCESS,
        http_status_code=response.status_code,
        extraction_status=IngestionStatus.SUCCESS,
        retrieved_at=retrieved_at,
        content=extracted_content
    )


def load_source_registry() -> list[dict]:
    """Load registered document sources from the source registry."""

    project_root = Path(__file__).resolve().parents[2]
    registry_path = (
        project_root / "data" / "documents" / "source_registry.json"
    )

    with registry_path.open("r", encoding="utf-8") as file:
        registry = json.load(file)

    return registry["sources"]


def ingest_registered_sources() -> list[DocumentIngestionResult]:
    """Ingest all sources listed in the source registry."""

    sources = load_source_registry()
    results = []

    for source in sources:
        result = extract_webpage_content(
            source_id=source["source_id"],
            url=source["url"]
        )

        save_document(result)
        results.append(result)

    save_ingestion_results(results)
    return results


def save_document(result: DocumentIngestionResult) -> None:
    """Save successfully extracted document content as Markdown."""

    if (
        result.retrieval_status != IngestionStatus.SUCCESS
        or result.extraction_status != IngestionStatus.SUCCESS
        or not result.content
    ):
        return

    project_root = Path(__file__).resolve().parents[2]

    document_path = (
        project_root
        / "data"
        / "documents"
        / "venue_guides"
        / f"{result.source_id}.md"
    )

    document_path.parent.mkdir(parents=True, exist_ok=True)

    document_content = (
        f"# Source: {result.source_id}\n\n"
        f"Venue ID: {result.venue_id}\n\n"
        f"Subject: {result.subject}\n\n"
        f"URL: {result.url}\n\n"
        f"Retrieved at: {result.retrieved_at.isoformat()}\n\n"
        f"Reliability: {result.reliability}\n\n"
        f"Verification status: {result.verification_status.value if result.verification_status else 'unverified'}\n\n"
        f"---\n\n"
        f"{result.content}\n"
    )
    document_path.write_text(document_content, encoding="utf-8")


def save_ingestion_results(results: list[DocumentIngestionResult]) -> None:
    """Save ingestion results to a JSON file."""

    project_root = Path(__file__).resolve().parents[2]

    results_path = (
        project_root
        / "data"
        / "documents"
        / "ingestion_results.json"
    )

    results_path.parent.mkdir(parents=True, exist_ok=True)

    results_data = [
        result.model_dump(mode="json")
        for result in results
    ]

    results_path.write_text(
        json.dumps(results_data, indent=4),
        encoding="utf-8"
    )


def validate_extracted_content(content: str) -> bool:
    """Check whether extracted webpage content meets basic quality requirements."""

    if len(content.strip()) < 300:
        return False

    relevance_keywords = [
        "visitor",
        "hours",
        "admission",
        "accessibility",
        "directions",
        "closure",
        "museum",
        "memorial",
        "entrance",
        "parking"
    ]

    content_lower = content.lower()

    return any(keyword in content_lower for keyword in relevance_keywords)


if __name__ == "__main__":
    results = ingest_registered_sources()

    for result in results:
        print(result.model_dump(mode="json"))
