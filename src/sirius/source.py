import time
from typing import Protocol

from sirius.capture import CameraGrabber
from sirius.config import RigConfig
from sirius.devices import list_video_devices, resolve
from sirius.health import SourceHealth, image_stats
from sirius.pairing import StereoPair, pair_latest


class StereoSource(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def read(self, timeout_s: float) -> StereoPair | None: ...
    def health(self) -> SourceHealth: ...


def health_of(pair: StereoPair | None, fps_left: float, fps_right: float,
              age_left: float, age_right: float) -> SourceHealth:
    if pair is None:
        return SourceHealth(fps_left, fps_right, age_left, age_right, 0.0, 0.0, 0.0, 0.0)
    ll, sl = image_stats(pair.left.image)
    lr, sr = image_stats(pair.right.image)
    return SourceHealth(fps_left, fps_right, age_left, age_right, ll, lr, sl, sr)


class LiveStereoSource:
    def __init__(self, cfg: RigConfig):
        devices = list_video_devices()
        self.left = CameraGrabber(resolve(cfg.left_path, devices), cfg.width, cfg.height, cfg.fps)
        self.right = CameraGrabber(resolve(cfg.right_path, devices), cfg.width, cfg.height, cfg.fps)
        self.max_skew_ns = int(1e9 / cfg.fps)
        self._last: tuple[int, int] | None = None
        self._last_pair: StereoPair | None = None

    def start(self) -> None:
        # Opening two identical cameras at the same instant sometimes fails; stagger them.
        self.left.start()
        self.left.opened.wait(timeout=8)
        self.right.start()
        self.right.opened.wait(timeout=8)

    def stop(self) -> None:
        self.left.stop()
        self.right.stop()

    def read(self, timeout_s: float) -> StereoPair | None:
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            pair = pair_latest(self.left.latest(), self.right.latest(), self.max_skew_ns, self._last)
            if pair is not None:
                self._last = (pair.left.seq, pair.right.seq)
                self._last_pair = pair
                return pair
            time.sleep(0.001)
        return None

    def health(self) -> SourceHealth:
        return health_of(self._last_pair, self.left.fps(), self.right.fps(),
                         self.left.age_ms(), self.right.age_ms())
