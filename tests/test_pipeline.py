import re

import numpy as np

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.detect import Detection
from sirius.pairing import Frame, StereoPair
from sirius.pipeline import Pipeline
from sirius.source import health_of
from sirius.voice import RecordingVoice

H, W = 360, 640
MS = 1_000_000
DISTANCE_WORDS = re.compile(r"metre")


class FakeSource:
    def __init__(self, n, right_black=False, step_ms=40):
        rng = np.random.default_rng(0)
        self.img = rng.integers(60, 200, (H, W, 3), dtype=np.uint8)
        self.right = np.zeros_like(self.img) if right_black else self.img
        self.n, self.i, self.step = n, 0, step_ms
        self._last = None

    def start(self):
        pass

    def stop(self):
        pass

    def read(self, timeout_s):
        if self.i >= self.n:
            return None
        t = 1_000 * MS + self.i * self.step * MS
        self.i += 1
        self._last = StereoPair(Frame(self.img, t, self.i), Frame(self.right, t, self.i))
        return self._last

    def health(self):
        return health_of(self._last, 25.0, 25.0, 10.0, 10.0)


class IdentityRect:
    def rectify(self, pair):
        return RectifiedPair(pair.left.image, pair.right.image, pair.t_ns, 457.0, 457.0, W / 2, H / 2, 0.117)


class FlatDepth:
    name, kind = "flat", "stereo"

    def __init__(self, ranges):
        self.ranges = list(ranges)

    def estimate(self, rp):
        r = self.ranges.pop(0) if len(self.ranges) > 1 else self.ranges[0]
        return DepthResult(np.full((H, W), r, np.float32), 1.0, self.name, np.full((H, W), r, np.float32))


class MonoDepth(FlatDepth):
    name, kind = "mono", "mono"


class FakeDetector:
    def __init__(self, dets):
        self.dets = dets
        self.last_ms = 1.0

    def detect(self, img):
        return list(self.dets)


PERSON = Detection((280, 100, 360, 300), "person", 0.9)
CHAIR = Detection((40, 150, 140, 300), "chair", 0.9)


def pipe_with(src, *args, **kw):
    """A pipeline whose wall clock is the source's frame clock (no processing delay)."""
    return Pipeline(src, *args, clock=lambda: src._last.left.t_ns, **kw)


def run(pipe, n):
    out = []
    for _ in range(n):
        r = pipe.step()
        if r is not None:
            out.append(r)
    return out


def test_speaks_stereo_distance():
    voice = RecordingVoice()
    pipe = pipe_with(FakeSource(3), IdentityRect(), FlatDepth([0.8]), FakeDetector([PERSON]), voice)
    run(pipe, 3)
    assert voice.said[0][0] == "person, one metre, ahead" and voice.said[0][1] is True


def test_urgent_interrupts():
    voice = RecordingVoice(busy=True)
    pipe = pipe_with(FakeSource(3), IdentityRect(), FlatDepth([0.8]), FakeDetector([PERSON]), voice)
    run(pipe, 1)
    assert voice.said == [("person, one metre, ahead", True)]


def test_pending_replaced_and_stale_dropped():
    voice = RecordingVoice(busy=True)
    # chair (near) is announced while the voice is busy -> pending; then the person appears (near, closer).
    pipe = pipe_with(FakeSource(40), IdentityRect(), FlatDepth([2.0]), FakeDetector([CHAIR]), voice)
    run(pipe, 1)
    assert voice.said == [] and pipe.pending is not None and pipe.pending.text.startswith("chair")
    pipe.detector.dets = [PERSON]  # chair leaves view: its pending alert is now stale
    run(pipe, 1)
    assert pipe.pending is not None and pipe.pending.text.startswith("person")
    voice.is_busy = False
    run(pipe, 1)
    assert [t for t, _ in voice.said] == ["person, two metres, ahead"]


def test_old_pending_never_spoken():
    voice = RecordingVoice(busy=True)
    pipe = pipe_with(FakeSource(40, step_ms=400), IdentityRect(), FlatDepth([2.0]), FakeDetector([CHAIR]), voice)
    run(pipe, 1)  # chair alert held as pending while the voice is busy
    assert pipe.pending is not None
    run(pipe, 3)  # 1.2 s later and still busy: the pending alert has gone stale
    assert pipe.pending is None
    voice.is_busy = False
    run(pipe, 1)  # idle again, but the 5 s repeat window has not passed
    assert voice.said == []


def test_black_frame_no_numbers():
    voice = RecordingVoice()
    pipe = pipe_with(FakeSource(5, right_black=True), IdentityRect(), FlatDepth([0.8]), FakeDetector([PERSON]), voice)
    run(pipe, 5)
    assert voice.said, "should still announce the object"
    assert not any(DISTANCE_WORDS.search(t) for t, _ in voice.said)


def test_mono_depth_never_spoken():
    voice = RecordingVoice()
    pipe = pipe_with(FakeSource(3), IdentityRect(), MonoDepth([0.8]), FakeDetector([PERSON]), voice)
    results = run(pipe, 3)
    assert not any(DISTANCE_WORDS.search(t) for t, _ in voice.said)
    assert results[-1].objects[0].range_m is not None  # still shown in the dashboard


def test_alert_from_slow_frame_not_spoken():
    # Processing (e.g. model warm-up) took 1.5 s: by the time the alert is ready its frame is too old.
    voice = RecordingVoice()
    src = FakeSource(3)
    clock = {"lag": 1_500 * MS}
    pipe = Pipeline(src, IdentityRect(), FlatDepth([2.0]), FakeDetector([PERSON]), voice,
                    clock=lambda: src._last.left.t_ns + clock["lag"])
    run(pipe, 1)
    assert voice.said == []
    clock["lag"] = 50 * MS
    run(pipe, 1)  # the same track is not re-announced for 5 s, so nothing late leaks out
    assert voice.said == []


def test_mono_distance_spoken_as_approximate_when_enabled():
    voice = RecordingVoice()
    pipe = pipe_with(FakeSource(3), IdentityRect(), MonoDepth([1.8]), FakeDetector([PERSON]), voice,
                     speak_approx_distances=True)
    run(pipe, 3)
    assert voice.said[0][0] == "person, about two metres, ahead"


def test_approximate_distance_still_needs_fresh_cameras():
    voice = RecordingVoice()
    pipe = pipe_with(FakeSource(3, right_black=True), IdentityRect(), MonoDepth([1.8]), FakeDetector([PERSON]), voice,
                     speak_approx_distances=True)
    run(pipe, 3)
    assert voice.said and not any(DISTANCE_WORDS.search(t) for t, _ in voice.said)


def test_muted_alerts_logged_as_muted_not_spoken():
    from sirius.voice import MutableVoice

    inner = RecordingVoice()
    voice = MutableVoice(inner)
    voice.muted = True
    pipe = pipe_with(FakeSource(2), IdentityRect(), FlatDepth([0.8]), FakeDetector([PERSON]), voice)
    r = run(pipe, 1)[0]
    assert r.spoken is None and r.log["spoken"] is None
    assert r.log["muted"] == "person, one metre, ahead"


def test_step_log_has_timings():
    pipe = pipe_with(FakeSource(2), IdentityRect(), FlatDepth([2.0]), FakeDetector([PERSON]), RecordingVoice())
    r = run(pipe, 1)[0]
    assert r.log["total_ms"] >= 0 and "depth_ms" in r.log and "detect_ms" in r.log and r.log["fresh"] is True
