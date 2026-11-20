# Initial Architecture Benchmark: Single-Agent vs. Multi-Agent

**Benchmark:** P-01  
**Model:** `qwen3.5:4b`  
**Strategy:** `minimal_disruption`  
**Date:** November 2026  
**Status:** Initial comparison complete

## 1. Objective

Compare a single-agent recovery workflow against a multi-agent workflow using the same itinerary, disruption scenario, investigation context, model, and deterministic evaluation criteria.

The objective was to assess recovery proposal quality, constraint preservation, evidence handling, workflow reliability, and computational cost.

## 2. Architecture comparison

| Metric | Single-agent | Multi-agent |
|---|---:|---:|
| LLM calls | 1 | 3 |
| Input tokens | 2,420 | 7,169 |
| Output tokens | 1,184 | 1,816 |
| LLM latency | ~39.18 sec | 62.80 sec |
| Deterministic validation | Incomplete | Incomplete |

The multi-agent workflow consists of a Researcher, Planner, and Auditor, coordinated through deterministic orchestration.

## 3. Shared results

Both architectures:
- Generated valid structured recovery proposals.
- Removed the unavailable National Gallery of Art.
- Preserved the mandatory National Museum of Natural History.
- Addressed the affected activity.
- Failed deterministic validation because three consecutive travel legs lacked travel estimates.

The missing estimates prevented the evaluator from establishing schedule feasibility.

## 4. Observed differences

**Single-agent**
- Generated a recovery proposal in one LLM call.
- Rescheduled all four remaining activities, with substantial changes to their original start times.
- Did not provide a separate independent audit.

**Multi-agent**
- Used three LLM calls to separate evidence interpretation, planning, and auditing.
- Produced a separate evidence brief and audit report.
- Preserved the original sequence and scheduled times of the remaining activities.
- The Auditor independently identified the missing travel estimates and highlighted unverified venue availability assumptions.

## 5. Initial interpretation

The multi-agent architecture provided more explicit separation of responsibilities and an independent review of the recovery proposal.

However, this came with higher computational cost: approximately 2.96 times the input tokens and 1.60 times the LLM latency of the single-agent run.

Both architectures had the same deterministic validation outcome. Therefore, the initial experiment does not establish that the multi-agent architecture produces a more feasible recovery itinerary.

The multi-agent workflow demonstrated additional transparency and review capability, but its overall advantage remains to be evaluated against its resource cost.

## 6. Limitations

- Only one benchmark scenario was evaluated.
- Only one run per architecture was used.
- The investigation fixture contained no retrieved evidence sources.
- Walking travel estimates were unavailable for all three remaining travel legs.
- The comparison does not establish statistical reliability or generalizability across scenarios.

## 7. Conclusion

The initial benchmark establishes a working baseline for both architectures.

The single-agent approach is less expensive and faster. The multi-agent approach provides explicit evidence interpretation and independent auditing, with additional latency and token consumption.

Further experiments are needed to determine whether these additional capabilities produce sufficiently better recovery decisions to justify the cost.

**Benchmark artifacts**

- Single-agent: `data/evaluations/architecture_comparison/single_agent/`
- Multi-agent: `data/evaluations/architecture_comparison/multi_agent/`
- Deterministic evaluation: `data/evaluations/deterministic_results/qwen_3_5_4b/P-01.json`
