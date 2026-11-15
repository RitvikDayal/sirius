import numpy as np

from sirius.health import SourceHealth, image_stats, ir_mismatch, is_fresh


def h(age_l=30.0, age_r=30.0, luma_l=120.0, luma_r=110.0, sat_l=8.0, sat_r=7.5):
    return SourceHealth(30.0, 30.0, age_l, age_r, luma_l, luma_r, sat_l, sat_r)


def test_freshness():
    assert is_fresh(h())
    assert not is_fresh(h(age_r=250.0))
    assert not is_fresh(h(luma_l=5.0))


def test_ir_mismatch():
    assert ir_mismatch(h(sat_l=8.0, sat_r=1.5))
    assert not ir_mismatch(h(sat_l=8.0, sat_r=7.5))


def test_image_stats_black_and_grey():
    luma, sat = image_stats(np.zeros((10, 10, 3), np.uint8))
    assert luma < 1 and sat < 1
    grey = np.full((10, 10, 3), 128, np.uint8)
    red = grey.copy()
    red[..., 2] = 255
    assert image_stats(red)[1] > image_stats(grey)[1] + 20
