import pytest
import requests
from unittest.mock import Mock, patch
from src.data_sources.routing_client import get_walking_route


def test_get_walking_route():
    origin = (-77.0199045, 38.8913116)
    destination = (-77.0300205, 38.8912397)

    result = get_walking_route(origin, destination)

    assert result["duration_seconds"] > 0
    assert result["distance_meters"] > 0

    print(result)


@patch("src.data_sources.routing_client.requests.post")
def test_get_walking_route_success(mock_post):
    mock_response = Mock()

    mock_response.json.return_value = {
        "routes": [
            {
                "summary": {
                    "duration": 683.5,
                    "distance": 949.3
                }
            }
        ]
    }

    mock_post.return_value = mock_response

    origin = (-77.0199045, 38.8913116)
    destination = (-77.0300205, 38.8912397)

    result = get_walking_route(origin, destination)

    assert result["duration_seconds"] == 683.5
    assert result["distance_meters"] == 949.3

    # Verify the API request
    call_args = mock_post.call_args

    # Verify endpoint
    assert call_args.args[0] == (
        "https://api.heigit.org/openrouteservice/v2/directions/foot-walking"
    )

    # Verify coordinates and their order
    sent_payload = call_args.kwargs["json"]

    assert sent_payload["coordinates"] == [
        [-77.0199045, 38.8913116],
        [-77.0300205, 38.8912397]
    ]

    # Verify authentication header exists
    sent_headers = call_args.kwargs["headers"]

    assert "Authorization" in sent_headers
    assert sent_headers["Content-Type"] == "application/json"

    mock_post.assert_called_once()



@patch("src.data_sources.routing_client.requests.post")
def test_get_walking_route_http_error(mock_post):
    mock_response = Mock()

    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    mock_post.return_value = mock_response

    origin = (-77.0199045, 38.8913116)
    destination = (-77.0300205, 38.8912397)

    with pytest.raises(RuntimeError, match="HTTP 429"):
        get_walking_route(origin, destination)


@patch("src.data_sources.routing_client.requests.post")
def test_get_walking_route_timeout(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout(
        "Request timed out"
    )

    origin = (-77.0199045, 38.8913116)
    destination = (-77.0300205, 38.8912397)

    with pytest.raises(RuntimeError, match="Unable to retrieve walking route"):
        get_walking_route(origin, destination)
