import cv2
import numpy as np

from sirius.calib.rectify import RectifiedPair
from sirius.depth.sgbm import SgbmEstimator

FX, B = 457.0, 0.117
H, W = 360, 640


def plane_pair(shift: int) -> RectifiedPair:
    """A fronto-parallel textured plane at disparity `shift` (x_left - x_right = shift)."""
    rng = np.random.default_rng(0)
    tex = cv2.GaussianBlur((rng.random((H, W + shift)) * 255).astype(np.uint8), (3, 3), 0.8)
    left = cv2.cvtColor(tex[:, :W], cv2.COLOR_GRAY2BGR)
    right = cv2.cvtColor(tex[:, shift:shift + W], cv2.COLOR_GRAY2BGR)
    return RectifiedPair(left, right, 0, FX, FX, W / 2, H / 2, B)


def centre(a: np.ndarray) -> np.ndarray:
    return a[H // 3: 2 * H // 3, W // 3: 2 * W // 3]


def test_sgbm_plane():
    res = SgbmEstimator().estimate(plane_pair(40))
    c = centre(res.range_m)
    expected = FX * B / 40
    assert np.isfinite(c).mean() > 0.9
    assert abs(np.nanmedian(c) - expected) / expected < 0.02
    assert res.method == "sgbm" and res.latency_ms > 0


def test_too_close_is_never_reported_far():
    # 200 px of disparity is beyond the full-resolution 128 px search range (0.27 m away).
    c = centre(SgbmEstimator().estimate(plane_pair(200)).range_m)
    assert not (c[np.isfinite(c)] > 1.0).any()
    expected = FX * B / 200
    assert np.isfinite(c).mean() > 0.5
    assert abs(np.nanmedian(c) - expected) / expected < 0.10
