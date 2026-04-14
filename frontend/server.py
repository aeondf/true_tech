#!/usr/bin/env python3
"""Simple frontend server with /v1 proxy support for local development."""

from __future__ import annotations

import http.server
import os
import socketserver
import urllib.error
import urllib.request


HOST = os.environ.get("FRONTEND_HOST", "127.0.0.1")
PORT = int(os.environ.get("FRONTEND_PORT", "8010"))
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8000")
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROXY_PREFIX = "/v1/"
HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "date",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "server",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request()
            return
        if self.path in {"/", ""}:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request()
            return
        self.send_error(501, f"Unsupported method ({self.command!r})")

    def do_PUT(self):
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request()
            return
        self.send_error(501, f"Unsupported method ({self.command!r})")

    def do_PATCH(self):
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request()
            return
        self.send_error(501, f"Unsupported method ({self.command!r})")

    def do_DELETE(self):
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request()
            return
        self.send_error(501, f"Unsupported method ({self.command!r})")

    def do_OPTIONS(self):
        if self.path.startswith(PROXY_PREFIX):
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(501, f"Unsupported method ({self.command!r})")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _proxy_request(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(content_length) if content_length else None
        upstream_url = f"{BACKEND_BASE_URL.rstrip('/')}{self.path}"

        forwarded_headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "connection"}
        }

        request = urllib.request.Request(
            upstream_url,
            data=body,
            headers=forwarded_headers,
            method=self.command,
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() in HOP_BY_HOP_HEADERS:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            for key, value in exc.headers.items():
                if key.lower() in HOP_BY_HOP_HEADERS:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except Exception as exc:
            payload = (
                f'{{"detail":"Frontend proxy could not reach backend: {exc}"}}'
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")


if __name__ == "__main__":
    os.chdir(DIRECTORY)
    with ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        print(f"MTS AI Frontend running at http://{HOST}:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        print(f"Proxying {PROXY_PREFIX}* to: {BACKEND_BASE_URL}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
