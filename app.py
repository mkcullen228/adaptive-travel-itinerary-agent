import json
from datetime import timedelta
from pathlib import Path
from unittest import result

from src.models import itinerary
import streamlit as st

from src.models.itinerary import Itinerary
from src.models.disruption import DisruptionScenario
from src.models.investigation import InvestigationResult
from src.data_sources.attraction_lookup import get_attraction_by_id
from src.workflows.investigation_workflow import run_investigation
from src.models.agent_workflow import RecoveryStrategy, ApprovalStatus
from src.workflows.multi_agent_recovery import (
    build_multi_agent_recovery_graph,
    apply_approval_decision,
)
from src.workflows.state_initialization import initialize_agent_state


PROJECT_ROOT = Path(__file__).resolve().parent

ITINERARY_PATH = (
    PROJECT_ROOT / "data" / "itineraries" / "dc_baseline_2026_11_07.json"
)

SCENARIO_FIXTURES = {
    "P-01 — National Gallery unavailable": {
        "scenario_path": (
            PROJECT_ROOT / "tests" / "fixtures" / "p01_disruption_scenario.json"
        ),
        "investigation_path": None,
    },
    "P-02 — Heavy rain": {
        "scenario_path": (
            PROJECT_ROOT / "tests" / "fixtures" / "p02_disruption_scenario.json"
        ),
        "investigation_path": (
            PROJECT_ROOT / "tests" / "fixtures" / "p02_investigation_context.json"
        ),
    },
}


@st.cache_data
def load_inputs(scenario_label):
    """Load the shared itinerary and selected disruption fixture."""

    itinerary_data = json.loads(
        ITINERARY_PATH.read_text(encoding="utf-8")
    )

    scenario_config = SCENARIO_FIXTURES[scenario_label]
    disruption_data = json.loads(
        scenario_config["scenario_path"].read_text(encoding="utf-8")
    )

    itinerary = Itinerary.model_validate(itinerary_data)
    disruption = DisruptionScenario.model_validate(disruption_data)

    investigation_context = None
    if scenario_config["investigation_path"] is not None:
        context_data = json.loads(
            scenario_config["investigation_path"].read_text(encoding="utf-8")
        )
        investigation_context = InvestigationResult.model_validate(context_data)

    return itinerary, disruption, investigation_context


def get_affected_attractions(itinerary, disruption):
    """Resolve the attraction records associated with affected activities."""

    affected_activities = [
        activity
        for activity in itinerary.activities
        if activity.activity_id in disruption.affected_activity_ids
    ]

    if not affected_activities:
        raise ValueError(
            "The disruption does not match any activity in the itinerary."
        )

    attractions = []
    for activity in affected_activities:
        if not activity.attraction_id:
            raise ValueError(
                f"Activity '{activity.activity_id}' has no attraction_id."
            )
        attractions.append(get_attraction_by_id(activity.attraction_id))

    return affected_activities, attractions


def run_recovery_workflow(
    itinerary,
    disruption,
    investigation_context=None,
):
    """Run investigation and the multi-agent recovery graph."""

    affected_activities, attractions = get_affected_attractions(
        itinerary,
        disruption,
    )

    # P-02 is a controlled benchmark: use its supplied synthetic investigation
    # context rather than replacing it with a live weather lookup.
    if investigation_context is not None:
        investigation = investigation_context
        venue_context = attractions[0]
    else:
        # P-01 retains its existing venue investigation behavior.
        if len(affected_activities) != 1:
            raise ValueError(
                "The P-01 venue investigation expects exactly one affected activity."
            )

        venue_context = attractions[0]
        investigation = run_investigation(
            itinerary=itinerary,
            scenario=disruption,
            venue_id=venue_context.attraction_id,
            latitude=venue_context.latitude,
            longitude=venue_context.longitude,
        )

    if disruption.scenario_id == "P-01":
        user_instructions = (
            "Recover the itinerary after the National Gallery of Art "
            "unavailability described in the disruption scenario. Preserve "
            "the existing mandatory National Museum of Natural History visit. "
            "Do not add a duplicate visit."
        )
        additional_instructions = (
            "Preserve unaffected original activities where feasible. Remove "
            "the unavailable National Gallery. Do not imply that remaining "
            "venues are available unless supported by evidence. Do not invent "
            "replacement activities. Explain remaining uncertainties and "
            "ensure all walking travel estimates support the proposed schedule."
        )
    elif disruption.scenario_id == "P-02":
        user_instructions = (
            "Recover the itinerary from the controlled heavy-rain disruption "
            "in P-02. Address both affected outdoor activities: the World War "
            "II Memorial and Lincoln Memorial. Use the supplied synthetic "
            "weather investigation context. Preserve mandatory activities. "
            "Do not treat any indoor alternative as confirmed available."
        )
        additional_instructions = (
            "The supplied P-02 weather context is synthetic benchmark input, "
            "not a live forecast. Heavy rain affects outdoor activities from "
            "12:00 PM through 6:00 PM on November 7, 2026. Do not schedule "
            "affected outdoor activities within that window. If proposing "
            "rescheduling before noon, ensure the full activity duration and "
            "all walking transitions fit the schedule. Do not invent indoor "
            "replacement activities or imply their availability is verified. "
            "Preserve mandatory activities and explain unresolved uncertainties."
        )
    else:
        raise ValueError(
            f"Unsupported scenario fixture: {disruption.scenario_id}"
        )

    state = initialize_agent_state(
        itinerary=itinerary,
        disruption=disruption,
        venue_id=venue_context.attraction_id,
        latitude=venue_context.latitude,
        longitude=venue_context.longitude,
        user_instructions=user_instructions,
    )

    state["investigation_result"] = investigation

    graph = build_multi_agent_recovery_graph(
        strategy=RecoveryStrategy.MINIMAL_DISRUPTION,
        additional_instructions=additional_instructions,
    )

    result = graph.invoke(state)

    evidence_brief = result.get("evidence_brief")

    print("\n========== P-01 EVIDENCE BRIEF ==========")

    if evidence_brief is not None:
        if hasattr(evidence_brief, "model_dump_json"):
            print(evidence_brief.model_dump_json(indent=2))
        else:
            print(evidence_brief)
    else:
        print("No EvidenceBrief was returned.")

    print("========== END EVIDENCE BRIEF ==========\n")

    return result


def render_travel_details(proposed_itinerary):
    """Display walking estimates and any route-generation failures."""

    st.subheader("Walking routes")

    travel_legs = getattr(proposed_itinerary, "travel_legs", []) or []
    routing_failures = (
        getattr(proposed_itinerary, "routing_failures", []) or []
    )

    if travel_legs:
        route_rows = []

        for leg in travel_legs:
            estimates = getattr(leg, "estimates", []) or []

            if not estimates:
                route_rows.append(
                    {
                        "From": leg.origin_activity_id,
                        "To": leg.destination_activity_id,
                        "Mode": getattr(leg, "selected_mode", "walking"),
                        "Duration (min)": "No estimate",
                        "Distance (m)": "—",
                        "Source": "—",
                    }
                )
                continue

            for estimate in estimates:
                route_rows.append(
                    {
                        "From": leg.origin_activity_id,
                        "To": leg.destination_activity_id,
                        "Mode": getattr(estimate, "mode", "walking"),
                        "Duration (min)": getattr(
                            estimate, "duration_minutes", "—"
                        ),
                        "Distance (m)": getattr(
                            estimate, "distance_meters", "—"
                        ),
                        "Source": getattr(estimate, "source", "—"),
                    }
                )

        st.dataframe(
            route_rows,
            width='content',
            hide_index=True,
        )
    else:
        st.warning("No walking travel legs were generated.")

    if routing_failures:
        st.warning(f"{len(routing_failures)} walking route request(s) failed.")

        with st.expander("Routing failure details", expanded=True):
            for failure in routing_failures:
                st.write(
                    f"**{failure.origin_activity_id} → "
                    f"{failure.destination_activity_id}**"
                )
                st.write(f"Requested mode: {failure.requested_mode}")
                st.write(f"Reason: {failure.failure_reason}")
    else:
        st.success("No walking route-generation failures were recorded.")


def render_schedule_assessment(proposed_itinerary, disruption):
    """Show deterministic timing checks for the proposed schedule."""

    st.subheader("Schedule and disruption assessment")

    activities = sorted(
        proposed_itinerary.activities,
        key=lambda activity: activity.start_time.replace(tzinfo=None),
    )

    def minutes_between(later, earlier):
        """Return elapsed minutes, or None for incompatible timezone data."""
        if (later.utcoffset() is None) != (earlier.utcoffset() is None):
            return None
        return (later - earlier).total_seconds() / 60

    # Assess affected outdoor activities against the disruption window.
    window_start = getattr(disruption, "affected_time_start", None)
    window_end = getattr(disruption, "affected_time_end", None)
    affected_ids = set(disruption.affected_activity_ids or [])

    if window_start and window_end:
        weather_rows = []

        for activity in activities:
            if activity.activity_id not in affected_ids or activity.indoor:
                continue

            activity_end = activity.start_time + timedelta(
                minutes=activity.duration_minutes
            )

            try:
                starts_before_window_end = (
                    minutes_between(window_end, activity.start_time) > 0
                )
                ends_after_window_start = (
                    minutes_between(activity_end, window_start) > 0
                )

                if (
                    starts_before_window_end is None
                    or ends_after_window_start is None
                ):
                    status = "Cannot compare — timezone mismatch"
                elif starts_before_window_end and ends_after_window_start:
                    status = "Overlaps disruption window"
                else:
                    status = "Outside disruption window"

            except (TypeError, ValueError):
                status = "Cannot compare — timezone mismatch"

            weather_rows.append({
                "Activity": activity.name,
                "Proposed start": activity.start_time.strftime("%I:%M %p"),
                "Proposed end": activity_end.strftime("%I:%M %p"),
                "Disruption assessment": status,
            })

        if weather_rows:
            st.write(
                f"**Affected outdoor activities — disruption window:** "
                f"{window_start.strftime('%b %d, %Y %I:%M %p')} to "
                f"{window_end.strftime('%I:%M %p')}"
            )
            st.dataframe(
                weather_rows,
                width="content",
                hide_index=True,
            )
        else:
            st.info(
                "No affected outdoor activities were found in the proposal."
            )
    else:
        st.info(
            "This scenario has no defined time-based disruption window. "
            "No disruption-window timing check applies."
        )

    # Assess walking time between consecutive proposed activities.
    travel_legs = getattr(proposed_itinerary, "travel_legs", []) or []
    legs_by_pair = {
        (leg.origin_activity_id, leg.destination_activity_id): leg
        for leg in travel_legs
    }

    travel_rows = []

    for current, following in zip(activities, activities[1:]):
        current_end = current.start_time + timedelta(
            minutes=current.duration_minutes
        )

        leg = legs_by_pair.get(
            (current.activity_id, following.activity_id)
        )

        estimate = None
        if leg:
            estimates = getattr(leg, "estimates", []) or []
            selected_mode = getattr(leg, "selected_mode", None)

            estimate = next(
                (
                    item for item in estimates
                    if item.mode == selected_mode
                ),
                None,
            )

            if estimate is None:
                estimate = next(
                    (
                        item for item in estimates
                        if str(item.mode).lower() == "walking"
                    ),
                    None,
                )

        walking_minutes = (
            getattr(estimate, "duration_minutes", None)
            if estimate else None
        )

        available_minutes = minutes_between(
            following.start_time,
            current_end,
        )

        if available_minutes is None:
            slack = None
            status = "Cannot compare — timezone mismatch"
        elif walking_minutes is None:
            slack = None
            status = "No walking estimate"
        else:
            slack = available_minutes - walking_minutes
            status = "Sufficient time" if slack >= 0 else "Insufficient time"

        travel_rows.append({
            "From": current.name,
            "To": following.name,
            "Walking (min)": (
                walking_minutes if walking_minutes is not None else "Missing"
            ),
            "Available gap (min)": (
                round(available_minutes, 1)
                if available_minutes is not None else "Unknown"
            ),
            "Slack (min)": (
                round(slack, 1) if slack is not None else "Unknown"
            ),
            "Assessment": status,
        })

    st.write("**Walking transition feasibility**")

    if travel_rows:
        st.dataframe(
            travel_rows,
            width="content",
            hide_index=True,
        )
    else:
        st.info("There are not enough activities to assess walking transitions.")

    st.caption(
        "These checks use the proposed schedule and generated walking "
        "estimates. They do not verify venue opening hours, access, or "
        "real-world conditions. Unknown or incompatible timestamps are "
        "not treated as passing checks."
    )


def render_itinerary_changes(original_itinerary, proposed_itinerary):
    """Compare original and proposed activities using structured fields."""

    original_by_id = {
        activity.activity_id: activity
        for activity in original_itinerary.activities
    }
    proposed_by_id = {
        activity.activity_id: activity
        for activity in proposed_itinerary.activities
    }

    rows = []

    for activity_id, original in original_by_id.items():
        proposed = proposed_by_id.get(activity_id)

        if proposed is None:
            rows.append({
                "Activity": original.name,
                "Change": "Removed",
                "Original start": original.start_time.strftime("%I:%M %p"),
                "Proposed start": "—",
                "Duration change": "—",
            })
            continue

        original_start = original.start_time.replace(tzinfo=None)
        proposed_start = proposed.start_time.replace(tzinfo=None)

        start_changed = original_start != proposed_start
        duration_changed = (
            original.duration_minutes != proposed.duration_minutes
        )

        if start_changed or duration_changed:
            changes = []
            if start_changed:
                changes.append("Rescheduled")
            if duration_changed:
                changes.append("Duration changed")

            rows.append({
                "Activity": original.name,
                "Change": ", ".join(changes),
                "Original start": original.start_time.strftime("%I:%M %p"),
                "Proposed start": proposed.start_time.strftime("%I:%M %p"),
                "Duration change": (
                    f"{original.duration_minutes} → "
                    f"{proposed.duration_minutes} min"
                    if duration_changed else "Unchanged"
                ),
            })

    for activity_id, proposed in proposed_by_id.items():
        if activity_id not in original_by_id:
            rows.append({
                "Activity": proposed.name,
                "Change": "Added",
                "Original start": "—",
                "Proposed start": proposed.start_time.strftime("%I:%M %p"),
                "Duration change": f"{proposed.duration_minutes} min",
            })

    st.subheader("What changed")

    if rows:
        st.dataframe(rows, width="content", hide_index=True)
    else:
        st.info("No activity additions, removals, rescheduling, or duration changes.")


def render_recovery_result(result, original_itinerary, disruption):
    """Render a completed recovery result from Streamlit session state."""

    st.divider()
    st.header("Recovery Proposal")

    selected_option_id = result.get("selected_option_id")
    option = next(
        (
            item
            for item in result.get("recovery_options", [])
            if item.option_id == selected_option_id
        ),
        None,
    )

    if option:
        st.subheader("Proposed itinerary")

        render_itinerary_changes(
            original_itinerary,
            option.proposed_itinerary,
        )

        with st.expander("Planner rationale"):
            st.write(option.rationale)

        proposal_rows = []

        for activity in option.proposed_itinerary.activities:
            end_time = activity.start_time + timedelta(
                minutes=activity.duration_minutes
            )
            proposal_rows.append({
                "Activity": activity.name,
                "Start": activity.start_time.strftime("%I:%M %p"),
                "End": end_time.strftime("%I:%M %p"),
                "Duration (min)": activity.duration_minutes,
                "Mandatory": "Yes" if activity.mandatory else "No",
            })

        st.dataframe(
            proposal_rows,
            width="content",
            hide_index=True,
        )

        render_travel_details(option.proposed_itinerary)

        render_schedule_assessment(
            option.proposed_itinerary,
            disruption,
        )

        with st.expander("Proposal details"):
            st.write("**Preserved constraints**")
            st.write(option.preserved_constraints or ["None listed"])

            st.write("**Violated constraints**")
            st.write(option.violated_constraints or ["None listed"])

            st.write("**Trade-offs**")
            st.write(option.trade_offs or ["None listed"])

            st.write("**Assumptions**")
            st.write(option.assumptions or ["None listed"])

            st.write("**Uncertainties**")
            st.write(option.uncertainties or ["None listed"])
    else:
        st.warning("The workflow did not return a recovery proposal.")

    validation = result.get("itinerary_validation_result")

    if validation:
        st.subheader("Deterministic validation")
        st.write(f"**Status:** {validation.status.value.upper()}")

        if validation.issues:
            for issue in validation.issues:
                activity_pair = " → ".join(issue.activity_ids or [])
                message = f"{issue.issue_type.value}: {issue.description}"

                if activity_pair:
                    message += f" Activities: {activity_pair}"

                st.warning(message)
        else:
            st.success("No deterministic validation issues identified.")
    else:
        st.warning("No deterministic validation result was returned.")

    audit = result.get("audit_report")

    if audit:
        st.subheader("Auditor findings")
        st.write(f"**Assessment:** {audit.assessment.value}")

        audit_sections = {
            "Supported claims": audit.supported_claims,
            "Unsupported claims": audit.unsupported_claims,
            "Conflicting claims": audit.conflicting_claims,
            "Omitted uncertainties": audit.omitted_uncertainties,
            "Rationale findings": audit.rationale_findings,
            "Recommendations": audit.recommendations,
        }

        for heading, findings in audit_sections.items():
            with st.expander(heading):
                if findings:
                    for finding in findings:
                        st.write(f"- {finding}")
                else:
                    st.write("None reported.")

    st.divider()
    st.subheader("Your decision")

    approval_status = result.get("approval_status")
    workflow_status = result.get("status")

    if approval_status == ApprovalStatus.PENDING:
        st.info(
            "Review the proposal and its validation findings. Approval "
            "records your decision; it does not verify unconfirmed venue "
            "availability or travel feasibility."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Approve proposal", type="primary"):
                decision_result = apply_approval_decision(
                    result,
                    ApprovalStatus.APPROVED,
                )
                result.update(decision_result)
                st.session_state["recovery_result"] = result
                st.rerun()

        with col2:
            if st.button("Reject proposal"):
                decision_result = apply_approval_decision(
                    result,
                    ApprovalStatus.REJECTED,
                )
                result.update(decision_result)
                st.session_state["recovery_result"] = result
                st.rerun()

    elif approval_status == ApprovalStatus.APPROVED:
        st.success("Proposal approved.")
        st.write(
            "The approved itinerary is now recorded as the final itinerary."
        )

    elif approval_status == ApprovalStatus.REJECTED:
        st.warning("Proposal rejected. No final itinerary was created.")

    error_details = result.get("error_details")

    if error_details:
        st.error("Workflow error details")
        for error in error_details:
            st.code(str(error))

    elif workflow_status:
        st.write(f"**Current workflow status:** {workflow_status.value}")

    st.write(
        "**Workflow status:**",
        getattr(workflow_status, "value", workflow_status),
    )
    st.write(
        "**Approval status:**",
        getattr(approval_status, "value", approval_status),
    )


def main():
    st.set_page_config(
        page_title="Travel Itinerary Recovery Agent",
        page_icon="✈️",
        layout="wide",
    )

    st.title("Travel Itinerary Recovery Agent")
    st.caption(
        "Investigate disruptions and evaluate itinerary recovery proposals."
    )

    scenario_label = st.selectbox(
        "Select benchmark scenario",
        options=list(SCENARIO_FIXTURES.keys()),
        key="scenario_selection",
    )

    # A scenario change invalidates the previous proposal so results from
    # one benchmark cannot be mistaken for results from the other.
    previous_scenario = st.session_state.get("loaded_scenario")
    if previous_scenario != scenario_label:
        st.session_state["recovery_result"] = None
        st.session_state["loaded_scenario"] = scenario_label

    try:
        itinerary, disruption, investigation_context = load_inputs(
            scenario_label
        )
    except Exception as error:
        st.error(f"Unable to load scenario inputs: {error}")
        st.stop()

    st.subheader("Travel scenario")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Destination", itinerary.destination)
        st.metric(
            "Travel date",
            itinerary.itinerary_date.strftime("%B %d, %Y"),
        )

    with col2:
        st.metric("Scheduled activities", len(itinerary.activities))
        st.metric("Travel legs", len(itinerary.travel_legs))

    if investigation_context is not None:
        st.info(
            "P-02 uses the supplied synthetic benchmark weather context. "
            "It is not a live forecast."
        )

    st.divider()
    st.subheader("Original itinerary")

    itinerary_rows = []

    for activity in itinerary.activities:
        end_time = activity.start_time + timedelta(
            minutes=activity.duration_minutes
        )

        itinerary_rows.append(
            {
                "Activity": activity.name,
                "Start": activity.start_time.strftime("%I:%M %p"),
                "End": end_time.strftime("%I:%M %p"),
                "Duration (min)": activity.duration_minutes,
                "Mandatory": "Yes" if activity.mandatory else "No",
                "Setting": "Indoor" if activity.indoor else "Outdoor",
            }
        )

    st.dataframe(
        itinerary_rows,
        width='content',
        hide_index=True,
    )

    st.divider()
    st.subheader("Disruption")

    st.warning(
        f"**{disruption.scenario_type.value.replace('_', ' ').title()}** "
        f"({disruption.severity.value.title()} severity)"
    )

    st.write(disruption.description)

    affected_activities = [
        activity.name
        for activity in itinerary.activities
        if activity.activity_id in disruption.affected_activity_ids
    ]

    if affected_activities:
        st.write(
            "**Affected activities:** " + ", ".join(affected_activities)
        )

    st.info(
        "The original itinerary is preserved. The recovery workflow will "
        "produce a separate proposal for review; no changes are applied "
        "without explicit approval."
    )

    if st.button("Start Recovery", type="primary"):
        try:
            with st.spinner(
                "Investigating the disruption and generating a recovery proposal..."
            ):
                result = run_recovery_workflow(
                    itinerary,
                    disruption,
                    investigation_context=investigation_context,
                )

            st.session_state["recovery_result"] = result
            st.success("Recovery workflow finished.")

        except Exception as error:
            st.error(f"Recovery workflow failed: {error}")

    result = st.session_state.get("recovery_result")

    if result is not None:
        render_recovery_result(result, itinerary, disruption)


if __name__ == "__main__":
    main()
