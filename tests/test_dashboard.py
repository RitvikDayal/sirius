import json
import struct
import urllib.error
import urllib.request

import numpy as np
import pytest

from sirius.viewer.dashboard import Dashboard
from sirius.viewer.points import depth_to_points


@pytest.fixture
def dash():
    d = Dashboard(port=0)  # any free port
    d.start()
    yield d
    d.stop()


def get(dash, path, n=None):
    with urllib.request.urlopen(f"http://127.0.0.1:{dash.port}{path}", timeout=5) as r:
        return r.headers, (r.read(n) if n else r.read())


def test_index_page_served(dash):
    headers, body = get(dash, "/")
    assert headers["Content-Type"].startswith("text/html")
    assert b"three" in body and b"/stream/left" in body


def test_three_js_served_locally(dash):
    headers, body = get(dash, "/static/three.module.js")
    assert headers["Content-Type"].startswith("text/javascript")
    assert len(body) > 500_000
    with pytest.raises(urllib.error.HTTPError):
        get(dash, "/static/../dashboard.py")


def test_mute_toggle(dash):
    assert dash.controls["mute"] is False
    req = urllib.request.Request(f"http://127.0.0.1:{dash.port}/control", data=json.dumps({"mute": True}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        assert json.loads(r.read()) == {"mute": True}
    assert dash.controls["mute"] is True
    _, body = get(dash, "/")
    assert b'id="mute"' in body


def test_muted_voice_says_nothing_and_unmutes():
    from sirius.voice import MutableVoice, RecordingVoice

    inner = RecordingVoice()
    v = MutableVoice(inner)
    v.muted = True
    v.say("person, ahead", interrupt=True)
    assert inner.said == [("", True)]  # muting also cuts off speech in progress
    v.muted = False
    v.say("chair, left", interrupt=False)
    assert inner.said[-1] == ("chair, left", False)


def test_stats_json(dash):
    dash.publish_stats({"fps_left": 25.0, "note": "hi"})
    _, body = get(dash, "/stats")
    assert json.loads(body) == {"fps_left": 25.0, "note": "hi"}


def test_stream_sends_jpeg_parts(dash):
    dash.publish_image("left", np.full((40, 60, 3), 200, np.uint8))
    headers, chunk = get(dash, "/stream/left", n=600)
    assert "multipart/x-mixed-replace" in headers["Content-Type"]
    assert b"Content-Type: image/jpeg" in chunk and b"\xff\xd8" in chunk


def test_points_binary_layout(dash):
    xyz = np.array([[0, 0, 1], [1, 2, 3]], np.float32)
    rgb = np.array([[255, 0, 0], [0, 255, 0]], np.uint8)
    dash.publish_points(xyz, rgb)
    _, body = get(dash, "/points")
    (n,) = struct.unpack("<I", body[:4])
    assert n == 2 and len(body) == 4 + n * 12 + n * 3
    assert np.allclose(np.frombuffer(body[4:4 + 24], np.float32).reshape(2, 3), xyz)
    assert np.array_equal(np.frombuffer(body[28:], np.uint8).reshape(2, 3), rgb)


def test_colorize_range_near_warm_far_cool_invalid_black():
    from sirius.viewer.live import colorize_range

    r = np.array([[0.4, 5.5, np.nan]], np.float32)
    img = colorize_range(r, near=0.3, far=6.0)
    near_bgr, far_bgr, bad = img[0, 0].astype(int), img[0, 1].astype(int), img[0, 2]
    assert near_bgr[2] > near_bgr[0]  # near: more red than blue
    assert far_bgr[0] > far_bgr[2]  # far: more blue than red
    assert not bad.any()


def test_depth_to_points_backprojects_and_skips_nan():
    z = np.full((4, 4), np.nan, np.float32)
    z[2, 2] = 2.0  # principal point
    img = np.zeros((4, 4, 3), np.uint8)
    img[2, 2] = (10, 20, 30)  # BGR
    xyz, rgb = depth_to_points(z, img, fx=100.0, fy=100.0, cx=2.0, cy=2.0, baseline_m=0.12, step=1)
    assert xyz.shape == (1, 3)
    assert np.allclose(xyz[0], [-0.06, 0.0, 2.0])  # origin at the lens midpoint
    assert tuple(rgb[0]) == (30, 20, 10)  # RGB
