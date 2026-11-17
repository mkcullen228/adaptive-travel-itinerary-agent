from datetime import datetime, timezone
from src.models.agent_workflow import ExecutionEvent, ApprovalRecord, ApprovalStatus
from src.workflows.state_reducers import (append_execution_events, append_unique_strings, append_approval_records)


def make_event(event_id: str) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=event_id,
        stage="investigation",
        event_type="tool_call",
        description=f"Test event {event_id}",
    )


def test_append_execution_events():
    existing = [make_event("event_001")]
    updates = [make_event("event_002")]

    result = append_execution_events(existing, updates)

    assert [event.event_id for event in result] == [
        "event_001",
        "event_002",
    ]


def test_append_execution_events_prevents_existing_duplicates():
    existing = [
        make_event("event_001"),
        make_event("event_002"),
    ]
    updates = [
        make_event("event_002"),
        make_event("event_003"),
    ]

    result = append_execution_events(existing, updates)

    assert [event.event_id for event in result] == [
        "event_001",
        "event_002",
        "event_003",
    ]


def test_append_execution_events_does_not_mutate_inputs():
    existing = [make_event("event_001")]
    updates = [make_event("event_002")]

    append_execution_events(existing, updates)

    assert len(existing) == 1
    assert len(updates) == 1


def test_append_execution_events_prevents_duplicates_within_updates():
    existing = [make_event("event_001")]
    updates = [
        make_event("event_002"),
        make_event("event_002"),
        make_event("event_003"),
    ]

    result = append_execution_events(existing, updates)

    assert [event.event_id for event in result] == [
        "event_001",
        "event_002",
        "event_003",
    ]


def test_append_unique_strings():
    existing = ["Weather API unavailable"]
    updates = ["Routing failed"]

    result = append_unique_strings(existing, updates)

    assert result == [
        "Weather API unavailable",
        "Routing failed",
    ]


def test_append_unique_strings_prevents_duplicates():
    existing = ["Weather API unavailable"]
    updates = [
        "Weather API unavailable",
        "Routing failed",
        "Routing failed",
    ]

    result = append_unique_strings(existing, updates)

    assert result == [
        "Weather API unavailable",
        "Routing failed",
    ]


def test_append_unique_strings_does_not_mutate_inputs():
    existing = ["Warning 1"]
    updates = ["Warning 2"]

    append_unique_strings(existing, updates)

    assert existing == ["Warning 1"]
    assert updates == ["Warning 2"]


def make_approval_record(timestamp):
    return ApprovalRecord(
        option_id="option_001",
        status=ApprovalStatus.APPROVED,
        timestamp=timestamp,
        user_feedback="Approved",
    )


def test_append_approval_records():
    timestamp_1 = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
    timestamp_2 = datetime(2026, 11, 15, 10, 5, tzinfo=timezone.utc)

    existing = [make_approval_record(timestamp_1)]
    updates = [make_approval_record(timestamp_2)]

    result = append_approval_records(existing, updates)

    assert len(result) == 2


def test_append_approval_records_prevents_duplicates():
    timestamp = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)

    existing = [make_approval_record(timestamp)]
    updates = [make_approval_record(timestamp)]

    result = append_approval_records(existing, updates)

    assert len(result) == 1