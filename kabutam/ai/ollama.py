# kabutam/ai/ollama.py

import json

import requests
from kabutam.ai.prompts import SYSTEM_PROMPT


class OllamaClient:
    def __init__(
        self,
        model="gemma4:latest",
        host="http://localhost:11434",
    ):
        self.model = model
        self.url = f"{host.rstrip('/')}/api/chat"

    def generate_stream(self, prompt):
        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": True,
                "think": False,
                "options": {
                    "num_ctx": 4096,
                    "num_predict": 2048,
                    "temperature": 0.2,
                    # "min_p": 0.05,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            },
            timeout=2000,
            stream=True,
        )

        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            data = json.loads(line)
            message = data.get("message", {})
            content = message.get("content", "")

            if content:
                yield {
                    "type": "content",
                    "text": content,
                }

            if data.get("done"):
                break
