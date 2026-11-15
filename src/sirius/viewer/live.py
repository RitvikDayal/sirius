"""`sirius view`: run capture + depth (+ detection when available) and feed the browser dashboard."""

import time
import webbrowser
from pathlib import Path

import cv2
import numpy as np

from sirius.calib.rectify import RectifiedPair, Rectifier
from sirius.config import RigConfig
from sirius.health import ir_mismatch, is_fresh
from sirius.viewer.dashboard import Dashboard
from sirius.viewer.points import depth_to_points

# Before calibration: no rectification, nominal intrinsics for a ~70 deg lens at 640 px wide.
UNCALIBRATED_FX = 457.0


def colorize_range(range_m: np.ndarray, near: float = 0.3, far: float = 6.0) -> np.ndarray:
    t = np.clip((np.nan_to_num(range_m, nan=far) - near) / (far - near), 0, 1)
    img = cv2.applyColorMap(((1 - t) * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    img[~np.isfinite(range_m)] = 0
    return img


def _label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.putText(out, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
    cv2.putText(out, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    return out


ZONE_BGR = {"urgent": (40, 40, 255), "near": (0, 170, 255), "aware": (80, 220, 80), None: (200, 200, 200)}


def draw_objects(img: np.ndarray, objs, approx: bool) -> np.ndarray:
    out = img.copy()
    for o in objs:
        x0, y0, x1, y1 = (int(v) for v in o.box)
        col = ZONE_BGR.get(o.zone, ZONE_BGR[None])
        cv2.rectangle(out, (x0, y0), (x1, y1), col, 2)
        dist = "?" if o.range_m is None else f"{'~' if approx else ''}{o.range_m:.2f} m"
        text = f"{o.label} {dist}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(out, (x0, max(0, y0 - th - 6)), (x0 + tw + 6, y0), col, -1)
        cv2.putText(out, text, (x0 + 3, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    return out


def _estimator(name: str):
    if name == "sgbm":
        from sirius.depth.sgbm import SgbmEstimator

        return SgbmEstimator()
    if name == "ffs":
        from sirius.depth.ffs import FfsEstimator

        return FfsEstimator(Path("data/models/ffs/onnx/c_fast_foundationstereo_bp2_dynbatch_dynhw.onnx"))
    from sirius.depth.mono import MonoEstimator

    return MonoEstimator()


class ApproxRectifier:
    """Before calibration: resize only, nominal intrinsics. Depth from this is never spoken as a number."""

    def __init__(self, cfg: RigConfig):
        self.size = (int(cfg.width * cfg.depth_scale), int(cfg.height * cfg.depth_scale))
        self.baseline = (cfg.baseline_mm_measured or 117.0) / 1000

    def rectify(self, pair) -> RectifiedPair:
        w, h = self.size
        left = cv2.resize(pair.left.image, (w, h), interpolation=cv2.INTER_AREA)
        right = cv2.resize(pair.right.image, (w, h), interpolation=cv2.INTER_AREA)
        return RectifiedPair(left, right, pair.t_ns, UNCALIBRATED_FX, UNCALIBRATED_FX, w / 2, h / 2, self.baseline)


class NoDepth:
    name, kind, latency_ms = "off", "none", 0.0

    def estimate(self, rp):
        from sirius.depth.base import DepthResult

        nan = np.full(rp.left.shape[:2], np.nan, np.float32)
        return DepthResult(nan, 0.0, self.name, None)


class NoDetector:
    last_ms = 0.0

    def detect(self, img):
        return []


class SilentVoice:
    def say(self, text, interrupt):
        return time.perf_counter_ns()

    def busy(self):
        return False


def run_view(cfg: RigConfig, source, depth_name: str | None, port: int, open_browser: bool = True,
             snapshot: Path | None = None, seconds: float | None = None, detector=None,
             voice=None, log_path: Path | None = None) -> None:
    from sirius.pipeline import Pipeline

    calib = None
    if cfg.calibration and Path(cfg.calibration).exists():
        from sirius.calib.stereo import Calibration

        calib = Calibration.load(cfg.calibration)
    depth_name = depth_name or (cfg.depth_method if calib else "mono")
    if depth_name not in ("mono", "none") and calib is None:
        print(f"no calibration yet: '{depth_name}' needs rectified pairs, using single-camera depth instead")
        depth_name = "mono"
    est = NoDepth() if depth_name == "none" else _estimator(depth_name)
    rect = Rectifier(calib, cfg.depth_scale) if calib else ApproxRectifier(cfg)
    note = "rectified" if calib else "uncalibrated"
    from sirius.voice import MutableVoice

    speaking = voice is not None
    voice = MutableVoice(voice or SilentVoice())
    pipe = Pipeline(source, rect, est, detector or NoDetector(), voice, log_path,
                    speak_approx_distances=cfg.speak_approx_distances)

    dash = Dashboard(port=port)
    dash.start()
    print(f"SIRIUS live view: {dash.url}  (Ctrl+C to stop)  voice: {'on' if speaking else 'off'}")
    if open_browser:
        webbrowser.open(dash.url)

    # Warm the models (CUDA kernels, cuDNN autotune) so the first real frame is not seconds late.
    w, h = int(cfg.width * cfg.depth_scale), int(cfg.height * cfg.depth_scale)
    blank = np.full((h, w, 3), 127, np.uint8)
    warm = RectifiedPair(blank, blank, 0, UNCALIBRATED_FX, UNCALIBRATED_FX, w / 2, h / 2, 0.117)
    for _ in range(3):
        est.estimate(warm)
        pipe.detector.detect(blank)

    source.start()
    t_end = time.perf_counter() + seconds if seconds else None
    last, last_said, frames, t_fps = None, "", 0, time.perf_counter()
    try:
        while t_end is None or time.perf_counter() < t_end:
            voice.muted = dash.controls["mute"]
            r = pipe.step()
            if r is None:
                continue
            rp, res, h = r.rp, r.depth, r.health
            approx = calib is None or est.kind != "stereo"
            dash.publish_image("left", _label(rp.left, f"left ({note})"))
            dash.publish_image("right", _label(rp.right, f"right ({note})"))
            dash.publish_image("depth", _label(colorize_range(res.range_m), f"{res.method}  {res.latency_ms:.0f} ms"))
            objects = _label(draw_objects(rp.left, r.objects, approx), f"D-FINE {r.log['detect_ms']:.0f} ms") if detector                 else _label(rp.left, "object detection off")
            dash.publish_image("objects", objects)
            if res.z_m is not None:
                dash.publish_points(*depth_to_points(res.z_m, rp.left, rp.fx, rp.fy, rp.cx, rp.cy, rp.baseline_m, step=3))
            if r.spoken:
                last_said = r.spoken
            frames += 1
            now = time.perf_counter()
            level = {}
            if not is_fresh(h):
                level["cameras"] = "bad"
            if ir_mismatch(h):
                level["saturation"] = "warn"
            dash.publish_stats({
                "view_fps": frames / max(now - t_fps, 1e-6),
                "fps_left": h.fps_left, "fps_right": h.fps_right,
                "depth": res.method, "depth_ms": res.latency_ms,
                "detector_ms": r.log["detect_ms"], "step_ms": r.log["total_ms"],
                "calibration": "yes" if calib else "no (approximate)",
                "cameras": "ok" if is_fresh(h) else "STALE/DARK",
                "saturation": f"{h.sat_left:.0f}/{h.sat_right:.0f}",
                "voice": ("muted" if voice.muted else "on") if speaking else "off",
                "muted": voice.muted,
                "speech": (last_said + ("" if speaking and not voice.muted else "   (not spoken)")) if last_said else "",
                "level": level,
            })
            if now - t_fps > 5:
                frames, t_fps = 0, now
            last = np.vstack([np.hstack([rp.left, rp.right]), np.hstack([colorize_range(res.range_m), objects])])
    except KeyboardInterrupt:
        pass
    finally:
        source.stop()
        pipe.close()
        dash.stop()
        if snapshot is not None and last is not None:
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(snapshot), last)
