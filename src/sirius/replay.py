import csv
import time
from pathlib import Path

import cv2

from sirius.health import SourceHealth
from sirius.pairing import Frame, StereoPair
from sirius.source import health_of


class ReplayStereoSource:
    """Plays back a recorded clip; timestamps keep their recorded spacing, rebased to now."""

    def __init__(self, clip_dir: Path, realtime: bool = True):
        self.dir = Path(clip_dir)
        with open(self.dir / "pairs.csv", newline="", encoding="utf-8") as fh:
            self.rows = [(int(r["idx"]), int(r["t_left_ns"]), int(r["t_right_ns"])) for r in csv.DictReader(fh)]
        self.realtime = realtime
        self._i = 0
        self._offset = 0
        self._last: StereoPair | None = None

    def start(self) -> None:
        self._i = 0
        if self.rows:
            self._offset = time.perf_counter_ns() - self.rows[0][1]

    def stop(self) -> None:
        pass

    def read(self, timeout_s: float) -> StereoPair | None:
        if self._i >= len(self.rows):
            return None
        idx, tl, tr = self.rows[self._i]
        self._i += 1
        tl, tr = tl + self._offset, tr + self._offset
        if self.realtime:
            wait = (max(tl, tr) - time.perf_counter_ns()) / 1e9
            if wait > 0:
                time.sleep(wait)
        name = f"{idx:06d}.png"
        left = cv2.imread(str(self.dir / "left" / name), cv2.IMREAD_COLOR)
        right = cv2.imread(str(self.dir / "right" / name), cv2.IMREAD_COLOR)
        self._last = StereoPair(Frame(left, tl, idx + 1), Frame(right, tr, idx + 1))
        return self._last

    def health(self) -> SourceHealth:
        # A replay is as fresh as the pair it just returned.
        return health_of(self._last, 0.0, 0.0, 0.0, 0.0)
