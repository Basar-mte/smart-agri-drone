# Dataset folder

The mango-leaf images are not stored in Git. Put the YOLO-format dataset here so it looks like this:

```
data/mango_leaf/
├── train/{images,labels}/
├── val/{images,labels}/
└── test/{images,labels}/
```

`python ml/scripts/split_dataset.py --src <raw-folder>` builds this layout from a flat `images/` + `labels/` export.
See [docs/dataset.md](../docs/dataset.md) for the classes and how the data was collected.
