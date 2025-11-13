"""
Frontend Server - Serves the HTML/CSS/JS files
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000
DIRECTORY = Path(__file__).parent / "frontend"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    os.chdir(DIRECTORY)

    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print("=" * 70)
        print("FRONTEND SERVER STARTED")
        print("=" * 70)
        print(f"\nFrontend running at: http://localhost:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        print("\nOpen your browser and go to: http://localhost:3000")
        print("\nMake sure the API server is running on port 8000")
        print("   (Run 'python run_server.py' in another terminal)")
        print("\nPress Ctrl+C to stop the server\n")
        print("=" * 70)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nFrontend server stopped")
