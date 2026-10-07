"""Offline augmentation of the training split (bounding boxes are transformed too).

Field images vary in sunlight, shadow, blur and viewing angle, so the transforms
below mimic what the drone camera sees over a mango canopy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import albumentations as A
import cv2

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def build_pipeline() -> A.Compose:
    return A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.2),
            A.Affine(scale=(0.85, 1.15), rotate=(-20, 20), translate_percent=(-0.05, 0.05), p=0.7),
            A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
            A.HueSaturationValue(hue_shift_limit=8, sat_shift_limit=25, val_shift_limit=20, p=0.5),
            A.RandomShadow(p=0.2),
            A.OneOf([A.MotionBlur(blur_limit=5), A.GaussianBlur(blur_limit=(3, 5))], p=0.25),
            A.GaussNoise(p=0.15),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_ids"], min_visibility=0.3),
    )


def read_labels(path: Path) -> tuple[list[list[float]], list[int]]:
    boxes, ids = [], []
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 5:
                ids.append(int(parts[0]))
                boxes.append([min(max(float(v), 0.0), 1.0) for v in parts[1:]])
    return boxes, ids


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-dir", type=Path, default=Path("data/mango_leaf/train"))
    p.add_argument("--copies", type=int, default=2, help="augmented copies per image")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    pipeline = build_pipeline()
    pipeline.set_random_seed(args.seed)
    img_dir, lbl_dir = args.split_dir / "images", args.split_dir / "labels"
    originals = [f for f in sorted(img_dir.iterdir()) if f.suffix.lower() in IMAGE_EXTS and "_aug" not in f.stem]

    written = 0
    for img_path in originals:
        image = cv2.imread(str(img_path))
        if image is None:
            continue
        boxes, ids = read_labels(lbl_dir / f"{img_path.stem}.txt")
        for k in range(args.copies):
            out = pipeline(image=image, bboxes=boxes, class_ids=ids)
            stem = f"{img_path.stem}_aug{k}"
            cv2.imwrite(str(img_dir / f"{stem}.jpg"), out["image"])
            pairs = zip(out["bboxes"], out["class_ids"], strict=True)
            lines = [f"{c} {' '.join(f'{v:.6f}' for v in b)}" for b, c in pairs]
            (lbl_dir / f"{stem}.txt").write_text("\n".join(lines))
            written += 1
    print(f"Wrote {written} augmented images from {len(originals)} originals")


if __name__ == "__main__":
    main()
