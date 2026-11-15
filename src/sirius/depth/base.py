from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np

from sirius.calib.rectify import RectifiedPair


@dataclass(frozen=True)
class DepthResult:
    range_m: np.ndarray  # float32 HxW, metres from the lens midpoint; NaN = invalid
    latency_ms: float
    method: str
    z_m: np.ndarray | None = None  # depth along the optical axis, for 3D views


class DepthEstimator(Protocol):
    name: str
    kind: Literal["stereo", "mono"]

    def estimate(self, rp: RectifiedPair) -> DepthResult: ...
