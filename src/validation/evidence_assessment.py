import re

from src.models.evidence import EvidenceAssessment
from src.models.retrieved_evidence import RetrievedEvidence


def assess_claim_evidence(
    claim: str,
    evidence: list[RetrievedEvidence],
) -> EvidenceAssessment:

    statements = split_claim_into_statements(claim)

    supported_statements = []
    unsupported_statements = []
    supporting_sources = set()
    conflicting_sources = set()
    conflicting_statements = []
    conflict_details = []

    for statement in statements:

        # Find evidence that directly supports this statement.
        supporting_evidence = [
            item
            for item in evidence
            if statement.lower() in item.content.lower()
        ]

        statement_supported_by = [
            item.source_id for item in supporting_evidence
        ]

        if supporting_evidence:
            supported_statements.append(statement)
            supporting_sources.update(statement_supported_by)

            # Identify the subject associated with the supporting evidence.
            subjects = {
                item.subject.lower()
                for item in supporting_evidence
            }

            # Only assess conflicts when the supporting evidence
            # refers to one unambiguous subject.
            if len(subjects) == 1:
                subject = supporting_evidence[0].subject

                if has_conflicting_evidence(statement, evidence, subject):
                    conflicting_statements.append(statement)

                    conflict_details.extend(
                        describe_conflicting_evidence(
                            statement, evidence, subject
                        )
                    )

                    for item in evidence:
                        if item.subject.lower() != subject.lower():
                            continue

                        evidence_time = extract_closing_time(item.content)

                        if evidence_time is not None:
                            if evidence_time == extract_closing_time(statement):
                                supporting_sources.add(item.source_id)
                            else:
                                conflicting_sources.add(item.source_id)

        else:
            unsupported_statements.append(statement)

    if conflicting_statements:
        status = "conflicting"
    elif supported_statements and unsupported_statements:
        status = "partially_supported"
    elif supported_statements:
        status = "supported"
    else:
        status = "unsupported"

    return EvidenceAssessment(
        claim=claim,
        status=status,
        supporting_source_ids=sorted(supporting_sources),
        conflicting_source_ids=sorted(conflicting_sources),
        explanation=(
            f"Supported statements: {supported_statements}. "
            f"Unsupported statements: {unsupported_statements}. "
            f"Conflicting evidence: {conflict_details}."
        ),
    )


def split_claim_into_statements(claim: str) -> list[str]:
    statements = claim.split(" and ")

    return [
        statement.strip().rstrip(".")
        for statement in statements
        if statement.strip()
    ]


def has_conflicting_evidence(
    statement: str,
    evidence: list[RetrievedEvidence],
    subject: str,
    ) -> bool:
    claim_time = extract_closing_time(statement)

    if claim_time is None:
        return False

    for item in evidence:
        if item.subject.lower() != subject.lower():
            continue

        evidence_time = extract_closing_time(item.content)

        if evidence_time is not None and evidence_time != claim_time:
            return True

    return False


def extract_closing_time(text: str) -> str | None:
    match = re.search(
        r"\bcloses at\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM))\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).replace(" ", "").upper()


def describe_conflicting_evidence(
    statement: str,
    evidence: list[RetrievedEvidence],
    subject: str,
    ) -> list[str]:
    claim_time = extract_closing_time(statement)

    if claim_time is None:
        return []

    conflicts = []

    for item in evidence:
        if item.subject.lower() != subject.lower():
            continue

        evidence_time = extract_closing_time(item.content)

        if evidence_time is not None and evidence_time != claim_time:
            conflicts.append(
                f"{item.source_id} reports {evidence_time}; "
                f"the claim states {claim_time}."
            )

    return conflicts