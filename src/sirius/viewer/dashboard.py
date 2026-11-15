"""Live browser dashboard: MJPEG panels, a stats feed and a 3D point cloud.

Anything in the pipeline publishes into it; the page polls/streams from it.
Serves on 127.0.0.1 only.
"""

import json
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

PAGE = Path(__file__).with_name("index.html")
STATIC = Path(__file__).with_name("static")
BOUNDARY = b"siriusframe"


class Dashboard:
    def __init__(self, port: int = 8765, host: str = "127.0.0.1"):
        self._host, self._port = host, port
        self._lock = threading.Lock()
        self._jpegs: dict[str, tuple[int, bytes]] = {}
        self._stats: dict = {}
        self._points = struct.pack("<I", 0)
        self.controls: dict = {"mute": False}
        self._server: ThreadingHTTPServer | None = None
        self._running = False

    @property
    def port(self) -> int:
        return self._server.server_address[1] if self._server else self._port

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self.port}/"

    def publish_image(self, name: str, image_bgr: np.ndarray, quality: int = 80) -> None:
        ok, buf = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            with self._lock:
                seq = self._jpegs.get(name, (0, b""))[0] + 1
                self._jpegs[name] = (seq, buf.tobytes())

    def publish_stats(self, stats: dict) -> None:
        with self._lock:
            self._stats = dict(stats)

    def publish_points(self, xyz: np.ndarray, rgb: np.ndarray) -> None:
        data = struct.pack("<I", len(xyz)) + np.ascontiguousarray(xyz, np.float32).tobytes() + np.ascontiguousarray(rgb, np.uint8).tobytes()
        with self._lock:
            self._points = data

    def _handler(self):
        dash = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, ctype: str, body: bytes) -> None:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                if self.path != "/control":
                    self.send_error(404)
                    return
                try:
                    body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                except ValueError:
                    self.send_error(400)
                    return
                with dash._lock:
                    if isinstance(body.get("mute"), bool):
                        dash.controls["mute"] = body["mute"]
                    out = json.dumps(dash.controls).encode()
                self._send("application/json", out)

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    self._send("text/html; charset=utf-8", PAGE.read_bytes())
                elif self.path == "/stats":
                    with dash._lock:
                        body = json.dumps(dash._stats).encode()
                    self._send("application/json", body)
                elif self.path == "/points":
                    with dash._lock:
                        body = dash._points
                    self._send("application/octet-stream", body)
                elif self.path.startswith("/static/"):
                    name = self.path[len("/static/"):]
                    f = STATIC / name
                    if "/" in name or "\\" in name or ".." in name or not f.is_file():
                        self.send_error(404)
                    else:
                        self._send("text/javascript; charset=utf-8", f.read_bytes())
                elif self.path.startswith("/stream/"):
                    self._stream(self.path.split("/", 2)[2])
                else:
                    self.send_error(404)

            def _stream(self, name: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY.decode()}")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                last = -1
                try:
                    while dash._running:
                        with dash._lock:
                            seq, jpg = dash._jpegs.get(name, (0, b""))
                        if seq != last and jpg:
                            last = seq
                            self.wfile.write(b"--" + BOUNDARY + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                             + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                            self.wfile.flush()
                        time.sleep(0.01)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        return Handler

    def start(self) -> None:
        self._running = True
        self._server = ThreadingHTTPServer((self._host, self._port), self._handler())
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()
