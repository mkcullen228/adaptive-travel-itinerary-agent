# Phase 3: Retrieval and Evidence Assessment

## 1. Objective

The objective of Phase 3 was to implement and evaluate a retrieval pipeline that allows the Travel Itinerary Recovery Agent to access relevant venue information and assess whether retrieved information adequately supports claims used in itinerary recommendations.

The focus was not simply retrieving semantically similar text. The system needed to preserve source metadata, assess information quality, identify unsupported claims, and detect conflicting information.

## 2. Architecture and Design Decisions

### Document ingestion

Implemented a document ingestion pipeline using `requests` and `trafilatura` to retrieve and extract information from publicly available venue webpages.

Ingestion results capture:
- Source ID and URL
- HTTP and extraction status
- Retrieval timestamp
- Extracted content
- Error information when ingestion fails

A content-quality check prevents documents with insufficient or irrelevant extracted text from being stored.

Some National Park Service pages returned HTTP 403 responses or generic page content. These were not bypassed; unsuccessful or low-quality extractions were rejected.

### Metadata and source quality

Each ingested document includes:
- `source_id`
- `subject`
- `url`
- `retrieved_at`
- `reliability`

Reliability and freshness are tracked separately. A source's reliability score represents an assessment of trustworthiness, while freshness reflects how recently the information was retrieved.

The system preserves these dimensions independently rather than combining them into a single quality score.

### Document chunking

Two chunking approaches were implemented and evaluated.

| Configuration | Chunk size | Overlap | Total chunks |
|---|---:|---:|---:|
| Recursive baseline | 500 | 75 | 13 |
| Sentence-aware experiment | 500 | 75 | 11 |

The baseline uses `RecursiveCharacterTextSplitter`. The experimental implementation uses NLTK sentence-aware splitting.

The sentence-aware approach produced fewer chunks and generally improved sentence readability. However, some chunks remained broad and occasional Markdown artifacts appeared at chunk boundaries.

Both approaches were retained for comparison.

### Embedding model

Selected `sentence-transformers/all-MiniLM-L6-v2`.

Reasons for selection:
- Open and locally runnable
- No per-request API cost
- Lightweight enough for the MVP
- Produces 384-dimensional embeddings

The model is cached within the process to avoid repeatedly loading it for each query or document embedding operation.

### Vector storage and retrieval

ChromaDB was selected for local persistent vector storage.

Two collections were maintained:
- `venue_visitor_information`
- `venue_visitor_information_experimental`

The collections allow baseline and experimental chunking configurations to be evaluated independently.

Retrieval returns document content, metadata, and cosine distance. Lower cosine distance indicates greater semantic similarity, but distance is not treated as a calibrated confidence score.

Structured information such as itinerary activities, travel estimates, and disruptions remains in Pydantic models rather than being stored in the vector database.

## 3. Retrieval Evaluation

Five retrieval test cases were developed:

| Test | Retrieval objective | Expected answerability |
|---|---|---|
| R-01 | Timed-entry ticket requirements | Answerable |
| R-02 | Weather-related closures | Answerable |
| R-03 | Seasonal WWII Memorial fountains | Answerable |
| R-04 | Monument hours and ticket release timing | Answerable |
| R-05 | Wheelchair-accessible restrooms | Unanswerable |

Evaluation metrics:
- **Precision@3:** Proportion of the top three retrieved chunks considered relevant.
- **Recall@3:** Proportion of known relevant chunks retrieved in the top three.
- **Mean Reciprocal Rank (MRR):** Measures how highly the first relevant result appears.

### Results

| Metric | Baseline | Sentence-aware |
|---|---:|---:|
| Precision@3 | 0.667 | 0.667 |
| Recall@3 | 1.000 | 1.000 |
| MRR | 0.875 | 0.875 |

The two configurations produced identical aggregate metrics and retrieved the same relevant result IDs in the evaluation.

The results suggest that sentence-aware chunking improved readability but did not demonstrate a retrieval-performance improvement on this small test set.

R-05 was excluded from relevance metric averages because it was intentionally unanswerable. Its behavior was evaluated separately through evidence assessment.

### Important retrieval finding

Cosine distance alone was not sufficient to determine whether retrieved evidence could answer a question.

For example, the unanswerable restroom query returned a top result with a cosine distance of approximately 0.477, while a fully relevant timed-entry query returned a top result with a distance of approximately 0.530.

A global similarity threshold could therefore reject useful evidence while retaining irrelevant evidence.

The system should assess evidence sufficiency separately from semantic similarity.

## 4. Evidence Assessment

A separate evidence assessment layer was implemented to evaluate claims against retrieved information.

This distinction is important:

- **Source quality:** How reliable and fresh is the information source?
- **Evidence sufficiency:** Does the retrieved information actually support the claim?

The `RetrievedEvidence` model preserves:
- Chunk ID
- Content
- Subject
- Source ID and URL
- Retrieval timestamp
- Similarity distance
- Reliability
- Freshness score

A retrieval adapter converts ChromaDB results into structured evidence objects and calculates freshness using the existing data-quality logic.

### Evidence assessment outcomes

The evidence assessment model supports four statuses:

| Status | Meaning |
|---|---|
| Supported | Retrieved information supports the claim |
| Partially supported | Some statements are supported, others are not |
| Unsupported | Retrieved information does not support the claim |
| Conflicting | Retrieved sources contain contradictory information |

Additional dimensions capture relevance and coverage.

The assessor also records whether source quality and consistency have been assessed.

### Evidence assessment tests

Tests cover:
- Directly supported claims
- Unsupported claims
- Partially supported claims
- Conflicting closing times
- Agreement between sources
- Different venues with different hours
- Relevant evidence that does not actually support a claim
- Evidence relevance and coverage classifications

A retrieval-to-evidence integration workflow was also implemented to connect vector retrieval, evidence conversion, and claim assessment.

## 5. Key Design Decisions

1. Retrieval is used for document-based venue information, not as the authority for live conditions.
2. Structured APIs and records are preferred for current weather, travel durations, and availability.
3. Source reliability and freshness remain separate quality dimensions.
4. Similarity distance is not interpreted as confidence or proof.
5. Evidence relevance does not automatically mean a claim is supported.
6. Unsupported claims should remain unsupported rather than being filled in through assumptions.
7. Conflicting sources should be explicitly identified rather than resolved through arbitrary source selection.

## 6. Known Limitations and Future Improvements

The current evidence assessment implementation is a deterministic MVP baseline.

Known limitations include:

- Claim support currently relies primarily on exact substring matching.
- Claim decomposition handles simple statements separated by "and".
- Conflict detection currently focuses on venue closing-time disagreements.
- Relevance uses lexical overlap rather than semantic entailment.
- Source quality and consistency assessment are represented in the model but are not yet fully integrated into the assessment workflow.
- Completeness checks currently assess metadata field presence rather than the actual quality of field values.
- The evaluation dataset is small and limited to two successfully ingested venue documents.

Future improvements could include:
- More robust claim decomposition.
- Broader contradiction detection.
- Better handling of negation, synonyms, and contextual meaning.
- Explicit abstention and escalation rules.
- Integration of source reliability and freshness into final recommendation decisions.
- Expanded retrieval evaluation with missing, stale, and conflicting information.

## 7. Phase 3 Completion

The retrieval and evidence assessment pipeline has been implemented, evaluated, and tested.

The full project test suite passes following corrections to failing tests.

Phase 3 establishes the document retrieval and evidence-grounding foundation required for the agent to make recommendations with traceable supporting information and explicit uncertainty.

**Next phase:** Integrate external tools, beginning with the National Weather Service, to retrieve structured weather information and translate relevant conditions into itinerary disruption scenarios.

