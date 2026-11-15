from dataclasses import dataclass

import cv2
import numpy as np

MIN_MATCHES = 50


@dataclass(frozen=True)
class IdentityResult:
    ok: bool
    median_dx: float  # x_left - x_right of matched content; > 0 for a correct pair
    median_dy: float
    matches: int


def match_points(a_bgr: np.ndarray, b_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """RANSAC-filtered ORB matches between two views, as Nx2 point arrays."""
    a = cv2.cvtColor(a_bgr, cv2.COLOR_BGR2GRAY) if a_bgr.ndim == 3 else a_bgr
    b = cv2.cvtColor(b_bgr, cv2.COLOR_BGR2GRAY) if b_bgr.ndim == 3 else b_bgr
    orb = cv2.ORB_create(4000)
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    empty = np.empty((0, 2), np.float32)
    if da is None or db is None:
        return empty, empty
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(m) < 8:
        return empty, empty
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    _, inl = cv2.findHomography(pa, pb, cv2.RANSAC, 3.0)
    if inl is None:
        return empty, empty
    keep = inl.ravel() == 1
    return pa[keep], pb[keep]


def check_left_right(left_img: np.ndarray, right_img: np.ndarray) -> IdentityResult:
    pl, pr = match_points(left_img, right_img)
    if len(pl) == 0:
        return IdentityResult(False, 0.0, 0.0, 0)
    d = pl - pr
    dx, dy = float(np.median(d[:, 0])), float(np.median(d[:, 1]))
    return IdentityResult(len(pl) >= MIN_MATCHES and dx > 0, dx, dy, len(pl))
