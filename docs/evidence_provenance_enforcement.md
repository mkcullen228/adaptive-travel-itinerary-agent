# Evidence Provenance Enforcement

## 1. Background

The initial multi-agent architecture benchmark identified a provenance issue in the Planner's output. The Planner referenced contextual identifiers, including investigation and disruption scenario IDs, as supporting evidence sources.

These identifiers provide workflow context but do not represent retrieved evidence. Accepting them as evidence references could make unsupported claims appear substantiated.

## 2. Design Objective

Ensure that every evidence ID cited by the Planner corresponds to an original retrieved evidence record.

The system must:
- Accept valid references to retrieved evidence.
- Reject references to identifiers that are not present in retrieved evidence.
- Return an empty evidence reference list when no retrieved evidence is available.
- Prevent Researcher interpretations from being treated as independent evidence sources.

## 3. Implementation

### Prompt-level controls

Multi-agent-specific provenance instructions are included in the Planner's generation messages when an EvidenceBrief is supplied.

The instructions distinguish original retrieved evidence from contextual identifiers and Researcher interpretations.

These instructions are conditional, preserving the single-agent baseline prompt.

### Deterministic validation

After the Planner generates a recovery option, the multi-agent workflow:

1. Retrieves the original investigation result.
2. Builds a set of available source IDs from `retrieved_evidence`.
3. Compares the Planner's `supporting_evidence_ids` against that set.
4. Raises an error if any referenced ID is unavailable.

This check occurs before the Auditor runs. Invalid references therefore stop the workflow rather than proceeding to audit.

## 4. Test Coverage

Three provenance scenarios are covered:

| Scenario | Expected behavior |
|---|---|
| No retrieved evidence and no Planner citations | Accept |
| No retrieved evidence and an invalid Planner citation | Reject |
| Retrieved evidence with a matching Planner citation | Accept |

The invalid-reference test also verifies that the Auditor is not called after the Planner fails.

## 5. Architectural Rationale

The implementation combines LLM instructions with deterministic enforcement.

Prompt instructions guide the Planner toward correct behavior, while Python validation independently enforces the provenance requirement.

This separation avoids relying exclusively on model compliance for an important quality-control requirement.

## 6. Validation Status

The full pytest suite passes following implementation of the provenance controls.

The single-agent baseline prompt remains unchanged.