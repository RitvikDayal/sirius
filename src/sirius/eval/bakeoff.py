"""M1 depth bake-off: score every depth estimator against a printed ArUco target at taped distances."""

from collections import defaultdict
from dataclasses import dataclass

import cv2
import numpy as np

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthEstimator

TARGET_DICT = cv2.aruco.DICT_4X4_50
TARGET_ID = 7
TARGET_MM = 145.0  # fits A4 with its quiet zone; true size does not affect scoring
SAMPLE_FRACTION = 0.6  # central part of the marker that is sampled
MIN_VALID = 0.5
MAX_P90_MS = 100.0


@dataclass(frozen=True)
class Score:
    method: str
    kind: str
    true_m: float
    est_m: float | None
    err_pct: float | None
    valid_frac: float
    latency_ms: float


def make_target(px: int = 800) -> np.ndarray:
    """The marker with a white quiet zone of one module (1/6 of the marker) on each side."""
    d = cv2.aruco.getPredefinedDictionary(TARGET_DICT)
    marker = cv2.aruco.generateImageMarker(d, TARGET_ID, px)
    pad = px // 6
    return cv2.copyMakeBorder(marker, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)


def find_target(image_bgr: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(TARGET_DICT))
    corners, ids, _ = det.detectMarkers(gray)
    if ids is None:
        return None
    for c, i in zip(corners, ids.ravel()):
        if i == TARGET_ID:
            return c.reshape(4, 2)
    return None


def score_capture(rp: RectifiedPair, est: DepthEstimator, true_range_m: float,
                  quad: np.ndarray | None = None) -> Score:
    """`quad`: target corners in rp's pixels, if found elsewhere (e.g. at full resolution for far targets)."""
    res = est.estimate(rp)
    quad = find_target(rp.left) if quad is None else quad
    if quad is None:
        return Score(est.name, est.kind, true_range_m, None, None, 0.0, res.latency_ms)
    centre = quad.mean(axis=0)
    inner = centre + (quad - centre) * SAMPLE_FRACTION
    mask = np.zeros(res.range_m.shape, np.uint8)
    cv2.fillConvexPoly(mask, np.round(inner).astype(np.int32), 1)
    vals = res.range_m[mask.astype(bool)]
    valid = float(np.isfinite(vals).mean()) if vals.size else 0.0
    if valid < MIN_VALID:
        return Score(est.name, est.kind, true_range_m, None, None, valid, res.latency_ms)
    est_m = float(np.nanmedian(vals))
    return Score(est.name, est.kind, true_range_m, est_m, abs(est_m - true_range_m) / true_range_m * 100, valid, res.latency_ms)


def _target_pct(true_m: float) -> float:
    return 10.0 if true_m <= 3.0 else 20.0


def _by_method_distance(scores: list[Score]) -> dict[str, dict[float, list[Score]]]:
    out: dict[str, dict[float, list[Score]]] = defaultdict(lambda: defaultdict(list))
    for s in scores:
        out[s.method][s.true_m].append(s)
    return out


def _median_err(group: list[Score]) -> float | None:
    """Median error over captures; None if most captures had no valid estimate."""
    errs = [s.err_pct for s in group if s.err_pct is not None]
    return float(np.median(errs)) if len(errs) * 2 > len(group) else None


def choose_default(scores: list[Score]) -> str | None:
    best, best_worst = None, float("inf")
    for method, by_d in _by_method_distance(scores).items():
        group = [s for g in by_d.values() for s in g]
        if group[0].kind != "stereo":
            continue
        if np.percentile([s.latency_ms for s in group], 90) > MAX_P90_MS:
            continue
        errs = {d: _median_err(g) for d, g in by_d.items()}
        if any(e is None or e > _target_pct(d) for d, e in errs.items()):
            continue
        worst = max(errs.values())
        if worst < best_worst:
            best, best_worst = method, worst
    return best


def summarise(scores: list[Score]) -> str:
    grouped = _by_method_distance(scores)
    methods = sorted(grouped)
    dists = sorted({s.true_m for s in scores})
    lines = ["| true m | " + " | ".join(methods) + " |", "|---" * (len(methods) + 1) + "|"]
    for d in dists:
        cells = []
        for m in methods:
            g = grouped[m].get(d, [])
            e = _median_err(g) if g else None
            valid = np.mean([s.valid_frac for s in g]) if g else 0.0
            cells.append("—" if e is None else f"{e:.1f}% ({valid * 100:.0f}% valid)")
        lines.append(f"| {d:.1f} | " + " | ".join(cells) + " |")
    lat = [f"{m}: median {np.median([s.latency_ms for s in sum(grouped[m].values(), [])]):.1f} ms, "
           f"p90 {np.percentile([s.latency_ms for s in sum(grouped[m].values(), [])], 90):.1f} ms" for m in methods]
    return "\n".join(lines) + "\n\nLatency (640x360): " + "; ".join(lat) + "\n"
