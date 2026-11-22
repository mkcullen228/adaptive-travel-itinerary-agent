# Adaptive Travel Itinerary Recovery Agent
## Phase 5 Benchmark Summary and Phase 6 Test Plan

### 1. Phase 5 — LLM Integration and Benchmarking

**Primary objective:** Evaluate whether the selected LLM can generate structured, evidence-aware itinerary recovery proposals while respecting mandatory constraints and schedule feasibility.

**Baseline model:** Qwen 3.5 4B, running locally through Ollama.

**Model configuration:**
- Thinking disabled for structured recovery generation.
- Temperature set to 0.
- Pydantic structured output using the RecoveryOption schema.
- Deterministic validation performed independently of model generation.

#### Benchmark findings

**P-01: Activity unavailability**
- Evaluated activity removal and preservation of mandatory activities.
- Identified unsupported assumptions about replacement activities and venue availability.
- Demonstrated improvements in evidence and uncertainty handling through prompt iterations.
- Identified discrepancies between the model's rationale and actual schedule changes.

**P-02: Heavy rain disruption**
- Tested minimal-disruption and best-overall-feasibility strategies.
- Minimal disruption preserved schedule validity but failed to resolve the weather disruption.
- Best overall feasibility attempted to reschedule outdoor activities but introduced schedule overlaps and insufficient travel time.
- Repeated generation reproduced the same key scheduling failures.
- No verified indoor replacement activities were available in the supplied investigation context.

#### Key conclusions

1. Structurally valid JSON does not guarantee a feasible itinerary.
2. Schedule validity and disruption-resolution effectiveness must be evaluated independently.
3. Narrative consistency must be evaluated separately from structured output.
4. Missing travel estimates and unverified venue availability must remain explicit uncertainties.
5. Deterministic validation provides an important safeguard against model-generated scheduling errors.
6. Prompt and strategy changes should be evaluated through controlled experiments.

#### Outstanding Phase 5 work

- Compare the four-agent workflow against a lightweight single-agent baseline.
- Use the same model, benchmark scenarios, and evaluation rubric.
- Compare recovery quality, constraint adherence, evidence grounding, schedule feasibility, latency, and resource consumption.
- Document whether the added agent complexity produces measurable benefits.

### 2. Phase 6 — End-to-End Testing

**Primary objective:** Verify that the complete application workflow behaves reliably, from initial itinerary input through investigation, retrieval, recovery planning, validation, and final reporting.

#### Proposed test scenarios

| Scenario | Expected behavior |
|---|---|
| Normal itinerary | Process and validate an itinerary without unnecessary recovery actions. |
| Weather disruption | Identify affected activities and propose evidence-supported recovery options. |
| Venue unavailable | Investigate alternatives or clearly report that no verified alternative is available. |
| Missing travel data | Treat missing estimates as unknown; do not invent routes or durations. |
| Conflicting evidence | Identify conflicts and communicate source reliability and uncertainty. |
| No feasible recovery | Explain constraint conflicts and request user approval before relaxing flexible constraints. |

#### Evaluation dimensions

- Structured output validity
- Deterministic schedule validity
- Mandatory constraint preservation
- Flexible constraint adherence
- Disruption resolution
- Evidence grounding and source reliability
- Narrative-to-itinerary consistency
- Uncertainty handling
- Agent/tool execution trace
- Latency and resource consumption

#### Phase 6 acceptance goals

- The workflow completes successfully for supported scenarios.
- Invalid schedules are detected before recommendations are presented as feasible.
- The agent does not invent missing travel estimates or evidence.
- Mandatory constraints are never silently relaxed.
- Conflicting or insufficient evidence is communicated clearly.
- The agent can explain when no feasible recovery is available.
- Tool calls and agent feedback loops remain bounded and observable.
- Evaluation results are reproducible and recorded separately from raw model responses.

### 3. Phase 7 — Interactive Application

The final application will demonstrate:
- Initial itinerary and disruption input.
- Agent workflow and investigation trace.
- Retrieved evidence and source reliability.
- Proposed itinerary and schedule changes.
- Validation results and constraint preservation.
- Remaining uncertainties and trade-offs.
- An evidence-backed recovery report.

### 4. Immediate Next Milestone

Complete the single-agent versus multi-agent comparison, then begin Phase 6 with the normal-itinerary scenario as the initial end-to-end integration test.