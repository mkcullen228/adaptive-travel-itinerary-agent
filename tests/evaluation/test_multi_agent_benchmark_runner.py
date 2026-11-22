
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.models.agent_state import WorkflowStatus
from src.evaluation import multi_agent_benchmark_runner as runner


def make_config(tmp_path):
    """Create a benchmark configuration for an isolated test."""

    return SimpleNamespace(
        benchmark_id="P-01-MULTI-AGENT",
        scenario_id="P-01",
        model_name="qwen3.5:4b",
        strategy=SimpleNamespace(value="minimal_disruption"),
        baseline_path=Path("baseline.json"),
        investigation_path=Path("investigation.json"),
        disruption_path=Path("disruption.json"),
        user_instructions="Recover the itinerary.",
        additional_instructions="Preserve uncertainties.",
        prompt_version="multi_agent_v1",
        output_path=Path("results/multi_agent/P-01.json"),
    )


def make_result(status=WorkflowStatus.COMPLETED):
    """Create a representative completed or failed graph result."""

    validation_issue = SimpleNamespace(
        model_dump=lambda mode="json": {"type": "test_issue"}
    )

    validation_result = SimpleNamespace(
        status=SimpleNamespace(value="valid"),
        issues=[],
    )

    audit_report = SimpleNamespace(
        model_dump=lambda mode="json": {
            "assessment": "partially_supported"
        }
    )

    return {
        "status": status,
        "current_stage": SimpleNamespace(value="completed"),
        "llm_call_count": 3,
        "total_tool_call_count": 0,
        "research_raw_response": '{"findings": []}',
        "planning_raw_response": '{"option_id": "test-option"}',
        "audit_raw_response": '{"assessment": "partially_supported"}',
        "research_generation_metadata": {
            "model_name": "qwen3.5:4b",
            "latency_seconds": 1.0,
            "input_tokens": 100,
            "output_tokens": 50,
        },
        "planning_generation_metadata": {
            "model_name": "qwen3.5:4b",
            "latency_seconds": 2.0,
            "input_tokens": 200,
            "output_tokens": 100,
        },
        "audit_generation_metadata": {
            "model_name": "qwen3.5:4b",
            "latency_seconds": 1.5,
            "input_tokens": 150,
            "output_tokens": 75,
        },
        "multi_agent_generation_metadata": {
            "agent_count": 3,
            "total_llm_calls": 3,
            "total_latency_seconds": 4.5,
            "total_workflow_latency_seconds": 5.0,
            "total_input_tokens": 450,
            "total_output_tokens": 225,
            "input_tokens_complete": True,
            "output_tokens_complete": True,
        },
        "itinerary_validation_result": validation_result,
        "audit_report": audit_report,
        "error_details": [],
    }


@pytest.fixture
def benchmark_setup(tmp_path, monkeypatch):
    """Set up a mocked benchmark run without invoking an LLM."""

    config = make_config(tmp_path)
    planning_input = object()
    initial_state = {"test_state": True}
    result = make_result()

    config_path = tmp_path / "p01_multi_agent.json"
    config_path.write_text("{}", encoding="utf-8")

    def resolve_path(path):
        path = Path(path)
        if path.is_absolute():
            return path
        return tmp_path / path

    monkeypatch.setattr(
        runner,
        "resolve_project_path",
        resolve_path,
    )
    monkeypatch.setattr(
        runner,
        "load_benchmark_config",
        Mock(return_value=config),
    )
    monkeypatch.setattr(
        runner,
        "build_planning_input",
        Mock(return_value=planning_input),
    )
    monkeypatch.setattr(
        runner,
        "build_initial_state",
        Mock(return_value=initial_state),
    )

    graph = Mock()
    graph.invoke.return_value = result

    graph_builder = Mock(return_value=graph)

    monkeypatch.setattr(
        runner,
        "build_multi_agent_recovery_graph",
        graph_builder,
    )

    return SimpleNamespace(
        config=config,
        config_path=config_path,
        planning_input=planning_input,
        initial_state=initial_state,
        result=result,
        graph=graph,
        graph_builder=graph_builder,
        tmp_path=tmp_path,
    )


def test_runner_uses_shared_benchmark_inputs(benchmark_setup):
    setup = benchmark_setup

    runner.run_multi_agent_benchmark(setup.config_path)

    runner.build_planning_input.assert_called_once_with(setup.config)
    runner.build_initial_state.assert_called_once_with(
        setup.planning_input
    )
    setup.graph.invoke.assert_called_once_with(setup.initial_state)


def test_runner_passes_configured_model_and_strategy(benchmark_setup):
    setup = benchmark_setup

    runner.run_multi_agent_benchmark(setup.config_path)

    setup.graph_builder.assert_called_once_with(
        strategy=setup.config.strategy,
        model_name=setup.config.model_name,
        additional_instructions=setup.config.additional_instructions,
    )


def test_runner_saves_all_raw_responses_and_metadata(benchmark_setup):
    setup = benchmark_setup

    runner.run_multi_agent_benchmark(setup.config_path)

    output_path = (
        setup.tmp_path / setup.config.output_path
    )
    research_path = output_path.with_name("P-01.research.json")
    audit_path = output_path.with_name("P-01.audit.json")
    metadata_path = output_path.with_name("P-01.metadata.json")

    assert output_path.read_text(encoding="utf-8") == (
        setup.result["planning_raw_response"]
    )
    assert research_path.read_text(encoding="utf-8") == (
        setup.result["research_raw_response"]
    )
    assert audit_path.read_text(encoding="utf-8") == (
        setup.result["audit_raw_response"]
    )

    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    assert metadata["benchmark_id"] == "P-01-MULTI-AGENT"
    assert metadata["scenario_id"] == "P-01"
    assert metadata["model_name"] == "qwen3.5:4b"
    assert metadata["llm_call_count"] == 3
    assert metadata["aggregate_generation_metadata"][
        "total_input_tokens"
    ] == 450
    assert metadata["aggregate_generation_metadata"][
        "total_output_tokens"
    ] == 225
    assert metadata["research_generation_metadata"]["input_tokens"] == 100
    assert metadata["planning_generation_metadata"]["input_tokens"] == 200
    assert metadata["audit_generation_metadata"]["input_tokens"] == 150


def test_runner_refuses_to_overwrite_existing_output(benchmark_setup):
    setup = benchmark_setup

    output_path = setup.tmp_path / setup.config.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("existing result", encoding="utf-8")

    with pytest.raises(FileExistsError):
        runner.run_multi_agent_benchmark(setup.config_path)

    assert output_path.read_text(encoding="utf-8") == "existing result"
    setup.graph_builder.assert_not_called()


def test_runner_does_not_save_results_when_workflow_fails(
    benchmark_setup,
):
    setup = benchmark_setup

    setup.result["status"] = WorkflowStatus.FAILED
    setup.result["error_details"] = ["research: test failure"]

    with pytest.raises(RuntimeError, match="did not complete successfully"):
        runner.run_multi_agent_benchmark(setup.config_path)

    output_path = setup.tmp_path / setup.config.output_path

    assert not output_path.exists()
    assert not output_path.with_name("P-01.research.json").exists()
    assert not output_path.with_name("P-01.audit.json").exists()
    assert not output_path.with_name("P-01.metadata.json").exists()


def test_runner_saves_pending_proposal_without_approval(benchmark_setup):
    setup = benchmark_setup

    setup.result["status"] = WorkflowStatus.AWAITING_APPROVAL
    setup.result["current_stage"] = SimpleNamespace(value="approval")

    result = runner.run_multi_agent_benchmark(setup.config_path)

    output_path = setup.tmp_path / setup.config.output_path
    metadata_path = output_path.with_name("P-01.metadata.json")

    assert result["status"] == WorkflowStatus.AWAITING_APPROVAL
    assert output_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["workflow_status"] == "awaiting_approval"
    assert metadata["current_stage"] == "approval"
