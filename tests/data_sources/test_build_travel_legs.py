from src.data_sources.build_travel_legs import build_travel_legs
from src.data_sources.build_baseline_itinerary import baseline_itinerary


def test_build_travel_legs():
    travel_legs = build_travel_legs(baseline_itinerary)

    assert len(travel_legs) == 4

    for leg in travel_legs:
        assert leg.selected_mode == "walking"
        assert len(leg.estimates) == 1
        assert leg.estimates[0].duration_minutes > 0
        assert leg.estimates[0].source == "OpenRouteService"
