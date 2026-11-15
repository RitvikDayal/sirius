from pathlib import Path

import cv2
import numpy as np
import pytest

from sirius.detect import ANNOUNCED_CLASSES, Detection, filter_detections

CLIP = Path(__file__).resolve().parents[1] / "data/clips/smoke"


def test_filters_classes():
    dets = [Detection((0, 0, 10, 10), "person", 0.9), Detection((0, 0, 5, 5), "toothbrush", 0.95),
            Detection((1, 1, 4, 4), "chair", 0.3)]
    kept = filter_detections(dets, threshold=0.5)
    assert [d.label for d in kept] == ["person"]
    assert "bottle" in ANNOUNCED_CLASSES and "toothbrush" not in ANNOUNCED_CLASSES


@pytest.mark.gpu
@pytest.mark.skipif(not (CLIP / "left/000010.png").exists(), reason=f"no recorded clip at {CLIP}")
def test_real_frame_finds_person():
    from sirius.detect import DFineDetector

    img = cv2.resize(cv2.imread(str(CLIP / "left/000010.png")), (640, 360), interpolation=cv2.INTER_AREA)
    dets = DFineDetector().detect(img)
    people = [d for d in dets if d.label == "person"]
    assert people and max(d.score for d in people) >= 0.5
    x0, y0, x1, y1 = people[0].box
    assert 0 <= x0 < x1 <= 640 and 0 <= y0 < y1 <= 360
