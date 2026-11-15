from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from sirius.config import CharucoSpec

MM_PER_INCH = 25.4


@dataclass(frozen=True)
class CharucoDetection:
    corners: np.ndarray  # N x 1 x 2
    ids: np.ndarray  # N x 1


def make_board(spec: CharucoSpec) -> cv2.aruco.CharucoBoard:
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, spec.dictionary))
    return cv2.aruco.CharucoBoard((spec.cols, spec.rows), spec.square_mm / 1000, spec.marker_mm / 1000, dictionary)


def render_board_png(spec: CharucoSpec, path: Path, dpi: int = 300) -> None:
    """Board at true size for printing at 100%, with a 10 mm white margin."""
    px_per_mm = dpi / MM_PER_INCH
    margin = int(10 * px_per_mm)
    w = int(spec.cols * spec.square_mm * px_per_mm) + 2 * margin
    h = int(spec.rows * spec.square_mm * px_per_mm) + 2 * margin
    img = make_board(spec).generateImage((w, h), marginSize=margin)
    cv2.imwrite(str(path), img)
    # A PNG carries no physical size; the PDF does, so it prints true-size at 100%.
    from PIL import Image

    Image.fromarray(img).save(Path(path).with_suffix(".pdf"), resolution=dpi)


def detect(board: cv2.aruco.CharucoBoard, image: np.ndarray) -> CharucoDetection:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    corners, ids, _, _ = cv2.aruco.CharucoDetector(board).detectBoard(gray)
    if ids is None:
        return CharucoDetection(np.empty((0, 1, 2), np.float32), np.empty((0, 1), np.int32))
    return CharucoDetection(corners, ids)
