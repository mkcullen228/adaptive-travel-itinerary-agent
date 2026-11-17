
import re
from datetime import datetime

from src.models.agent_workflow import RecoveryOption
from src.models.itinerary import Itinerary


TIME_PATTERN = re.compile(
    r"\b(\d{1,2}:\d{2}\s*(?:AM|PM))\b",
    flags=re.IGNORECASE,
)


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _format_local_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _split_into_clauses(sentence: str) -> list[str]:
    """Split coordinated claims while preserving activity-time pairs."""
    return re.split(r",\s+and\s+", sentence, flags=re.IGNORECASE)


def evaluate_narrative_consistency(
    original: Itinerary,
    proposal: RecoveryOption,
) -> dict:
    """
    Check explicit activity start-time claims in the rationale.

    Only checks clauses that mention exactly one proposed activity
    and contain a recognizable 12-hour clock time.
    """
    del original  # Reserved for future checks of claims about changes.

    rationale = proposal.rationale
    proposed = proposal.proposed_itinerary

    checked_claims = []
    inconsistent_claims = []

    sentences = re.split(r"(?<=[.!?])\s+", rationale)

    for sentence in sentences:
        clauses = _split_into_clauses(sentence)

        for clause in clauses:
            normalized_clause = _normalize_name(clause)

            mentioned_activities = [
                activity
                for activity in proposed.activities
                if _normalize_name(activity.name) in normalized_clause
            ]

            if len(mentioned_activities) != 1:
                continue

            activity = mentioned_activities[0]
            time_matches = TIME_PATTERN.findall(clause)

            if len(time_matches) != 1:
                continue

            claimed_time = time_matches[0].upper().replace("  ", " ")
            actual_time = _format_local_time(activity.start_time)

            claim = {
                "activity_id": activity.activity_id,
                "activity_name": activity.name,
                "claimed_start_time": claimed_time,
                "actual_start_time": actual_time,
            }

            checked_claims.append(claim)

            if claimed_time != actual_time.upper():
                inconsistent_claims.append(claim)

    if inconsistent_claims:
        status = "inconsistent"
    elif checked_claims:
        status = "consistent"
    else:
        status = "inconclusive"

    return {
        "status": status,
        "checked_claims": checked_claims,
        "inconsistent_claims": inconsistent_claims,
        "checked_claim_count": len(checked_claims),
        "inconsistent_claim_count": len(inconsistent_claims),
    }
