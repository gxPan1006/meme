import json
import subprocess
from typing import Any

from meme.config import APIConfig
from meme.exceptions import APIError


class DoubaoClient:
    def __init__(self, config: APIConfig) -> None:
        self.config = config

    def analyze_image(
        self,
        image_url: str,
        prompt_override: str | None = None,
        extra_text: str | None = None,
    ) -> dict[str, Any]:
        prompt = prompt_override or self.config.prompt
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        if extra_text:
            payload["messages"][0]["content"].append(
                {"type": "text", "text": f"用户需求: {extra_text}"}
            )

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

    def generate_image(
        self,
        prompt: str,
        size: str = "1920x1920",
        image_url: str | None = None,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": "doubao-seedream-4-5-251128",
            "prompt": prompt,
            "sequential_image_generation": "disabled",
            "response_format": "url",
            "size": size,
            "stream": False,
            "watermark": True,
        }
        if images:
            payload["image"] = images
        elif image_url:
            payload["image"] = image_url

        api_url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

        cmd = [
            "curl",
            "-sS",
            api_url,
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
                f"Image generation failed: {result.stderr.strip() or 'curl failed'}",
                response=result.stderr,
            )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise APIError(
                f"Invalid JSON response: {e}",
                response=result.stdout[:500],
            ) from e
