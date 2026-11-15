"""Fast-FoundationStereo through onnxruntime (nvidia/c-fast-foundationstereo, dynamic H/W export).

Model I/O, from inspecting the ONNX file on 2026-11-14:
  left_image, right_image: float32 [batch, 3, H, W], RGB 0-255
  disparity:               float32 [batch, 1, H, W], pixels at the input scale
"""

import time
from pathlib import Path

import cv2
import numpy as np
import torch  # noqa: F401 - load PyTorch's CUDA 12 / cuDNN 9 first; onnxruntime then reuses them
import onnxruntime as ort

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.depth.geometry import depth_from_disparity, range_from_z

MULTIPLE = 32


class FfsEstimator:
    name = "ffs"
    kind = "stereo"

    def __init__(self, onnx_path: Path):
        # One cuDNN per process: onnxruntime 1.26 (CUDA 12) finds PyTorch's copy first.
        ort.preload_dlls()
        opts = ort.SessionOptions()
        opts.log_severity_level = 3  # the export logs a ScatterND warning per run
        self.session = ort.InferenceSession(
            str(onnx_path), opts, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.provider = self.session.get_providers()[0]

    @staticmethod
    def _tensor(bgr: np.ndarray, ph: int, pw: int) -> np.ndarray:
        # Pad bottom/right (edge-replicated) so fx and cx stay valid for the original pixels.
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.copyMakeBorder(rgb, 0, ph, 0, pw, cv2.BORDER_REPLICATE)
        return np.ascontiguousarray(rgb.transpose(2, 0, 1)[None], dtype=np.float32)

    def estimate(self, rp: RectifiedPair) -> DepthResult:
        t0 = time.perf_counter()
        h, w = rp.left.shape[:2]
        ph, pw = (-h) % MULTIPLE, (-w) % MULTIPLE
        disp = self.session.run(
            ["disparity"],
            {"left_image": self._tensor(rp.left, ph, pw), "right_image": self._tensor(rp.right, ph, pw)},
        )[0][0, 0, :h, :w]
        disp = disp.astype(np.float32)
        # Columns where the matching point would fall left of the right image are unobservable.
        cols = np.arange(w, dtype=np.float32)[None, :]
        disp[disp >= cols] = 0.0
        z = depth_from_disparity(disp, rp.fx, rp.baseline_m)
        rng = range_from_z(z, rp.fx, rp.fy, rp.cx, rp.cy, rp.baseline_m)
        return DepthResult(rng, (time.perf_counter() - t0) * 1000, self.name, z)
