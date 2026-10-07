"""Split a YOLO-format dataset into train/val/test folders.

Input layout (e.g. a Roboflow / LabelImg export):
    raw/images/*.jpg
    raw/labels/*.txt   (one YOLO label file per image, same stem)

Output layout:
    data/mango_leaf/{train,val,test}/{images,labels}/
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def split(src: Path, dst: Path, ratios: tuple[float, float, float], seed: int) -> dict[str, int]:
    images = sorted(p for p in (src / "images").iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise SystemExit(f"No images found in {src / 'images'}")
    random.Random(seed).shuffle(images)

    n = len(images)
    n_train = round(n * ratios[0])
    n_val = round(n * ratios[1])
    parts = {
        "train": images[:n_train],
        "val": images[n_train:n_train + n_val],
        "test": images[n_train + n_val:],
    }
    missing = 0
    for name, files in parts.items():
        (dst / name / "images").mkdir(parents=True, exist_ok=True)
        (dst / name / "labels").mkdir(parents=True, exist_ok=True)
        for img in files:
            shutil.copy2(img, dst / name / "images" / img.name)
            label = src / "labels" / f"{img.stem}.txt"
            if label.exists():
                shutil.copy2(label, dst / name / "labels" / label.name)
            else:
                missing += 1
    if missing:
        print(f"Warning: {missing} images have no label file (treated as background).")
    return {k: len(v) for k, v in parts.items()}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", type=Path, required=True, help="folder containing images/ and labels/")
    p.add_argument("--dst", type=Path, default=Path("data/mango_leaf"))
    p.add_argument("--ratios", type=float, nargs=3, default=(0.7, 0.2, 0.1), metavar=("TRAIN", "VAL", "TEST"))
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    if abs(sum(args.ratios) - 1.0) > 1e-6:
        raise SystemExit("Ratios must sum to 1")
    counts = split(args.src, args.dst, tuple(args.ratios), args.seed)
    print("Split:", counts)


if __name__ == "__main__":
    main()
