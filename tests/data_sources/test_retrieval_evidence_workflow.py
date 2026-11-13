from src.data_sources.embedding_client import embed_query
from src.data_sources.retrieval_adapter import (
    convert_search_results_to_evidence,
)
from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
    search_documents,
)
from src.validation.evidence_assessment import assess_claim_evidence


def test_timed_entry_ticket_claim_is_supported():

    # 1. Retrieve relevant documents.
    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    query = "Washington Monument timed-entry tickets and advance ticket release"

    query_embedding = embed_query(query)

    results = search_documents(
        collection,
        query,
        query_embedding,
        n_results=3,
    )

    # 2. Convert retrieved chunks into structured evidence.
    evidence = convert_search_results_to_evidence(results)

    assert evidence

    # 3. Assess a claim using the retrieved evidence.
    claim = (
        "Visitors must have a timed-entry ticket "
        "and advance tickets are available online"
    )

    assessment = assess_claim_evidence(claim, evidence)

    # 4. Verify the assessment.
    assert assessment.status == "supported"
    assert assessment.supporting_source_ids
    assert assessment.coverage.value == "complete"


def test_timed_entry_ticket_claim_is_unsupported():

    # 1. Retrieve relevant documents.
    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    query = "National Mall has elevators"

    query_embedding = embed_query(query)

    results = search_documents(
        collection,
        query,
        query_embedding,
        n_results=3,
    )

    # 2. Convert retrieved chunks into structured evidence.
    evidence = convert_search_results_to_evidence(results)

    assert evidence

    # 3. Assess a claim using the retrieved evidence.
    claim = (
        "Visitors must have a timed-entry ticket "
        "and advance tickets are available online"
    )

    assessment = assess_claim_evidence(claim, evidence)

    # 4. Verify the assessment.
    assert assessment.status == "unsupported"
    assert assessment.coverage.value == "none"
    assert not assessment.supporting_source_ids
