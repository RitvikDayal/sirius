import time

import cv2
import numpy as np

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.depth.geometry import depth_from_disparity, range_from_z

AGREE = 0.25  # full- and half-resolution disparities must agree within 25%


def _matcher(num_disparities: int, block_size: int) -> cv2.StereoSGBM:
    return cv2.StereoSGBM_create(
        minDisparity=0, numDisparities=num_disparities, blockSize=block_size,
        P1=8 * 3 * block_size ** 2, P2=32 * 3 * block_size ** 2,
        disp12MaxDiff=1, uniquenessRatio=10, speckleWindowSize=100, speckleRange=2,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )


def _disparity(m: cv2.StereoSGBM, left: np.ndarray, right: np.ndarray, num: int) -> np.ndarray:
    d = m.compute(left, right).astype(np.float32) / 16.0
    d[d <= 0] = np.nan
    d[:, :num] = np.nan  # leftmost columns have no partner in the right image
    return d


class SgbmEstimator:
    """SGBM at full and half resolution.

    Something closer than the full-resolution search range gets mismatched to a
    small disparity and reads as far away. The half-resolution pass covers twice
    the disparity: it supplies near values and vetoes full-resolution pixels it
    disagrees with.
    """

    name = "sgbm"
    kind = "stereo"

    def __init__(self, num_disparities: int = 128, block_size: int = 5):
        self.num = num_disparities
        self.full = _matcher(num_disparities, block_size)
        self.half = _matcher(num_disparities, block_size)

    def estimate(self, rp: RectifiedPair) -> DepthResult:
        t0 = time.perf_counter()
        h, w = rp.left.shape[:2]
        full = _disparity(self.full, rp.left, rp.right, self.num)
        small = [cv2.resize(i, (w // 2, h // 2), interpolation=cv2.INTER_AREA) for i in (rp.left, rp.right)]
        half = _disparity(self.half, *small, self.num // 2)
        half = cv2.resize(np.nan_to_num(half, nan=0.0), (w, h), interpolation=cv2.INTER_NEAREST) * 2.0
        half[half <= 0] = np.nan

        with np.errstate(invalid="ignore"):
            near = half >= self.num * 0.95  # beyond what the full-resolution pass can see
            disagree = np.abs(full - half) > AGREE * half
        disp = np.where(near, half, np.where(disagree, np.nan, full))

        z = depth_from_disparity(np.nan_to_num(disp, nan=0.0), rp.fx, rp.baseline_m)
        rng = range_from_z(z, rp.fx, rp.fy, rp.cx, rp.cy, rp.baseline_m)
        return DepthResult(rng, (time.perf_counter() - t0) * 1000, self.name, z)
