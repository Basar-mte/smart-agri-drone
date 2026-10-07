# Training the YOLOv8 model

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-train.txt
```

With an NVIDIA GPU, install the matching CUDA build of PyTorch from [pytorch.org](https://pytorch.org) first.

## Pipeline

| Step | Command | Output |
|---|---|---|
| Split | `python ml/scripts/split_dataset.py --src <raw>` | `data/mango_leaf/{train,val,test}` |
| Augment | `python ml/scripts/augment.py --copies 2` | `*_aug*.jpg` in the train split |
| Train | `python ml/scripts/train.py --model yolov8n.pt --epochs 100` | `runs/train/mango_leaf_yolov8/`, `models/best.pt` |
| Evaluate | `python ml/scripts/evaluate.py --split test` | `runs/val/test/metrics.json` |
| Export | `python ml/scripts/export.py --format ncnn` | `models/best_ncnn_model/` |
| Predict | `python ml/scripts/predict.py --source <img/video/0> --show` | `runs/predict/latest/` |

## Choosing a model size

| Weights | Speed on Pi 5 (CPU) | Notes |
|---|---|---|
| `yolov8n.pt` | Fastest | Recommended for onboard real-time use |
| `yolov8s.pt` | ~2–3× slower | Better on small lesions if frame rate allows |
| `yolov8m.pt` | Too slow onboard | Use for offline analysis of recorded flights |

## Key settings

- `imgsz=640` balances detail and speed. Train and run at the same size.
- `patience=25` stops training early when validation mAP stops improving.
- `seed=42` makes runs repeatable.

## Reported results

| Precision | Recall | mAP@50 |
|---|---|---|
| 96.4 % | 95.3 % | 98.6 % |

Ultralytics writes training curves, the confusion matrix and PR curves to `runs/train/<name>/`.
