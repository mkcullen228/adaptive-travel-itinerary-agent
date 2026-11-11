import json
from pathlib import Path

from datetime import datetime, timezone
from src.models.attraction import Attraction
from src.models.source_reference import SourceReference, VerificationStatus
from src.data_sources.nominatim_client import (
    collect_attraction_location, select_location_candidate, LocationMatchStatus)


attractions_to_process = [
    {
        "attraction_id": "national_gallery",
        "name": "National Gallery of Art",
        "address": "6th Street and Constitution Avenue NW, Washington, DC 20565",
        "location": "Washington DC",
        "expected_types": ["museum"],
        "category": "museum",
        "indoor": True,
        "typical_duration_minutes": 120  
    },
    {
        "attraction_id": "american_history",
        "name": "National Museum of American History",
        "address" : "1300 Constitution Ave. NW, Washington, DC 20560",
        "location": "Washington DC",
        "expected_types": ["museum"], 
        "category": "museum",
        "indoor": True,
        "typical_duration_minutes": 120  
    },
    {
        "attraction_id": "air_space",
        "name": "National Air and Space Museum",
        "address" : "650 Jefferson Drive SW, Washington, DC 20004",
        "location": "Washington DC",
        "expected_types": ["museum"], 
        "category": "museum",
        "indoor": True,
        "typical_duration_minutes": 120  
    },
    {
        "attraction_id": "holocaust_memorial",
        "name": "United States Holocaust Memorial Museum",
        "address" : "100 Raoul Wallenberg Place, SW, Washington, DC 20024",
        "aliases": ["U.S. Holocaust Memorial Museum"],
        "location": "Washington DC",
        "expected_types": ["museum"], 
        "category": "museum",
        "indoor": True,
        "typical_duration_minutes": 120  
    },
    {
        "attraction_id": "natural_history",
        "name": "National Museum of Natural History",
        "address" : "10th St. & Constitution Ave. NW, Washington, DC 20560",
        "location": "Washington DC",
        "expected_types": ["museum"], 
        "category": "museum",
        "indoor": True,
        "typical_duration_minutes": 120  
    },
       {
        "attraction_id": "lincoln_memorial",
        "name": "Lincoln Memorial",
        "address" : "2 Lincoln Memorial Circle NW, Washington, DC 20037",
        "location": "Washington DC",
        "expected_types": ["memorial", "park"], 
        "category": "memorial",
        "indoor": False,
        "typical_duration_minutes": 30  
    },
    {
        "attraction_id": "washington_monument",
        "name": "Washington Monument",
        "address" : "2 15th St. NW, Washington, D.C.",
        "location": "Washington DC",
        "expected_types": ["monument", "attraction"], 
        "category": "monument",
        "indoor": True,
        "typical_duration_minutes": 60  
    },
    {
        "attraction_id": "wwii_memorial",
        "name": "World War II Memorial",
        "address" : "1750 Independence Ave. SW, Washington, DC 20006",
        "location": "Washington DC",
        "expected_types": ["monument", "attraction"], 
        "category": "monument",
        "indoor": False,
        "typical_duration_minutes": 15  
    },
    {
        "attraction_id": "us_capitol",
        "name": "United States Capitol",
        "address" : "First St SE, Washington, DC 20004",
        "location": "Washington DC",
        "expected_types": ["government"], 
        "category": "government",
        "indoor": True,
        "typical_duration_minutes": 120  
    },
    {
        "attraction_id": "national_zoo",
        "name": "Smithsonian National Zoological Park",
        "address" : "3001 Connecticut Ave. NW, Washington, D.C. 20008",
        "aliases": ["National Zoological Park"],
        "location": "Washington DC",
        "expected_types": ["zoo"], 
        "category": "zoo",
        "indoor": False,
        "typical_duration_minutes": 180  
    }
]


def process_attractions(attractions):
    results = []

    for attraction in attractions:
        candidates = collect_attraction_location(
            attraction["name"],
            attraction["location"]
        )

        if not candidates:
            for alias in attraction.get("aliases", []):
                candidates = collect_attraction_location(
                    alias,
                    attraction["location"]
                )

                if candidates:
                    break

        evaluation = select_location_candidate(
            candidates,
            attraction["name"],
            attraction["location"],
            attraction["expected_types"],
            38.80,
            38.995,
            -77.12,
            -76.91, 
            attraction.get("aliases", []),
        )

        results.append({
            "attraction": attraction,
            "status": evaluation["status"],
            "selected_candidate": evaluation["selected_candidate"],
            "candidate_evaluations": evaluation["candidate_evaluations"]
        })
    return results


def convert_to_attraction_records(results):
    attraction_records = []
    review_records = []

    for result in results:
        if result["status"] != LocationMatchStatus.UNIQUE_VALID_MATCH:
            review_records.append(result)
            continue
        
        attraction = result["attraction"]
        candidate = result["selected_candidate"]
        
        osm_type = candidate["osm_type"]
        osm_id = candidate["osm_id"]

        source_reference = SourceReference(
            source_id=f"osm_{osm_type}_{osm_id}",
            source_name="OpenStreetMap",
            source_type="openstreetmap",
            url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
            retrieved_at=datetime.now(timezone.utc),
            reliability=0.85,
            verification_status=VerificationStatus.VERIFIED
        )

        attraction_record = Attraction(
            attraction_id=attraction["attraction_id"],
            name=attraction["name"],
            address=attraction["address"],
            latitude=float(candidate["lat"]),
            longitude=float(candidate["lon"]),
            category=attraction["category"],
            indoor=attraction["indoor"],
            typical_duration_minutes=attraction["typical_duration_minutes"],
            source_references=[source_reference]
        )

        attraction_records.append(attraction_record)

    return attraction_records, review_records


if __name__ == "__main__":
    results = process_attractions(attractions_to_process)
    records, review = convert_to_attraction_records(results)

    print(f"Successfully converted: {len(records)}")
    print(f"Requiring review: {len(review)}")

    output_path = Path("data/attractions/washington_dc.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [record.model_dump(mode="json") for record in records],
            file,
            indent=2
        )