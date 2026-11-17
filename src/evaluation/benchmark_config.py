from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from src.models.agent_workflow import RecoveryStrategy


class BenchmarkConfig(BaseModel):
    """Configuration for one reproducible LLM recovery benchmark run."""

    model_config = ConfigDict(extra="forbid")

    benchmark_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    strategy: RecoveryStrategy

    baseline_path: Path
    investigation_path: Path
    disruption_path: Path

    user_instructions: str = Field(min_length=1)
    additional_instructions: str = ""
    prompt_version: str = Field(min_length=1)

    output_path: Path


def get_project_root() -> Path:
    """Return the repository root, based on this module's location."""
    return Path(__file__).resolve().parents[2]


def resolve_project_path(path: Path) -> Path:
    """Resolve relative paths from the repository root."""
    if path.is_absolute():
        return path
    return get_project_root() / path


def load_benchmark_config(config_path: str | Path) -> BenchmarkConfig:
    """Load and validate a benchmark configuration from a JSON file."""
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = get_project_root() / config_path

    if not config_path.exists():
        raise FileNotFoundError(f"Benchmark config not found: {config_path}")

    config = BenchmarkConfig.model_validate_json(
        config_path.read_text(encoding="utf-8")
    )

    return config
