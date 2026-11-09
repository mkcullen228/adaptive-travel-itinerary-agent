from pydantic import BaseModel, Field
from typing import List


class TravelEstimate(BaseModel):
    """Stores a travel-time estimate for a specific transportation mode.

    Includes the estimated duration and the source of the estimate.

    Ex: 
        TravelEstimate(
            mode="walking",
            duration_minutes=12,
            source="manual_test_data",
            )
    """
    mode: str
    duration_minutes: int = Field(gt=0)
    source: str


class TravelLeg(BaseModel):
    """
    Represents travel between two activities in an itinerary.

    Stores available travel estimates for different transportation
    modes and identifies which mode is selected for itinerary validation.

    Ex: 
        TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=12,
                    source="manual_test_data",
                    ), 
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )
            ]
        )
    """
    origin_activity_id: str
    destination_activity_id: str
    estimates: List[TravelEstimate]
    selected_mode: str
