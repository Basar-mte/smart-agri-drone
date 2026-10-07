"""YOLOv8 mango-leaf disease detector."""

from __future__ import annotations

from .config import ModelConfig
from .decision import Detection


class LeafDiseaseDetector:
    def __init__(self, cfg: ModelConfig) -> None:
        from ultralytics import YOLO

        self.cfg = cfg
        # Accepts a .pt file or an exported NCNN/ONNX model (NCNN is fastest on a Pi 5).
        self.model = YOLO(cfg.weights, task="detect")
        self.names: dict[int, str] = self.model.names

    def detect(self, frame) -> tuple[list[Detection], object]:
        """Return detections and the raw Ultralytics result (for drawing)."""
        result = self.model.predict(
            frame,
            imgsz=self.cfg.imgsz,
            conf=self.cfg.confidence,
            iou=self.cfg.iou,
            device=self.cfg.device,
            verbose=False,
        )[0]
        boxes = result.boxes
        dets = [
            Detection(
                cls=self.names[int(c)],
                confidence=float(p),
                xyxy=tuple(float(v) for v in box),
            )
            for box, p, c in zip(boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist(), strict=True)
        ]
        return dets, result
