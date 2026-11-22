
import json
import time
from dataclasses import dataclass
from typing import Any

import ollama

from src.models.multi_agent import EvidenceBrief
from src.models.agent_workflow import (
    RecoveryOption,
    RecoveryPlanningInput,
    RecoveryStrategy,
)
from src.prompts.strategy_instructions import (
    MINIMAL_DISRUPTION_INSTRUCTION,
    BEST_OVERALL_FEASIBILITY_INSTRUCTION,
    PREFERENCE_ORIENTED_INSTRUCTION,
)
from src.prompts.recovery_planning import RECOVERY_SYSTEM_PROMPT
from src.prompts.recovery_planning_experimental import (
    RECOVERY_SYSTEM_PROMPT as EXPERIMENTAL_RECOVERY_SYSTEM_PROMPT,
)


DEFAULT_MODEL = "qwen3.5:4b"

STRATEGY_INSTRUCTIONS = {
    RecoveryStrategy.MINIMAL_DISRUPTION:
        MINIMAL_DISRUPTION_INSTRUCTION,
    RecoveryStrategy.BEST_OVERALL_FEASIBILITY:
        BEST_OVERALL_FEASIBILITY_INSTRUCTION,
    RecoveryStrategy.PREFERENCE_ORIENTED:
        PREFERENCE_ORIENTED_INSTRUCTION,
}


@dataclass
class RecoveryGenerationResult:
    """Output from one recovery proposal generation."""

    recovery_option: RecoveryOption
    raw_response: str
    model_name: str
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None



def build_recovery_messages(
    planning_input: RecoveryPlanningInput,
    evidence_brief: EvidenceBrief | None = None,
) -> list[dict[str, str]]:
    """Build messages for recovery proposal generation.

    An optional EvidenceBrief provides additional structured
    research context for the multi-agent workflow.
    """

    strategy_instruction = STRATEGY_INSTRUCTIONS[
        planning_input.strategy
    ]

    base_prompt = (
        EXPERIMENTAL_RECOVERY_SYSTEM_PROMPT
        if evidence_brief is not None
        else RECOVERY_SYSTEM_PROMPT
    )

    system_prompt = base_prompt + "\n\n" + strategy_instruction

    planning_context = planning_input.model_dump(mode="json")

    user_prompt = (
        "Prepare a recovery proposal using the following planning context.\n\n"
        "Return a complete RecoveryOption object.\n"
        "The original itinerary must remain unchanged.\n\n"
    )

    if evidence_brief is not None:
        user_prompt += (
            "SCHEDULE FEASIBILITY AND RECOVERY ACTION RULES:\n"
            "- Distinguish between evidence that supports a specific venue "
            "adjustment and evidence that establishes the feasibility of "
            "the entire revised itinerary.\n"
            "- Do not describe the overall revised schedule as feasible, "
            "confirmed, or achievable unless the available travel estimates "
            "and remaining activity availability support that conclusion.\n"
            "- If travel estimates or remaining activity availability have "
            "not been verified, explicitly state in the main rationale that "
            "overall schedule feasibility remains provisional or unverified.\n"
            "- Include this qualification in the rationale itself, not only "
            "in the uncertainties or assumptions lists.\n"
            "- Clearly distinguish rescheduling an existing visit from "
            "extending its duration. Only describe the visit as extended "
            "if its actual duration is increased in the proposed itinerary.\n\n"
            "ADDITIONAL RESEARCHER EVIDENCE BRIEF\n"
            "The following brief is an interpretation of the original "
            "investigation evidence. Use it as additional context, but "
            "do not treat interpretations as stronger than the underlying "
            "evidence. The original investigation remains the source of truth.\n\n"
            "EVIDENCE PROVENANCE RULES:\n"
            "- Only use source IDs belonging to actual retrieved evidence records "
            "in supporting_evidence_ids.\n"
            "- Investigation IDs and disruption scenario IDs are contextual "
            "identifiers, not evidence source IDs. Never include them in "
            "supporting_evidence_ids.\n"
            "- If no retrieved evidence records are supplied, return an empty "
            "supporting_evidence_ids list.\n"
            "- Do not treat the Researcher's interpretations, claims, or "
            "evidence brief as independent evidence sources. Cite only "
            "original retrieved evidence source IDs.\n\n"
            "RESEARCHER EVIDENCE BRIEF:\n"
            "- Follow the Researcher's evidence classification for the "
            "specific claim. If the Researcher classifies a claim as "
            "unsupported, do not cite its sources as supporting evidence "
            "for that claim, even if those sources are valid retrieved "
            "evidence records.\n"
            "- A stale source may be discussed as historical context, "
            "but must not substantiate current venue availability.\n"
            "- Rescheduling changes an activity's start_time while preserving "
            "its duration_minutes.\n"
            "- Extending a visit increases that activity's duration_minutes.\n"
            "- Never describe a visit as extended merely because its start "
            "time changes or because another activity is moved.\n"
            "- When evidence does not support extending a visit, do not "
            "propose an extension as an established recovery action.\n"
            "- When evidence is insufficient to establish that a proposed "
            "schedule change is feasible, preserve the original mandatory "
            "activity time and duration unless another change is independently "
            "supported. Clearly identify the unresolved constraint rather "
            "than presenting an unverified schedule change as a recovery.\n"
            + evidence_brief.model_dump_json(indent=2)
            + "\n\n"
        )

    user_prompt += json.dumps(planning_context, indent=2)

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def align_proposal_timestamps(recovery_option, original_itinerary):
    """
    Align proposed activity timezone awareness with the original itinerary.

    This MVP uses local wall-clock times for its single-destination itinerary.
    The original activity timestamp determines the expected timezone format.
    """
    original_by_id = {
        activity.activity_id: activity
        for activity in original_itinerary.activities
    }

    normalized_activities = []

    for proposed_activity in recovery_option.proposed_itinerary.activities:
        original_activity = original_by_id.get(
            proposed_activity.activity_id
        )

        if original_activity is None:
            normalized_activities.append(proposed_activity)
            continue

        original_time = original_activity.start_time
        proposed_time = proposed_activity.start_time

        original_is_aware = original_time.utcoffset() is not None
        proposed_is_aware = proposed_time.utcoffset() is not None

        if original_is_aware and not proposed_is_aware:
            normalized_time = proposed_time.replace(
                tzinfo=original_time.tzinfo
            )
        elif not original_is_aware and proposed_is_aware:
            normalized_time = proposed_time.replace(tzinfo=None)
        else:
            normalized_time = proposed_time

        if normalized_time != proposed_time:
            proposed_activity = proposed_activity.model_copy(
                update={"start_time": normalized_time}
            )

        normalized_activities.append(proposed_activity)

    normalized_itinerary = recovery_option.proposed_itinerary.model_copy(
        update={"activities": normalized_activities}
    )

    return recovery_option.model_copy(
        update={"proposed_itinerary": normalized_itinerary}
    )


def generate_recovery_option(
    planning_input: RecoveryPlanningInput,
    model_name: str = DEFAULT_MODEL,
    client: Any | None = None,
    evidence_brief: EvidenceBrief | None = None,
) -> RecoveryGenerationResult:
    """
    Generate a structured recovery proposal.

    The client parameter supports dependency injection for testing.
    If omitted, the standard Ollama module is used.
    """

    if client is None:
        client = ollama

    messages = build_recovery_messages(
        planning_input,
        evidence_brief=evidence_brief,
    )

    start_time = time.perf_counter()

    response = client.chat(
        model=model_name,
        think=False,
        messages=messages,
        format=RecoveryOption.model_json_schema(),
        options={"temperature": 0},
    )

    latency_seconds = time.perf_counter() - start_time

    raw_response = response.message.content

    recovery_option = RecoveryOption.model_validate_json(
        raw_response
    )

    recovery_option = align_proposal_timestamps(
        recovery_option,
        planning_input.original_itinerary,
    )

    return RecoveryGenerationResult(
        recovery_option=recovery_option,
        raw_response=raw_response,
        model_name=getattr(response, "model", model_name),
        latency_seconds=latency_seconds,
        input_tokens=getattr(response, "prompt_eval_count", None),
        output_tokens=getattr(response, "eval_count", None),
    )
