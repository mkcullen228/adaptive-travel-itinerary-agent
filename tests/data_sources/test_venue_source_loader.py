import pytest
from src.data_sources.venue_source_loader import load_venue_sources, get_sources_by_venue  


def test_load_venue_sources():
    venue_sources = load_venue_sources()

    assert "national_gallery" in venue_sources
    assert "washington_monument" in venue_sources
    assert len(venue_sources["national_gallery"]) == 1
    assert len(venue_sources["washington_monument"]) == 1


def test_get_sources_by_venue():
    sources = get_sources_by_venue("national_gallery")
    assert len(sources) == 1
    assert sources[0].source_id == "nga_visitor_info"

    sources = get_sources_by_venue("washington_monument")
    assert len(sources) == 1
    assert sources[0].source_id == "nps_washington_monument"

    try:
        get_sources_by_venue("nonexistent_venue")
    except ValueError as e:
        assert "No sources found for venue: nonexistent_venue" in str(e)
    else:
        assert False, "Expected ValueError to be raised"


def test_get_sources_by_venue_not_found():
    with pytest.raises(
        ValueError,
        match="No sources found for venue: nonexistent_venue"
    ):
        get_sources_by_venue("nonexistent_venue")
