
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models.weather import (
    WeatherForecastPeriod,
    WeatherAlert,
    WeatherDataResult,
    WeatherRetrievalStatus
)


def test_valid_forecast_period():
    forecast = WeatherForecastPeriod(
        start_time=datetime(2026, 11, 14, 10, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 14, 11, tzinfo=timezone.utc),
        temperature=55,
        temperature_unit="F",
        precipitation_probability=30,
        wind_speed="10 mph",
        short_forecast="Partly Cloudy",
    )

    assert forecast.temperature == 55
    assert forecast.precipitation_probability == 30


def test_precipitation_probability_out_of_range():
    with pytest.raises(ValidationError):
        WeatherForecastPeriod(
            start_time=datetime(2026, 11, 14, 10, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 14, 11, tzinfo=timezone.utc),
            precipitation_probability=110,
            short_forecast="Rain",
        )


def test_missing_weather_values_are_allowed():
    forecast = WeatherForecastPeriod(
        start_time=datetime(2026, 11, 14, 10, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 14, 11, tzinfo=timezone.utc),
        short_forecast="Cloudy",
    )

    assert forecast.temperature is None
    assert forecast.precipitation_probability is None


def test_weather_result_defaults_to_empty_lists():
    result = WeatherDataResult(
        latitude=38.8977,
        longitude=-77.0365,
        retrieved_at=datetime.now(timezone.utc),
        forecast_source_url="https://api.weather.gov/gridpoints/example/forecast/hourly",
        alerts_source_url="https://api.weather.gov/alerts/active",
        retrieval_status=WeatherRetrievalStatus.SUCCESS,
        forecast_error=None,
        alerts_error=None,
    )

    assert result.forecast_periods == []
    assert result.alerts == []
