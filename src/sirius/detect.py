"""Object detection with D-FINE (Apache-2.0), limited to the classes SIRIUS announces."""

import time
from dataclasses import dataclass
from typing import Protocol

import numpy as np

MODEL_ID = "ustc-community/dfine-small-coco"
ANNOUNCED_CLASSES = frozenset({
    "person", "chair", "couch", "bed", "dining table", "bench", "bicycle", "car", "motorcycle",
    "dog", "potted plant", "tv", "laptop", "backpack", "suitcase", "bottle", "cup",
})


@dataclass(frozen=True)
class Detection:
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in the rectified left image
    label: str
    score: float


class Detector(Protocol):
    def detect(self, image_bgr: np.ndarray) -> list[Detection]: ...


def filter_detections(dets: list[Detection], threshold: float, classes=ANNOUNCED_CLASSES) -> list[Detection]:
    return [d for d in dets if d.score >= threshold and d.label in classes]


class DFineDetector:
    def __init__(self, model_id: str = MODEL_ID, threshold: float = 0.5, device: str = "cuda"):
        import torch
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self.torch = torch
        self.threshold = threshold
        self.device = device
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModelForObjectDetection.from_pretrained(model_id, torch_dtype=torch.float16).to(device).eval()
        self.id2label = self.model.config.id2label
        self.last_ms = 0.0

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        torch = self.torch
        t0 = time.perf_counter()
        h, w = image_bgr.shape[:2]
        inputs = self.processor(images=image_bgr[:, :, ::-1].copy(), return_tensors="pt")
        inputs = {k: v.to(self.device, torch.float16 if v.is_floating_point() else v.dtype) for k, v in inputs.items()}
        with torch.inference_mode():
            out = self.model(**inputs)
        res = self.processor.post_process_object_detection(out, target_sizes=[(h, w)], threshold=self.threshold)[0]
        dets = [
            Detection(tuple(float(v) for v in box), self.id2label[int(label)], float(score))
            for box, label, score in zip(res["boxes"].float().cpu(), res["labels"].cpu(), res["scores"].float().cpu())
        ]
        dets = [Detection((max(0.0, b[0]), max(0.0, b[1]), min(float(w), b[2]), min(float(h), b[3])), lab, s)
                for (b, lab, s) in ((d.box, d.label, d.score) for d in dets)]
        self.last_ms = (time.perf_counter() - t0) * 1000
        return filter_detections(dets, self.threshold)
