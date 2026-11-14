# from src.data_sources.weather_client import get_weather_data

# weather = get_weather_data(38.8977, -77.0365)

# print(f"Retrieved: {weather.retrieved_at}")
# print(f"Forecast periods: {len(weather.forecast_periods)}")
# print(f"Active alerts: {len(weather.alerts)}")

# for period in weather.forecast_periods[:3]:
#     print(
#         period.start_time,
#         period.temperature,
#         period.short_forecast
#     )

# for alert in weather.alerts:
#     print(alert.event, alert.severity)


from pathlib import Path
import json

path = Path("data/venues/venue_sources.json").resolve()

print("Registry path:", path)

data = json.loads(path.read_text(encoding="utf-8"))

for venue in data:
    for source in venue["sources"]:
        print(source["source_id"], repr(source["url"]))
