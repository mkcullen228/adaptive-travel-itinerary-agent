
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
from src.prompts.recovery_planning import RECOVERY_SYSTEM_PROMPT
from src.prompts.strategy_instructions import (
    MINIMAL_DISRUPTION_INSTRUCTION,
    BEST_OVERALL_FEASIBILITY_INSTRUCTION,
    PREFERENCE_ORIENTED_INSTRUCTION,
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

    system_prompt = (
        RECOVERY_SYSTEM_PROMPT
        + "\n\n"
        + strategy_instruction
    )

    planning_context = planning_input.model_dump(mode="json")

    user_prompt = (
        "Prepare a recovery proposal using the following planning context.\n\n"
        "Return a complete RecoveryOption object.\n"
        "The original itinerary must remain unchanged.\n\n"
    )

    if evidence_brief is not None:
        user_prompt += (
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

    return RecoveryGenerationResult(
        recovery_option=recovery_option,
        raw_response=raw_response,
        model_name=getattr(response, "model", model_name),
        latency_seconds=latency_seconds,
        input_tokens=getattr(response, "prompt_eval_count", None),
        output_tokens=getattr(response, "eval_count", None),
    )
