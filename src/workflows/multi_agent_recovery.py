
from uuid import uuid4
from time import perf_counter

from langgraph.graph import StateGraph, START, END

from src.models.agent_state import (
    TravelAgentState,
    WorkflowStage,
    WorkflowStatus,
)
from src.models.agent_workflow import (
    Constraint,
    ConstraintType,
    ExecutionEvent,
    OptionValidation,
    RecoveryPlanningInput,
    RecoveryStrategy,
)

from src.models.validation import (
    IssueType,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from src.recovery.audit import (
    audit_recovery_proposal,
    compare_mandatory_activities,
)
from src.recovery.generation import DEFAULT_MODEL
from src.recovery.planning import plan_recovery
from src.recovery.research import research_evidence
from src.validation.schedule_validator import validate_itinerary


def validate_mandatory_activity_preservation(
    original_itinerary,
    proposed_itinerary,
    mandatory_constraints: list[Constraint],
) -> ValidationResult:
    """Deterministically check that mandatory activities are preserved."""

    issues = []

    # Check activities already marked mandatory in the original itinerary.
    comparisons = compare_mandatory_activities(
        original_itinerary=original_itinerary,
        proposed_itinerary=proposed_itinerary,
    )

    for comparison in comparisons:
        if not comparison["preserved"]:
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.MANDATORY_ACTIVITY_NOT_PRESERVED,
                    description=(
                        "Original mandatory activity "
                        f"'{comparison['activity_name']}' "
                        f"(ID: {comparison['activity_id']}) is missing "
                        "or is no longer marked mandatory in the proposal."
                    ),
                    activity_ids=[comparison["activity_id"]],
                )
            )

    # Check mandatory constraints that explicitly refer to activities.
    for constraint in mandatory_constraints:
        if constraint.constraint_type != ConstraintType.MANDATORY:
            continue

        if constraint.category.strip().casefold() != "activity":
            continue

        target = constraint.value.strip().casefold()

        matches = [
            activity
            for activity in proposed_itinerary.activities
            if target in {
                activity.activity_id.strip().casefold(),
                activity.name.strip().casefold(),
            }
        ]

        if len(matches) == 0:
            description = (
                f"Mandatory activity constraint '{constraint.constraint_id}' "
                f"('{constraint.value}') has no exact match in the proposal."
            )
            activity_ids = []

        elif len(matches) > 1:
            description = (
                f"Mandatory activity constraint '{constraint.constraint_id}' "
                f"('{constraint.value}') matches multiple proposed activities "
                "and is ambiguous."
            )
            activity_ids = [
                activity.activity_id for activity in matches
            ]

        else:
            continue

        issues.append(
            ValidationIssue(
                issue_type=IssueType.MANDATORY_ACTIVITY_NOT_PRESERVED,
                description=description,
                activity_ids=activity_ids,
            )
        )

    status = (
        ValidationStatus.INVALID
        if issues
        else ValidationStatus.VALID
    )

    return ValidationResult(status=status, issues=issues)


def build_multi_agent_recovery_graph(
    strategy: RecoveryStrategy = RecoveryStrategy.BEST_OVERALL_FEASIBILITY,
    model_name: str = DEFAULT_MODEL,
    client=None,
    additional_instructions: str = "",
):
    """Build a bounded three-agent recovery workflow.

    Researcher, Planner, and Auditor each make one LLM call.
    Coordinator nodes handle preparation, deterministic validation,
    failure routing, and finalization without LLM calls.
    """

    def make_event(stage, event_type, description, details=None):
        return ExecutionEvent(
            event_id=str(uuid4()),
            stage=stage,
            event_type=event_type,
            description=description,
            details=details or {},
        )

    def record_failure(state, stage, error, llm_call_attempted=False):
        """Record a failed stage and stop the workflow."""

        event = make_event(
            stage=stage,
            event_type="agent_failed",
            description=f"The {stage} stage failed.",
            details={"error": str(error)},
        )

        stage_mapping = {
            "initialization": WorkflowStage.INITIALIZATION,
            "research": WorkflowStage.INVESTIGATION,
            "planning": WorkflowStage.RECOVERY_PLANNING,
            "validation": WorkflowStage.VALIDATION,
            "audit": WorkflowStage.VALIDATION,
        }

        return {
            "current_stage": stage_mapping[stage],
            "status": WorkflowStatus.FAILED,
            "error_details": [f"{stage}: {error}"],
            "llm_call_count": (
                state["llm_call_count"] + 1
                if llm_call_attempted
                else state["llm_call_count"]
            ),
            "execution_trace": [event],
        }

    def prepare_recovery_input(state: TravelAgentState):
        workflow_started_at = perf_counter()

        try:
            disruption = state["disruption_scenario"]
            investigation = state["investigation_result"]

            if disruption is None:
                raise ValueError(
                    "A disruption scenario is required for recovery."
                )

            if investigation is None:
                raise ValueError(
                    "An investigation result is required for recovery."
                )

            planning_input = RecoveryPlanningInput(
                original_itinerary=state["original_itinerary"],
                disruption_scenario=disruption,
                investigation_result=investigation,
                mandatory_constraints=state["mandatory_constraints"],
                flexible_preferences=state["flexible_preferences"],
                user_instructions=state["user_instructions"],
                strategy=strategy,
                revision_count=state["revision_count"],
                rejected_options=state["rejected_options"],
                additional_instructions=additional_instructions,
            )

            event = make_event(
                stage="recovery_planning",
                event_type="input_prepared",
                description="Prepared shared recovery planning input.",
                details={"strategy": strategy.value},
            )

            return {
                "recovery_planning_input": planning_input,
                "workflow_started_at": workflow_started_at,
                "current_stage": WorkflowStage.INVESTIGATION,
                "execution_trace": [event],
            }

        except Exception as error:
            return record_failure(
                state,
                "initialization",
                error,
            )

    def research_context(state: TravelAgentState):
        llm_call_attempted = False

        try:
            investigation = state["investigation_result"]
            disruption = state["disruption_scenario"]

            if investigation is None or disruption is None:
                raise ValueError(
                    "Investigation result and disruption scenario are required."
                )

            llm_call_attempted = True
            result = research_evidence(
                investigation=investigation,
                disruption=disruption,
                model_name=model_name,
                client=client,
            )

            # Record the complete source inventory supplied to the
            # Researcher. This is deterministic provenance metadata,
            # not an LLM judgment about evidence quality.
            expected_source_ids = sorted(
                {
                    evidence.source_id
                    for evidence in investigation.retrieved_evidence
                }
            )

            result.evidence_brief.source_ids_reviewed = expected_source_ids

            metadata = {
                "model_name": result.model_name,
                "latency_seconds": result.latency_seconds,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }

            event = make_event(
                stage="investigation",
                event_type="evidence_brief_created",
                description="Researcher created an evidence brief.",
                details={
                    "model_name": result.model_name,
                    "latency_seconds": result.latency_seconds,
                    "source_count": len(
                        result.evidence_brief.source_ids_reviewed
                    ),
                },
            )

            return {
                "evidence_brief": result.evidence_brief,
                "research_generation_metadata": metadata,
                "research_raw_response": result.raw_response,
                "llm_call_count": state["llm_call_count"] + 1,
                "current_stage": WorkflowStage.RECOVERY_PLANNING,
                "execution_trace": [event],
            }

        except Exception as error:
            return record_failure(
                state,
                "research",
                error,
                llm_call_attempted=llm_call_attempted,
            )

    def generate_plan(state: TravelAgentState):
        llm_call_attempted = False

        try:
            planning_input = state["recovery_planning_input"]
            evidence_brief = state["evidence_brief"]

            if planning_input is None:
                raise ValueError("Recovery planning input is missing.")

            if evidence_brief is None:
                raise ValueError("Researcher evidence brief is missing.")

            llm_call_attempted = True
            result = plan_recovery(
                planning_input=planning_input,
                evidence_brief=evidence_brief,
                model_name=model_name,
                client=client,
            )

            option = result.recovery_option

            investigation = state["investigation_result"]

            if investigation is None:
                raise ValueError(
                    "Investigation result is required for evidence validation."
                )

            available_source_ids = {
                evidence.source_id
                for evidence in investigation.retrieved_evidence
            }

            invalid_source_ids = (
                set(option.supporting_evidence_ids)
                - available_source_ids
            )

            if invalid_source_ids:
                raise ValueError(
                    "Planner referenced evidence IDs not present in the "
                    f"investigation: {sorted(invalid_source_ids)}"
                )

            metadata = {
                "model_name": result.model_name,
                "latency_seconds": result.latency_seconds,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }

            event = make_event(
                stage="recovery_planning",
                event_type="proposal_generated",
                description="Planner generated one recovery proposal.",
                details={
                    "option_id": option.option_id,
                    "model_name": result.model_name,
                    "latency_seconds": result.latency_seconds,
                },
            )

            return {
                "recovery_options": [option],
                "selected_option_id": option.option_id,
                "planning_rationale": option.rationale,
                "planning_generation_metadata": metadata,
                "llm_call_count": state["llm_call_count"] + 1,
                "current_stage": WorkflowStage.VALIDATION,
                "execution_trace": [event],
                "planning_raw_response": result.raw_response,
            }

        except Exception as error:
            return record_failure(
                state,
                "planning",
                error,
                llm_call_attempted=llm_call_attempted,
            )

    def validate_proposal(state: TravelAgentState):
        try:
            option_id = state["selected_option_id"]

            if option_id is None or not state["recovery_options"]:
                raise ValueError("No recovery proposal is available.")

            option = next(
                (
                    item
                    for item in state["recovery_options"]
                    if item.option_id == option_id
                ),
                None,
            )

            if option is None:
                raise ValueError(
                    "Selected recovery proposal was not found."
                )

            validation_result = validate_itinerary(
                option.proposed_itinerary
            )

            mandatory_validation = validate_mandatory_activity_preservation(
                original_itinerary=state["original_itinerary"],
                proposed_itinerary=option.proposed_itinerary,
                mandatory_constraints=state["mandatory_constraints"],
            )

            combined_issues = (
                validation_result.issues
                + mandatory_validation.issues
            )
            
            if (
                validation_result.status == ValidationStatus.INVALID
                or mandatory_validation.status == ValidationStatus.INVALID
            ):
                combined_status = ValidationStatus.INVALID

            elif validation_result.status == ValidationStatus.INCOMPLETE:
                combined_status = ValidationStatus.INCOMPLETE

            else:
                combined_status = ValidationStatus.VALID

            validation_result = ValidationResult(
                status=combined_status,
                issues=combined_issues,
            )

            option_validation = OptionValidation(
                option_id=option_id,
                validation_result=validation_result,
            )

            validation_warnings = []

            if validation_result.status == ValidationStatus.INCOMPLETE:
                validation_warnings.append(
                    "The recovery proposal is incomplete. "
                    "Review the unresolved validation issues before relying "
                    "on its feasibility."
                )
                validation_warnings.extend(
                    issue.description
                    for issue in validation_result.issues
                )

            event = make_event(
                stage="validation",
                event_type="proposal_validated",
                description=(
                    "Completed deterministic itinerary and mandatory "
                    "activity validation."
                ),
                details={
                    "option_id": option_id,
                    "validation_status": validation_result.status.value,
                    "issue_count": len(validation_result.issues),
                },
            )

            return {
                "validation_results": [option_validation],
                "itinerary_validation_result": validation_result,
                "warnings": validation_warnings,
                "current_stage": WorkflowStage.VALIDATION,
                "execution_trace": [event],
            }

        except Exception as error:
            return record_failure(
                state,
                "validation",
                error,
            )


    def audit_proposal(state: TravelAgentState):
        llm_call_attempted = False

        try:
            planning_input = state["recovery_planning_input"]
            evidence_brief = state["evidence_brief"]
            option_id = state["selected_option_id"]

            if planning_input is None or evidence_brief is None:
                raise ValueError(
                    "Planning input and evidence brief are required."
                )

            option = next(
                (
                    item
                    for item in state["recovery_options"]
                    if item.option_id == option_id
                ),
                None,
            )

            if option is None:
                raise ValueError(
                    "Recovery proposal for audit was not found."
                )

            validation_result = state["itinerary_validation_result"]


            schedule_findings = assess_schedule_preservation(
                original_itinerary=planning_input.original_itinerary,
                proposed_itinerary=option.proposed_itinerary,
                affected_activity_ids=(
                    planning_input.disruption_scenario.affected_activity_ids
                ),
            )

            validation_data = (
                validation_result.model_dump(mode="json")
                if validation_result is not None
                else {}
            )

            validation_data["schedule_preservation_findings"] = schedule_findings


            llm_call_attempted = True
            result = audit_recovery_proposal(
                planning_input=planning_input,
                evidence_brief=evidence_brief,
                recovery_option=option,
                deterministic_validation=validation_data,
                model_name=model_name,
                client=client,
            )

            metadata = {
                "model_name": result.model_name,
                "latency_seconds": result.latency_seconds,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }

            event = make_event(
                stage="validation",
                event_type="proposal_audited",
                description="Auditor completed the evidence and rationale review.",
                details={
                    "assessment": result.audit_report.assessment.value,
                    "model_name": result.model_name,
                    "latency_seconds": result.latency_seconds,
                },
            )

            return {
                "audit_report": result.audit_report,
                "audit_generation_metadata": metadata,
                "llm_call_count": state["llm_call_count"] + 1,
                "current_stage": WorkflowStage.FINALIZATION,
                "execution_trace": [event],
                "audit_raw_response": result.raw_response,
            }

        except Exception as error:
            return record_failure(
                state,
                "audit",
                error,
                llm_call_attempted=llm_call_attempted,
            )


    def finalize_workflow(state: TravelAgentState):
        """Finalize workflow metadata and preserve deterministic outcome."""
        validation_result = state.get("itinerary_validation_result")

        no_valid_recovery = (
            validation_result is not None
            and validation_result.status == ValidationStatus.INVALID
        )

        final_status = (
            WorkflowStatus.NO_VALID_RECOVERY
            if no_valid_recovery
            else WorkflowStatus.COMPLETED
        )

        event = make_event(
            stage="finalization",
            event_type=(
                "no_valid_recovery"
                if no_valid_recovery
                else "workflow_completed"
            ),
            description=(
                "No valid recovery proposal was produced. "
                "The proposal is retained for diagnosis but is not "
                "presented as a valid recovery."
                if no_valid_recovery
                else "Multi-agent recovery generation, validation, and audit "
                "completed. No user approval or execution is implied."
            ),
            details={
                "llm_call_count": state["llm_call_count"],
                "tool_call_count": state["total_tool_call_count"],
                "validation_status": (
                    validation_result.status.value
                    if validation_result is not None
                    else None
                ),
            },
        )

        agent_metadata = [
            state.get("research_generation_metadata"),
            state.get("planning_generation_metadata"),
            state.get("audit_generation_metadata"),
        ]

        completed_metadata = [
            metadata
            for metadata in agent_metadata
            if metadata is not None
        ]

        input_tokens = [
            metadata.get("input_tokens")
            for metadata in completed_metadata
        ]
        output_tokens = [
            metadata.get("output_tokens")
            for metadata in completed_metadata
        ]

        total_input_tokens = (
            sum(input_tokens)
            if len(input_tokens) == 3
            and all(value is not None for value in input_tokens)
            else None
        )

        total_output_tokens = (
            sum(output_tokens)
            if len(output_tokens) == 3
            and all(value is not None for value in output_tokens)
            else None
        )

        total_latency_seconds = sum(
            float(metadata["latency_seconds"])
            for metadata in completed_metadata
            if metadata.get("latency_seconds") is not None
        )

        workflow_started_at = state.get("workflow_started_at")

        total_workflow_latency_seconds = (
            perf_counter() - workflow_started_at
            if workflow_started_at is not None
            else None
        )

        aggregate_metadata = {
            "agent_count": len(completed_metadata),
            "total_llm_calls": state.get("llm_call_count", 0),
            "total_latency_seconds": total_latency_seconds,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "input_tokens_complete": total_input_tokens is not None,
            "output_tokens_complete": total_output_tokens is not None,
            "total_workflow_latency_seconds": total_workflow_latency_seconds,
        }

        return {
            "current_stage": WorkflowStage.COMPLETED,
            "status": final_status,
            "final_itinerary": None,
            "execution_trace": [event],
            "multi_agent_generation_metadata": aggregate_metadata,
        }


    def route_on_status(state: TravelAgentState):
        if state["status"] == WorkflowStatus.FAILED:
            return END
        return "continue"


    def assess_schedule_preservation(
            original_itinerary,
            proposed_itinerary,
            affected_activity_ids,
        ):
        """Identify schedule changes to retained activities."""
        
        original_by_id = {
            activity.activity_id: activity
            for activity in original_itinerary.activities
        }
        proposed_by_id = {
            activity.activity_id: activity
            for activity in proposed_itinerary.activities
        }

        findings = []
        
        affected_ids = set(affected_activity_ids)

        for activity_id, original in original_by_id.items():
            if activity_id in affected_ids:
                continue

            proposed = proposed_by_id.get(activity_id)

            if proposed is None:
                continue

            changed = (
                original.start_time != proposed.start_time
                or original.duration_minutes != proposed.duration_minutes
            )

            if changed:
                findings.append({
                    "activity_id": activity_id,
                    "activity_name": original.name,
                    "original_start_time": original.start_time.isoformat(),
                    "proposed_start_time": proposed.start_time.isoformat(),
                    "original_duration_minutes": original.duration_minutes,
                    "proposed_duration_minutes": proposed.duration_minutes,
                    "reason": (
                        "An existing activity's schedule changed. Review whether the "
                        "change is necessary and supported by the disruption, evidence, "
                        "and travel estimates. This finding alone does not establish "
                        "that the change is unjustified."
                    ),
                })

        return findings



    graph = StateGraph(TravelAgentState)

    graph.add_node("prepare_recovery_input", prepare_recovery_input)
    graph.add_node("research_context", research_context)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("validate_proposal", validate_proposal)
    graph.add_node("audit_proposal", audit_proposal)
    graph.add_node("finalize_workflow", finalize_workflow)

    graph.add_edge(START, "prepare_recovery_input")

    graph.add_conditional_edges(
        "prepare_recovery_input",
        route_on_status,
        {
            "continue": "research_context",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "research_context",
        route_on_status,
        {
            "continue": "generate_plan",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "generate_plan",
        route_on_status,
        {
            "continue": "validate_proposal",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "validate_proposal",
        route_on_status,
        {
            "continue": "audit_proposal",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "audit_proposal",
        route_on_status,
        {
            "continue": "finalize_workflow",
            END: END,
        },
    )

    graph.add_edge("finalize_workflow", END)

    return graph.compile()
