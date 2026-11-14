import re
from pathlib import Path
from datetime import datetime


def extract_required_metadata(header: str) -> dict:
    """Extract and validate required document metadata."""

    required_fields = {
        "source_id": r"# Source: (.+)",
        "subject": r"Subject: (.+)",
        "url": r"URL: (.+)",
        "retrieved_at": r"Retrieved at: (.+)",
        "reliability": r"Reliability: (.+)",
    }
    
    optional_fields = {
        "venue_id": r"Venue ID: (.+)",
        "verification_status": r"Verification status: (.+)",
    }

    metadata = {}

    # required fields
    for field, pattern in required_fields.items():
        match = re.search(pattern, header)

        if not match:
            raise ValueError(
                f"Missing required document metadata: {field}"
            )

        metadata[field] = match.group(1).strip()

    # optional fields
    for field, pattern in optional_fields.items():
        match = re.search(pattern, header)

        if match:
            metadata[field] = match.group(1).strip()

    # Clean Markdown link formatting from URLs.
    url = metadata["url"]
    if url.startswith("[") and "](" in url:
        metadata["url"] = url.split("](", maxsplit=1)[1].rstrip(")")

    try:
        metadata["retrieved_at"] = datetime.fromisoformat(
            metadata["retrieved_at"]
        )
    except ValueError as error:
        raise ValueError(
            "Invalid retrieved_at metadata. Expected an ISO-formatted datetime."
        ) from error

    try:
        metadata["reliability"] = float(metadata["reliability"])
    except ValueError as error:
        raise ValueError(
            "Invalid reliability metadata. Expected a numeric value between 0 and 1."
        ) from error

    if not 0 <= metadata["reliability"] <= 1:
        raise ValueError(
            "Invalid reliability metadata. Expected a value between 0 and 1."
        )

    return metadata


def load_markdown_document(file_path: Path) -> tuple[dict, str]:
    """Load a Markdown document and separate its metadata from its content."""

    text = file_path.read_text(encoding="utf-8")

    header, content = text.split("---", maxsplit=1)

    metadata = extract_required_metadata(header)

    return metadata, content.strip()


if __name__ == "__main__":
    metadata, content = load_markdown_document(
        Path("data/documents/venue_guides/washington_monument_visitor_info.md")
    )

    print(metadata)
    print(content[:300])