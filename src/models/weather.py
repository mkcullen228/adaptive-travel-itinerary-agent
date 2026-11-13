
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class WeatherForecastPeriod(BaseModel):
    start_time: datetime
    end_time: datetime
    temperature: int | None = None
    temperature_unit: str | None = None
    precipitation_probability: float | None = Field(
        default=None, ge=0, le=100
    )
    wind_speed: str | None = None
    short_forecast: str
    detailed_forecast: str | None = None


class WeatherAlert(BaseModel):
    event: str
    severity: str
    headline: str
    description: str
    effective: datetime | None = None
    expires: datetime | None = None
    area_description: str | None = None
    instruction: str | None = None


class WeatherDataResult(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    retrieved_at: datetime
    forecast_source_url: str
    alerts_source_url: str
    forecast_periods: list[WeatherForecastPeriod] = Field(
        default_factory=list
    )
    alerts: list[WeatherAlert] = Field(default_factory=list)
    retrieval_status: WeatherRetrievalStatus
    forecast_error: str | None = None
    alerts_error: str | None = None


class NWSLocation(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    forecast_office: str
    grid_x: int
    grid_y: int
    forecast_hourly_url: str


class WeatherRetrievalStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
