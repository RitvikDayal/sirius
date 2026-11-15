"""What to say, and when: one short alert at a time, most urgent first."""

from dataclasses import dataclass

from sirius.track import TrackedObject

REPEAT_NS = 5_000_000_000
MAX_AGE_NS = 1_000_000_000
AHEAD_DEG = 15.0
ZONE_RANK = {"urgent": 0, "near": 1, "aware": 2}
SPOKEN_LABEL = {"dining table": "table", "tv": "TV", "potted plant": "plant"}


@dataclass(frozen=True)
class Alert:
    text: str
    urgent: bool
    track_id: int
    zone: str | None
    frame_t_ns: int


def distance_words(r: float) -> str:
    if r < 0.75:
        return "half a metre"
    for limit, words in ((1.5, "one metre"), (2.5, "two metres"), (3.5, "three metres"), (4.5, "four metres")):
        if r < limit:
            return words
    return "five metres"


def direction(bearing: float) -> str:
    if bearing < -AHEAD_DEG:
        return "left"
    return "right" if bearing > AHEAD_DEG else "ahead"


def phrase(o: TrackedObject, approx: bool = False) -> str:
    """`approx`: the distance is a single-camera estimate, said with "about"."""
    label = SPOKEN_LABEL.get(o.label, o.label)
    if o.range_m is None:
        return f"{label}, {direction(o.bearing_deg)}"
    return f"{label}, {'about ' if approx else ''}{distance_words(o.range_m)}, {direction(o.bearing_deg)}"


def _priority(o: TrackedObject):
    rank = ZONE_RANK.get(o.zone, 3)
    return (rank, o.range_m if o.range_m is not None else float("inf"), abs(o.bearing_deg))


class AlertPolicy:
    def __init__(self, repeat_ns: int = REPEAT_NS, approx: bool = False):
        self.repeat_ns = repeat_ns
        self.approx = approx
        self._said: dict[int, tuple[str | None, int]] = {}  # track -> (zone, when)
        self._texts: dict[str, int] = {}  # sentence -> when; a flickering detection makes new tracks

    def _eligible(self, o: TrackedObject, now_ns: int) -> bool:
        if o.range_m is not None and o.zone is None:
            return False  # measured, but beyond 5 m
        prev = self._said.get(o.track_id)
        if prev is None:
            return True
        if o.range_m is None:
            return False  # direction-only alerts are said once per track
        zone, when = prev
        return zone != o.zone or now_ns - when >= self.repeat_ns

    def update(self, objs: list[TrackedObject], now_ns: int) -> Alert | None:
        candidates = sorted(
            (o for o in objs if self._eligible(o, now_ns) and now_ns - self._texts.get(phrase(o, self.approx), -self.repeat_ns) >= self.repeat_ns),
            key=_priority,
        )
        if not candidates:
            return None
        o = candidates[0]
        text = phrase(o, self.approx)
        self._said[o.track_id] = (o.zone, now_ns)
        self._texts[text] = now_ns
        return Alert(text, o.zone == "urgent", o.track_id, o.zone, o.frame_t_ns)


def is_stale(alert: Alert, objs_now: list[TrackedObject], now_ns: int) -> bool:
    if now_ns - alert.frame_t_ns > MAX_AGE_NS:
        return True
    current = next((o for o in objs_now if o.track_id == alert.track_id), None)
    return current is None or current.zone != alert.zone
