"""Greedy IoU tracker with smoothed ranges.

Small and dependency-free: a navigation aid sees a handful of objects, and a
track only has to survive long enough to stop repeated announcements.
"""

from dataclasses import dataclass

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.depth.geometry import bearing_deg
from sirius.detect import Detection
from sirius.fusion import object_range, zone_of

IOU_MATCH = 0.3
MAX_AGE_NS = 500_000_000
EMA_ALPHA = 0.4
NOMINAL_Z = 2.0  # for direction only, when range is unknown


@dataclass(frozen=True)
class TrackedObject:
    track_id: int
    label: str
    box: tuple[float, float, float, float]
    range_m: float | None
    bearing_deg: float
    frame_t_ns: int
    zone: str | None


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass
class _Track:
    track_id: int
    label: str
    box: tuple
    range_m: float | None
    last_ns: int


class Tracker:
    def __init__(self):
        self._tracks: list[_Track] = []
        self._next_id = 1

    def update(self, dets: list[Detection], depth: DepthResult | None, rp: RectifiedPair, fresh: bool) -> list[TrackedObject]:
        now = rp.t_ns
        self._tracks = [t for t in self._tracks if now - t.last_ns <= MAX_AGE_NS]
        trusted = fresh and depth is not None
        free = set(range(len(self._tracks)))
        out = []
        for d in sorted(dets, key=lambda d: -d.score):
            best, best_iou = None, IOU_MATCH
            for i in free:
                t = self._tracks[i]
                if t.label == d.label and (v := iou(t.box, d.box)) >= best_iou:
                    best, best_iou = i, v
            measured = object_range(d, depth) if trusted else None
            if best is None:
                t = _Track(self._next_id, d.label, d.box, measured, now)
                self._next_id += 1
                self._tracks.append(t)
            else:
                free.discard(best)
                t = self._tracks[best]
                t.box, t.last_ns = d.box, now
                if measured is None:
                    t.range_m = None
                elif t.range_m is None:
                    t.range_m = measured
                else:
                    t.range_m = EMA_ALPHA * measured + (1 - EMA_ALPHA) * t.range_m
            if not trusted:
                t.range_m = None
            u = (d.box[0] + d.box[2]) / 2
            bearing = bearing_deg(u, t.range_m or NOMINAL_Z, rp.fx, rp.cx, rp.baseline_m)
            out.append(TrackedObject(t.track_id, t.label, t.box, t.range_m, bearing, now, zone_of(t.range_m)))
        return out
