#!/usr/bin/env python3
"""Simple HTTP server for the MTS AI frontend on port 8010."""
import http.server
import socketserver
import os

PORT = 8010
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Serve index.html for root
        if self.path == '/' or self.path == '':
            self.path = '/index.html'
        super().do_GET()

    def end_headers(self):
        # Allow CORS for API calls from the page
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")


if __name__ == '__main__':
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"MTS AI Frontend running at http://localhost:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
