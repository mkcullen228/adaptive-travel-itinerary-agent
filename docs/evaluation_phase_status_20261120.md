# Phase A — Evidence Quality Evaluation Review

## 1. Objective

Phase A evaluates whether the Travel Itinerary Recovery Agent interprets retrieved evidence appropriately, produces recovery recommendations grounded in that evidence, and independently identifies limitations and risks.

The evaluation focuses on evidence quality and decision reliability rather than simply whether the workflow completes successfully.

## 2. Evaluation scenarios

Five controlled scenarios were developed to test different evidence conditions:

| Scenario | Evidence condition |
|---|---|
| E1 — High Quality | Reliable, relevant evidence |
| E2 — Low Reliability | Evidence with limited reliability |
| E3 — Stale | Evidence that may no longer reflect current conditions |
| E4 — Conflicting | Evidence sources that disagree |
| E5 — Missing | Incomplete or unavailable evidence |

The scenarios use a consistent recovery problem involving an unavailable National Gallery of Art visit and a proposed recovery involving an existing mandatory National Museum of Natural History visit.

These are synthetic evaluation scenarios, not claims about actual venue availability.

## 3. Evaluation design

The evaluation separates responsibilities across three components:

- **Researcher:** Evaluates evidence interpretation, source provenance, reliability, and uncertainty.
- **Planner:** Evaluates recovery recommendations, evidence support, and preservation of itinerary constraints.
- **Auditor:** Independently evaluates the proposed recovery, including evidence limitations, conflicts, and schedule accuracy.
- **Deterministic validation:** Separately checks schedule and itinerary constraints.

Workflow completion, proposal validity, and evaluation quality are treated as distinct outcomes.

## 4. Findings

### Researcher

The evaluation provides a structured way to assess whether the Researcher identifies relevant evidence and communicates its limitations.

Source provenance remains important: recommendations should be traceable to retrieved evidence rather than unsupported assumptions or interpretations presented as independent evidence.

### Planner

The Planner evaluation checks whether recovery recommendations preserve mandatory activities, avoid unsupported claims, and minimize unnecessary changes to unaffected activities.

Testing also exposed variability in schedule preservation. In some E3 runs, unaffected activities were shifted despite instructions to preserve their original times and durations.

This suggests that prompt instructions alone do not guarantee consistent constraint preservation.

### Auditor

The Auditor provides an independent review of the proposed recovery. Its evaluation includes mandatory activity accuracy, conflict recognition, evidence limitation recognition, schedule accuracy, and `uncertainty_coverage`.

The existing `uncertainty_coverage` metric is retained. It is a heuristic acknowledgment check based on expected uncertainty conditions and language in the audit report. It should not be interpreted as a comprehensive measure of substantive reasoning.

In particular, phrase matching cannot reliably determine whether the Auditor explains how an uncertainty affects recovery feasibility. The current approach also has limitations in connecting individual deterministic validation failures to specific explanations in the report.

No additional metric or implementation change is proposed for this phase. Results should be interpreted alongside the actual Auditor report.

## 5. Evaluation limitations

### Aggregate evaluation

The overall evaluation result should require all three evaluations—Researcher, Planner, and Auditor—to exist and pass.

A missing Auditor evaluation must not result in an overall pass.

This is the agreed evaluation rule. The local runner implementation still needs to be verified to ensure the change preserves existing workflow-status handling, deterministic validation inputs, and result output.

### Evaluator version consistency

Historical Auditor results were generated using different evaluator versions. Some earlier versions handled uncertainty differently, including a version that effectively hardcoded a passing result.

Consequently, historical results across evaluator versions are not directly comparable. Future evaluation artifacts should identify the evaluator version used.

### Model variability

Repeated runs demonstrated variation in Planner and Auditor outcomes. A single run per scenario is not sufficient to establish consistent performance or statistical robustness.

### Scenario coverage

The five scenarios provide focused coverage of the evidence conditions relevant to the MVP. They do not establish broad robustness across all possible itinerary disruptions or evidence conditions.

## 6. Decisions

1. Retain the five existing evaluation scenarios.
2. Keep Researcher provenance, Planner constraint preservation, and deterministic schedule validation as distinct checks.
3. Retain the existing `uncertainty_coverage` metric, documenting it as a heuristic acknowledgment check.
4. Require Researcher, Planner, and Auditor evaluations to all exist and pass for an overall evaluation pass.
5. Preserve evaluator-version information in future result artifacts.
6. Interpret individual evaluation results alongside the underlying reports and execution traces.
7. Avoid additional E3-specific prompt or evaluator tuning based on isolated runs.

## 7. Conclusion

The Phase A evaluation framework provides a useful foundation for assessing evidence quality and recovery reliability. It distinguishes evidence interpretation, planning, independent auditing, and deterministic validation rather than relying on a single accuracy or completion measure.

The results also demonstrate why evaluation outcomes need context. Heuristic checks, evaluator-version changes, and model variability can affect reported performance.

The next phase should build on this evaluation foundation without treating the current results as proof of broad system reliability.

## 8. Phase A completion checklist

- [x] Design controlled evidence scenarios.
- [x] Define evaluation criteria.
- [x] Implement evaluation fixtures, tests, and runner.
- [x] Review scenario coverage and historical results.
- [x] Decide how Auditor uncertainty coverage should be interpreted and reported.
- [ ] Verify the aggregate evaluation correction in the local runner.
- [ ] Finalize and save the Phase A report.
- [ ] Explicitly announce the transition to Phase B.