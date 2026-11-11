from enum import Enum
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from src.models.source_reference import SourceReference


class DisruptionType(str, Enum):
    WEATHER = "weather"
    TRAVEL_DELAY = "travel_delay"
    VENUE_UNAVAILABLE = "venue_unavailable"


class DisruptionSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class WeatherCondition(str, Enum):
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    ICE = "ice"
    HIGH_WIND = "high_wind"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"


class DisruptionScenario(BaseModel):
    scenario_id: str
    scenario_type: DisruptionType
    description: str
    affected_activity_ids: List[str] = Field(default_factory=list)
    affected_travel_leg_ids: List[str] = Field(default_factory=list)
    severity: DisruptionSeverity
    source_references: List[SourceReference] = Field(default_factory=list)
    additional_duration_minutes: int | None = Field(default=None, gt=0)
    additional_duration_percent: float | None = Field(default=None, gt=0)
    weather_condition: WeatherCondition | None = None
    affected_time_start: datetime | None = None
    affected_time_end: datetime | None = None


    @model_validator(mode="after")
    def validate_travel_delay(self):
        has_fixed_delay = self.additional_duration_minutes is not None
        has_percentage_delay = self.additional_duration_percent is not None

        if self.scenario_type == DisruptionType.TRAVEL_DELAY:
            if has_fixed_delay == has_percentage_delay:
                raise ValueError(
                    "Travel delays must specify exactly one of "
                    "additional_duration_minutes or additional_duration_percent."
                )

        elif has_fixed_delay or has_percentage_delay:
            raise ValueError(
                "Only travel delay scenarios can specify additional duration."
            )

        return self


    @model_validator(mode="after")
    def validate_affected_time_window(self):
        if self.scenario_type == DisruptionType.WEATHER:
            if self.weather_condition is None:
                raise ValueError("Weather scenarios must specify a weather condition.")

            if self.affected_time_start is None or self.affected_time_end is None:
                raise ValueError("Weather scenarios must specify both affected time boundaries.")

            if self.affected_time_end <= self.affected_time_start:
                raise ValueError("Affected time end must be later than affected time start.")

        else:
            if (
                self.weather_condition is not None
                or self.affected_time_start is not None
                or self.affected_time_end is not None
            ):
                raise ValueError("Only weather scenarios can specify weather-related fields.")

        return self

    @model_validator(mode="after")
    def validate_venue_unavailability(self):
        if self.scenario_type == DisruptionType.VENUE_UNAVAILABLE:
            if not self.affected_activity_ids:
                raise ValueError(
                    "Venue unavailability scenarios must specify at least one affected activity."
                )
        return self
