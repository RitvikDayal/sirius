import numpy as np
import pytest

from sirius.depth.geometry import bearing_deg, depth_from_disparity, range_from_z


def test_depth_from_disparity():
    z = depth_from_disparity(np.array([[40.0, 0.0, -1.0]]), fx=457.0, baseline_m=0.117)
    assert z[0, 0] == pytest.approx(457 * 0.117 / 40)
    assert np.isnan(z[0, 1]) and np.isnan(z[0, 2])


def test_range_on_axis():
    z = np.full((3, 3), 2.0)
    r = range_from_z(z, fx=457.0, fy=457.0, cx=1.0, cy=1.0, baseline_m=0.12)
    assert r[1, 1] == pytest.approx(np.hypot(0.06, 2.0))


def test_bearing_signs():
    cx, fx, b = 320.0, 457.0, 0.12
    centre_u = cx + fx * (b / 2) / 2.0  # straight ahead of the rig midpoint at 2 m
    assert bearing_deg(centre_u, 2.0, fx, cx, b) == pytest.approx(0.0, abs=1e-9)
    assert bearing_deg(600.0, 2.0, fx, cx, b) > 0
    assert bearing_deg(40.0, 2.0, fx, cx, b) < 0
