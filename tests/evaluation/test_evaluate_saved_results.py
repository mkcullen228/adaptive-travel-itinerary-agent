
import json
from types import SimpleNamespace
from unittest.mock import Mock

from src.evaluation import evaluate_saved_results


def test_saved_run_fails_overall_when_auditor_fails(
    monkeypatch,
    tmp_path,
):
    scenario = SimpleNamespace(scenario_id="E1")
    original_itinerary = object()
    proposed_itinerary = object()
    evidence_brief = object()

    recovery_option = SimpleNamespace(
        proposed_itinerary=proposed_itinerary,
    )

    planner_evaluation = SimpleNamespace(
        passed=True,
        schedule_consistency_failures=[],
        failures=[],
        model_dump=lambda mode="json": {"passed": True},
    )

    researcher_evaluation = SimpleNamespace(
        passed=True,
        model_dump=lambda mode="json": {"passed": True},
    )

    auditor_evaluation = SimpleNamespace(
        passed=False,
        model_dump=lambda mode="json": {"passed": False},
    )

    monkeypatch.setattr(
        evaluate_saved_results,
        "load_evaluation_inputs",
        lambda scenario_id: (
            scenario,
            {"original_itinerary": original_itinerary},
        ),
    )

    monkeypatch.setattr(
        evaluate_saved_results.EvidenceBrief,
        "model_validate_json",
        Mock(return_value=evidence_brief),
    )
    monkeypatch.setattr(
        evaluate_saved_results.RecoveryOption,
        "model_validate_json",
        Mock(return_value=recovery_option),
    )
    monkeypatch.setattr(
        evaluate_saved_results.AuditReport,
        "model_validate_json",
        Mock(return_value=object()),
    )

    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_researcher_output",
        Mock(return_value=researcher_evaluation),
    )
    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_planner_output",
        Mock(return_value=planner_evaluation),
    )
    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_auditor_output",
        Mock(return_value=auditor_evaluation),
    )

    result_path = tmp_path / "saved_run.json"
    result_path.write_text(
        json.dumps({
            "run_id": "RUN-001",
            "scenario_id": "E1",
            "model_name": "qwen3.5:4b",
            "raw_responses": {
                "researcher": '{"findings": []}',
                "planner": '{"option_id": "OPTION-01"}',
                "auditor": '{"assessment": "partially_supported"}',
            },
        }),
        encoding="utf-8",
    )

    result = evaluate_saved_results.evaluate_saved_run(result_path)

    assert result["researcher_evaluation"]["passed"] is True
    assert result["planner_evaluation"]["passed"] is True
    assert result["auditor_evaluation"]["passed"] is False
    assert result["overall_evaluation_passed"] is False

def test_saved_run_fails_overall_when_auditor_is_missing(
    monkeypatch,
    tmp_path,
):
    scenario = SimpleNamespace(scenario_id="E1")
    original_itinerary = object()
    evidence_brief = object()

    recovery_option = SimpleNamespace(
        proposed_itinerary=object(),
    )

    planner_evaluation = SimpleNamespace(
        passed=True,
        schedule_consistency_failures=[],
        failures=[],
        model_dump=lambda mode="json": {"passed": True},
    )

    researcher_evaluation = SimpleNamespace(
        passed=True,
        model_dump=lambda mode="json": {"passed": True},
    )

    monkeypatch.setattr(
        evaluate_saved_results,
        "load_evaluation_inputs",
        lambda scenario_id: (
            scenario,
            {"original_itinerary": original_itinerary},
        ),
    )

    monkeypatch.setattr(
        evaluate_saved_results.EvidenceBrief,
        "model_validate_json",
        Mock(return_value=evidence_brief),
    )
    monkeypatch.setattr(
        evaluate_saved_results.RecoveryOption,
        "model_validate_json",
        Mock(return_value=recovery_option),
    )

    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_researcher_output",
        Mock(return_value=researcher_evaluation),
    )
    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_planner_output",
        Mock(return_value=planner_evaluation),
    )

    result_path = tmp_path / "saved_run.json"
    result_path.write_text(
        json.dumps({
            "run_id": "RUN-002",
            "scenario_id": "E1",
            "model_name": "qwen3.5:4b",
            "raw_responses": {
                "researcher": '{"findings": []}',
                "planner": '{"option_id": "OPTION-01"}',
            },
        }),
        encoding="utf-8",
    )

    result = evaluate_saved_results.evaluate_saved_run(result_path)

    assert result["auditor_evaluation"] is None
    assert result["overall_evaluation_passed"] is False


def test_saved_deterministic_validation_is_passed_to_auditor(
    monkeypatch,
    tmp_path,
):
    scenario = SimpleNamespace(scenario_id="E1")
    original_itinerary = object()
    evidence_brief = object()
    recovery_option = SimpleNamespace(
        proposed_itinerary=object(),
    )
    audit_report = object()

    deterministic_validation = {
        "status": "invalid",
        "issues": [
            {
                "issue_type": "activity_overlap",
                "description": "Two activities overlap.",
                "activity_ids": ["activity_1", "activity_2"],
            }
        ],
    }

    planner_evaluation = SimpleNamespace(
        passed=True,
        schedule_consistency_failures=[],
        failures=[],
        model_dump=lambda mode="json": {"passed": True},
    )
    researcher_evaluation = SimpleNamespace(
        passed=True,
        model_dump=lambda mode="json": {"passed": True},
    )
    auditor_evaluation = SimpleNamespace(
        passed=False,
        model_dump=lambda mode="json": {"passed": False},
    )

    monkeypatch.setattr(
        evaluate_saved_results,
        "load_evaluation_inputs",
        lambda scenario_id: (
            scenario,
            {"original_itinerary": original_itinerary},
        ),
    )

    monkeypatch.setattr(
        evaluate_saved_results.EvidenceBrief,
        "model_validate_json",
        Mock(return_value=evidence_brief),
    )
    monkeypatch.setattr(
        evaluate_saved_results.RecoveryOption,
        "model_validate_json",
        Mock(return_value=recovery_option),
    )
    monkeypatch.setattr(
        evaluate_saved_results.AuditReport,
        "model_validate_json",
        Mock(return_value=audit_report),
    )

    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_researcher_output",
        Mock(return_value=researcher_evaluation),
    )
    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_planner_output",
        Mock(return_value=planner_evaluation),
    )

    auditor_mock = Mock(return_value=auditor_evaluation)
    monkeypatch.setattr(
        evaluate_saved_results,
        "evaluate_auditor_output",
        auditor_mock,
    )

    result_path = tmp_path / "saved_run.json"
    result_path.write_text(
        json.dumps({
            "run_id": "RUN-003",
            "scenario_id": "E1",
            "model_name": "qwen3.5:4b",
            "deterministic_validation": deterministic_validation,
            "raw_responses": {
                "researcher": '{"findings": []}',
                "planner": '{"option_id": "OPTION-01"}',
                "auditor": '{"assessment": "partially_supported"}',
            },
        }),
        encoding="utf-8",
    )

    evaluate_saved_results.evaluate_saved_run(result_path)

    auditor_mock.assert_called_once()
    assert (
        auditor_mock.call_args.kwargs["deterministic_validation"]
        == deterministic_validation
    )
