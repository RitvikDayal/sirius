"""Camera capture through ffmpeg.

OpenCV's DirectShow backend tops out at 25 FPS in MJPEG on these boards while
ffmpeg gets 30, and ffmpeg opens a camera by device path rather than by index.
ffmpeg passes the camera's JPEGs through untouched; raw BGR at 83 MB/s per
camera saturates the pipe. Frames are decoded here.
"""

import collections
import subprocess
import threading
import time
from typing import BinaryIO, Iterator

import cv2
import numpy as np

from sirius.devices import DeviceInfo
from sirius.pairing import Frame

REOPEN_AFTER_S = 1.0
SOI, EOI = b"\xff\xd8", b"\xff\xd9"


def ffmpeg_args(device_path: str, width: int, height: int, fps: int) -> list[str]:
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-fflags", "nobuffer", "-flags", "low_delay",
        "-f", "dshow", "-rtbufsize", "16M",
        "-vcodec", "mjpeg", "-video_size", f"{width}x{height}", "-framerate", str(fps),
        "-i", f"video={device_path}",
        "-an", "-c:v", "copy", "-f", "mjpeg", "pipe:1",
    ]


def iter_jpegs(stream: BinaryIO, chunk: int = 1 << 16) -> Iterator[bytes]:
    """Split a concatenated MJPEG byte stream into JPEGs (SOI ... EOI)."""
    buf = bytearray()
    while True:
        data = stream.read(chunk)
        if not data:
            return
        buf += data
        while True:
            start = buf.find(SOI)
            if start < 0:
                buf.clear()
                break
            end = buf.find(EOI, start + 2)
            if end < 0:
                del buf[:start]
                break
            yield bytes(buf[start:end + 2])
            del buf[:end + 2]


class CameraGrabber:
    """Reads one camera through an ffmpeg process and keeps only the newest frame."""

    def __init__(self, device: DeviceInfo, width: int, height: int, fps: int):
        self.device = device
        self.size = (width, height)
        self.target_fps = fps
        self._lock = threading.Lock()
        self._latest: Frame | None = None
        self._stamps: collections.deque[int] = collections.deque(maxlen=256)
        self._seq = 0
        self._running = False
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self.opened = threading.Event()
        self.reopens = 0

    def _read_loop(self, proc: subprocess.Popen) -> None:
        for jpg in iter_jpegs(proc.stdout):
            now_ns = time.perf_counter_ns()
            img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            with self._lock:
                self._seq += 1
                self._latest = Frame(img, now_ns, self._seq)
                self._stamps.append(now_ns)
            self.opened.set()

    def _spawn(self) -> tuple[subprocess.Popen, threading.Thread]:
        proc = subprocess.Popen(
            ffmpeg_args(self.device.path, *self.size, self.target_fps),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        reader = threading.Thread(target=self._read_loop, args=(proc,), daemon=True)
        reader.start()
        return proc, reader

    def _run(self) -> None:
        proc, reader = self._spawn()
        started = time.perf_counter()
        while self._running:
            time.sleep(0.05)
            f = self.latest()
            last = f.t_ns / 1e9 if f is not None else started
            if not reader.is_alive() or time.perf_counter() - max(last, started) > REOPEN_AFTER_S:
                proc.kill()
                proc.wait()
                reader.join(timeout=1)
                time.sleep(0.5)
                proc, reader = self._spawn()
                started = time.perf_counter()
                self.reopens += 1
        proc.kill()
        proc.wait()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, name=f"cam{self.device.index}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)

    def latest(self) -> Frame | None:
        with self._lock:
            return self._latest

    def fps(self, window_s: float = 2.0) -> float:
        now = time.perf_counter_ns()
        with self._lock:
            n = sum(1 for t in self._stamps if now - t <= window_s * 1e9)
        return n / window_s

    def age_ms(self) -> float:
        f = self.latest()
        return float("inf") if f is None else (time.perf_counter_ns() - f.t_ns) / 1e6
