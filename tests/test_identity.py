import cv2
import numpy as np

from sirius.identity import check_left_right


def _views(shift=60):
    rng = np.random.default_rng(0)
    base = (rng.random((360, 900)) * 255).astype(np.uint8)
    base = cv2.GaussianBlur(base, (5, 5), 1.5)
    base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    # A left camera sees content further right than the right camera does.
    left = base[:, 100:740]
    right = base[:, 100 + shift:740 + shift]
    return left, right


def test_identity_accepts_left_right():
    left, right = _views()
    r = check_left_right(left, right)
    assert r.ok and r.matches >= 50
    assert abs(r.median_dx - 60) < 2


def test_identity_detects_swap():
    left, right = _views()
    r = check_left_right(right, left)
    assert not r.ok
    assert r.median_dx < 0
