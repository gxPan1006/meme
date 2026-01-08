#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, List


def usage() -> None:
    cmd = sys.argv[0].rsplit("/", 1)[-1]
    print(f"Usage: {cmd} <input.json> <output.json>", file=sys.stderr)


def is_gif_entry(entry: Dict[str, Any]) -> bool:
    name = str(entry.get("name", "")).lower()
    url = str(entry.get("url", "")).lower()
    return name.endswith(".gif") or url.endswith(".gif")


def main() -> int:
    if len(sys.argv) != 3:
        usage()
        return 1

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data_array: List[Dict[str, Any]]
    if isinstance(data, list):
        data_array = data
    elif isinstance(data, dict) and isinstance(data.get("data"), list):
        data_array = data["data"]
    else:
        print("Error: expected an array or an object with data array.", file=sys.stderr)
        return 1

    filtered = [entry for entry in data_array if not is_gif_entry(entry)]

    if isinstance(data, list):
        output = filtered
    else:
        output = dict(data)
        output["data"] = filtered

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(filtered)} static entries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
