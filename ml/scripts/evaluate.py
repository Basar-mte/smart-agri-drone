"""Evaluate trained weights on the held-out test split and save the metrics as JSON."""

from __future__ import annotations

import argparse
import json

from ultralytics import YOLO

from common import DEFAULT_DATA, REPO_ROOT, resolve_data_yaml


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights", default=str(REPO_ROOT / "models" / "best.pt"))
    p.add_argument("--data", default=str(DEFAULT_DATA))
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--imgsz", type=int, default=640)
    args = p.parse_args()

    model = YOLO(args.weights)
    m = model.val(data=resolve_data_yaml(args.data), split=args.split, imgsz=args.imgsz,
                  project=str(REPO_ROOT / "runs" / "val"), name=args.split, exist_ok=True)

    metrics = {
        "precision": round(float(m.box.mp), 4),
        "recall": round(float(m.box.mr), 4),
        "mAP50": round(float(m.box.map50), 4),
        "mAP50-95": round(float(m.box.map), 4),
        "per_class_mAP50-95": {model.names[int(c)]: round(float(v), 4)
                               for c, v in zip(m.box.ap_class_index, m.box.maps[m.box.ap_class_index], strict=True)},
    }
    out = REPO_ROOT / "runs" / "val" / args.split / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
