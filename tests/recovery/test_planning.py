
from unittest.mock import Mock

from src.models.multi_agent import EvidenceBrief
from src.recovery.generation import RecoveryGenerationResult
from src.recovery.planning import plan_recovery


def test_plan_recovery_delegates_to_generation(
    monkeypatch,
):
    planning_input = Mock()
    evidence_brief = EvidenceBrief()

    expected_result = Mock(spec=RecoveryGenerationResult)

    def fake_generate_recovery_option(
        planning_input,
        model_name,
        client,
        evidence_brief,
    ):
        assert evidence_brief is not None
        assert evidence_brief == expected_brief
        return expected_result

    expected_brief = evidence_brief

    monkeypatch.setattr(
        "src.recovery.planning.generate_recovery_option",
        fake_generate_recovery_option,
    )

    result = plan_recovery(
        planning_input=planning_input,
        evidence_brief=evidence_brief,
        model_name="qwen3.5:4b",
        client=Mock(),
    )

    assert result is expected_result
