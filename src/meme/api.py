import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from meme.analyze_memes import fetch_as_data_url
from meme.client import DoubaoClient
from meme.config import APIConfig, ServerConfig
from meme.exceptions import ConfigurationError


class AnalysisHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self._send_json(404, {"error": "not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length or 0)

        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
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

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host: str, port: int) -> None:
    server = HTTPServer((host, port), AnalysisHandler)
    print(f"Starting meme analysis server on http://{host}:{port}")
    print("Endpoints:")
    print(f"  POST http://{host}:{port}/analyze")
    print("\nPress Ctrl+C to stop...")
    server.serve_forever()


def main() -> None:
    config = ServerConfig.from_env()
    run_server(config.host, config.port)


if __name__ == "__main__":
    main()
