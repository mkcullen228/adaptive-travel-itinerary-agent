
import json
from pathlib import Path

from src.models.attraction import Attraction


def load_attractions() -> list[Attraction]:
    dataset_path = Path("data/attractions/washington_dc.json")

    with dataset_path.open(encoding="utf-8") as file:
        data = json.load(file)

    return [
        Attraction.model_validate(record)
        for record in data
    ]


def get_attraction_by_id(attraction_id: str) -> Attraction:
    attractions = load_attractions()

    for attraction in attractions:
        if attraction.attraction_id == attraction_id:
            return attraction

    raise ValueError(
        f"No attraction found with ID: {attraction_id}"
    )


if __name__ == "__main__":
    attraction = get_attraction_by_id("national_gallery")
