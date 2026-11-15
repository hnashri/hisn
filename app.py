# Hisn web interface - runs only on your own computer (127.0.0.1)
# start it with:  python app.py   then open  http://127.0.0.1:8000
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from hisn import analyze

PAGE = (Path(__file__).parent / "web" / "index.html").read_bytes()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE)

    def do_POST(self):
        if self.path != "/check":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", 0))
        password = json.loads(self.rfile.read(size)).get("password", "")
        body = json.dumps(analyze(password), ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # never print requests, so passwords never show up in the terminal


if __name__ == "__main__":
    print("Hisn is running: http://127.0.0.1:8000  (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
