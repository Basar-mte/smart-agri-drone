# Model weights

Trained weights are kept out of Git. After training, `ml/scripts/train.py` copies the best checkpoint to `models/best.pt`, and `ml/scripts/export.py` writes `models/best_ncnn_model/` for the Raspberry Pi.

To share weights, attach `best.pt` to a [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github) instead of committing it.
