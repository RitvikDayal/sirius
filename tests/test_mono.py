from pathlib import Path

import cv2
import numpy as np
import pytest

from sirius.calib.rectify import RectifiedPair

CLIP = Path(__file__).resolve().parents[1] / "data/clips/smoke"

pytestmark = [
    pytest.mark.gpu,
    pytest.mark.skipif(not (CLIP / "left/000010.png").exists(), reason=f"no recorded clip at {CLIP} (sirius record)"),
]


def test_mono_shapes_and_units():
    from sirius.depth.mono import MonoEstimator

    left = cv2.resize(cv2.imread(str(CLIP / "left/000010.png")), (640, 360), interpolation=cv2.INTER_AREA)
    rp = RectifiedPair(left, left, 0, 457.0, 457.0, 320.0, 180.0, 0.117)
    res = MonoEstimator().estimate(rp)
    assert res.range_m.shape == (360, 640)
    assert np.isfinite(res.range_m).mean() > 0.95
    assert 0.3 < float(np.nanmedian(res.range_m)) < 20.0
    assert res.method.startswith("mono")
