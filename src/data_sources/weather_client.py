import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

from src.models.weather import (
    NWSLocation,
    WeatherForecastPeriod,
    WeatherAlert,
    WeatherDataResult,
    WeatherRetrievalStatus
)


load_dotenv()

NWS_BASE_URL = "https://api.weather.gov"

NWS_CONTACT_EMAIL = os.getenv("NWS_CONTACT_EMAIL")

if not NWS_CONTACT_EMAIL:
    raise ValueError("NWS_CONTACT_EMAIL is missing from .env")

HEADERS = {
    "User-Agent": (
        f"adaptive-travel-itinerary-agent/0.1 "
        f"(contact: {NWS_CONTACT_EMAIL})"
    ),
    "Accept": "application/geo+json",
}

REQUEST_TIMEOUT = 30


def make_nws_request(url: str) -> dict:
    """Retrieve JSON data from the National Weather Service API."""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def get_nws_location(latitude: float, longitude: float) -> NWSLocation:
    """Resolve coordinates to an NWS forecast location."""

    url = f"{NWS_BASE_URL}/points/{latitude},{longitude}"

    response = make_nws_request(url)
    properties = response["properties"]

    forecast_office_url = properties["forecastOffice"].rstrip("/")
    forecast_office = forecast_office_url.split("/")[-1]

    grid_id = properties["gridId"]
    grid_x = properties["gridX"]
    grid_y = properties["gridY"]

    return NWSLocation(
        latitude=latitude,
        longitude=longitude,
        forecast_office=forecast_office,
        grid_x=grid_x,
        grid_y=grid_y,
        forecast_hourly_url=properties["forecastHourly"],
    )


def get_hourly_forecast(location: NWSLocation) -> list[WeatherForecastPeriod]:
    response = make_nws_request(location.forecast_hourly_url)
    periods = response["properties"]["periods"]

    forecasts = []

    for period in periods:
        precipitation = period.get("probabilityOfPrecipitation") or {}

        forecast = WeatherForecastPeriod(
            start_time=period["startTime"],
            end_time=period["endTime"],
            temperature=period.get("temperature"),
            temperature_unit=period.get("temperatureUnit"),
            precipitation_probability=precipitation.get("value"),
            wind_speed=period.get("windSpeed"),
            short_forecast=period["shortForecast"],
            detailed_forecast=period.get("detailedForecast"),
        )

        forecasts.append(forecast)

    return forecasts


def get_active_alerts(latitude: float, longitude: float) -> list[WeatherAlert]:
    url = (
        f"{NWS_BASE_URL}/alerts/active"
        f"?point={latitude},{longitude}"
    )

    response = make_nws_request(url)
    features = response["features"]

    alerts = []

    for feature in features:
        properties = feature["properties"]

        alert = WeatherAlert(
            event=properties["event"],
            severity=properties["severity"],
            headline=properties["headline"],
            description=properties["description"],
            effective=properties.get("effective"),
            expires=properties.get("expires"),
            area_description=properties.get("areaDesc"),
            instruction=properties.get("instruction"),
        )

        alerts.append(alert)

    return alerts


def get_weather_data(latitude: float, longitude: float) -> WeatherDataResult:
    try:
        location = get_nws_location(latitude, longitude)
    except requests.RequestException as error:
        error_message = f"Location lookup failed: {error}"

        return WeatherDataResult(
            latitude=latitude,
            longitude=longitude,
            retrieved_at=datetime.now(timezone.utc),
            forecast_source_url="",
            alerts_source_url="",
            forecast_periods=[],
            alerts=[],
            retrieval_status=WeatherRetrievalStatus.FAILED,
            forecast_error=error_message,
            alerts_error=error_message,
        )

    forecasts = []
    alerts = []
    forecast_error = None
    alerts_error = None

    try:
        forecasts = get_hourly_forecast(location)
    except requests.RequestException as error:
        forecast_error = str(error)

    try:
        alerts = get_active_alerts(latitude, longitude)
    except requests.RequestException as error:
        alerts_error = str(error)

    if forecast_error and alerts_error:
        status = WeatherRetrievalStatus.FAILED
    elif forecast_error or alerts_error:
        status = WeatherRetrievalStatus.PARTIAL
    else:
        status = WeatherRetrievalStatus.SUCCESS

    return WeatherDataResult(
        latitude=latitude,
        longitude=longitude,
        retrieved_at=datetime.now(timezone.utc),
        forecast_source_url=location.forecast_hourly_url,
        alerts_source_url=(
            f"{NWS_BASE_URL}/alerts/active"
            f"?point={latitude},{longitude}"
        ),
        forecast_periods=forecasts,
        alerts=alerts,
        retrieval_status=status,
        forecast_error=forecast_error,
        alerts_error=alerts_error,
    )
