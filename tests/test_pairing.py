import numpy as np

from sirius.pairing import Frame, StereoPair, pair_latest

MS = 1_000_000
IMG = np.zeros((2, 2, 3), np.uint8)


def f(t_ms, seq):
    return Frame(IMG, int(t_ms * MS), seq)


def test_pair_rejects_skew():
    assert pair_latest(f(0, 1), f(40, 1), 33 * MS, None) is None
    pair = pair_latest(f(0, 1), f(20, 1), 33 * MS, None)
    assert isinstance(pair, StereoPair)
    assert pair.skew_ns == 20 * MS
    assert pair.t_ns == 20 * MS


def test_pair_no_duplicates():
    assert pair_latest(f(0, 5), f(10, 7), 33 * MS, (5, 7)) is None
    assert pair_latest(f(0, 6), f(10, 7), 33 * MS, (5, 7)) is not None


def test_pair_missing_side():
    assert pair_latest(None, f(0, 1), 33 * MS, None) is None
