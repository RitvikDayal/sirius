"""Rectified-stereo geometry in the left rectified camera frame (x right, y down, z forward).

Distances are measured from the midpoint between the two lenses, at x = B/2.
"""

import numpy as np


def depth_from_disparity(disp: np.ndarray, fx: float, baseline_m: float) -> np.ndarray:
    disp = np.asarray(disp, np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(disp > 0, fx * baseline_m / disp, np.nan)
    return z.astype(np.float32)


def range_from_z(z: np.ndarray, fx: float, fy: float, cx: float, cy: float, baseline_m: float) -> np.ndarray:
    h, w = z.shape
    u = np.arange(w, dtype=np.float32)[None, :]
    v = np.arange(h, dtype=np.float32)[:, None]
    x = (u - cx) * z / fx - baseline_m / 2
    y = (v - cy) * z / fy
    return np.sqrt(x * x + y * y + z * z).astype(np.float32)


def bearing_deg(u: float, z: float, fx: float, cx: float, baseline_m: float) -> float:
    """Horizontal angle from the rig midpoint; positive = right."""
    x = (u - cx) * z / fx - baseline_m / 2
    return float(np.degrees(np.arctan2(x, z)))
