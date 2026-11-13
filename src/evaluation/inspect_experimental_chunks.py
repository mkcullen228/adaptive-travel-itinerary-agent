from src.data_sources.vector_store import (
    create_vector_store_client,
    get_or_create_collection
)

COLLECTION_NAME = "venue_visitor_information_experimental"


def main():
    client = create_vector_store_client()

    collection = get_or_create_collection(
        client,
        collection_name=COLLECTION_NAME
    )

    results = collection.get(
        include=["documents", "metadatas"]
    )

    for chunk_id, document, metadata in zip(
        results["ids"],
        results["documents"],
        results["metadatas"]
    ):
        print("\n" + "=" * 60)
        print(f"Chunk ID: {chunk_id}")
        print(f"Source: {metadata['source_id']}")
        print(document)


if __name__ == "__main__":
    main()
