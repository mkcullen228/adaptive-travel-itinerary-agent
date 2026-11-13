import json
from pathlib import Path

from src.models.attraction import Attraction


def test_washington_dc_dataset_loads():
    dataset_path = Path("data/attractions/washington_dc.json")

    with dataset_path.open(encoding="utf-8") as file:
        data = json.load(file)

    attractions = [
        Attraction.model_validate(record)
        for record in data
    ]

    assert len(attractions) == 10
    assert all(isinstance(a, Attraction) for a in attractions)