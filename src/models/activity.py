from pydantic import BaseModel, Field
from datetime import datetime, timedelta


class Activity(BaseModel):
    """
    Represents an individual activity within a travel itinerary.

    An activity includes identifying information, location, scheduled
    start time, duration, and attributes used during itinerary recovery
    and validation.
    
    Ex: 
        museum = Activity(
            activity_id="activity_001",
            name="National Gallery of Art",
            location="Washington, DC",
            start_time=datetime(2026, 11, 7, 10, 0),
            duration_minutes=90,
            mandatory=False,
            indoor=True)
        
        museam.end_time

    """
    activity_id: str
    name: str
    location: str

    start_time: datetime
    duration_minutes: int = Field(gt=0)

    mandatory: bool = False
    indoor: bool = True

    @property
    def end_time(self) -> datetime:
        """
        Calculate the scheduled end time of the activity.

        Returns:
            datetime: The activity's start time plus its duration.
        """
        # Calculate end time using start_time and duration_minutes
        return self.start_time + timedelta(minutes=self.duration_minutes)
