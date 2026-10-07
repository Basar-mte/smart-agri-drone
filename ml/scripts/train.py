"""Train the YOLOv8 mango-leaf disease detector."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

from common import DEFAULT_DATA, REPO_ROOT, resolve_data_yaml


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", default=str(DEFAULT_DATA))
    p.add_argument("--model", default="yolov8n.pt", help="starting weights (yolov8n/s/m.pt)")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default=None, help="0 for the first GPU, or cpu")
    p.add_argument("--patience", type=int, default=25, help="early-stopping patience (epochs)")
    p.add_argument("--name", default="mango_leaf_yolov8")
    args = p.parse_args()

    model = YOLO(args.model)
    model.train(
        data=resolve_data_yaml(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project=str(REPO_ROOT / "runs" / "train"),
        name=args.name,
        exist_ok=True,
        seed=42,
        plots=True,
    )

    best = Path(model.trainer.best)
    dest = REPO_ROOT / "models" / "best.pt"
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(best, dest)
    print(f"Best weights copied to {dest}")


if __name__ == "__main__":
    main()
