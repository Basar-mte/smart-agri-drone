"""Export trained weights for the Raspberry Pi 5 (NCNN is the fastest CPU backend there)."""

from __future__ import annotations

import argparse

from ultralytics import YOLO

from common import REPO_ROOT


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights", default=str(REPO_ROOT / "models" / "best.pt"))
    p.add_argument("--format", default="ncnn", choices=["ncnn", "onnx", "tflite", "openvino"])
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--half", action="store_true", help="FP16 weights")
    args = p.parse_args()

    out = YOLO(args.weights).export(format=args.format, imgsz=args.imgsz, half=args.half)
    print(f"Exported to {out}")


if __name__ == "__main__":
    main()
