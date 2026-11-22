# Travel Itinerary Recovery Agent

An agentic system that investigates travel disruptions, proposes itinerary adjustments, and evaluates recovery options against evidence, schedule feasibility, and user constraints.

## Project Overview

This project is a Carnegie Mellon Agentic AI Certification Program capstone. It demonstrates how a multi-agent workflow can support travel itinerary recovery while maintaining explicit controls over evidence, uncertainty, and user approval.

The application uses a Washington, DC itinerary and evaluates recovery under predefined disruption scenarios.

### MVP Scope

- **Destination:** Washington, DC
- **Disruptions:** Weather, travel delays, and venue unavailability
- **Routing:** Walking-only
- **LLM:** Qwen 3.5 4B through Ollama
- **Interface:** Streamlit
- **Orchestration:** LangGraph

The system generates recommendations; it does not book, cancel, or purchase anything.

### Core Design Principles

- Preserve the original itinerary separately from recovery proposals.
- Do not silently remove mandatory activities or relax constraints.
- Distinguish evidence-backed facts from assumptions and unverified availability.
- Validate schedule feasibility deterministically.
- Require explicit user approval before treating a proposal as the final itinerary.
- Treat workflow completion, proposal validity, and user approval as separate states.

## Architecture

The default recovery workflow uses three agents coordinated by a deterministic LangGraph workflow:

**Researcher → Planner → Auditor**

A deterministic Coordinator manages workflow state, transitions, validation, and failure handling.

### Researcher

Interprets the available investigation evidence and produces an evidence brief for the Planner. It identifies relevant findings, source limitations, conflicts, and uncertainty.

### Planner

Generates a recovery proposal using the original itinerary and the Researcher's evidence brief. It aims to preserve mandatory constraints, minimize unnecessary changes, and avoid unsupported assumptions.

### Auditor

Independently reviews the proposed recovery for evidence support, schedule accuracy, mandatory-activity preservation, and unsupported assumptions.

### Deterministic Validation and Approval

Code-based validation checks schedule consistency and travel feasibility. The Auditor's assessment is retained separately from deterministic validation.

A proposal is not automatically accepted when the workflow finishes. The user must explicitly approve it. Rejected proposals do not become final itineraries.

A single-agent recovery workflow is retained as an evaluation baseline for architecture comparison.

## Technology Stack

- Python
- LangGraph
- Pydantic
- Ollama and Qwen 3.5 4B
- Streamlit
- ChromaDB
- Sentence Transformers (`all-MiniLM-L6-v2`)
- OpenRouteService walking directions
- pytest

## Repository Structure

```text
.
├── app.py
├── requirements.txt
├── data/
│   ├── attractions/
│   ├── documents/
│   │   └── venue_guides/
│   ├── evaluations/
│   ├── itineraries/
│   └── vector_store/
├── docs/
├── src/
│   ├── data_sources/
│   ├── evaluation/
│   ├── models/
│   ├── prompts/
│   ├── recovery/
│   ├── validation/
│   └── workflows/
└── tests/
    ├── data_sources/
    ├── evaluation/
    ├── fixtures/
    ├── integration/
    ├── models/
    ├── recovery/
    ├── validation/
    └── workflows/
```

## Local Setup

### Prerequisites

- Python
- Ollama
- An Ollama-compatible local model
- An OpenRouteService API key for walking-route requests

### 1. Clone the repository

```bash
git clone <repository-url>
cd adaptive-travel-itinerary-agent
```

### 2. Create and activate a virtual environment

For macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and provide your own values:

```bash
cp .env.example .env
```

Configure the following variables:

```text
OPENROUTESERVICE_API_KEY=your_api_key
NWS_CONTACT_EMAIL=your_email@example.com
```

- `OPENROUTESERVICE_API_KEY` is used for walking-route requests.
- `NWS_CONTACT_EMAIL` provides contact information for National Weather Service requests.

Do not commit `.env` or API credentials.

### 5. Configure Ollama

Install and pull the model:

```bash
ollama pull qwen3.5:4b
```

Ensure the Ollama server is running before starting the application. If it is not already running, start it with:

```bash
ollama serve
```

The application uses the local Ollama service for LLM execution.

### 6. Build the local venue vector store

The application uses ChromaDB for venue-document retrieval. The venue guide Markdown files are stored in:

```text
data/documents/venue_guides/
```

Build the baseline collection from those documents:

```bash
PYTHONPATH="$(pwd)" python -m src.evaluation.build_baseline_vector_store
```

The script chunks the venue guides, generates embeddings, and stores them in the persistent local ChromaDB collection:

```text
venue_visitor_information
```

The embedding model is downloaded locally through Sentence Transformers on first use.

The vector store is persisted under:

```text
data/vector_store/
```

## Run the Application

From the repository root, with the virtual environment activated and Ollama available:

```bash
streamlit run app.py
```

Streamlit will provide a local URL in the terminal, typically:

```text
http://localhost:8501
```

### Available Scenarios

The application currently supports two controlled scenarios:

**P-01 — National Gallery unavailable**

- Uses the existing Washington, DC baseline itinerary.
- Runs the venue investigation and retrieval workflow.
- Evaluates recovery after the National Gallery disruption.
- Retains the mandatory National Museum of Natural History visit.

**P-02 — Heavy rain**

- Uses a supplied synthetic investigation context.
- Evaluates the impact of heavy rain on the World War II Memorial and Lincoln Memorial.
- The controlled disruption window is November 7, 2026, from 12:00 PM through 6:00 PM.
- Does not represent a live weather forecast.

### Reviewing a Recovery

The application displays the original itinerary, proposed changes, walking-route estimates, schedule feasibility, and relevant evidence and uncertainty.

If a proposal is eligible for approval, the user can approve or reject it. An invalid proposal cannot be approved.

A valid schedule does not establish that venue hours, access, or availability have been independently verified.

## Testing

Run the full test suite from the repository root:

```bash
PYTHONPATH="$(pwd)" pytest -q
```

Run an individual test file when investigating a specific component:

```bash
PYTHONPATH="$(pwd)" pytest tests/workflows/test_agent_graph.py -q
```

The test suite covers data models, data sources, retrieval, evaluation, recovery generation, validation, workflow orchestration, and approval decisions.

## Evaluation

The project includes configurable benchmark runners and saved evaluation artifacts.

### Multi-Agent Benchmark

The multi-agent benchmark runner accepts a JSON configuration containing the scenario, model, strategy, input fixtures, instructions, prompt version, and output path.

Example P-01 run:

```bash
PYTHONPATH="$(pwd)" python -m src.evaluation.multi_agent_benchmark_runner ./src/evaluation/configs/p01_multi_agent.json
```

Benchmark configurations are stored in:

```text
src/evaluation/configs/
```

Evaluation scripts and historical benchmark artifacts are retained under:

```text
src/evaluation/
data/evaluations/
```

The evaluation work includes:

- Single-agent versus multi-agent architecture comparisons.
- Evidence-quality evaluation.
- Planner and Auditor assessments.
- Deterministic schedule and recovery validation.
- Narrative and structured-output consistency checks.
- Saved benchmark results for repeatable analysis.

See the `docs/` directory for supporting evaluation and design notes.

## Known Limitations

- **LLM schedule reasoning:** The Planner can produce narrative explanations that do not fully match the structured itinerary. Structured schedule data and deterministic validation should be treated as authoritative.
- **Recovery generation:** The system can safely return no valid recovery when it cannot construct a feasible proposal that preserves mandatory constraints. This is preferable to inventing alternatives or presenting an invalid schedule.
- **Venue availability:** Retrieved venue documents may not establish current operating hours, closures, or real-time availability.
- **P-02 weather data:** P-02 uses synthetic benchmark context, not a live forecast.
- **Routing:** Walking estimates depend on the external routing service and successful route retrieval.
- **Scope:** Driving and public-transit routing are outside the current MVP.

## Project Status

The MVP includes:

- A working Streamlit application.
- A multi-agent recovery workflow.
- A single-agent evaluation baseline.
- Venue-document retrieval and evidence handling.
- Walking-route integration.
- Deterministic schedule validation.
- Approval and rejection handling.
- Automated tests and configurable evaluation tooling.

The current focus is on reliability, reproducibility, documentation, and communicating the system's limitations—not expanding the MVP scope.
