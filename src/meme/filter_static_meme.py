import json
import sys
from typing import Any


def is_gif_entry(entry: dict[str, Any]) -> bool:
    name = str(entry.get("name", "")).lower()
    url = str(entry.get("url", "")).lower()
    return name.endswith(".gif") or url.endswith(".gif")


def run_filter(input_path: str, output_path: str) -> int:
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        return 1

    data_array: list[dict[str, Any]]
    if isinstance(data, list):
        data_array = data
    elif isinstance(data, dict) and isinstance(data.get("data"), list):
        data_array = data["data"]
    else:
        print("Error: Input must be a JSON array or an object with 'data' array.", file=sys.stderr)
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


def main() -> int:
    if len(sys.argv) != 3:
        cmd = sys.argv[0].rsplit("/", 1)[-1]
        print(f"Usage: {cmd} <input.json> <output.json>", file=sys.stderr)
        return 1

    return run_filter(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    raise SystemExit(main())
