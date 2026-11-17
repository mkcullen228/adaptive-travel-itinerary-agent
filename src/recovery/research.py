
import json
import time

from dataclasses import dataclass
from typing import Any

import ollama

from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.multi_agent import EvidenceBrief
from src.prompts.evidence_research import (
    EVIDENCE_RESEARCH_SYSTEM_PROMPT,
)


@dataclass
class EvidenceResearchResult:
    """Output and usage metadata from one research call."""

    evidence_brief: EvidenceBrief
    raw_response: str
    model_name: str
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


def build_research_messages(
    investigation: InvestigationResult,
    disruption: DisruptionScenario,
) -> list[dict[str, str]]:
    """Build messages for evidence interpretation."""

    research_context = {
        "disruption_scenario": disruption.model_dump(mode="json"),
        "investigation_result": investigation.model_dump(mode="json"),
    }

    user_prompt = (
        "Interpret the following investigation results and disruption "
        "scenario. Produce an evidence brief for the recovery planner.\n\n"
        "Use only the supplied information and exact source IDs.\n\n"
        + json.dumps(research_context, indent=2)
    )

    return [
        {
            "role": "system",
            "content": EVIDENCE_RESEARCH_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def validate_evidence_brief_sources(
    brief: EvidenceBrief,
    investigation: InvestigationResult,
) -> None:
    """Ensure the Researcher references only retrieved source IDs."""

    available_source_ids = {
        evidence.source_id
        for evidence in investigation.retrieved_evidence
    }

    referenced_source_ids = set(brief.source_ids_reviewed)

    for finding in brief.findings:
        referenced_source_ids.update(finding.supporting_source_ids)
        referenced_source_ids.update(finding.conflicting_source_ids)

    unknown_source_ids = referenced_source_ids - available_source_ids

    if unknown_source_ids:
        raise ValueError(
            "Evidence brief references source IDs not present in "
            f"the investigation: {sorted(unknown_source_ids)}"
        )


def research_evidence(
    investigation: InvestigationResult,
    disruption: DisruptionScenario,
    model_name: str = "qwen3.5:4b",
    client: Any | None = None,
) -> EvidenceResearchResult:
    """Interpret frozen investigation evidence in one LLM call."""

    if client is None:
        client = ollama

    messages = build_research_messages(
        investigation=investigation,
        disruption=disruption,
    )

    start_time = time.perf_counter()

    response = client.chat(
        model=model_name,
        think=False,
        messages=messages,
        format=EvidenceBrief.model_json_schema(),
        options={"temperature": 0},
    )

    latency_seconds = time.perf_counter() - start_time
    raw_response = response.message.content

    brief = EvidenceBrief.model_validate_json(raw_response)

    validate_evidence_brief_sources(
        brief=brief,
        investigation=investigation,
    )

    return EvidenceResearchResult(
        evidence_brief=brief,
        raw_response=raw_response,
        model_name=getattr(response, "model", model_name),
        latency_seconds=latency_seconds,
        input_tokens=getattr(response, "prompt_eval_count", None),
        output_tokens=getattr(response, "eval_count", None),
    )
