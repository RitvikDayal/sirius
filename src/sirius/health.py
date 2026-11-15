from dataclasses import dataclass

import cv2
import numpy as np

MAX_AGE_MS = 200.0
MIN_LUMA = 10.0
IR_SAT_RATIO = 3.0


@dataclass(frozen=True)
class SourceHealth:
    fps_left: float
    fps_right: float
    age_ms_left: float
    age_ms_right: float
    luma_left: float
    luma_right: float
    sat_left: float
    sat_right: float


def image_stats(image_bgr: np.ndarray) -> tuple[float, float]:
    """Mean luma and mean HSV saturation (0-255) on a subsampled image."""
    small = image_bgr[::8, ::8]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    luma = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return float(luma.mean()), float(hsv[..., 1].mean())


def is_fresh(h: SourceHealth) -> bool:
    return (
        h.age_ms_left <= MAX_AGE_MS
        and h.age_ms_right <= MAX_AGE_MS
        and h.luma_left >= MIN_LUMA
        and h.luma_right >= MIN_LUMA
    )


def ir_mismatch(h: SourceHealth) -> bool:
    """One board flipped to IR/greyscale while the other stayed in colour."""
    hi, lo = max(h.sat_left, h.sat_right), min(h.sat_left, h.sat_right)
    return hi / max(lo, 0.1) > IR_SAT_RATIO
