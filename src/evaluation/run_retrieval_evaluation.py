import json
import argparse
from pprint import pprint
from pathlib import Path

from src.data_sources.embedding_client import embed_query
from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
    search_documents,
)
from src.evaluation.retrieval_metrics import (
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr,
)


# TEST_CASES_PATH = Path("data/evaluation/retrieval_test_cases.json")
# COLLECTION_NAME = "venue_visitor_information"
K = 3


CONFIGURATIONS = {
    "baseline": {
        "collection_name": "venue_visitor_information",
        "test_cases_path": Path(
            "data/evaluation/retrieval_test_cases.json"
        ),
    },
    "experimental": {
        "collection_name": "venue_visitor_information_experimental",
        "test_cases_path": Path(
            "data/evaluation/retrieval_test_cases_sentence_aware_v1.json"
        ),
    },
}


def load_test_cases(test_cases_path: Path) -> list[dict]:
    with open(test_cases_path, "r", encoding="utf-8") as file:
        return json.load(file)


def evaluate_query(collection, test_case: dict) -> dict:
    query = test_case["query"]
    relevant_chunk_ids = test_case["relevant_chunk_ids"]

    query_embedding = embed_query(query)

    retrieval_results = search_documents(
        collection,
        query,
        query_embedding,
        n_results=K,
    )

    pprint(retrieval_results)

    retrieved_chunk_ids = retrieval_results["ids"][0]

    if not test_case.get("expected_answerable", True):
        return {
            "query_id": test_case["query_id"],
            "expected_answerable": False,
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "precision_at_3": None,
            "recall_at_3": None,
            "mrr": None,
        }

    return {
        "query_id": test_case["query_id"],
        "expected_answerable": True,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "precision_at_3": calculate_precision_at_k(
            retrieved_chunk_ids, relevant_chunk_ids, K
        ),
        "recall_at_3": calculate_recall_at_k(
            retrieved_chunk_ids, relevant_chunk_ids, K
        ),
        "mrr": calculate_mrr(
            retrieved_chunk_ids[:K], relevant_chunk_ids
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate document retrieval performance."
    )
    parser.add_argument(
        "--config",
        choices=CONFIGURATIONS.keys(),
        default="baseline",
        help="Retrieval configuration to evaluate.",
    )
    args = parser.parse_args()

    config = CONFIGURATIONS[args.config]

    client = create_vector_store_client()
    collection = get_or_create_collection(
        client,
        collection_name=config["collection_name"],
    )

    print(f"Configuration: {args.config}")
    print(f"Collection: {config['collection_name']}")

    test_cases = load_test_cases(config["test_cases_path"])
    evaluation_results = []

    # Run each test case
    for test_case in test_cases:
        result = evaluate_query(collection, test_case)
        evaluation_results.append(result)

        print(f"\n{'=' * 60}")
        print(f"Query: {result['query_id']}")
        print(f"Retrieved chunks: {result['retrieved_chunk_ids']}")

        # Display metrics only for answerable queries
        if not result["expected_answerable"]:
            print("Expected answerability: NO")
            print("Relevance metrics: Not applicable")
        else:
            print(f"Precision@3: {result['precision_at_3']:.3f}")
            print(f"Recall@3:    {result['recall_at_3']:.3f}")
            print(f"MRR:         {result['mrr']:.3f}")

    # Calculate overall averages using answerable queries only
    print(f"\n{'=' * 60}")
    print("OVERALL RETRIEVAL PERFORMANCE")

    answerable_results = [
        result for result in evaluation_results
        if result["expected_answerable"]
    ]

    for metric in ["precision_at_3", "recall_at_3", "mrr"]:
        average = sum(
            result[metric] for result in answerable_results
        ) / len(answerable_results)

        print(f"Average {metric}: {average:.3f}")


if __name__ == "__main__":
    main()
