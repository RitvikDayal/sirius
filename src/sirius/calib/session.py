"""Interactive calibration capture: saves a pair whenever the board is in a new pose."""

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from sirius.calib.board import detect

MIN_COMMON = 20
MOVE_PX = 80.0
AREA_CHANGE = 0.20


@dataclass(frozen=True)
class View:
    centroid: tuple[float, float]
    area: float


def is_novel(v: View, saved: list[View]) -> bool:
    for s in saved:
        moved = np.hypot(v.centroid[0] - s.centroid[0], v.centroid[1] - s.centroid[1])
        resized = abs(v.area - s.area) / s.area
        if moved <= MOVE_PX and resized <= AREA_CHANGE:
            return False
    return True


def _view(corners: np.ndarray) -> View:
    pts = corners.reshape(-1, 2)
    hull = cv2.convexHull(pts.astype(np.float32))
    return View(tuple(pts.mean(axis=0)), float(cv2.contourArea(hull)))


def capture(source, board, out_dir: Path, target: int = 30) -> int:
    out_dir = Path(out_dir)
    (out_dir / "left").mkdir(parents=True, exist_ok=True)
    (out_dir / "right").mkdir(parents=True, exist_ok=True)
    saved: list[View] = []
    last_check = 0.0
    while len(saved) < target:
        pair = source.read(timeout_s=1.0)
        if pair is None:
            continue
        status = f"saved {len(saved)}/{target}  - move the board: near/far, left/right, tilted"
        if time.perf_counter() - last_check > 0.3:
            last_check = time.perf_counter()
            dl, dr = detect(board, pair.left.image), detect(board, pair.right.image)
            common = np.intersect1d(dl.ids.ravel(), dr.ids.ravel()) if len(dl.ids) and len(dr.ids) else []
            if len(common) >= MIN_COMMON:
                v = _view(dl.corners)
                if is_novel(v, saved):
                    name = f"{len(saved):06d}.png"
                    cv2.imwrite(str(out_dir / "left" / name), pair.left.image)
                    cv2.imwrite(str(out_dir / "right" / name), pair.right.image)
                    saved.append(v)
                    print(f"saved pair {len(saved)}/{target} ({len(common)} common corners)")
        preview = np.hstack([pair.left.image, pair.right.image])
        preview = cv2.resize(preview, (preview.shape[1] // 2, preview.shape[0] // 2))
        cv2.putText(preview, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("sirius calib-capture (q to stop)", preview)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()
    return len(saved)


def load_pairs(calib_dir: Path) -> list[tuple[np.ndarray, np.ndarray]]:
    calib_dir = Path(calib_dir)
    names = sorted(p.name for p in (calib_dir / "left").glob("*.png"))
    return [(cv2.imread(str(calib_dir / "left" / n)), cv2.imread(str(calib_dir / "right" / n))) for n in names]
