import csv
import queue
import threading
import time
from pathlib import Path

import cv2

from sirius.source import StereoSource

PNG_FAST = [cv2.IMWRITE_PNG_COMPRESSION, 1]


def _writer(q: queue.Queue, out_dir: Path) -> None:
    while (item := q.get()) is not None:
        name, left, right = item
        cv2.imwrite(str(out_dir / "left" / name), left, PNG_FAST)
        cv2.imwrite(str(out_dir / "right" / name), right, PNG_FAST)


def record(source: StereoSource, out_dir: Path, seconds: float, writers: int = 4) -> int:
    """Save stereo pairs as lossless PNGs plus their capture timestamps.

    PNG encoding at 720p is slower than the cameras, so it runs on writer threads.
    """
    out_dir = Path(out_dir)
    (out_dir / "left").mkdir(parents=True, exist_ok=True)
    (out_dir / "right").mkdir(parents=True, exist_ok=True)
    q: queue.Queue = queue.Queue()
    threads = [threading.Thread(target=_writer, args=(q, out_dir), daemon=True) for _ in range(writers)]
    for t in threads:
        t.start()
    n = 0
    deadline = time.perf_counter() + seconds
    with open(out_dir / "pairs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["idx", "t_left_ns", "t_right_ns"])
        while time.perf_counter() < deadline:
            pair = source.read(timeout_s=0.5)
            if pair is None:
                continue
            q.put((f"{n:06d}.png", pair.left.image, pair.right.image))
            w.writerow([n, pair.left.t_ns, pair.right.t_ns])
            n += 1
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()
    return n
