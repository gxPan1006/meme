import json
import subprocess
from typing import Any

from meme.config import APIConfig
from meme.exceptions import APIError


class DoubaoClient:
    def __init__(self, config: APIConfig) -> None:
        self.config = config

    def analyze_image(self, image_url: str) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": self.config.prompt},
                    ],
                }
            ],
        }

        cmd = [
            "curl",
            "-sS",
            self.config.api_url,
            "-H",
            "Content-Type: application/json",
            "-H",
            f"Authorization: Bearer {self.config.api_key}",
            "-d",
            json.dumps(payload, ensure_ascii=True),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise APIError(
                f"API request failed: {result.stderr.strip() or 'curl failed'}",
                response=result.stderr,
            )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise APIError(
                f"Invalid JSON response from API: {e}",
                response=result.stdout[:500],
            ) from e

    def extract_analysis(self, response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return {"error": "missing choices", "raw": response}

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"raw": content}

        return {"raw": content}
