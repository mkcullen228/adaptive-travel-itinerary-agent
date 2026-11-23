
import json
import time

from dataclasses import dataclass
from typing import Any

import ollama

from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.models.multi_agent import EvidenceBrief
from src.prompts.evidence_research_experimental import (
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

    allowed_source_ids = sorted({
    evidence.source_id
    for evidence in investigation.retrieved_evidence
    })

    research_context["allowed_source_ids"] = allowed_source_ids

    user_prompt = (
        "Interpret the following investigation results and disruption "
        "scenario. Produce an evidence brief for the recovery planner.\n\n"
        "Use only the supplied information and exact source IDs.\n"
        "You may reference only IDs in allowed_source_ids. "
        "If allowed_source_ids is empty, do not invent or reference any "
        "source IDs. Report that no retrieved sources were available.\n\n"
        "Your response must contain a top-level findings array with "
        "exactly one EvidenceFinding object. Do not omit findings or "
        "return an empty array. The finding must include claim, status, "
        "supporting_source_ids, conflicting_source_ids, explanation, "
        "and source_quality_warnings. "
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


def build_evidence_brief_schema() -> dict[str, Any]:
    """Build a schema with required Researcher output fields."""

    schema = EvidenceBrief.model_json_schema()

    findings_schema = schema["properties"]["findings"]
    findings_schema["minItems"] = 1
    findings_schema["maxItems"] = 1

    required_fields = schema.setdefault("required", [])

    for field in ("findings", "source_ids_reviewed"):
        if field not in required_fields:
            required_fields.append(field)

    return schema


def remove_out_of_scope_routing_uncertainties(
    brief: EvidenceBrief,
) -> EvidenceBrief:
    """
    Remove routing and schedule-feasibility claims from the Researcher's
    uncertainties because the Researcher does not receive routing data.

    Routing feasibility is evaluated separately using structured
    itinerary travel estimates and deterministic validation.
    """
    routing_terms = (
        "travel estimate",
        "travel estimates",
        "walking estimate",
        "walking estimates",
        "walking time",
        "walking times",
        "routing",
        "schedule feasibility",
        "travel feasibility",
    )

    filtered_uncertainties = [
        uncertainty
        for uncertainty in brief.overall_uncertainties
        if not any(
            term in uncertainty.lower()
            for term in routing_terms
        )
    ]

    return brief.model_copy(
        update={
            "overall_uncertainties": filtered_uncertainties
        }
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
        format=build_evidence_brief_schema(),
        options={"temperature": 0},
    )

    latency_seconds = time.perf_counter() - start_time
    raw_response = response.message.content

    # Parse the original response before applying deterministic
    # provenance rules.
    brief_data = json.loads(raw_response)

    # Without retrieved evidence, no finding can be classified as
    # supported by retrieved sources. Contextual investigation data
    # remains available to inform the explanation and implications.
    if not investigation.retrieved_evidence:
        brief_data["source_ids_reviewed"] = []

        for finding in brief_data.get("findings", []):
            finding["status"] = "unsupported"
            finding["supporting_source_ids"] = []
            finding["conflicting_source_ids"] = []

            warnings = finding.setdefault(
                "source_quality_warnings", []
            )
            warning = (
                "No retrieved evidence sources were available; "
                "this finding is based on supplied context only."
            )
            if warning not in warnings:
                warnings.append(warning)

    brief = EvidenceBrief.model_validate(brief_data)

    brief = remove_out_of_scope_routing_uncertainties(brief)

    validate_evidence_brief_findings(brief)

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


def validate_evidence_brief_findings(
    brief: EvidenceBrief,
) -> None:
    """Enforce the structured finding requirement for the Researcher."""

    if len(brief.findings) != 1:
        raise ValueError(
            "Researcher must return exactly one structured evidence finding."
        )
