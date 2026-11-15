from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from sirius.calib.board import detect

MIN_CORNERS = 8
CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)


@dataclass
class Calibration:
    K1: np.ndarray
    D1: np.ndarray
    K2: np.ndarray
    D2: np.ndarray
    R: np.ndarray
    T: np.ndarray
    R1: np.ndarray
    R2: np.ndarray
    P1: np.ndarray
    P2: np.ndarray
    Q: np.ndarray
    size: tuple[int, int]
    rms_left: float
    rms_right: float
    rms_stereo: float

    @property
    def baseline_m(self) -> float:
        return float(np.linalg.norm(self.T))

    def save(self, path: Path) -> None:
        np.savez(path, **{k: np.asarray(v) for k, v in asdict(self).items()})

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        z = np.load(path)
        d = {k: z[k] for k in z.files}
        d["size"] = tuple(int(v) for v in d["size"])
        for k in ("rms_left", "rms_right", "rms_stereo"):
            d[k] = float(d[k])
        return cls(**d)


def _points(board, det):
    obj, img = board.matchImagePoints(det.corners, det.ids)
    return obj.astype(np.float32), img.astype(np.float32)


def calibrate(pairs: list[tuple[np.ndarray, np.ndarray]], board, size: tuple[int, int]) -> Calibration:
    dets = [(detect(board, left), detect(board, right)) for left, right in pairs]

    def mono(side: int):
        obj, img = [], []
        for d in (p[side] for p in dets):
            if len(d.ids) >= MIN_CORNERS:
                o, i = _points(board, d)
                obj.append(o)
                img.append(i)
        rms, K, D, _, _ = cv2.calibrateCamera(obj, img, size, None, None)
        return rms, K, D

    rms_l, K1, D1 = mono(0)
    rms_r, K2, D2 = mono(1)

    chess = board.getChessboardCorners().astype(np.float32)
    obj, img_l, img_r = [], [], []
    for dl, dr in dets:
        if len(dl.ids) == 0 or len(dr.ids) == 0:
            continue
        cl = dict(zip(dl.ids.ravel(), dl.corners.reshape(-1, 2)))
        cr = dict(zip(dr.ids.ravel(), dr.corners.reshape(-1, 2)))
        common = sorted(set(cl) & set(cr))
        if len(common) < MIN_CORNERS:
            continue
        obj.append(chess[common].reshape(-1, 1, 3))
        img_l.append(np.float32([cl[i] for i in common]).reshape(-1, 1, 2))
        img_r.append(np.float32([cr[i] for i in common]).reshape(-1, 1, 2))

    rms_s, K1, D1, K2, D2, R, T, _, _ = cv2.stereoCalibrate(
        obj, img_l, img_r, K1, D1, K2, D2, size, criteria=CRITERIA, flags=cv2.CALIB_FIX_INTRINSIC
    )
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K1, D1, K2, D2, size, R, T, alpha=0)
    return Calibration(K1, D1, K2, D2, R, T, R1, R2, P1, P2, Q, tuple(size), rms_l, rms_r, rms_s)
