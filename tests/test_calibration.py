import cv2
import numpy as np
import pytest

from sirius.calib.board import detect, make_board
from sirius.calib.rectify import Rectifier
from sirius.calib.stereo import Calibration, calibrate
from sirius.config import CharucoSpec
from sirius.pairing import Frame, StereoPair

from synth import BASELINE, H, K, W, board_poses, render, to_right

SPEC = CharucoSpec(square_mm=35.0, marker_mm=26.0)
PX_PER_M = 4000.0


@pytest.fixture(scope="module")
def calib() -> Calibration:
    board = make_board(SPEC)
    bw, bh = SPEC.cols * SPEC.square_mm / 1000, SPEC.rows * SPEC.square_mm / 1000
    tex = board.generateImage((int(bw * PX_PER_M), int(bh * PX_PER_M)), marginSize=0)
    pairs = []
    for R_b, t_b in board_poses(25, bw, bh):
        left = render(tex, PX_PER_M, R_b, t_b)
        right = render(tex, PX_PER_M, *to_right(R_b, t_b))
        pairs.append((left, right))
    return calibrate(pairs, board, (W, H))


def test_detect_finds_corners_on_rendered_board():
    board = make_board(SPEC)
    tex = board.generateImage((1200, 860), marginSize=40)
    det = detect(board, tex)
    assert len(det.ids) == (SPEC.cols - 1) * (SPEC.rows - 1)


def test_synthetic_stereo_calibration(calib):
    assert abs(calib.baseline_m - BASELINE) / BASELINE < 0.01
    assert calib.rms_stereo < 0.5


def test_rectified_rows_align(calib):
    rng = np.random.default_rng(3)
    pts = np.column_stack([rng.uniform(-0.5, 0.6, 50), rng.uniform(-0.3, 0.3, 50), rng.uniform(1, 4, 50)])
    from synth import C_RIGHT, R_REL

    pl = cv2.projectPoints(pts, np.zeros(3), np.zeros(3), K, None)[0]
    pr = cv2.projectPoints((R_REL @ (pts - C_RIGHT).T).T, np.zeros(3), np.zeros(3), K, None)[0]
    rl = cv2.undistortPoints(pl, calib.K1, calib.D1, R=calib.R1, P=calib.P1).reshape(-1, 2)
    rr = cv2.undistortPoints(pr, calib.K2, calib.D2, R=calib.R2, P=calib.P2).reshape(-1, 2)
    assert np.median(np.abs(rl[:, 1] - rr[:, 1])) < 0.5


def test_rectifier_scales_intrinsics(calib):
    img = np.zeros((H, W, 3), np.uint8)
    rp = Rectifier(calib, 0.5).rectify(StereoPair(Frame(img, 1, 1), Frame(img, 2, 1)))
    assert rp.left.shape == (H // 2, W // 2, 3) and rp.right.shape == rp.left.shape
    assert rp.fx == pytest.approx(calib.P1[0, 0] * 0.5)
    assert rp.baseline_m == pytest.approx(calib.baseline_m, rel=1e-3)
    assert rp.t_ns == 2


def test_save_load_roundtrip(calib, tmp_path):
    p = tmp_path / "calib.npz"
    calib.save(p)
    back = Calibration.load(p)
    assert np.allclose(back.P2, calib.P2) and back.size == calib.size
