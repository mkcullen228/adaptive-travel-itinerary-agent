
from src.models.agent_workflow import ExecutionEvent, ApprovalRecord


def append_execution_events(
    existing: list[ExecutionEvent],
    updates: list[ExecutionEvent],
) -> list[ExecutionEvent]:
    """Append new execution events while preventing duplicate event IDs."""

    seen_ids = {event.event_id for event in existing}
    new_events = []

    for event in updates:
        if event.event_id not in seen_ids:
            new_events.append(event)
            seen_ids.add(event.event_id)

    return existing + new_events


def append_unique_strings(
    existing: list[str],
    updates: list[str],
) -> list[str]:
    """Append new strings while preventing duplicates."""

    seen = set(existing)
    new_items = []

    for item in updates:
        if item not in seen:
            new_items.append(item)
            seen.add(item)

    return existing + new_items


def append_approval_records(
    existing: list[ApprovalRecord],
    updates: list[ApprovalRecord],
) -> list[ApprovalRecord]:
    """Append approval records while preventing duplicate records."""

    seen_records = {
        (record.option_id, record.timestamp)
        for record in existing
    }

    new_records = []

    for record in updates:
        record_key = (record.option_id, record.timestamp)

        if record_key not in seen_records:
            new_records.append(record)
            seen_records.add(record_key)

    return existing + new_records
