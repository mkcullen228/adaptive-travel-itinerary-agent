import json
from pathlib import Path

from src.models.source_reference import SourceReference


VENUE_SOURCES_PATH = Path("data/venues/venue_sources.json")


def load_venue_sources() -> dict[str, list[SourceReference]]:
    with VENUE_SOURCES_PATH.open(encoding="utf-8") as file:
        data = json.load(file)
    print(data)
    venue_sources = {}

    for venue in data:
        venue_id = venue["venue_id"]

        sources = [
            SourceReference.model_validate(source)
            for source in venue["sources"]
        ]

        venue_sources[venue_id] = sources

    return venue_sources


def get_sources_by_venue(
    venue_id: str,
) -> list[SourceReference]:
    venue_sources = load_venue_sources()

    if venue_id not in venue_sources:
        raise ValueError(f"No sources found for venue: {venue_id}")

    return venue_sources[venue_id]
