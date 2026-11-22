
from datetime import date, datetime

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.agent_workflow import (
    Constraint,
    ConstraintPriority,
    ConstraintType,
)
from src.models.validation import (
    IssueType,
    ValidationStatus,
)
from src.workflows.multi_agent_recovery import (
    validate_mandatory_activity_preservation,
)


def make_activity(
    activity_id="national_gallery",
    name="National Gallery of Art",
    mandatory=True,
):
    return Activity(
        activity_id=activity_id,
        name=name,
        location="Washington, DC",
        start_time=datetime(2026, 11, 7, 10, 0),
        duration_minutes=90,
        mandatory=mandatory,
        indoor=True,
    )


def make_itinerary(activities):
    return Itinerary(
        itinerary_id="test_itinerary",
        destination="Washington, DC",
        itinerary_date=date(2026, 11, 7),
        activities=activities,
        travel_legs=[],
    )


def make_constraint(
    value="National Gallery of Art",
    constraint_type=ConstraintType.MANDATORY,
    category="activity",
):
    return Constraint(
        constraint_id="constraint_001",
        description="Visit the National Gallery of Art",
        constraint_type=constraint_type,
        category=category,
        priority=ConstraintPriority.HIGH,
        value=value,
    )


def test_original_mandatory_activity_is_preserved():
    activity = make_activity()

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([activity]),
        proposed_itinerary=make_itinerary([activity.model_copy()]),
        mandatory_constraints=[],
    )

    assert result.status == ValidationStatus.VALID
    assert result.issues == []


def test_original_mandatory_activity_cannot_be_removed():
    activity = make_activity()

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([activity]),
        proposed_itinerary=make_itinerary([]),
        mandatory_constraints=[],
    )

    assert result.status == ValidationStatus.INVALID
    assert any(
        issue.issue_type == IssueType.MANDATORY_ACTIVITY_NOT_PRESERVED
        for issue in result.issues
    )
    assert "national_gallery" in result.issues[0].activity_ids


def test_original_mandatory_activity_cannot_become_non_mandatory():
    original_activity = make_activity(mandatory=True)
    proposed_activity = make_activity(mandatory=False)

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([original_activity]),
        proposed_itinerary=make_itinerary([proposed_activity]),
        mandatory_constraints=[],
    )

    assert result.status == ValidationStatus.INVALID
    assert any(
        issue.issue_type == IssueType.MANDATORY_ACTIVITY_NOT_PRESERVED
        for issue in result.issues
    )


def test_mandatory_constraint_matches_activity_name_case_insensitively():
    activity = make_activity()

    constraint = make_constraint(
        value="  NATIONAL GALLERY OF ART  "
    )

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([]),
        proposed_itinerary=make_itinerary([activity]),
        mandatory_constraints=[constraint],
    )

    assert result.status == ValidationStatus.VALID
    assert result.issues == []


def test_mandatory_constraint_matches_activity_id():
    activity = make_activity()

    constraint = make_constraint(value="NATIONAL_GALLERY")

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([]),
        proposed_itinerary=make_itinerary([activity]),
        mandatory_constraints=[constraint],
    )

    assert result.status == ValidationStatus.VALID
    assert result.issues == []


def test_missing_mandatory_constraint_match_is_invalid():
    constraint = make_constraint(value="National Gallery of Art")

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([]),
        proposed_itinerary=make_itinerary([]),
        mandatory_constraints=[constraint],
    )

    assert result.status == ValidationStatus.INVALID
    assert len(result.issues) == 1
    assert "no exact match" in result.issues[0].description


def test_ambiguous_mandatory_constraint_match_is_invalid():
    first_activity = make_activity(
        activity_id="gallery_1",
        name="National Gallery of Art",
        mandatory=False,
    )
    second_activity = make_activity(
        activity_id="gallery_2",
        name="National Gallery of Art",
        mandatory=False,
    )

    constraint = make_constraint(value="National Gallery of Art")

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([]),
        proposed_itinerary=make_itinerary(
            [first_activity, second_activity]
        ),
        mandatory_constraints=[constraint],
    )

    assert result.status == ValidationStatus.INVALID
    assert len(result.issues) == 1
    assert "ambiguous" in result.issues[0].description


def test_flexible_constraint_is_not_treated_as_mandatory():
    constraint = make_constraint(
        value="Activity that does not exist",
        constraint_type=ConstraintType.FLEXIBLE,
    )

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([]),
        proposed_itinerary=make_itinerary([]),
        mandatory_constraints=[constraint],
    )

    assert result.status == ValidationStatus.VALID
    assert result.issues == []


def test_non_activity_mandatory_constraint_is_not_matched_as_activity():
    constraint = make_constraint(
        value="indoor",
        category="activity_type",
    )

    result = validate_mandatory_activity_preservation(
        original_itinerary=make_itinerary([]),
        proposed_itinerary=make_itinerary([]),
        mandatory_constraints=[constraint],
    )

    assert result.status == ValidationStatus.VALID
    assert result.issues == []
