from pathlib import Path

import numpy as np
import pytest

from test_sgbm import B, FX, H, W, centre, plane_pair

ONNX = Path(__file__).resolve().parents[1] / "data/models/ffs/onnx/c_fast_foundationstereo_bp2_dynbatch_dynhw.onnx"

pytestmark = [
    pytest.mark.gpu,
    pytest.mark.skipif(not ONNX.exists(), reason=f"model missing: run `uv run python scripts/fetch_models.py` ({ONNX})"),
]


@pytest.fixture(scope="module")
def est():
    from sirius.depth.ffs import FfsEstimator

    e = FfsEstimator(ONNX)
    assert e.provider == "CUDAExecutionProvider", f"running on {e.provider}"
    return e


def test_ffs_plane(est):
    res = est.estimate(plane_pair(40))
    c = centre(res.range_m)
    expected = FX * B / 40
    assert res.range_m.shape == (H, W)
    assert np.isfinite(c).mean() > 0.9
    assert abs(np.nanmedian(c) - expected) / expected < 0.05
