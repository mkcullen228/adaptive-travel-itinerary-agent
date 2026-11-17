import json
import ollama

from src.models.agent_workflow import RecoveryOption


def test_qwen_structured_output():
    schema = RecoveryOption.model_json_schema()

    response = ollama.chat(
        model="qwen3.5:4b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a travel itinerary recovery assistant. "
                    "Return a structured recovery option that conforms "
                    "to the supplied schema. Do not invent evidence. "
                    "Use an empty itinerary if no itinerary details "
                    "are supplied."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generate a minimal, partial recovery option for "
                    "Washington, DC. There is insufficient information "
                    "to recommend replacement activities. Use an empty "
                    "itinerary with itinerary_id='test', destination "
                    "Washington, DC, and itinerary_date 2026-11-07. "
                    "Explain the uncertainty in the rationale."
                ),
            },
        ],
        format=schema,
        options={"temperature": 0},
    )

    raw_response = response.message.content

    print("\nRAW RESPONSE:")
    print(raw_response)

    validated_option = RecoveryOption.model_validate_json(raw_response)

    print("\nPYDANTIC VALIDATION:")
    print(validated_option)
