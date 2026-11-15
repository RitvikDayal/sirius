from dataclasses import dataclass

import cv2
import numpy as np

from sirius.calib.stereo import Calibration
from sirius.pairing import StereoPair


@dataclass(frozen=True)
class RectifiedPair:
    left: np.ndarray
    right: np.ndarray
    t_ns: int
    fx: float
    fy: float
    cx: float
    cy: float
    baseline_m: float


class Rectifier:
    def __init__(self, calib: Calibration, scale: float):
        self.scale = scale
        self.size = calib.size
        self.maps_l = cv2.initUndistortRectifyMap(calib.K1, calib.D1, calib.R1, calib.P1, calib.size, cv2.CV_16SC2)
        self.maps_r = cv2.initUndistortRectifyMap(calib.K2, calib.D2, calib.R2, calib.P2, calib.size, cv2.CV_16SC2)
        P1, P2 = calib.P1, calib.P2
        self.fx, self.fy = P1[0, 0] * scale, P1[1, 1] * scale
        self.cx, self.cy = P1[0, 2] * scale, P1[1, 2] * scale
        self.baseline_m = float(-P2[0, 3] / P2[0, 0])

    def _one(self, img: np.ndarray, maps) -> np.ndarray:
        out = cv2.remap(img, maps[0], maps[1], cv2.INTER_LINEAR)
        if self.scale != 1.0:
            w, h = self.size
            out = cv2.resize(out, (round(w * self.scale), round(h * self.scale)), interpolation=cv2.INTER_AREA)
        return out

    def rectify(self, pair: StereoPair) -> RectifiedPair:
        return RectifiedPair(
            self._one(pair.left.image, self.maps_l), self._one(pair.right.image, self.maps_r),
            pair.t_ns, self.fx, self.fy, self.cx, self.cy, self.baseline_m,
        )
