import json
from pathlib import Path

from src.models.itinerary import Itinerary


def test_baseline_itinerary_loads():
    dataset_path = Path(
        "data/itineraries/dc_baseline_2026_11_07.json"
    )

    with dataset_path.open(encoding="utf-8") as file:
        data = json.load(file)

    itinerary = Itinerary.model_validate(data)

    assert itinerary.itinerary_id == "dc_baseline_2026_11_07"
    assert itinerary.destination == "Washington, DC"
    assert len(itinerary.activities) == 5

    mandatory_activities = [
        activity for activity in itinerary.activities
        if activity.mandatory
    ]

    assert len(mandatory_activities) == 1
    assert mandatory_activities[0].activity_id == "natural_history"
    
    assert len(itinerary.travel_legs) == 4
    # assert itinerary.travel_legs == [
    #     TravelLeg(origin_activity_id='national_gallery', destination_activity_id='american_history', estimates=[
    #         TravelEstimate(mode='walking', duration_minutes=12, duration_seconds=683.5, distance_meters=949.3, source='OpenRouteService')], selected_mode='walking'), 
    #     TravelLeg(origin_activity_id='american_history', destination_activity_id='natural_history', estimates=[
    #         TravelEstimate(mode='walking', duration_minutes=5, duration_seconds=299.5, distance_meters=416.0, source='OpenRouteService')], selected_mode='walking'), 
    #     TravelLeg(origin_activity_id='natural_history', destination_activity_id='wwii_memorial', estimates=[
    #         TravelEstimate(mode='walking', duration_minutes=17, duration_seconds=985.9, distance_meters=1369.3, source='OpenRouteService')], selected_mode='walking'), 
    #     TravelLeg(origin_activity_id='wwii_memorial', destination_activity_id='lincoln_memorial', estimates=[
    #         TravelEstimate(mode='walking', duration_minutes=12, duration_seconds=694.1, distance_meters=964.0, source='OpenRouteService')], selected_mode='walking')]