
import pytest

from src.evaluation.input_loader import load_evaluation_inputs
from src.models.agent_state import WorkflowStatus


SCENARIO_IDS = ["E1", "E2", "E3", "E4", "E5"]


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_loads_each_evidence_scenario(scenario_id):
    print(scenario_id)
    scenario, state = load_evaluation_inputs(scenario_id)
    print(scenario)
    print("\n")
    print(state)

    assert scenario.scenario_id == scenario_id
    assert state["original_itinerary"].itinerary_id == (
        "dc_baseline_2026_11_07"
    )
    assert scenario.base_case.itinerary_id == "P-01"
    assert state["disruption_scenario"].scenario_id == "P-01"
    assert state["investigation_result"] is not None


def test_all_scenarios_use_same_original_itinerary_and_disruption():
    loaded = [
        load_evaluation_inputs(scenario_id)
        for scenario_id in SCENARIO_IDS
    ]

    baseline = loaded[0][1]

    for _, state in loaded[1:]:
        assert state["original_itinerary"] == baseline["original_itinerary"]
        assert state["disruption_scenario"] == baseline["disruption_scenario"]


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_only_selected_scenario_evidence_is_loaded(scenario_id):
    scenario, state = load_evaluation_inputs(scenario_id)

    investigation = state["investigation_result"]

    assert investigation.retrieved_evidence == scenario.retrieved_evidence


def test_e5_has_no_retrieved_evidence():
    scenario, state = load_evaluation_inputs("E5")

    assert scenario.retrieved_evidence == []
    assert state["investigation_result"].retrieved_evidence == []


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_original_assessments_are_not_carried_forward(scenario_id):
    _, state = load_evaluation_inputs(scenario_id)

    assert state["investigation_result"].evidence_assessments == []


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_general_investigation_warnings_are_preserved(scenario_id):
    _, state = load_evaluation_inputs(scenario_id)

    warnings = state["investigation_result"].investigation_warnings

    assert any(
        "remaining original activities" in warning.lower()
        for warning in warnings
    )
    assert any(
        "schedule feasibility" in warning.lower()
        for warning in warnings
    )
    assert not any(
        "replacement venue availability" in warning.lower()
        for warning in warnings
    )


def test_loader_initializes_workflow_without_running_it():
    _, state = load_evaluation_inputs("E1")

    assert state["status"] == WorkflowStatus.IN_PROGRESS
    assert state["recovery_options"] == []
    assert state["evidence_brief"] is None
    assert state["final_itinerary"] is None
