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


def index_main() -> int:
    parser = argparse.ArgumentParser(
        description="Build vector index from meme analysis data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    meme-index meme0_100_analysis.json --output meme_index.npz
        """,
    )
    parser.add_argument("input", help="Input analysis JSON file")
    parser.add_argument("--output", "-o", default="meme_index.npz", help="Output index file (default: meme_index.npz)")

    args = parser.parse_args()

    try:
        from meme.rag import build_index
        build_index(args.input, args.output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def search_main() -> int:
    parser = argparse.ArgumentParser(
        description="Search similar memes using text query.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    meme-search "开心搞笑的表情" --index meme_index.npz
    meme-search "愤怒吐槽" --index meme_index.npz --top-k 5
        """,
    )
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--index", "-i", required=True, help="Path to index file (.npz)")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of results (default: 3)")

    args = parser.parse_args()

    try:
        from meme.rag import search_memes
        import json
        results = search_memes(args.query, args.index, args.top_k)
        for i, meme in enumerate(results, 1):
            print(f"\n[{i}] {meme['name']} (score: {meme['score']:.4f})")
            print(f"    URL: {meme['url']}")
            if "analysis" in meme:
                emotion = meme["analysis"].get("所代表情绪", "")
                if isinstance(emotion, str) and len(emotion) > 100:
                    emotion = emotion[:100] + "..."
                print(f"    情绪: {emotion}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def match_main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze image and find similar memes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    meme-match https://example.com/image.jpg --index meme_index.npz
    meme-match image.jpg --index meme_index.npz --image-mode data

Environment Variables:
    ARK_API_KEY     Required. API key for Doubao API.
        """,
    )
    parser.add_argument("image", help="Image URL or path")
    parser.add_argument("--index", "-i", required=True, help="Path to index file (.npz)")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of results (default: 3)")
    parser.add_argument("--image-mode", choices=["remote", "data"], default="remote", help="Use remote URL or embed as base64 (default: remote)")
    parser.add_argument("--api-key", help="API key (defaults to ARK_API_KEY env var)")

    args = parser.parse_args()

    try:
        from meme.client import DoubaoClient
        from meme.config import APIConfig
        from meme.rag import MemeRAG
        from meme.analyze_memes import fetch_as_data_url
        import json

        config = APIConfig.from_env(api_key_override=args.api_key)
        client = DoubaoClient(config)

        image_url = args.image
        if args.image_mode == "data":
            image_url = fetch_as_data_url(args.image, 15.0)

        print("Analyzing image...")
        response = client.analyze_image(image_url)
        analysis = client.extract_analysis(response)

        print("\n=== Image Analysis ===")
        print(json.dumps(analysis, ensure_ascii=False, indent=2))

        rag = MemeRAG()
        rag.load_index(args.index)
        matches = rag.find_similar_from_analysis(analysis, args.top_k)

        print("\n=== Similar Memes ===")
        for i, meme in enumerate(matches, 1):
            print(f"\n[{i}] {meme['name']} (score: {meme['score']:.4f})")
            print(f"    URL: {meme['url']}")
            design = meme.get("analysis", {}).get("设计灵感", "")
            if isinstance(design, str) and len(design) > 150:
                design = design[:150] + "..."
            print(f"    设计灵感: {design}")

        return 0
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
