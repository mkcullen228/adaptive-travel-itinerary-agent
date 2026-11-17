
import ollama
from src.models.agent_workflow import RecoveryOption

print("Loading schema...", flush=True)
schema = RecoveryOption.model_json_schema()

print("Sending request with thinking disabled...", flush=True)

response = ollama.chat(
    model="qwen3.5:4b",
    messages=[
        {
            "role": "user",
            "content": (
                "Return a minimal recovery proposal that conforms "
                "to the supplied JSON schema. Return the JSON object only."
            ),
        }
    ],
    format=schema,
    think=False,
    options={
        "temperature": 0,
        "num_predict": 1500,
    },
)

print("\n--- RESPONSE ---", flush=True)
print("Content:", repr(response.message.content), flush=True)
print("Done reason:", response.done_reason, flush=True)
print("Generated tokens:", response.eval_count, flush=True)

if response.message.content:
    try:
        proposal = RecoveryOption.model_validate_json(
            response.message.content
        )
        print("\nPydantic validation: PASSED", flush=True)
        print(proposal.model_dump_json(indent=2))
    except Exception as exc:
        print("\nPydantic validation: FAILED", flush=True)
        print(exc)
else:
    print("\nNo response content was generated.", flush=True)
