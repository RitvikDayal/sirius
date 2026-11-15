"""One step = one stereo pair: rectify, depth ∥ detect, track, decide, speak, log."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

from sirius.alerts import Alert, AlertPolicy, is_stale
from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.health import SourceHealth, is_fresh
from sirius.track import Tracker, TrackedObject


@dataclass
class StepResult:
    rp: RectifiedPair
    depth: DepthResult
    objects: list[TrackedObject]  # with display ranges (mono included)
    spoken: str | None
    health: SourceHealth
    log: dict


class Pipeline:
    def __init__(self, source, rectifier, depth, detector, voice, log_path: Path | None = None,
                 clock=time.perf_counter_ns, speak_approx_distances: bool = False):
        # Frame timestamps are perf_counter_ns (live and replay), so `clock` measures how late an alert is.
        self.clock = clock
        self.source, self.rect, self.depth, self.detector, self.voice = source, rectifier, depth, detector, voice
        self.tracker = Tracker()
        # Stereo distances are measured; single-camera ones are estimates and, only if allowed, said with "about".
        self.stereo = getattr(depth, "kind", "") == "stereo"
        self.approx_ok = speak_approx_distances and getattr(depth, "kind", "") == "mono"
        self.policy = AlertPolicy(approx=not self.stereo)
        self.pending: Alert | None = None
        self.last_spoken: str | None = None
        self._pool = ThreadPoolExecutor(max_workers=2)
        self._log = open(log_path, "a", encoding="utf-8") if log_path else None

    def _say(self, alert: Alert, interrupt: bool) -> int:
        t = self.voice.say(alert.text, interrupt)
        self.last_spoken = alert.text
        return t

    def step(self) -> StepResult | None:
        pair = self.source.read(timeout_s=1.0)
        if pair is None:
            return None
        t0 = time.perf_counter()
        rp = self.rect.rectify(pair)
        f_depth = self._pool.submit(self.depth.estimate, rp)
        f_det = self._pool.submit(self.detector.detect, rp.left)
        depth, dets = f_depth.result(), f_det.result()
        health = self.source.health()
        fresh = is_fresh(health)
        objs = self.tracker.update(dets, depth, rp, fresh)

        # Stereo distances are spoken; mono ones only when explicitly allowed, and never with a dark/stale camera.
        speakable = fresh and (self.stereo or self.approx_ok)
        say_objs = objs if speakable else [replace(o, range_m=None, zone=None) for o in objs]
        alert = self.policy.update(say_objs, rp.t_ns)
        now = self.clock()  # staleness is wall-clock age since capture: slow frames never speak late

        if self.pending is not None and is_stale(self.pending, say_objs, now):
            self.pending = None
        spoken, speak_ns = None, None
        if alert is not None and is_stale(alert, say_objs, now):
            alert = None
        if alert is not None:
            if not self.voice.busy() or alert.urgent:
                speak_ns = self._say(alert, interrupt=alert.urgent)
                spoken, self.pending = alert.text, None
            else:
                self.pending = alert
        elif self.pending is not None and not self.voice.busy():
            speak_ns = self._say(self.pending, interrupt=False)
            spoken, self.pending = self.pending.text, None

        muted = None
        if spoken is not None and getattr(self.voice, "muted", False):
            muted, spoken, speak_ns = spoken, None, None
        log = {
            "frame_t_ns": rp.t_ns,
            "depth_ms": round(depth.latency_ms, 2),
            "detect_ms": round(getattr(self.detector, "last_ms", 0.0), 2),
            "total_ms": round((time.perf_counter() - t0) * 1000, 2),
            "fresh": fresh,
            "objects": [[o.label, None if o.range_m is None else round(o.range_m, 3), round(o.bearing_deg, 1)] for o in objs],
            "spoken": spoken,
            "muted": muted,
            "speak_t_ns": speak_ns,
        }
        if self._log:
            self._log.write(json.dumps(log) + "\n")
            self._log.flush()
        return StepResult(rp, depth, objs, spoken, health, log)

    def close(self) -> None:
        self._pool.shutdown(wait=False)
        if self._log:
            self._log.close()
