from pydantic import BaseModel, Field
from typing import List

from src.models.source_reference import SourceReference

class Attraction(BaseModel):
    """
    Represents a venue or destination that can be included in an itinerary.

    Stores identifying information, geographic coordinates, venue
    characteristics, and references to supporting data sources.

    Field: Type - Purpose
        attraction_id: str - Unique identifier
        name: str - Venue name
        address: str - Physical address
        latitude: float - Geographic latitude
        longitude: float - Geographic longitude
        category: str - Museum, monument, park, etc.
        indoor: bool - Whether the attraction is primarily indoors
        typical_duration_minutes: int - Expected visit duration
        source_references: List[SourceReference]
    
    """
    attraction_id: str
    name: str
    address: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: str
    indoor: bool
    typical_duration_minutes: int = Field(gt=0)
    source_references: List[SourceReference] = Field(default_factory=list)
