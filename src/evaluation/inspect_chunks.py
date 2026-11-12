from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection,
)


def main():
    client = create_vector_store_client()
    collection = get_or_create_collection(client)

    source_ids = [
        "washington_monument_visitor_info",
        "wwii_memorial_visitor_info",
    ]

    for source_id in source_ids:
        print(f"\n{'=' * 70}")
        print(f"SOURCE: {source_id}")
        print("=" * 70)

        results = collection.get(
            where={"source_id": source_id},
            include=["documents", "metadatas"],
        )

        for chunk_id, document, metadata in zip(
            results["ids"],
            results["documents"],
            results["metadatas"],
        ):
            print(f"\nChunk ID: {chunk_id}")
            print(f"Chunk index: {metadata['chunk_index']}")
            print(f"Text:\n{document}")


if __name__ == "__main__":
    main()
