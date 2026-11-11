from pydantic import BaseModel, Field


class DataQualityAssessment(BaseModel):
    """
    Scoring Notes: 
    Reliability Score: 
    - 1.0:  Official source or authoritative government data
    - 0.85:  Established, reputable data provider
    - 0.65:  Secondary source with reasonable credibility
    - 0.40:  Unverified or informal source

    Freshness (age of information):
    - Up to and including 1 day: 1.0
    - More than 1 day through 7 days: 0.85
    - More than 7 days through 30 days: 0.65
    - More than 30 days through 90 days: 0.40
    - More than 90 days: 0.20

    Completeness:
    - 1.0: All required information is available.
    - 0.5:  Some information is missing.
    - 0.0:  Critical information is missing.

    reliability_score: float - Reliability score from 0 to 1
    freshness_score: float - Freshness score from 0 to 1
    completeness_score: float - Completeness score from 0 to 1
    """

    reliability_score: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
