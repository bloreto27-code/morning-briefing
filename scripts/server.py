#!/usr/bin/env python3
"""Local dashboard server — serves docs/ and proxies /api/chat to Anthropic."""
import http.server
import json
import os
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
PORT = 8080


class BriefingHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def log_message(self, fmt, *args):
        if "/favicon" not in self.path:
            super().log_message(fmt, *args)

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_chat(self):
        try:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                self._json_error(500, "ANTHROPIC_API_KEY not set. Set it before starting server.py.")
                return

            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            messages = body.get("messages", [])
            system = body.get("system", "")

            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self._send_cors()
            self.end_headers()

            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    payload = json.dumps({"text": text})
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()

            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        except Exception as e:
            traceback.print_exc()
            try:
                payload = json.dumps({"error": str(e)})
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception:
                pass

    def _json_error(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._send_cors()
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())


def main():
    key_status = "SET" if os.environ.get("ANTHROPIC_API_KEY") else "NOT SET — AI bot disabled"
    print(f"\n  Morning Briefing Dashboard")
    print(f"  http://localhost:{PORT}")
    print(f"  ANTHROPIC_API_KEY: {key_status}")
    print(f"  Press Ctrl+C to stop\n")
    with http.server.HTTPServer(("", PORT), BriefingHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
