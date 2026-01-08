import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from meme.analyze_memes import fetch_as_data_url
from meme.client import DoubaoClient
from meme.config import APIConfig, ServerConfig
from meme.exceptions import ConfigurationError


_rag_instance = None


def get_rag():
    global _rag_instance
    if _rag_instance is None:
        index_path = os.getenv("MEME_INDEX_PATH", "meme_index.npz")
        if os.path.exists(index_path):
            from meme.rag import MemeRAG
            _rag_instance = MemeRAG()
            _rag_instance.load_index(index_path)
    return _rag_instance


class AnalysisHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_request(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length or 0)
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return None

    def do_POST(self) -> None:
        if self.path == "/analyze":
            self._handle_analyze()
        elif self.path == "/match":
            self._handle_match()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_analyze(self) -> None:
        payload = self._parse_request()
        if payload is None:
            return

        image_url = payload.get("url")
        if not isinstance(image_url, str) or not image_url:
            self._send_json(400, {"error": "missing or invalid 'url' field"})
            return

        image_mode = payload.get("image_mode", "remote")
        timeout = float(payload.get("download_timeout", 15.0))
        api_key_override = payload.get("api_key")

        try:
            config = APIConfig.from_env(api_key_override=api_key_override)
            client = DoubaoClient(config)

            if image_mode == "data":
                image_url = fetch_as_data_url(image_url, timeout)

            response = client.analyze_image(image_url)
            analysis = client.extract_analysis(response)

            self._send_json(200, {"analysis": analysis})

        except ConfigurationError as e:
            self._send_json(500, {"error": "configuration_error", "message": str(e)})
        except Exception as exc:
            self._send_json(500, {"error": "analysis_failed", "message": str(exc)})

    def _handle_match(self) -> None:
        payload = self._parse_request()
        if payload is None:
            return

        image_url = payload.get("url")
        if not isinstance(image_url, str) or not image_url:
            self._send_json(400, {"error": "missing or invalid 'url' field"})
            return

        rag = get_rag()
        if rag is None:
            self._send_json(500, {
                "error": "index_not_loaded",
                "message": "Set MEME_INDEX_PATH env var to index file path",
            })
            return

        image_mode = payload.get("image_mode", "remote")
        timeout = float(payload.get("download_timeout", 15.0))
        top_k = int(payload.get("top_k", 3))
        api_key_override = payload.get("api_key")

        try:
            config = APIConfig.from_env(api_key_override=api_key_override)
            client = DoubaoClient(config)

            if image_mode == "data":
                image_url = fetch_as_data_url(image_url, timeout)

            response = client.analyze_image(image_url)
            analysis = client.extract_analysis(response)
            matches = rag.find_similar_from_analysis(analysis, top_k)

            self._send_json(200, {
                "analysis": analysis,
                "matches": matches,
            })

        except ConfigurationError as e:
            self._send_json(500, {"error": "configuration_error", "message": str(e)})
        except Exception as exc:
            self._send_json(500, {"error": "match_failed", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host: str, port: int) -> None:
    server = HTTPServer((host, port), AnalysisHandler)
    print(f"Starting meme analysis server on http://{host}:{port}")
    print("Endpoints:")
    print(f"  POST http://{host}:{port}/analyze")
    print(f"  POST http://{host}:{port}/match")
    print("\nPress Ctrl+C to stop...")
    server.serve_forever()


def main() -> None:
    config = ServerConfig.from_env()
    run_server(config.host, config.port)


if __name__ == "__main__":
    main()
