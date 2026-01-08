import base64
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from meme.client import DoubaoClient
from meme.config import APIConfig
from meme.exceptions import ConfigurationError, ImageFetchError


def load_input(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, list):
        return data

    raise ValueError("Input JSON must be an array or an object with a data array.")


def load_existing(output_path: str) -> dict[str, dict[str, Any]]:
    if not os.path.exists(output_path):
        return {}

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return {}

    existing: dict[str, dict[str, Any]] = {}
    for item in data:
        name = item.get("name")
        if isinstance(name, str):
            existing[name] = item
    return existing


def guess_mime_type(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


def sanitize_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/")
    query = urllib.parse.quote_plus(parts.query, safe="=&")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_as_data_url(url: str, timeout: float) -> str:
    safe_url = sanitize_url(url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            mime = resp.headers.get_content_type() or guess_mime_type(url)
    except Exception as e:
        raise ImageFetchError(f"Failed to fetch image: {e}", url=url) from e

    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def run_batch_analysis(
    input_path: str,
    output_path: str,
    api_key: str | None = None,
    sleep_seconds: float = 0.0,
    limit: int = 0,
    resume: bool = False,
    image_mode: str = "remote",
    download_timeout: float = 15.0,
) -> int:
    config = APIConfig.from_env(api_key_override=api_key)
    client = DoubaoClient(config)

    items = load_input(input_path)
    if limit > 0:
        items = items[:limit]

    existing = load_existing(output_path) if resume else {}
    output: list[dict[str, Any]] = list(existing.values()) if resume else []

    for idx, item in enumerate(items, start=1):
        name = item.get("name")

        if resume and isinstance(name, str) and name in existing:
            continue

        url = item.get("url")
        if not isinstance(url, str):
            output.append({
                "name": name,
                "category": item.get("category"),
                "url": url,
                "analysis": {"error": "missing url"},
            })
            continue

        try:
            image_url = url
            if image_mode == "data":
                image_url = fetch_as_data_url(url, download_timeout)

            response = client.analyze_image(image_url)
            analysis = client.extract_analysis(response)
        except Exception as exc:
            analysis = {"error": str(exc)}

        output.append({
            "name": name,
            "category": item.get("category"),
            "url": url,
            "analysis": analysis,
        })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[{idx}/{len(items)}] {name}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return 0


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Analyze meme images via Doubao API.")
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--image-mode", choices=["remote", "data"], default="remote")
    parser.add_argument("--download-timeout", type=float, default=15.0)

    args = parser.parse_args()

    try:
        return run_batch_analysis(
            input_path=args.input,
            output_path=args.output,
            api_key=args.api_key,
            sleep_seconds=args.sleep,
            limit=args.limit,
            resume=args.resume,
            image_mode=args.image_mode,
            download_timeout=args.download_timeout,
        )
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
