import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.attraction import Attraction
from src.models.source_reference import SourceReference, VerificationStatus


@pytest.fixture
def valid_source_reference_data():
    return {
        "source_id": "sid01",
        "source_name": "test_source",
        "source_type": "website",
        "url": "https://source.com",
        "retrieved_at": datetime(2026, 11, 7, 10, 0),
        "reliability": 0.9,
        "verification_status": VerificationStatus.VERIFIED
    }

@pytest.fixture
def valid_source_reference_data2():
    return {
        "source_id": "sid02",
        "source_name": "test_source2",
        "source_type": "website2",
        "url": "https://source2.com",
        "retrieved_at": datetime(2026, 11, 5, 10, 0),
        "reliability": 0.3,
        "verification_status": VerificationStatus.UNVERIFIED
    }

@pytest.fixture
def valid_attraction_data(valid_source_reference_data):
    return {
        "attraction_id":"id01",
        "name":"test_attraction",
        "address":"123 address washington, DC",
        "latitude":10,
        "longitude":10,
        "category":"museum",
        "indoor":True,
        "typical_duration_minutes":90,
        "source_references": [SourceReference(**valid_source_reference_data)]
    }


def test_valid_attraction(valid_attraction_data):
    t = Attraction(**valid_attraction_data)
    
    # Assert the name and duration
    assert t.attraction_id == "id01"
    assert t.name == "test_attraction"
    assert t.address == "123 address washington, DC"
    assert t.latitude == 10
    assert t.longitude == 10
    assert t.category == "museum"
    assert t.indoor is True
    assert t.typical_duration_minutes == 90
    # Verify nested SourceReference
    assert len(t.source_references) == 1
    assert isinstance(t.source_references[0], SourceReference)
    assert t.source_references[0].source_id == "sid01"


def test_attraction_negative_duration(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["typical_duration_minutes"] = -10

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_zero_duration(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["typical_duration_minutes"] = 0

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_latitude_gt90(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["latitude"] = 91

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_latitude_ltn90(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["latitude"] = -91

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_longitude_gt180(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["longitude"] = 181

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_longitude_lt180(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["longitude"] = -181

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_empty_source(valid_attraction_data):
    data = valid_attraction_data.copy()
    data["source_references"] = []
    t = Attraction(**data)
    assert t.source_references == []


def test_attraction_multiple_sources(valid_attraction_data, valid_source_reference_data, valid_source_reference_data2):
    data = valid_attraction_data.copy()
    data["source_references"] = [SourceReference(**valid_source_reference_data), 
                                 SourceReference(**valid_source_reference_data2)]
    t = Attraction(**data)
    assert len(t.source_references) == 2


def test_attraction_accepts_source_reference_dict(valid_attraction_data, valid_source_reference_data):
    data = valid_attraction_data.copy()
    data["source_references"] = [valid_source_reference_data]

    t = Attraction(**data)

    assert isinstance(t.source_references[0], SourceReference)
    assert t.source_references[0].source_id == "sid01"


def test_attraction_rejects_invalid_nested_source(valid_attraction_data):
    data = valid_attraction_data.copy()
    invalid_source = {
        "source_id": "sid03",
        "source_name": "bad_source",
        "source_type": "website",
        "url": "https://source.com",
        "retrieved_at": datetime(2026, 11, 7, 10, 0),
        "reliability": 1.5,
        "verification_status": VerificationStatus.VERIFIED
    }
    data["source_references"] = [invalid_source]

    with pytest.raises(ValidationError):
        Attraction(**data)


def test_attraction_default_source_lists_are_independent(valid_attraction_data):
    data = valid_attraction_data.copy()
    del data["source_references"]

    attraction1 = Attraction(**data)
    attraction2 = Attraction(**data)

    attraction1.source_references.append(
        SourceReference(
            source_id="sid01",
            source_name="test_source",
            source_type="website",
            url="https://source.com",
            retrieved_at=datetime(2026, 11, 7, 10, 0),
            reliability=0.9,
            verification_status=VerificationStatus.VERIFIED
        )
    )

    assert len(attraction1.source_references) == 1
    assert len(attraction2.source_references) == 0