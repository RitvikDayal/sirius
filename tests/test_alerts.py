from sirius.alerts import Alert, AlertPolicy, is_stale, phrase
from sirius.fusion import zone_of
from sirius.track import TrackedObject

S = 1_000_000_000


def obj(tid, label, r, bearing=0.0, t=0):
    return TrackedObject(tid, label, (0, 0, 1, 1), r, bearing, t, zone_of(r))


def test_phrase():
    assert phrase(obj(1, "person", 0.9)) == "person, one metre, ahead"
    assert phrase(obj(2, "chair", 2.2, -30)) == "chair, two metres, left"
    assert phrase(obj(3, "bottle", None, 20)) == "bottle, right"
    assert phrase(obj(4, "dining table", 0.6, 0)) == "table, half a metre, ahead"
    assert phrase(obj(5, "tv", 4.6, 0)) == "TV, five metres, ahead"


def test_phrase_approximate():
    assert phrase(obj(1, "person", 0.9), approx=True) == "person, about one metre, ahead"
    assert phrase(obj(3, "bottle", None, 20), approx=True) == "bottle, right"


def test_one_alert_most_urgent():
    objs = [obj(1, "chair", 3.0), obj(2, "person", 0.8, 10), obj(3, "cup", 2.0), obj(4, "dog", 4.0), obj(5, "bench", 1.8)]
    a = AlertPolicy().update(objs, now_ns=0)
    assert a.track_id == 2 and a.urgent and a.text == "person, one metre, ahead"


def test_ties_prefer_closer_then_ahead():
    p = AlertPolicy()
    a = p.update([obj(1, "chair", 2.0, 40), obj(2, "bench", 1.5, 40), obj(3, "cup", 1.5, 0)], now_ns=0)
    assert a.track_id == 3


def test_no_repeat_within_5s():
    p = AlertPolicy()
    assert p.update([obj(1, "chair", 2.0)], 0) is not None
    assert p.update([obj(1, "chair", 2.0)], 4 * S) is None


def test_repeat_after_5s():
    p = AlertPolicy()
    p.update([obj(1, "chair", 2.0)], 0)
    assert p.update([obj(1, "chair", 2.0)], 5 * S) is not None


def test_repeat_on_zone_change():
    p = AlertPolicy()
    p.update([obj(1, "chair", 2.0)], 0)
    a = p.update([obj(1, "chair", 0.9)], 1 * S)
    assert a is not None and a.urgent


def test_beyond_5m_silent():
    assert AlertPolicy().update([obj(1, "car", 6.0)], 0) is None


def test_no_range_announced_once_per_track():
    p = AlertPolicy()
    assert p.update([obj(1, "bottle", None, 20)], 0).text == "bottle, right"
    assert p.update([obj(1, "bottle", None, 20)], 10 * S) is None


def test_same_sentence_not_repeated_when_track_flickers():
    # The detector loses the bed for a moment; it comes back as a new track with the same description.
    p = AlertPolicy()
    assert p.update([obj(1, "bed", None, 30)], 0).text == "bed, right"
    assert p.update([obj(2, "bed", None, 30)], 2 * S) is None
    assert p.update([obj(3, "bed", None, 30)], 6 * S) is not None  # after 5 s it may be said again


def test_stale_dropped():
    a = Alert("chair, two metres, ahead", False, 1, "near", frame_t_ns=0)
    now = [obj(1, "chair", 2.0)]
    assert not is_stale(a, now, 500_000_000)
    assert is_stale(a, now, 1_200_000_000)  # older than 1 s
    assert is_stale(a, [], 100)  # track gone
    assert is_stale(a, [obj(1, "chair", 0.8)], 100)  # different zone now
