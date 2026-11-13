import pytest
from datetime import datetime
from pydantic import ValidationError

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


# @pytest.mark.parametrize(
#     "status",
#     [
#         VerificationStatus.VERIFIED,
#         VerificationStatus.UNVERIFIED,
#         VerificationStatus.CONFLICTING,
#         VerificationStatus.STALE,
#     ]
# )


def test_valid_source_reference(valid_source_reference_data):
    t = SourceReference(**valid_source_reference_data)
    assert t.source_id == "sid01"
    assert t.source_name == "test_source"
    assert t.source_type == "website"
    assert str(t.url) == "https://source.com/"
    assert t.retrieved_at == datetime(2026, 11, 7, 10, 0)
    assert t.reliability == 0.9
    assert t.verification_status == VerificationStatus.VERIFIED


def test_source_reference_reliability_lt0(valid_source_reference_data):
    data = valid_source_reference_data.copy()
    data["reliability"] = -0.1

    with pytest.raises(ValidationError):
        SourceReference(**data)


def test_source_reference_reliability_gt1(valid_source_reference_data):
    data = valid_source_reference_data.copy()
    data["reliability"] = 1.1

    with pytest.raises(ValidationError):
        SourceReference(**data)

def test_source_reference_reliability_eq0(valid_source_reference_data):
    data = valid_source_reference_data.copy()
    data["reliability"] = 0
    t = SourceReference(**data)
    assert t.reliability == 0


def test_source_reference_reliability_eq1(valid_source_reference_data):
    data = valid_source_reference_data.copy()
    data["reliability"] = 1
    t = SourceReference(**data)
    assert t.reliability == 1


def test_source_reference_invalid_url(valid_source_reference_data):
    data = valid_source_reference_data.copy()
    data["url"] = "source.com"

    with pytest.raises(ValidationError):
        SourceReference(**data)


def test_source_reference_valid_url(valid_source_reference_data):
    t = SourceReference(**valid_source_reference_data)
    assert str(t.url) == "https://source.com/"


def test_source_reference_verification_status_valid(valid_source_reference_data):
    t = SourceReference(**valid_source_reference_data)
    assert t.verification_status == VerificationStatus.VERIFIED


def test_source_reference_verification_status_invalid(valid_source_reference_data):

    data = valid_source_reference_data.copy()
    data["verification_status"] = "Good"

    with pytest.raises(ValidationError):
        SourceReference(**data)


def test_source_reference_missing_required_field(valid_source_reference_data):
    data = valid_source_reference_data.copy()
    del data["source_name"]

    with pytest.raises(ValidationError):
        SourceReference(**data)


# def test_source_reference_verification_status(valid_source_reference_data, status):
#     data = valid_source_reference_data.copy()
#     data["verification_status"] = status

#     t = SourceReference(**data)

#     assert t.verification_status == status
