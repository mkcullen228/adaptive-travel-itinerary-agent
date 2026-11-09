from datetime import datetime, date

from src.models.activity import Activity
from src.models.itinerary import Itinerary
from src.models.validation import ValidationStatus, IssueType
from src.models.travel import TravelLeg, TravelEstimate
from src.validation.schedule_validator import (check_activity_overlaps, get_selected_travel_estimate, 
                                               check_travel_time_feasibility, validate_itinerary)


def test_activities_without_overlap():
    # Create two activities that do not overlap
    # Create an itinerary containing them
    # Run the validator
    # Assert that the result is VALID
    t1 = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 30),
                duration_minutes=90,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ]
    )

    r = check_activity_overlaps(t1)
    assert r.status == ValidationStatus.VALID


def test_activities_with_overlap():
    # Create two activities that overlap
    # Create an itinerary containing them
    # Run the validator
    # Assert that the result is INVALID
    # Assert that the issue identifies both activity IDs

    t1 = Itinerary(
            itinerary_id="Fun Day Out",
            destination="Washington, DC", 
            itinerary_date=date(2026, 11, 7),
            activities=[
                Activity(
                    activity_id="activity_002",
                    name="Smithsonian's National Air and Space Museum",
                    location="Washington, DC",
                    start_time=datetime(2026, 11, 7, 11, 0),
                    duration_minutes=90,
                ),
                Activity(
                    activity_id="activity_001",
                    name="National Gallery of Art",
                    location="Washington, DC",
                    start_time=datetime(2026, 11, 7, 10, 0),
                    duration_minutes=90,
                ),
            ]
        )
    
    r = check_activity_overlaps(t1)
    assert r.status == ValidationStatus.INVALID
    assert len(r.issues) == 1
    assert r.issues[0].activity_ids == [
        "activity_001",
        "activity_002"
    ]
    assert r.issues[0].issue_type == "activity_overlap"


def test_activities_starting_at_same_time():
    # Create two activities starting at 10:00
    # Run the validator
    # Assert INVALID
    t1 = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ]
    )
        
    r = check_activity_overlaps(t1)
    assert r.status == "invalid"
    assert len(r.issues) == 1
    assert set(r.issues[0].activity_ids) == {
        "activity_001",
        "activity_002"
    }
    assert r.issues[0].issue_type == "activity_overlap"


def test_selected_travel_estimate():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=12,
                    source="manual_test_data",
                    ), 
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )

    result = get_selected_travel_estimate(
        itinerary,
        "activity_001",
        "activity_002"
    )

    assert result is not None
    assert result.mode == "walking"
    assert result.duration_minutes == 12


def test_selected_travel_estimate_missing_mode():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )

    result = get_selected_travel_estimate(
        itinerary,
        "activity_001",
        "activity_002"
    )

    assert result is None


def test_selected_travel_leg_not_found():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        )

    result = get_selected_travel_estimate(
        itinerary,
        "activity_001",
        "activity_002"
    )

    assert result is None


def test_sufficient_travel_time():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=12,
                    source="manual_test_data",
                    ), 
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )

    result = check_travel_time_feasibility(itinerary)
    assert result.status == ValidationStatus.VALID
    assert len(result.issues) == 0


def test_insufficient_travel_time():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=15,
                    source="manual_test_data",
                    ), 
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )

    result = check_travel_time_feasibility(itinerary)
    assert result.status == ValidationStatus.INVALID
    assert result.issues[0].issue_type == IssueType.INSUFFICIENT_TRAVEL_TIME


def test_missing_selected_travel_estimate():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )

    result = check_travel_time_feasibility(itinerary)
    assert result.status == ValidationStatus.INCOMPLETE
    assert result.issues[0].issue_type == IssueType.MISSING_TRAVEL_ESTIMATE


def test_no_activities_to_validate():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[],
        travel_legs = []
        )

    result = check_travel_time_feasibility(itinerary)
    assert result.status == ValidationStatus.VALID


def test_validate_itinerary_valid():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=12,
                    source="manual_test_data",
                    ), 
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )
    
    result = validate_itinerary(itinerary)
    assert result.status == ValidationStatus.VALID
    assert len(result.issues) == 0


def test_validate_itinerary_invalid():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=15,
                    source="manual_test_data",
                    ), 
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )
    
    result = validate_itinerary(itinerary)
    assert result.status == ValidationStatus.INVALID
    assert result.issues[0].issue_type == IssueType.INSUFFICIENT_TRAVEL_TIME
    assert len(result.issues) == 1


def test_validate_itinerary_incomplete():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
        ],
        travel_legs = [TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )
    
    result = validate_itinerary(itinerary)
    assert result.status == ValidationStatus.INCOMPLETE
    assert result.issues[0].issue_type == IssueType.MISSING_TRAVEL_ESTIMATE
    assert len(result.issues) == 1


def test_validate_itinerary_invalid_with_multiple_issues():
    itinerary = Itinerary(
        itinerary_id="Fun Day Out",
        destination="Washington, DC", 
        itinerary_date=date(2026, 11, 7),
        activities=[
            Activity(
                activity_id="activity_002",
                name="Smithsonian's National Air and Space Museum",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 11, 42),
                duration_minutes=60,
            ),
            Activity(
                activity_id="activity_001",
                name="National Gallery of Art",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 10, 0),
                duration_minutes=90,
            ),
            Activity(
                activity_id="activity_003",
                name="Coffee Shop",
                location="Washington, DC",
                start_time=datetime(2026, 11, 7, 12, 30),
                duration_minutes=90,
            ),
        ],
        travel_legs = [
            TravelLeg(
            origin_activity_id="activity_001",
            destination_activity_id="activity_002",
            estimates=[
                TravelEstimate(
                    mode="driving",
                    duration_minutes=8,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            ), 
            TravelLeg(
            origin_activity_id="activity_002",
            destination_activity_id="activity_003",
            estimates=[
                TravelEstimate(
                    mode="walking",
                    duration_minutes=12,
                    source="manual_test_data",
                    )], 
            selected_mode="walking"
            )]
        )
    
    result = validate_itinerary(itinerary)
    issue_types = {issue.issue_type for issue in result.issues}
    assert result.status == ValidationStatus.INVALID
    assert IssueType.ACTIVITY_OVERLAP in issue_types
    assert IssueType.MISSING_TRAVEL_ESTIMATE in issue_types
    assert len(result.issues) == 3
