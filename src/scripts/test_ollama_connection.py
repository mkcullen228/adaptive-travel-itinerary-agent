import ollama

response = ollama.chat(
    model="qwen3.5:4b",
    messages=[
        {
            "role": "user",
            "content": 'Return only JSON: {"status": "success"}'
        }
    ],
    format="json"
)

print(response.message.content)
