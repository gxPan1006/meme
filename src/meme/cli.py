import argparse
import sys

from meme.analyze_memes import run_batch_analysis
from meme.api import run_server
from meme.config import ServerConfig
from meme.exceptions import ConfigurationError
from meme.filter_static_meme import run_filter


def analyze_main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze meme images via Doubao API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    meme-analyze memes.json results.json
    meme-analyze memes.json results.json --image-mode data --limit 10
    meme-analyze memes.json results.json --resume

Environment Variables:
    ARK_API_KEY     Required. API key for Doubao API.
    ARK_API_URL     Optional. Override API endpoint.
    ARK_MODEL       Optional. Override model name.
        """,
    )
    parser.add_argument("input", help="Input JSON file (expects {data: [...]} or [...])")
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument("--api-key", help="API key (defaults to ARK_API_KEY env var)")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between requests (default: 0)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items to process (default: all)")
    parser.add_argument("--resume", action="store_true", help="Skip items already in output file")
    parser.add_argument("--image-mode", choices=["remote", "data"], default="remote", help="Use remote URL or embed as base64 data URL (default: remote)")
    parser.add_argument("--download-timeout", type=float, default=15.0, help="Timeout for image download in seconds (default: 15)")

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
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1


def filter_main() -> int:
    parser = argparse.ArgumentParser(
        description="Filter GIF entries from meme JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    meme-filter all_memes.json static_memes.json
        """,
    )
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output JSON file")

    args = parser.parse_args()
    return run_filter(args.input, args.output)


def server_main() -> int:
    parser = argparse.ArgumentParser(
        description="Start HTTP server for meme analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    meme-server
    meme-server --host 0.0.0.0 --port 8080

Environment Variables:
    ARK_API_KEY       Required for /analyze endpoint.
    ANALYSIS_HOST     Server host (default: 127.0.0.1)
    ANALYSIS_PORT     Server port (default: 8000)
        """,
    )
    parser.add_argument("--host", help="Host to bind to (default: from ANALYSIS_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, help="Port to listen on (default: from ANALYSIS_PORT or 8000)")

    args = parser.parse_args()

    config = ServerConfig.from_env()
    host = args.host or config.host
    port = args.port or config.port

    try:
        run_server(host, port)
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        return 1
