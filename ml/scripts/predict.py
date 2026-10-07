"""Run the detector on an image, a folder, a video, an FPV capture device or a webcam.

Examples
    python ml/scripts/predict.py --source assets/images/dataset/gall_midge.jpg
    python ml/scripts/predict.py --source 0 --show          # live webcam / FPV receiver
"""

from __future__ import annotations

import argparse
from collections import Counter

from ultralytics import YOLO

from common import REPO_ROOT


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", default=str(REPO_ROOT / "models" / "best.pt"))
    p.add_argument("--source", required=True, help="file, folder, video, or camera index")
    p.add_argument("--conf", type=float, default=0.5)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--show", action="store_true")
    args = p.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    model = YOLO(args.weights)
    counts: Counter[str] = Counter()
    for r in model.predict(source, conf=args.conf, imgsz=args.imgsz, stream=True, show=args.show,
                           save=True, project=str(REPO_ROOT / "runs" / "predict"), name="latest", exist_ok=True):
        counts.update(model.names[int(c)] for c in r.boxes.cls.tolist())
    print("Detections:", dict(counts) or "none")


if __name__ == "__main__":
    main()
