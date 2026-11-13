
import pytest
import requests

from src.data_sources.weather_client import (make_nws_request, 
                                             get_nws_location, 
                                             get_active_alerts, 
                                             get_weather_data)

from src.models.weather import NWSLocation
from src.models.weather import WeatherRetrievalStatus


def mock_location():
    return NWSLocation(
        latitude=38.8977,
        longitude=-77.0365,
        forecast_office="LWX",
        grid_x=96,
        grid_y=70,
        forecast_hourly_url=(
            "https://api.weather.gov/gridpoints/LWX/96,70/forecast/hourly"
        ),
    )


def test_successful_nws_request(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"properties": {"forecast": "test"}}

    def mock_get(url, headers, timeout):
        assert url == "https://api.weather.gov/test"
        assert headers["Accept"] == "application/geo+json"
        assert timeout == 30
        return MockResponse()

    monkeypatch.setattr(
        "src.data_sources.weather_client.requests.get",
        mock_get,
    )

    result = make_nws_request("https://api.weather.gov/test")

    assert result == {"properties": {"forecast": "test"}}


def test_nws_http_error_propagates(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            raise requests.HTTPError("Service unavailable")

    monkeypatch.setattr(
        "src.data_sources.weather_client.requests.get",
        lambda *args, **kwargs: MockResponse(),
    )

    with pytest.raises(requests.HTTPError):
        make_nws_request("https://api.weather.gov/test")


def test_get_nws_location(monkeypatch):
    mock_response = {
        "properties": {
            "forecastOffice": "https://api.weather.gov/offices/LWX",
            "gridId": "LWX",
            "gridX": 96,
            "gridY": 70,
            "forecastHourly": (
                "https://api.weather.gov/gridpoints/LWX/96,70/forecast/hourly"
            ),
        }
    }

    monkeypatch.setattr(
        "src.data_sources.weather_client.make_nws_request",
        lambda url: mock_response,
    )

    location = get_nws_location(38.8977, -77.0365)

    assert location.forecast_office == "LWX"
    assert location.grid_x == 96
    assert location.grid_y == 70
    assert location.forecast_hourly_url.endswith("/forecast/hourly")


def test_get_hourly_forecast(monkeypatch):
    from src.data_sources.weather_client import get_hourly_forecast
    from src.models.weather import NWSLocation

    location = NWSLocation(
        latitude=38.8977,
        longitude=-77.0365,
        forecast_office="LWX",
        grid_x=96,
        grid_y=70,
        forecast_hourly_url="https://api.weather.gov/gridpoints/LWX/96,70/forecast/hourly",
    )

    mock_response = {
        "properties": {
            "periods": [
                {
                    "startTime": "2024-06-01T00:00:00Z",
                    "endTime": "2024-06-01T06:00:00Z",
                    "temperature": 75,
                    "temperatureUnit": "F",
                    "probabilityOfPrecipitation": {"value": 10},
                    "windSpeed": "5 mph",
                    "shortForecast": "Sunny",
                    "detailedForecast": "Clear skies expected",
                }
            ]
        }
    }

    monkeypatch.setattr(
        "src.data_sources.weather_client.make_nws_request",
        lambda url: mock_response,
    )

    forecasts = get_hourly_forecast(location)

    assert len(forecasts) == 1
    assert forecasts[0].temperature == 75
    assert forecasts[0].temperature_unit == "F"
    assert forecasts[0].precipitation_probability == 10
    assert forecasts[0].wind_speed == "5 mph"
    assert forecasts[0].short_forecast == "Sunny"
    assert forecasts[0].detailed_forecast == "Clear skies expected"

def test_get_active_alerts(monkeypatch):
    from src.data_sources.weather_client import get_active_alerts
    from src.models.weather import WeatherAlert

    mock_response = {
        "features": [
            {
                "properties": {
                    "event": "Severe Thunderstorm Warning",
                    "severity": "Severe",
                    "headline": "Severe thunderstorms expected",
                    "description": "Strong winds and heavy rain expected",
                    "effective": "2024-06-01T00:00:00Z",
                    "expires": "2024-06-01T06:00:00Z",
                    "areaDesc": "Washington, DC",
                    "instruction": "Seek shelter immediately",
                }
            }
        ]
    }

    monkeypatch.setattr(
        "src.data_sources.weather_client.make_nws_request",
        lambda url: mock_response,
    )

    alerts = get_active_alerts(38.8977, -77.0365)

    assert len(alerts) == 1
    assert alerts[0].event == "Severe Thunderstorm Warning"
    assert alerts[0].severity == "Severe"
    assert alerts[0].headline == "Severe thunderstorms expected"
    assert alerts[0].description == "Strong winds and heavy rain expected"
    assert alerts[0].area_description == "Washington, DC"
    assert alerts[0].instruction == "Seek shelter immediately"

def test_get_active_alerts_empty(monkeypatch):
    from src.data_sources.weather_client import get_active_alerts
    from src.models.weather import WeatherAlert

    mock_response = {
        "features": []
    }

    monkeypatch.setattr(
        "src.data_sources.weather_client.make_nws_request",
        lambda url: mock_response,
    )

    alerts = get_active_alerts(38.8977, -77.0365)

    assert len(alerts) == 0


def test_get_weather_data(monkeypatch):
    from src.data_sources.weather_client import get_weather_data
    from src.models.weather import WeatherDataResult

    def mock_nws_request(url):
        if "/points/" in url:
            return {
                "properties": {
                    "forecastOffice": "https://api.weather.gov/offices/LWX",
                    "gridId": "LWX",
                    "gridX": 96,
                    "gridY": 70,
                    "forecastHourly": (
                        "https://api.weather.gov/gridpoints/LWX/96,70/forecast/hourly"
                    ),
                }
            }

        if "/forecast/hourly" in url:
            return {
                "properties": {
                    "periods": []
                }
            }

        if "/alerts/active" in url:
            return {"features": []}

        raise ValueError(f"Unexpected NWS URL: {url}")

    monkeypatch.setattr(
        "src.data_sources.weather_client.make_nws_request",
        mock_nws_request,
    )

    weather_data = get_weather_data(38.8977, -77.0365)

    assert isinstance(weather_data, WeatherDataResult)
    assert weather_data.latitude == 38.8977
    assert weather_data.longitude == -77.0365
    assert weather_data.alerts == []
    assert weather_data.forecast_periods == []
    assert weather_data.retrieved_at is not None
    assert weather_data.forecast_source_url.endswith("/forecast/hourly")
    assert "/alerts/active" in weather_data.alerts_source_url


def test_get_weather_data_success(monkeypatch):
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_nws_location",
        lambda lat, lon: mock_location(),
    )
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_hourly_forecast",
        lambda location: [],
    )
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_active_alerts",
        lambda lat, lon: [],
    )

    result = get_weather_data(38.8977, -77.0365)

    assert result.retrieval_status == WeatherRetrievalStatus.SUCCESS
    assert result.forecast_error is None
    assert result.alerts_error is None


def test_get_weather_data_alerts_failure(monkeypatch):
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_nws_location",
        lambda lat, lon: mock_location(),
    )
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_hourly_forecast",
        lambda location: [],
    )

    def mock_alerts(lat, lon):
        raise requests.RequestException("Alerts service unavailable")

    monkeypatch.setattr(
        "src.data_sources.weather_client.get_active_alerts",
        mock_alerts,
    )

    result = get_weather_data(38.8977, -77.0365)

    assert result.retrieval_status == WeatherRetrievalStatus.PARTIAL
    assert result.forecast_error is None
    assert result.alerts_error == "Alerts service unavailable"
    assert result.forecast_periods == []


def test_get_weather_data_forecast_failure(monkeypatch):
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_nws_location",
        lambda lat, lon: mock_location(),
    )

    def mock_forecast(location):
        raise requests.RequestException("Forecast service unavailable")

    monkeypatch.setattr(
        "src.data_sources.weather_client.get_hourly_forecast",
        mock_forecast,
    )
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_active_alerts",
        lambda lat, lon: [],
    )

    result = get_weather_data(38.8977, -77.0365)

    assert result.retrieval_status == WeatherRetrievalStatus.PARTIAL
    assert result.forecast_error == "Forecast service unavailable"
    assert result.alerts_error is None
    assert result.alerts == []


def test_get_weather_data_both_fail(monkeypatch):
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_nws_location",
        lambda lat, lon: mock_location(),
    )

    def mock_forecast(location):
        raise requests.RequestException("Forecast service unavailable")

    def mock_alerts(lat, lon):
        raise requests.RequestException("Alerts service unavailable")

    monkeypatch.setattr(
        "src.data_sources.weather_client.get_hourly_forecast",
        mock_forecast,
    )
    monkeypatch.setattr(
        "src.data_sources.weather_client.get_active_alerts",
        mock_alerts,
    )

    result = get_weather_data(38.8977, -77.0365)

    assert result.retrieval_status == WeatherRetrievalStatus.FAILED
    assert result.forecast_error == "Forecast service unavailable"
    assert result.alerts_error == "Alerts service unavailable"


def test_get_weather_data_location_failure(monkeypatch):
    def mock_location(lat, lon):
        raise requests.RequestException("NWS location service unavailable")

    monkeypatch.setattr(
        "src.data_sources.weather_client.get_nws_location",
        mock_location,
    )

    result = get_weather_data(38.8977, -77.0365)

    assert result.retrieval_status == WeatherRetrievalStatus.FAILED
    assert result.forecast_periods == []
    assert result.alerts == []
    assert result.forecast_error is not None
    assert result.alerts_error is not None
