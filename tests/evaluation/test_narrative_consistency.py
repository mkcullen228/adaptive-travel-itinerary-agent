
from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.agent_workflow import RecoveryOption
from src.evaluation.narrative_consistency import (
    evaluate_narrative_consistency,
)


def make_activity(activity_id, name, hour, minute=0):
    return Activity(
        activity_id=activity_id,
        name=name,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, hour, minute),
        duration_minutes=60,
    )


def make_itinerary(activities):
    return Itinerary(
        itinerary_id="test",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities,
    )


def make_proposal(proposed, rationale):
    return RecoveryOption.model_construct(
        proposed_itinerary=proposed,
        rationale=rationale,
    )


def test_correct_activity_time_is_consistent():
    original = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    proposed = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 10, 50)
    ])

    proposal = make_proposal(
        proposed,
        "The WWII Memorial is scheduled for 10:50 AM.",
    )

    result = evaluate_narrative_consistency(original, proposal)

    assert result["status"] == "consistent"
    assert result["checked_claim_count"] == 1
    assert result["inconsistent_claim_count"] == 0


def test_incorrect_activity_time_is_inconsistent():
    original = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    proposed = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    proposal = make_proposal(
        proposed,
        "The WWII Memorial is scheduled for 10:50 AM.",
    )

    result = evaluate_narrative_consistency(original, proposal)

    assert result["status"] == "inconsistent"
    assert result["checked_claim_count"] == 1
    assert result["inconsistent_claim_count"] == 1
    assert result["inconsistent_claims"][0]["actual_start_time"] == "3:10 PM"


def test_no_verifiable_time_claim_is_inconclusive():
    original = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    proposed = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    proposal = make_proposal(
        proposed,
        "The WWII Memorial remains in the itinerary.",
    )

    result = evaluate_narrative_consistency(original, proposal)

    assert result["status"] == "inconclusive"
    assert result["checked_claim_count"] == 0


def test_multiple_activities_in_sentence_are_not_assumed():
    original = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10),
        make_activity("lincoln_memorial", "Lincoln Memorial", 16, 0),
    ])

    proposed = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10),
        make_activity("lincoln_memorial", "Lincoln Memorial", 16, 0),
    ])

    proposal = make_proposal(
        proposed,
        "The WWII Memorial and Lincoln Memorial are scheduled for 10:50 AM.",
    )

    result = evaluate_narrative_consistency(original, proposal)

    assert result["status"] == "inconclusive"
    assert result["checked_claim_count"] == 0


def test_evaluator_does_not_modify_itineraries():
    original = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    proposed = make_itinerary([
        make_activity("wwii_memorial", "WWII Memorial", 15, 10)
    ])

    original_start = original.activities[0].start_time
    proposed_start = proposed.activities[0].start_time

    proposal = make_proposal(
        proposed,
        "The WWII Memorial is scheduled for 10:50 AM.",
    )

    evaluate_narrative_consistency(original, proposal)

    assert original.activities[0].start_time == original_start
    assert proposed.activities[0].start_time == proposed_start



def test_coordinated_activity_time_claims_are_checked_individually():
    original = make_itinerary([
        make_activity("wwii_memorial", "World War II Memorial", 15, 10),
        make_activity("lincoln_memorial", "Lincoln Memorial", 16, 0),
    ])

    proposed = make_itinerary([
        make_activity("wwii_memorial", "World War II Memorial", 15, 10),
        make_activity("lincoln_memorial", "Lincoln Memorial", 16, 0),
    ])

    proposal = make_proposal(
        proposed,
        (
            "The World War II Memorial is rescheduled to start "
            "at 10:50 AM, and the Lincoln Memorial is rescheduled "
            "to start at 11:40 AM."
        ),
    )

    result = evaluate_narrative_consistency(original, proposal)

    assert result["status"] == "inconsistent"
    assert result["checked_claim_count"] == 2
    assert result["inconsistent_claim_count"] == 2

    assert {
        claim["activity_id"]: claim["claimed_start_time"]
        for claim in result["inconsistent_claims"]
    } == {
        "wwii_memorial": "10:50 AM",
        "lincoln_memorial": "11:40 AM",
    }
