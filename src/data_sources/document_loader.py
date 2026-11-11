import re
from pathlib import Path
from datetime import datetime


def load_markdown_document(file_path: Path) -> tuple[dict, str]:
    """Load a Markdown document and separate its metadata from its content."""

    text = file_path.read_text(encoding="utf-8")

    header, content = text.split("---", maxsplit=1)

    source_match = re.search(r"# Source: (.+)", header)
    
    url_match = re.search(r"URL: (.+)", header)
    url = url_match.group(1).strip()

    # Remove Markdown link formatting, if present.
    if url.startswith("[") and "](" in url:
        url = url.split("](", maxsplit=1)[1].rstrip(")")

    retrieved_match = re.search(r"Retrieved at: (.+)", header)

    metadata = {
        "source_id": source_match.group(1).strip(),
        "url": url,
        "retrieved_at": datetime.fromisoformat(
            retrieved_match.group(1).strip()
        ),
    }

    content = content.strip()

    return metadata, content


if __name__ == "__main__":
    metadata, content = load_markdown_document(
        Path("data/documents/venue_guides/washington_monument_visitor_info.md")
    )

    print(metadata)
    print(content[:300])