import numpy as np

from sirius.pairing import Frame, StereoPair
from sirius.recorder import record
from sirius.replay import ReplayStereoSource

MS = 1_000_000


class FakeSource:
    def __init__(self, pairs):
        self._pairs = list(pairs)

    def start(self):
        pass

    def stop(self):
        pass

    def read(self, timeout_s):
        return self._pairs.pop(0) if self._pairs else None

    def health(self):
        raise NotImplementedError


def _pairs(n=5):
    rng = np.random.default_rng(1)
    out = []
    for i in range(n):
        left = rng.integers(0, 255, (12, 16, 3), dtype=np.uint8)
        right = rng.integers(0, 255, (12, 16, 3), dtype=np.uint8)
        t = 1_000 * MS + i * 40 * MS
        out.append(StereoPair(Frame(left, t, i + 1), Frame(right, t + 7 * MS, i + 1)))
    return out


def test_roundtrip(tmp_path):
    pairs = _pairs()
    assert record(FakeSource(pairs), tmp_path, seconds=0.3) == 5
    src = ReplayStereoSource(tmp_path, realtime=False)
    src.start()
    got = [src.read(0.1) for _ in range(5)]
    assert src.read(0.1) is None
    for a, b in zip(pairs, got):
        assert np.array_equal(a.left.image, b.left.image)
        assert np.array_equal(a.right.image, b.right.image)
        assert b.right.t_ns - b.left.t_ns == 7 * MS
    assert got[4].left.t_ns - got[0].left.t_ns == 160 * MS
