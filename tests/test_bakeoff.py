import cv2
import numpy as np

from sirius.calib.rectify import RectifiedPair
from sirius.depth.sgbm import SgbmEstimator
from sirius.eval.bakeoff import Score, choose_default, make_target, score_capture, summarise

FX, B, H, W = 457.0, 0.117, 360, 640


def target_pair(shift: int) -> tuple[RectifiedPair, float]:
    """Textured plane at disparity `shift` with the ArUco target pasted on it."""
    rng = np.random.default_rng(0)
    tex = cv2.GaussianBlur((rng.random((H, W + shift)) * 255).astype(np.uint8), (3, 3), 0.8)
    marker = cv2.resize(make_target(), (110, 110), interpolation=cv2.INTER_NEAREST)
    z = FX * B / shift
    u0 = int(W / 2 + FX * (B / 2) / z) - 55  # centred in front of the rig midpoint
    tex[H // 2 - 55: H // 2 + 55, u0: u0 + 110] = marker
    left = cv2.cvtColor(tex[:, :W], cv2.COLOR_GRAY2BGR)
    right = cv2.cvtColor(tex[:, shift:shift + W], cv2.COLOR_GRAY2BGR)
    return RectifiedPair(left, right, 0, FX, FX, W / 2, H / 2, B), z


def test_score_on_synthetic():
    rp, z = target_pair(40)
    s = score_capture(rp, SgbmEstimator(), true_range_m=z)
    assert s.est_m is not None and s.err_pct < 3
    assert s.method == "sgbm" and s.valid_frac >= 0.5


def test_missing_target_scores_none():
    rp, z = target_pair(40)
    blank = RectifiedPair(np.full_like(rp.left, 128), rp.right, 0, FX, FX, W / 2, H / 2, B)
    s = score_capture(blank, SgbmEstimator(), true_range_m=z)
    assert s.est_m is None and s.err_pct is None


def _scores(method, kind, errs, latency):
    dists = [0.5, 1.0, 2.0, 3.0, 5.0]
    return [Score(method, kind, d, d * (1 + e / 100), e, 1.0, latency) for d, e in zip(dists, errs)]


def test_choose_default_rules():
    good = _scores("sgbm", "stereo", [2, 3, 4, 6, 15], 18)
    slow = _scores("ffs", "stereo", [1, 1, 1, 2, 5], 150)
    mono = _scores("mono", "mono", [0, 0, 0, 0, 0], 14)
    assert choose_default(good + slow + mono) == "sgbm"  # mono never; slow stereo excluded
    bad = _scores("sgbm", "stereo", [2, 3, 12, 6, 15], 18)  # 12% at 2 m breaks the 10% target
    assert choose_default(bad + mono) is None


def test_summarise_has_a_row_per_distance():
    md = summarise(_scores("sgbm", "stereo", [2, 3, 4, 6, 15], 18))
    for d in ("0.5", "1.0", "2.0", "3.0", "5.0"):
        assert f"| {d}" in md
