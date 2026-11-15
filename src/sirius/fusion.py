"""Distance per detected object, from the depth map."""

import numpy as np

from sirius.depth.base import DepthResult
from sirius.detect import Detection

CENTRE_FRACTION = 0.5  # inner 50% of the box width and height
MIN_VALID = 0.5

URGENT_M, NEAR_M, AWARE_M = 1.0, 2.5, 5.0


def object_range(det: Detection, depth: DepthResult) -> float | None:
    """Median range over the box centre; None when under half of it has valid depth."""
    x0, y0, x1, y1 = det.box
    cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * CENTRE_FRACTION / 2, (y1 - y0) * CENTRE_FRACTION / 2
    h, w = depth.range_m.shape
    region = depth.range_m[max(0, int(cy - hh)):min(h, int(cy + hh)), max(0, int(cx - hw)):min(w, int(cx + hw))]
    if region.size == 0 or np.isfinite(region).mean() < MIN_VALID:
        return None
    return float(np.nanmedian(region))


def zone_of(range_m: float | None) -> str | None:
    if range_m is None or range_m >= AWARE_M:
        return None
    if range_m < URGENT_M:
        return "urgent"
    return "near" if range_m < NEAR_M else "aware"
