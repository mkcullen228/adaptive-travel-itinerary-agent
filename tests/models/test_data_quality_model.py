import pytest
from pydantic import ValidationError

from src.models.data_quality import DataQualityAssessment

@pytest.fixture
def valid_data_quality_data():
    return {
    "reliability_score": 0.8,
    "freshness_score": 1,
    "completeness_score": 0,
    }

def test_valid_assessment(valid_data_quality_data):
    t = DataQualityAssessment(**valid_data_quality_data)

    assert t.reliability_score == 0.8
    assert t.freshness_score == 1
    assert t.completeness_score == 0


def test_assessment_low_value(valid_data_quality_data):
    data = valid_data_quality_data.copy()
    data["freshness_score"] = -1

    with pytest.raises(ValidationError):
        DataQualityAssessment(**data)


def test_assessment_high_value(valid_data_quality_data):
    data = valid_data_quality_data.copy()
    data["freshness_score"] = 1.1

    with pytest.raises(ValidationError):
        DataQualityAssessment(**data)