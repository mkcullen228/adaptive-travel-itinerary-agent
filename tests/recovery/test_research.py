
from types import SimpleNamespace

import pytest

from src.models.evidence import EvidenceStatus
from src.models.multi_agent import EvidenceBrief
from src.recovery.research import (
    build_research_messages,
    research_evidence,
    validate_evidence_brief_sources,
)


def make_investigation():
    from src.models.investigation import InvestigationResult
    from src.models.retrieved_evidence import RetrievedEvidence
    from src.models.source_reference import VerificationStatus

    evidence = RetrievedEvidence(
        chunk_id="chunk_1",
        content="The National Gallery is temporarily closed.",
        subject="National Gallery",
        source_id="source_1",
        source_url="https://example.com/closure",
        retrieved_at="2026-11-17T12:00:00Z",
        similarity_distance=0.1,
        reliability=0.95,
        freshness_score=0.95,
        verification_status=VerificationStatus.VERIFIED,
    )

    return InvestigationResult(
        investigation_id="investigation_1",
        scenario_id="P-01",
        retrieved_evidence=[evidence],
    )


def make_disruption():
    from tests.models.test_agent_workflow import (
        make_recovery_planning_input,
    )

    return make_recovery_planning_input().disruption_scenario


def test_build_research_messages_includes_evidence_and_disruption():
    investigation = make_investigation()
    disruption = make_disruption()

    messages = build_research_messages(
        investigation,
        disruption,
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "source_1" in messages[1]["content"]
    assert "National Gallery" in messages[1]["content"]


def test_research_evidence_returns_structured_brief():
    investigation = make_investigation()
    disruption = make_disruption()

    response_content = EvidenceBrief(
        findings=[
            {
                "claim": "The National Gallery is temporarily closed.",
                "status": EvidenceStatus.SUPPORTED,
                "supporting_source_ids": ["source_1"],
                "explanation": "The retrieved source confirms closure.",
            }
        ],
        source_ids_reviewed=["source_1"],
        disruption_implications=[
            "The National Gallery activity should be removed."
        ],
    ).model_dump_json()

    def fake_chat(**kwargs):
        assert kwargs["model"] == "qwen3.5:4b"
        assert kwargs["think"] is False
        assert kwargs["options"] == {"temperature": 0}
        return SimpleNamespace(
            message=SimpleNamespace(content=response_content),
            model="qwen3.5:4b",
            prompt_eval_count=100,
            eval_count=150,
        )

    result = research_evidence(
        investigation=investigation,
        disruption=disruption,
        client=SimpleNamespace(chat=fake_chat),
    )

    assert result.evidence_brief.findings[0].status == (
        EvidenceStatus.SUPPORTED
    )
    assert result.model_name == "qwen3.5:4b"
    assert result.input_tokens == 100
    assert result.output_tokens == 150


def test_research_rejects_unknown_source_ids():
    investigation = make_investigation()

    brief = EvidenceBrief(
        source_ids_reviewed=["unknown_source"]
    )

    with pytest.raises(ValueError, match="not present"):
        validate_evidence_brief_sources(
            brief,
            investigation,
        )


def test_research_accepts_empty_evidence():
    from src.models.investigation import InvestigationResult

    investigation = InvestigationResult(
        investigation_id="investigation_empty",
        scenario_id="P-01",
    )

    brief = EvidenceBrief(
        unresolved_questions=["Venue availability is unknown."]
    )

    validate_evidence_brief_sources(
        brief,
        investigation,
    )
