import pytest
from datetime import datetime, timezone, timedelta
from src.validation.data_quality import (calculate_freshness_score, calculate_reliability_score, 
                                         calculate_completeness_score, assess_data_quality)

def test_received_same_day():
    retrieved_at = datetime.now(timezone.utc) - timedelta(days = 0)
    score = calculate_freshness_score(retrieved_at)
    assert score == 1.0


def test_received_5_days_old():
    retrieved_at = datetime.now(timezone.utc) - timedelta(days = 5)
    score = calculate_freshness_score(retrieved_at)
    assert score == 0.85


def test_received_exactly_7_days_old():
    retrieved_at = datetime.now(timezone.utc) - timedelta(days=7) + timedelta(seconds=1)
    score = calculate_freshness_score(retrieved_at)
    assert score == 0.85


def test_received_45_days_old():
    retrieved_at = datetime.now(timezone.utc) - timedelta(days = 45)
    score = calculate_freshness_score(retrieved_at)
    assert score == 0.4


def test_received_100_days_old():
    retrieved_at = datetime.now(timezone.utc) - timedelta(days = 100)
    score = calculate_freshness_score(retrieved_at)
    assert score == 0.2


def test_received_future():
    retrieved_at = datetime.now(timezone.utc) + timedelta(days = 2)
    with pytest.raises(ValueError):
        calculate_freshness_score(retrieved_at)


def test_reliability_mid_range():
    score = calculate_reliability_score(0.85)
    assert score == 0.85


def test_reliability_high_bound():
    score = calculate_reliability_score(1.0)
    assert score == 1


def test_reliability_low_bound():
    score = calculate_reliability_score(0)
    assert score == 0


def test_reliability_invalid_low():
    with pytest.raises(ValueError):
        calculate_reliability_score(-0.1)


def test_reliability_invalid_high():
    with pytest.raises(ValueError):
        calculate_reliability_score(1.1)


def test_calculate_completeness_all_required():
    required_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    available_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    score = calculate_completeness_score(required_fields, available_fields)
    assert score == 1.0


def test_calculate_completeness_some_required():
    required_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    available_fields = ['source_name', 'source_type', 'url']
    score = calculate_completeness_score(required_fields, available_fields)
    assert score == 0.5


def test_calculate_completeness_none_required():
    required_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    available_fields = []
    score = calculate_completeness_score(required_fields, available_fields)
    assert score == 0


def test_calculate_completeness_extra_required():
    required_fields = ['source_name', 'source_type', 'url']
    available_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    score = calculate_completeness_score(required_fields, available_fields)
    assert score == 1.0


def test_calculate_completeness_invalid_empty_required():
    required_fields = []
    available_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    with pytest.raises(ValueError):
        calculate_completeness_score(required_fields, available_fields)


def test_valid_assess_data_quality():
    reliability = 0.85
    received_at = datetime.now(timezone.utc)
    required_fields = ['source_name', 'source_type', 'url', 'retrieved_at']
    available_fields = ['source_name', 'source_type']

    quality_assessment = assess_data_quality(reliability, received_at, 
                                             required_fields, available_fields)

    assert quality_assessment.reliability_score == 0.85 
    assert quality_assessment.freshness_score == 1.0
    assert quality_assessment.completeness_score == 0.5
