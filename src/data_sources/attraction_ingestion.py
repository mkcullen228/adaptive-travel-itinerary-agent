from src.data_sources.nominatim_client import (
    collect_attraction_location, select_location_candidate, LocationMatchStatus)


attractions_to_process = [
    {
        "attraction_id": "nga",
        "name": "National Gallery of Art",
        "location": "Washington DC",
        "expected_types": ["museum"]
    },
    {
        "attraction_id": "american_history",
        "name": "National Museum of American History",
        "location": "Washington DC",
        "expected_types": ["museum"]
    },
    {
        "attraction_id": "air_space",
        "name": "National Air and Space Museum",
        "location": "Washington DC",
        "expected_types": ["museum"]
    },
    {
        "attraction_id": "holocaust_memorial",
        "name": "United States Holocaust Memorial Museum",
        "aliases": ["U.S. Holocaust Memorial Museum"],
        "location": "Washington DC",
        "expected_types": ["museum"]
    },
    {
        "attraction_id": "natural_history",
        "name": "National Museum of Natural History",
        "location": "Washington DC",
        "expected_types": ["museum"]
    },
       {
        "attraction_id": "lincoln_memorial",
        "name": "Lincoln Memorial",
        "location": "Washington DC",
        "expected_types": ["memorial", "park"]
    },
    {
        "attraction_id": "washington_monument",
        "name": "Washington Monument",
        "location": "Washington DC",
        "expected_types": ["monument", "attraction"]
    },
    {
        "attraction_id": "wwii_memorial",
        "name": "World War II Memorial",
        "location": "Washington DC",
        "expected_types": ["monument", "attraction"]
    },
    {
        "attraction_id": "us_capitol",
        "name": "United States Capitol",
        "location": "Washington DC",
        "expected_types": ["government"]
    },
    {
        "attraction_id": "national_zoo",
        "name": "Smithsonian National Zoological Park",
        "aliases": ["National Zoological Park"],
        "location": "Washington DC",
        "expected_types": ["zoo"]
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
            "attraction_id": attraction["attraction_id"],
            "status": evaluation["status"],
            "selected_candidate": evaluation["selected_candidate"],
            "candidate_evaluations": evaluation["candidate_evaluations"]
        })
    return results



# Scratch 
results = process_attractions(attractions_to_process)

for result in results:
    print(
        result["attraction_id"],
        result["status"].value
    )


# for result in results:
#     if result["attraction_id"] == "national_zoo":
#         for evaluation in result["candidate_evaluations"]:
#             print("Candidate:", evaluation["candidate"].get("display_name"))
#             print("Category:", evaluation["candidate"].get("category"))
#             print("Type:", evaluation["candidate"].get("type"))
#             print("Failed checks:", evaluation["failure_reasons"])


### Scratch 
# attraction_name = "National Museum of American History"
# attraction_location = "Washington DC"
# expected_type = "museum"
# min_lat = 38.80
# max_lat = 38.995
# min_lon = -77.12
# max_lon = -76.91

# results = collect_attraction_location(attraction_name, attraction_location)
# candidates = select_location_candidate(results, attraction_name, attraction_location, expected_type, 
#                               min_lat, max_lat, min_lon, max_lon)
# # print(candidates)

# if candidates["status"] == LocationMatchStatus.UNIQUE_VALID_MATCH:
#     print("Unique candidate found:")
#     print(candidates["selected_candidate"])
# else:
#     print("Manual review required:")
#     print(candidates)