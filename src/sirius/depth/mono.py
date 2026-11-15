"""Monocular metric depth (Depth Anything V2, indoor metric, small). Benchmark only.

Phase 1 never speaks a distance from this estimator; the bake-off compares it with stereo.
"""

import time

import cv2
import numpy as np
import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.depth.geometry import range_from_z

MODEL_ID = "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf"


class MonoEstimator:
    name = "mono-dav2-indoor-s"
    kind = "mono"

    def __init__(self, model_id: str = MODEL_ID, device: str = "cuda"):
        self.device = device
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_id).to(device).eval()

    @torch.inference_mode()
    def estimate(self, rp: RectifiedPair) -> DepthResult:
        t0 = time.perf_counter()
        h, w = rp.left.shape[:2]
        inputs = self.processor(images=cv2.cvtColor(rp.left, cv2.COLOR_BGR2RGB), return_tensors="pt").to(self.device)
        z = self.model(**inputs).predicted_depth[None]  # metres along the optical axis
        z = torch.nn.functional.interpolate(z, size=(h, w), mode="bilinear", align_corners=False)[0, 0]
        z = z.float().cpu().numpy()
        z[z <= 0] = np.nan
        rng = range_from_z(z, rp.fx, rp.fy, rp.cx, rp.cy, rp.baseline_m)
        return DepthResult(rng, (time.perf_counter() - t0) * 1000, self.name, z)
