#!/usr/bin/env python3
"""Simple HTTP server for the MTS AI frontend."""
import http.server
import os
import socketserver

HOST = os.environ.get("FRONTEND_HOST", "127.0.0.1")
PORT = int(os.environ.get("FRONTEND_PORT", "8010"))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/index.html'
        super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")


if __name__ == '__main__':
    os.chdir(DIRECTORY)
    with ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        print(f"MTS AI Frontend running at http://{HOST}:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
