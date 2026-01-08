#!/usr/bin/env python3
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List

API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL = "doubao-seed-1-8-251228"
DEFAULT_API_KEY = "2e0cbfab-c31d-4eb3-85cf-0cda18101482"
PROMPT = "通过分析给出这个表情包的：所代表情绪、使用场景、设计灵感，最终以json的格式返回"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze meme images via Doubao API.")
    parser.add_argument("input", help="Input JSON file (expects {data: [...]})")
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument("--api-key", default=os.getenv("ARK_API_KEY") or DEFAULT_API_KEY)
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between requests")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items to process")
    parser.add_argument("--resume", action="store_true", help="Skip names already in output")
    parser.add_argument(
        "--image-mode",
        choices=["remote", "data"],
        default="remote",
        help="Use remote URL or embed base64 data URL",
    )
    parser.add_argument("--download-timeout", type=float, default=15.0, help="Download timeout in seconds")
    return parser.parse_args()


def load_input(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, list):
        return data
    raise ValueError("Input JSON must be an array or an object with a data array.")


def load_existing(output_path: str) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(output_path):
        return {}
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return {}
    existing = {}
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


def fetch_as_data_url(url: str, timeout: float) -> str:
    safe_url = sanitize_url(url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read()
        mime = resp.headers.get_content_type() or guess_mime_type(url)
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def sanitize_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/")
    query = urllib.parse.quote_plus(parts.query, safe="=&")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def call_api(api_key: str, image_url: str) -> Dict[str, Any]:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    }
    cmd = [
        "curl",
        "-sS",
        API_URL,
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
        "-d",
        json.dumps(payload, ensure_ascii=True),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "curl failed")
    return json.loads(result.stdout)


def extract_analysis(response: Dict[str, Any]) -> Any:
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


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Error: missing API key. Set ARK_API_KEY or use --api-key.", file=sys.stderr)
        return 1

    items = load_input(args.input)
    if args.limit > 0:
        items = items[: args.limit]

    existing = load_existing(args.output) if args.resume else {}
    output: List[Dict[str, Any]] = list(existing.values()) if args.resume else []

    for idx, item in enumerate(items, start=1):
        name = item.get("name")
        if args.resume and isinstance(name, str) and name in existing:
            continue
        url = item.get("url")
        if not isinstance(url, str):
            output.append(
                {
                    "name": name,
                    "category": item.get("category"),
                    "url": url,
                    "analysis": {"error": "missing url"},
                }
            )
            continue

        try:
            image_url = url
            if args.image_mode == "data":
                image_url = fetch_as_data_url(url, args.download_timeout)
            response = call_api(args.api_key, image_url)
            analysis = extract_analysis(response)
        except Exception as exc:
            analysis = {"error": str(exc)}

        output.append(
            {
                "name": name,
                "category": item.get("category"),
                "url": url,
                "analysis": analysis,
            }
        )

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[{idx}/{len(items)}] {name}")
        if args.sleep > 0:
            time.sleep(args.sleep)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
