
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.evaluation import run_evaluation
from src.models.agent_state import WorkflowStage, WorkflowStatus


class FakeEvaluation:
    def __init__(self, passed=True):
        self.passed = passed

    def model_dump(self, mode="python"):
        return {"passed": self.passed}


@pytest.fixture
def fake_scenario():
    return SimpleNamespace(
        scenario_id="E1",
        scenario_name="High quality evidence",
    )


@pytest.fixture
def completed_state():
    return {
        "status": WorkflowStatus.COMPLETED,
        "current_stage": WorkflowStage.COMPLETED,
        "original_itinerary": object(),
        "evidence_brief": object(),
        "recovery_options": [object()],
        "error_details": [],
        "llm_call_count": 3,
        "research_generation_metadata": {
            "latency_seconds": 1.0,
            "input_tokens": 100,
            "output_tokens": 50,
        },
        "planning_generation_metadata": {
            "latency_seconds": 2.0,
            "input_tokens": 200,
            "output_tokens": 75,
        },
        "audit_generation_metadata": {
            "latency_seconds": 1.5,
            "input_tokens": 150,
            "output_tokens": 25,
        },
        "audit_report": None,
        "research_raw_response": "research response",
        "planning_raw_response": "planning response",
        "audit_raw_response": "audit response",
    }


def test_run_scenario_saves_result(
    monkeypatch,
    tmp_path,
    fake_scenario,
    completed_state,
):
    monkeypatch.setattr(
        run_evaluation,
        "load_evaluation_inputs",
        lambda scenario_id: (fake_scenario, {}),
    )
    monkeypatch.setattr(
        run_evaluation,
        "evaluate_researcher_output",
        lambda scenario, brief: FakeEvaluation(True),
    )
    monkeypatch.setattr(
        run_evaluation,
        "evaluate_planner_output",
        lambda scenario, itinerary, option: FakeEvaluation(True),
    )

    graph = Mock()
    graph.invoke.return_value = completed_state

    result = run_evaluation.run_scenario(
        scenario_id="E1",
        output_directory=tmp_path,
        graph=graph,
    )

    assert result["scenario_id"] == "E1"
    assert result["workflow_status"] == "completed"
    assert result["overall_evaluation_passed"] is True
    assert result["metadata"]["llm_call_count"] == 3
    assert result["metadata"]["total_latency_seconds"] == 4.5
    assert result["metadata"]["total_input_tokens"] == 450
    assert result["metadata"]["total_output_tokens"] == 150

    saved_path = Path(result["result_path"])
    assert saved_path.exists()

    saved_result = json.loads(saved_path.read_text(encoding="utf-8"))
    assert saved_result["scenario_id"] == "E1"
    assert saved_result["raw_responses"]["researcher"] == (
        "research response"
    )

    graph.invoke.assert_called_once()


def test_run_scenario_does_not_evaluate_failed_workflow(
    monkeypatch,
    tmp_path,
    fake_scenario,
):
    monkeypatch.setattr(
        run_evaluation,
        "load_evaluation_inputs",
        lambda scenario_id: (fake_scenario, {}),
    )

    researcher_evaluator = Mock()
    planner_evaluator = Mock()

    monkeypatch.setattr(
        run_evaluation,
        "evaluate_researcher_output",
        researcher_evaluator,
    )
    monkeypatch.setattr(
        run_evaluation,
        "evaluate_planner_output",
        planner_evaluator,
    )

    graph = Mock()
    graph.invoke.return_value = {
        "status": WorkflowStatus.FAILED,
        "current_stage": WorkflowStage.INVESTIGATION,
        "error_details": ["research: Research failed"],
        "llm_call_count": 1,
    }

    result = run_evaluation.run_scenario(
        scenario_id="E1",
        output_directory=tmp_path,
        graph=graph,
    )

    assert result["workflow_status"] == "failed"
    assert result["overall_evaluation_passed"] is False
    assert result["researcher_evaluation"] is None
    assert result["planner_evaluation"] is None
    assert result["error_details"] == ["research: Research failed"]

    researcher_evaluator.assert_not_called()
    planner_evaluator.assert_not_called()


def test_separate_runs_do_not_overwrite_results(
    monkeypatch,
    tmp_path,
    fake_scenario,
    completed_state,
):
    monkeypatch.setattr(
        run_evaluation,
        "load_evaluation_inputs",
        lambda scenario_id: (fake_scenario, {}),
    )
    monkeypatch.setattr(
        run_evaluation,
        "evaluate_researcher_output",
        lambda scenario, brief: FakeEvaluation(True),
    )
    monkeypatch.setattr(
        run_evaluation,
        "evaluate_planner_output",
        lambda scenario, itinerary, option: FakeEvaluation(True),
    )

    graph = Mock()
    graph.invoke.return_value = completed_state

    first = run_evaluation.run_scenario(
        "E1", output_directory=tmp_path, graph=graph
    )
    second = run_evaluation.run_scenario(
        "E1", output_directory=tmp_path, graph=graph
    )

    assert first["run_id"] != second["run_id"]
    assert first["result_path"] != second["result_path"]
    assert len(list(tmp_path.glob("E1_*.json"))) == 2
