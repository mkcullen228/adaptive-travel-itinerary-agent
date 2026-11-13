from pathlib import Path
from src.data_sources.document_chunking import load_and_chunk_document
from src.data_sources.venue_ingestion import ingest_venue_sources

if __name__ == "__main__":
    results = ingest_venue_sources("washington_monument")

    for result in results:
        print(result.model_dump(mode="json"))


    document_path = Path(
        "data/documents/venue_guides/nps_washington_monument.md"
    )

    chunks = load_and_chunk_document(document_path)

    print(f"Number of chunks: {len(chunks)}")

    for chunk in chunks:
        print("\n---")
        print("Chunk index:", chunk.metadata["chunk_index"])
        print("Source ID:", chunk.metadata["source_id"])
        print("Reliability:", chunk.metadata["reliability"])
        print("Content:", chunk.page_content[:150])


    assert chunks[0].metadata["subject"] == "National Park Service - Washington Monument"
    assert chunks[0].metadata["url"] == "https://www.nps.gov/wamo/index.htm"
    assert "retrieved_at" in chunks[0].metadata
