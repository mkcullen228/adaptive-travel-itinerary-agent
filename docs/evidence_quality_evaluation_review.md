# Phase A — Evidence Quality Evaluation Review

**Status:** Evaluation and analysis in progress  
**Scope:** Researcher, Planner, and Auditor behavior across five controlled evidence-quality scenarios.

## 1. Objective

Evaluate whether the multi-agent recovery workflow interprets evidence quality appropriately, produces constraint-preserving recovery proposals, and communicates uncertainty and limitations.

The evaluation distinguishes between:
- Evidence interpretation and provenance.
- Recovery recommendation quality.
- Deterministic schedule validation.
- Auditor assessment and uncertainty communication.
- Workflow completion and overall proposal acceptability.

## 2. Scenario coverage

| Scenario | Evidence condition | Intended evaluation |
|---|---|---|
| E1 | High quality | Appropriate use of reliable, current evidence |
| E2 | Low reliability | Recognition of weak evidence and cautious conclusions |
| E3 | Stale | Recognition that historical evidence cannot establish current availability |
| E4 | Conflicting | Recognition of contradictory claims and need for resolution |
| E5 | Missing | Avoidance of unsupported claims when evidence is unavailable |

The five scenarios provide a useful controlled test set. They do not establish broad statistical robustness across all possible disruptions, evidence sources, or itinerary configurations.

## 3. Evaluation strengths

- Researcher evaluation checks finding status, source IDs, provenance, and evidence-quality warnings.
- Planner evaluation checks mandatory-visit preservation, duplicate prevention, evidence provenance, uncertainty, and preservation of unaffected activities.
- Deterministic schedule validation operates independently of the LLM-based Auditor.
- The Auditor receives the proposal and validation findings and provides an independent assessment.
- Raw responses and token/latency metadata are retained for analysis.

These are appropriate foundations for evaluating a multi-agent recovery workflow.

## 4. Limitations and findings

### 4.1 Overall evaluation calculation

The current runner records the Auditor evaluation but calculates `overall_evaluation_passed` using only Researcher and Planner results.

Consequently, an Auditor failure can coexist with an overall passing result. The aggregate calculation should account for all required evaluations, or report component outcomes separately without presenting an incomplete aggregate as a full pass.

### 4.2 Auditor uncertainty evaluation

The current uncertainty-coverage approach relies substantially on phrase matching. This does not reliably distinguish between:
- Mentioning an uncertainty.
- Explaining why the uncertainty matters.
- Explaining how it affects the feasibility or reliability of the proposed recovery.

E3 illustrates this limitation. The latest reviewed Auditor report identified stale evidence, missing travel estimates, and unverified schedule feasibility, yet the uncertainty-coverage check failed.

This does not prove the evaluator is incorrect in every respect. It does show that the current score is not a sufficiently reliable standalone measure of substantive uncertainty communication.

### 4.3 Evaluator version consistency

Historical Auditor evaluator files contain materially different implementations, including versions where uncertainty coverage was not meaningfully evaluated.

Results produced under different evaluator versions should not be treated as directly comparable. Future result artifacts should identify the evaluator version used.

### 4.4 Model-output variability

Historical E3 runs show variation in Planner scheduling behavior and Auditor evaluation outcomes. A single run per scenario is insufficient to establish consistent behavior or superiority.

The results should be presented as observed examples, not statistically conclusive performance estimates.

### 4.5 Scenario coverage

The five scenarios test distinct evidence conditions but do not cover every possible combination of evidence quality, missing information, conflicting constraints, and schedule feasibility.

The current scenario set is appropriate for a focused MVP evaluation, provided this limitation is stated explicitly.

## 5. Phase A decisions

1. Retain the five existing scenarios.
2. Retain Researcher provenance and evidence-quality checks.
3. Retain Planner constraint-preservation and deterministic schedule checks.
4. Treat Auditor uncertainty coverage as a limitation requiring clearer evaluation semantics.
5. Correct the overall evaluation calculation before relying on aggregate pass rates.
6. Record evaluator versions when comparing historical results.
7. Avoid scenario-specific prompt tuning based solely on one failed run.
8. Report workflow completion, proposal validity, and Auditor quality as distinct outcomes.

## 6. Conclusion

The current evaluation framework provides a useful foundation for assessing evidence-aware itinerary recovery. It tests important behaviors across the Researcher, Planner, and Auditor while keeping deterministic validation separate from LLM judgment.

However, the aggregate pass calculation and Auditor uncertainty measure limit the reliability of the current evaluation results. These limitations should be addressed or explicitly documented before drawing conclusions about overall system quality.

The current results support qualitative observations about system behavior, but do not yet establish consistent performance across repeated runs.

## 7. Phase A completion criteria

- [x] Design controlled evidence scenarios.
- [x] Define evaluation criteria.
- [x] Implement evaluation fixtures, tests, and runner.
- [x] Review scenario coverage and historical results.
- [ ] Resolve or document the overall evaluation calculation.
- [ ] Define how Auditor uncertainty quality will be reported.
- [ ] Finalize Phase A report and explicitly announce transition before Phase B.

**Phase status: Open.** Phase B has not started.