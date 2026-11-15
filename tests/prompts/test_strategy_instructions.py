from src.prompts.strategy_instructions import (
    MINIMAL_DISRUPTION_INSTRUCTION,
    BEST_OVERALL_FEASIBILITY_INSTRUCTION,
    PREFERENCE_ORIENTED_INSTRUCTION,
)


def test_all_strategy_instructions_are_defined():
    instructions = [
        MINIMAL_DISRUPTION_INSTRUCTION,
        BEST_OVERALL_FEASIBILITY_INSTRUCTION,
        PREFERENCE_ORIENTED_INSTRUCTION,
    ]

    assert all(isinstance(item, str) and item.strip() for item in instructions)


def test_strategy_instructions_are_distinct():
    instructions = [
        MINIMAL_DISRUPTION_INSTRUCTION,
        BEST_OVERALL_FEASIBILITY_INSTRUCTION,
        PREFERENCE_ORIENTED_INSTRUCTION,
    ]

    assert len(set(instructions)) == 3
