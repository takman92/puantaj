import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE, "index.html")
STATE_FILE = os.path.join(BASE, "state.json")
DEFAULT_PORT = 8321

_lock = threading.Lock()


def read_state():
    with _lock:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                return f.read()
    return None


def write_state(raw):
    with _lock:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "wb") as f:
            f.write(raw)
        os.replace(tmp, STATE_FILE)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(INDEX_FILE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, b"index.html yok", "text/plain; charset=utf-8")
        elif path == "/state.json":
            data = read_state()
            if data is None:
                self._send(404, b"", "application/json")
            else:
                self._send(200, data, "application/json; charset=utf-8")
        else:
            self._send(404, b"", "application/json")

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/state.json":
            self._send(404, b"", "application/json")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            json.loads(raw)
        except Exception:
            self._send(400, b'{"error":"gecersiz json"}', "application/json")
            return
        write_state(raw)
        self._send(200, b'{"ok":true}', "application/json")

    def log_message(self, fmt, *args):
        pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_browser = any(a.startswith("--") for a in sys.argv[1:])
    port = DEFAULT_PORT
    if args:
        try:
            port = int(args[0])
        except ValueError:
            pass

    server = None
    chosen = None
    for candidate in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            chosen = candidate
            break
        except OSError:
            continue
    if server is None:
        print("Uygun bir port bulunamadi. Farkli bir port dene: python server.py 9000")
        sys.exit(1)

    url = f"http://localhost:{chosen}"
    print("Puantaj sunucusu calisiyor:", url)
    print("Veri dosyasi:", STATE_FILE)
    print("Durdurmak icin Ctrl+C")
    if not no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
