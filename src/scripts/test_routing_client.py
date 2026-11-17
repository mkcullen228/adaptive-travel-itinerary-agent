from src.data_sources.routing_client import get_walking_route

origin = (-77.0502, 38.8895)
destination = (-77.0434, 38.8906)

print("Testing OpenRouteService...")
print(f"Origin: {origin}")
print(f"Destination: {destination}")

try:
    result = get_walking_route(
        origin_coordinates=origin,
        destination_coordinates=destination,
    )

    print("\nRoute successful!")
    print(f"Duration: {result['duration_seconds']} seconds")
    print(f"Distance: {result['distance_meters']} meters")

except Exception as error:
    print("\nRoute failed!")
    print(type(error).__name__)
    print(error)
    