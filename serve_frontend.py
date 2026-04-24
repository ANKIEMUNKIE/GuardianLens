"""
GuardianLens — Frontend Dev Server
Serves the frontend directory over HTTP on port 5500.

Run this from the project root:   python serve_frontend.py
Then open:  http://localhost:5500

This avoids the file:// CORS issue where browsers block API calls
from HTML files opened directly from disk.
"""
import http.server
import socketserver
import os
import webbrowser

PORT = 5500
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        print(f"  [{self.address_string()}] {format % args}", flush=True)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True  # Prevents [WinError 10048] on quick restarts


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print("=" * 60, flush=True)
    print(f"  GuardianLens Frontend Server", flush=True)
    print(f"  Serving:  {FRONTEND_DIR}", flush=True)
    print(f"  URL:      {url}", flush=True)
    print(f"  Backend:  http://localhost:8000", flush=True)
    print("=" * 60, flush=True)

    with ReusableTCPServer(("", PORT), NoCacheHTTPRequestHandler) as httpd:
        print(f"\n  [OK] Listening on {url}", flush=True)
        print(f"  Opening browser...\n", flush=True)
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Frontend server stopped.")
