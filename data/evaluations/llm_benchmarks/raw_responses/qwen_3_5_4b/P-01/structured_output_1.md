{
  "option_id": "recovery_proposal_dc_2026_11_07_minimal",
  "strategy": "minimal_disruption",
  "proposed_itinerary": {
    "itinerary_id": "dc_baseline_2026_11_07",
    "destination": "Washington, DC",
    "itinerary_date": "2026-11-07",
    "activities": [
      {
        "activity_id": "american_history",
        "name": "National Museum of American History",
        "location": "1300 Constitution Ave. NW, Washington, DC",
        "start_time": "2026-11-07T09:00:00-05:00",
        "duration_minutes": 90,
        "mandatory": false,
        "indoor": true
      },
      {
        "activity_id": "natural_history",
        "name": "National Museum of Natural History",
        "location": "10th St. & Constitution Ave. NW, Washington, DC",
        "start_time": "2026-11-07T10:50:00-05:00",
        "duration_minutes": 90,
        "mandatory": true,
        "indoor": true
      },
      {
        "activity_id": "wwii_memorial",
        "name": "World War II Memorial",
        "location": "1750 Independence Ave. SW, Washington, DC",
        "start_time": "2026-11-07T12:40:00-05:00",
        "duration_minutes": 30,
        "mandatory": false,
        "indoor": false
      },
      {
        "activity_id": "lincoln_memorial",
        "name": "Lincoln Memorial",
        "location": "2 Lincoln Memorial Circle NW, Washington, DC",
        "start_time": "2026-11-07T13:50:00-05:00",
        "duration_minutes": 30,
        "mandatory": false,
        "indoor": false
      }
    ],
    "travel_legs": [
      {
        "origin_activity_id": "american_history",
        "destination_activity_id": "natural_history",
        "estimates": [
          {
            "mode": "walking",
            "duration_minutes": 5,
            "duration_seconds": 299.5,
            "distance_meters": 416.0,
            "source": "OpenRouteService"
          }
        ],
        "selected_mode": "walking"
      },
      {
        "origin_activity_id": "natural_history",
        "destination_activity_id": "wwii_memorial",
        "estimates": [
          {
            "mode": "walking",
            "duration_minutes": 17,
            "duration_seconds": 985.9,
            "distance_meters": 1369.3,
            "source": "OpenRouteService"
          }
        ],
        "selected_mode": "walking"
      },
      {
        "origin_activity_id": "wwii_memorial",
        "destination_activity_id": "lincoln_memorial",
        "estimates": [
          {
            "mode": "walking",
            "duration_minutes": 12,
            "duration_seconds": 694.1,
            "distance_meters": 964.0,
            "source": "OpenRouteService"
          }
        ],
        "selected_mode": "walking"
      }
    ]
  },
  "proposal_status": "partial",
  "rationale": "The National Gallery of Art has been confirmed unavailable for the scheduled time slot (09:00–10:30). To adhere to the 'minimal_disruption' strategy, the original itinerary structure and sequence have been preserved as much as possible. The National Gallery activity has been removed from the schedule. Consequently, the start times of subsequent activities have been shifted forward by 50 minutes (the duration of the removed activity) to maintain logical sequencing. No new replacement activities have been added due to a lack of verified availability data.",
  "preserved_constraints": [
    "Original itinerary date: 2026-11-07",
    "Original destination: Washington, DC",
    "Mandatory activity status: National Museum of Natural History remains mandatory",
    "Travel modes: Walking estimates preserved for remaining legs",
    "Activity durations: Unchanged for all remaining activities"
  ],
  "violated_constraints": [
    "Original activity 'national_gallery' is removed due to confirmed unavailability.",
    "Original travel leg between 'national_gallery' and 'american_history' is removed as the origin activity no longer exists."
  ],
  "trade_offs": [
    "Trade-off: Removing the National Gallery eliminates one scheduled activity. This allows the itinerary to proceed without waiting for an unavailable venue, but it reduces the total number of planned activities.",
    "Trade-off: Shifting start times forward may conflict with other user constraints (e.g., lunch time, transportation availability) if they were not explicitly defined in the original plan. The user must verify that the new schedule aligns with their personal preferences and external commitments."
  ],
  "supporting_evidence_ids": [
    "p01_controlled_test"
  ],
  "assumptions": [
    "The National Museum of American History is open at 09:00 AM. This assumption is not explicitly verified by the investigation results.",
    "The travel times between remaining venues remain accurate and unaffected by the removal of the National Gallery."
  ],
  "uncertainties": [
    "Availability of replacement activities: No verified evidence exists to confirm that any alternative venue is available for the time slot originally occupied by the National Gallery. The absence of closure information does not confirm availability.",
    "Schedule feasibility: It has not been determined whether the shifted start times for subsequent activities (American History, Natural History, etc.) align with user preferences or other unlisted constraints.",
    "Unverified replacement suggestions: None identified as feasible candidates due to lack of verification data."
  ]
}