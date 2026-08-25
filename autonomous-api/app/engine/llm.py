import httpx


async def call_llm(prompt: str):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                }
            )

            data = response.json()
            return data.get("response", "")

    except Exception as e:
        return f"[OLLAMA ERROR] {str(e)}"