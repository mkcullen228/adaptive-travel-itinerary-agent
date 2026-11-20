
import json
import time
from dataclasses import dataclass
from typing import Any

import ollama

from src.models.agent_workflow import (
    RecoveryOption,
    RecoveryPlanningInput,
)
from src.models.multi_agent import AuditReport, EvidenceBrief
from src.prompts.recovery_audit import RECOVERY_AUDIT_SYSTEM_PROMPT
from src.recovery.generation import DEFAULT_MODEL


@dataclass
class AuditGenerationResult:
    """Output from one validation and evidence audit."""

    audit_report: AuditReport
    raw_response: str
    model_name: str
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


def compare_mandatory_activities(
    original_itinerary,
    proposed_itinerary,
) -> list[dict[str, Any]]:
    """Compare mandatory activities between original and proposed itineraries."""

    comparison = []

    for original_activity in original_itinerary.activities:
        if not original_activity.mandatory:
            continue

        matching_activity = next(
            (
                activity
                for activity in proposed_itinerary.activities
                if activity.activity_id == original_activity.activity_id
            ),
            None,
        )

        comparison.append({
            "activity_id": original_activity.activity_id,
            "activity_name": original_activity.name,
            "original_mandatory": True,
            "preserved": (
                matching_activity is not None
                and matching_activity.mandatory
            ),
            "proposed_activity_id": (
                matching_activity.activity_id
                if matching_activity is not None
                else None
            ),
            "proposed_activity_name": (
                matching_activity.name
                if matching_activity is not None
                else None
            ),
            "proposed_mandatory": (
                matching_activity.mandatory
                if matching_activity is not None
                else None
            ),
        })

    return comparison


def build_audit_messages(
    planning_input: RecoveryPlanningInput,
    evidence_brief: EvidenceBrief,
    recovery_option: RecoveryOption,
    deterministic_validation: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build the messages used by the Auditor."""

    mandatory_activity_comparison = compare_mandatory_activities(
        original_itinerary=planning_input.original_itinerary,
        proposed_itinerary=recovery_option.proposed_itinerary,
    )

    audit_context = {
        "original_itinerary": (
            planning_input.original_itinerary.model_dump(mode="json")
        ),
        "disruption_scenario": (
            planning_input.disruption_scenario.model_dump(mode="json")
        ),
        "evidence_brief": evidence_brief.model_dump(mode="json"),
        "recovery_proposal": recovery_option.model_dump(mode="json"),
        "deterministic_validation": deterministic_validation,
        "mandatory_activity_comparison": mandatory_activity_comparison,
    }

    user_prompt = (
        "Audit the following recovery proposal using only the "
        "supplied context.\n\n"
        "Return an AuditReport. Do not modify or replace the proposal.\n\n"
        + json.dumps(audit_context, indent=2)
    )

    return [
        {
            "role": "system",
            "content": RECOVERY_AUDIT_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def audit_recovery_proposal(
    planning_input: RecoveryPlanningInput,
    evidence_brief: EvidenceBrief,
    recovery_option: RecoveryOption,
    deterministic_validation: dict[str, Any] | None = None,
    model_name: str = DEFAULT_MODEL,
    client: Any | None = None,
) -> AuditGenerationResult:
    """Audit a recovery proposal without modifying it."""

    if client is None:
        client = ollama

    messages = build_audit_messages(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        recovery_option=recovery_option,
        deterministic_validation=deterministic_validation,
    )

    start_time = time.perf_counter()

    response = client.chat(
        model=model_name,
        think=False,
        messages=messages,
        format=AuditReport.model_json_schema(),
        options={"temperature": 0},
    )

    latency_seconds = time.perf_counter() - start_time
    raw_response = response.message.content

    audit_report = AuditReport.model_validate_json(raw_response)

    return AuditGenerationResult(
        audit_report=audit_report,
        raw_response=raw_response,
        model_name=getattr(response, "model", model_name),
        latency_seconds=latency_seconds,
        input_tokens=getattr(response, "prompt_eval_count", None),
        output_tokens=getattr(response, "eval_count", None),
    )
