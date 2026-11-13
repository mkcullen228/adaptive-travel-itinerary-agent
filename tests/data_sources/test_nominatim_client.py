from src.data_sources.nominatim_client import (coordinates_valid, validate_location_candidate, 
                                               select_location_candidate, LocationMatchStatus, 
                                               coordinates_within_expected_area)

def test_valid_coordinates():
    candidate = {
        "lat": "38.8913116",
        "lon": "-77.0199045"
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is True


def test_coordinates_lat_invalid():
    candidate = {
        "lat": "98.8913116",
        "lon": "-77.0199045"
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is False
    assert result["longitude_valid"] is True


def test_coordinates_missing_lon():
    candidate = {
        "lat": "35.8913116",
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is False


def test_coordinates_missing_lat():
    candidate = {
        "lon": "-77.0199045"
    }

    result = coordinates_valid(candidate)

    assert result["latitude_valid"] is False
    assert result["longitude_valid"] is True


def test_coordinates_within_expected_area_inside():
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91

    candidate = {
        "lat": "38.8913116",
        "lon": "-77.0199045"
    }

    result = coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon)

    assert result["latitude_within_area"] is True
    assert result["longitude_within_area"] is True


def test_coordinates_within_expected_area_outside():
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91

    candidate = {
        "lat": "88.8913116",
        "lon": "-177.0199045"
    }

    result = coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon)

    assert result["latitude_within_area"] is False
    assert result["longitude_within_area"] is False


def test_coordinates_within_expected_area_missing_one():
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91

    candidate = {"lat": "38.8913116"}

    result = coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon)

    assert result["latitude_within_area"] is True
    assert result["longitude_within_area"] is False


def test_coordinates_within_expected_area_missing_both():
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91

    candidate = {}

    result = coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon)

    assert result["latitude_within_area"] is False
    assert result["longitude_within_area"] is False


def test_coordinates_within_expected_area_equal():
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91

    candidate = {
        "lat": "38.80",
        "lon": "-77.12"
    }   

    result = coordinates_within_expected_area(candidate, min_lat, max_lat, min_lon, max_lon)

    assert result["latitude_within_area"] is True
    assert result["longitude_within_area"] is True


def test_incorrect_feature_type():
    candidate = {
        "name": "National Museum of Natural History",
        "display_name": "National Museum of Natural History, Washington, District of Columbia",
        "lat": "38.8912450",
        "lon": "-77.0",
        "type": "restaurant"
    }

    result = validate_location_candidate(
        candidate,
        "National Museum of Natural History",
        "Washington, DC",
        "museum", 
        38.80,
        38.995,
        -77.12,
        -76.91,
        )

    assert result["name_match"] is True
    assert result["location_match"] is True
    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is True
    assert result["feature_type_match"] is False
    assert result["latitude_within_area"] is True
    assert result["longitude_within_area"] is True  
    assert result["valid"] is False


def test_incorrect_feature_type():
    candidate = {
        "name": "National Museum of Natural History",
        "display_name": "National Museum of Natural History, Washington, District of Columbia",
        "lat": "40.8912450",
        "lon": "-90.0",
        "type": "restaurant"
    }

    result = validate_location_candidate(
        candidate,
        "National Museum of Natural History",
        "Washington, DC",
        "museum", 
        38.80,
        38.995,
        -77.12,
        -76.91,
        )

    assert result["name_match"] is True
    assert result["location_match"] is True
    assert result["latitude_valid"] is True
    assert result["longitude_valid"] is True
    assert result["feature_type_match"] is False
    assert result["latitude_within_area"] is False
    assert result["longitude_within_area"] is False  
    assert result["valid"] is False


def test_select_location_candidate_no_candidate():
    candidates=[]
    expected_name = "National Museum of Natural History"
    expected_location = "Washington, DC"
    expected_types = ["museum"]
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91
    
    result = select_location_candidate(candidates, expected_name, expected_location, expected_types, 
                                       min_lat, max_lat, min_lon, max_lon)

    assert(result['status'] == LocationMatchStatus.NO_CANDIDATE_MATCHES)
    assert(result['selected_candidate'] is None)
    assert(result['valid_candidates'] == [])
    assert(result['candidate_evaluations'] == [])


def test_select_location_candidate_no_match():
    candidates=[{
        'name': 'National Museum of Natural History', 
        'display_name': 'Museum of Natural History Pittsburgh PA', 
        'lat': '38.8912',
        'lon': '-77.0261',
        'type': 'museum'
    }]
    expected_name = "National Museum of Natural History"
    expected_location = "Washington, DC"
    expected_types = ["monument"]
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91
    
    result = select_location_candidate(candidates, expected_name, expected_location, expected_types, 
                                       min_lat, max_lat, min_lon, max_lon)

    assert(result['status'] == LocationMatchStatus.NO_VALID_MATCHES)
    assert(result['selected_candidate'] is None)
    assert(result['valid_candidates'] == [])
    assert(result['candidate_evaluations'] == [
        {'candidate': {
            'name': 'National Museum of Natural History', 
            'display_name': 'Museum of Natural History Pittsburgh PA', 
            'lat': '38.8912',
            'lon': '-77.0261',
            'type': 'museum'
         },
         'validation' : {
             'name_match': True,
             'location_match': False,
             'latitude_valid': True, 
             'longitude_valid': True, 
             'feature_type_match': False,
             'latitude_within_area': True,
             'longitude_within_area': True ,
             'valid': False
               }, 
         'failure_reasons': ['location_match', 'feature_type_match']
        }])
    assert result["candidate_evaluations"][0]["failure_reasons"] == ["location_match", "feature_type_match"]


def test_select_location_candidate_unique_match():
    candidates=[{
        'name': 'National Museum of Natural History', 
        'display_name': 'National Museum of Natural History Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0261',
        'type': 'museum'
    }, 
    {
        'name': 'National Museum of Natural History', 
        'display_name': 'National Museum of Natural History San Francisco, CA', 
        'lat': '38', 
        'lon': '90', 
        'type': 'museum'
    }]

    expected_name = "National Museum of Natural History"
    expected_location = "Washington, DC"
    expected_types = ["museum"]
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91
    
    result = select_location_candidate(candidates, expected_name, expected_location, expected_types, 
                                       min_lat, max_lat, min_lon, max_lon)

    assert(result['status'] == LocationMatchStatus.UNIQUE_VALID_MATCH)
    assert(result['selected_candidate'] == {
        'name': 'National Museum of Natural History', 
        'display_name': 'National Museum of Natural History Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0261',
        'type': 'museum'
        })
    assert(result['valid_candidates'] == [{
        'name': 'National Museum of Natural History', 
        'display_name': 'National Museum of Natural History Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0261',
        'type': 'museum'
    }])
    assert(result['candidate_evaluations'] == [
        {'candidate': {
            'name': 'National Museum of Natural History', 
            'display_name': 'National Museum of Natural History Washington, DC', 
            'lat': '38.8912',
            'lon': '-77.0261',
            'type': 'museum'
         },
         'validation' : {
             'name_match': True,
             'location_match': True,
             'latitude_valid': True, 
             'longitude_valid': True, 
             'feature_type_match': True, 
             'latitude_within_area': True,
             'longitude_within_area': True,
             'valid': True
               }, 
         'failure_reasons': []
        }, 
        {'candidate': {
            'name': 'National Museum of Natural History', 
            'display_name': 'National Museum of Natural History San Francisco, CA', 
            'lat': '38', 
            'lon': '90', 
            'type': 'museum'
         },
         'validation' : {
             'name_match': True,
             'location_match': False,
             'latitude_valid': True, 
             'longitude_valid': True, 
             'feature_type_match': True, 
             'latitude_within_area': False,
             'longitude_within_area': False,
             'valid': False
               }, 
            'failure_reasons': ['location_match', 'latitude_within_area', 'longitude_within_area']
        },
    ])
    assert result["candidate_evaluations"][0]["failure_reasons"] == []


def test_multiple_expected_types():
    candidate = {
        "name": "Lincoln Memorial",
        "display_name": "Lincoln Memorial, Washington, District of Columbia",
        "lat": "38.8893",
        "lon": "-77.0502",
        "type": "park"
    }

    result = validate_location_candidate(
        candidate,
        "Lincoln Memorial",
        "Washington DC",
        ["memorial", "park"],
        38.80,
        38.995,
        -77.12,
        -76.91
    )

    assert result["feature_type_match"] is True
    assert result["valid"] is True

def test_select_location_candidate_multiple_match():
    candidates=[{
        'name': 'National Museum of Natural History', 
        'display_name': 'National Museum of Natural History Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0261',
        'type': 'museum'
    }, 
    {
        'name': 'National Museum of Natural History', 
        'display_name': 'Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0161',
        'type': 'museum'
    }]
    
    expected_name = "National Museum of Natural History"
    expected_location = "Washington, DC"
    expected_types = ["museum"]
    min_lat = 38.80
    max_lat = 38.995
    min_lon = -77.12
    max_lon = -76.91
    
    result = select_location_candidate(candidates, expected_name, expected_location, expected_types, 
                                       min_lat, max_lat, min_lon, max_lon)

    assert(result['status'] == LocationMatchStatus.MULTIPLE_VALID_MATCHES)
    assert(result['selected_candidate'] is None)
    assert(result['valid_candidates'] == [{
        'name': 'National Museum of Natural History', 
        'display_name': 'National Museum of Natural History Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0261',
        'type': 'museum'
    },  
    {
        'name': 'National Museum of Natural History', 
        'display_name': 'Washington, DC', 
        'lat': '38.8912',
        'lon': '-77.0161',
        'type': 'museum'
    }])
    assert(result['candidate_evaluations'] == [
            {'candidate': {
                'name': 'National Museum of Natural History', 
                'display_name': 'National Museum of Natural History Washington, DC', 
                'lat': '38.8912',
                'lon': '-77.0261',
                'type': 'museum'
             },
             'validation' : {
                 'name_match': True,
                 'location_match': True,
                 'latitude_valid': True, 
                 'longitude_valid': True, 
                 'feature_type_match': True, 
                 'latitude_within_area': True,
                 'longitude_within_area': True, 
                 'valid': True
                   }, 
              'failure_reasons': []
            }, 
            {'candidate': {
                'name': 'National Museum of Natural History', 
                'display_name': 'Washington, DC', 
                'lat': '38.8912',
                'lon': '-77.0161',
                'type': 'museum'
             },
             'validation' : {
                 'name_match': True,
                 'location_match': True,
                 'latitude_valid': True, 
                 'longitude_valid': True, 
                 'feature_type_match': True, 
                 'latitude_within_area': True,
                 'longitude_within_area': True ,
                 'valid': True
                   }, 
             'failure_reasons': []
            }, 
        
        ])

