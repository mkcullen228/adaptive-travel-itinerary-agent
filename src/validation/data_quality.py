from datetime import datetime, timezone
from src.models.data_quality import DataQualityAssessment


def calculate_freshness_score(retrieved_at: datetime) -> float:
    """Calculate a freshness score based on the age of retrieved information.
    
    Scoring Rubric:
    Freshness (days): 
    - 0–1 days: 1.0
    - 2–7 days: 0.85
    - 8–30 days: 0.65
    - 31–90 days: 0.40
    - Over 90 days: 0.20

    Returns Score between 0 - 1

    """

    now = datetime.now(timezone.utc)

    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)

    age_days = (now - retrieved_at).total_seconds() / 86400

    if age_days < 0:
        raise ValueError("Retrieved timestamp cannot be in the future.")

    if age_days <= 1:
        return 1.0
    elif age_days <= 7:
        return 0.85
    elif age_days <= 30:
        return 0.65
    elif age_days <= 90:
        return 0.40
    else:
        return 0.20


def calculate_reliability_score(reliability: float) -> float:
    """Return the source reliability score after validating its range.
    
    Reliability Score: 
    - 1.0: Official source or authoritative government data
    - 0.85: Established, reputable data provider
    - 0.65: Secondary source with reasonable credibility
    - 0.40: Unverified or informal source
    
     Returns Score between 0 - 1
    """

    if not 0 <= reliability <= 1:
        raise ValueError("Reliability must be between 0 and 1.")

    return reliability


def calculate_completeness_score(required_fields: list[str],
                                 available_fields: list[str]) -> float:
    """Calculate a completeness score based on required information available.
    
    Completeness:
    - 1.0: All required information is available.
    - 0.5:  Some information is missing.
    - 0.0:  Critical information is missing.
    """

    if not required_fields:
        raise ValueError("At least one required field must be specified.")

    available_count = sum(
        field in available_fields for field in required_fields
    )

    if available_count == len(required_fields):
        return 1.0
    elif available_count > 0:
        return 0.5
    else:
        return 0.0


def assess_data_quality(reliability: float, 
                        retrieved_at: datetime, 
                        required_fields: list[str], 
                        available_fields: list[str]) -> DataQualityAssessment:

    reliability_score = calculate_reliability_score(reliability)
    freshness_score = calculate_freshness_score(retrieved_at)
    completeness_score = calculate_completeness_score(required_fields, available_fields)

    return DataQualityAssessment(
        reliability_score = reliability_score,
        freshness_score = freshness_score,
        completeness_score = completeness_score,
        )
