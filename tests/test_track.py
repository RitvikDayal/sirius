import numpy as np

from sirius.calib.rectify import RectifiedPair
from sirius.depth.base import DepthResult
from sirius.detect import Detection
from sirius.track import Tracker

H, W = 360, 640
IMG = np.zeros((H, W, 3), np.uint8)


def rp(t_ns=0):
    return RectifiedPair(IMG, IMG, t_ns, 457.0, 457.0, W / 2, H / 2, 0.117)


def flat(r):
    return DepthResult(np.full((H, W), r, np.float32), 1.0, "test")


def test_not_fresh_suppresses_ranges():
    det = [Detection((200, 100, 300, 300), "person", 0.9)]
    t = Tracker()
    objs = t.update(det, flat(1.5), rp(), fresh=False)
    assert objs and all(o.range_m is None and o.zone is None for o in objs)
    objs = t.update(det, None, rp(1), fresh=True)
    assert all(o.range_m is None for o in objs)


def test_track_ids_stable_and_range_smoothed():
    t = Tracker()
    ids, ranges = set(), []
    for i in range(10):
        x = 200 + 5 * i
        objs = t.update([Detection((x, 100, x + 100, 300), "person", 0.9)], flat(2.0 if i < 9 else 1.0), rp(i), fresh=True)
        assert len(objs) == 1
        ids.add(objs[0].track_id)
        ranges.append(objs[0].range_m)
    assert len(ids) == 1
    assert abs(ranges[8] - 2.0) < 1e-6
    assert 1.0 < ranges[9] < 2.0  # EMA, not a jump


def test_bearing_sign():
    t = Tracker()
    right = t.update([Detection((520, 100, 600, 300), "chair", 0.9)], flat(2.0), rp(), fresh=True)[0]
    assert right.bearing_deg > 15
