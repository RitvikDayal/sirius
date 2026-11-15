import numpy as np

from sirius.depth.base import DepthResult
from sirius.detect import Detection
from sirius.fusion import object_range, zone_of


def depth(arr):
    return DepthResult(np.asarray(arr, np.float32), 1.0, "test")


def test_range_median_ignores_edges():
    r = np.full((100, 100), 4.0, np.float32)
    r[30:70, 30:70] = 1.0  # object fills the box centre; box edges hit the 4 m background
    assert object_range(Detection((20, 20, 80, 80), "chair", 0.9), depth(r)) == 1.0


def test_insufficient_valid_is_none():
    r = np.full((100, 100), 2.0, np.float32)
    r[35:65, 35:65][:, :18] = np.nan  # 60% of the central region invalid
    assert object_range(Detection((20, 20, 80, 80), "chair", 0.9), depth(r)) is None


def test_zones():
    assert zone_of(0.8) == "urgent"
    assert zone_of(1.0) == "near"
    assert zone_of(2.6) == "aware"
    assert zone_of(5.1) is None
    assert zone_of(None) is None
