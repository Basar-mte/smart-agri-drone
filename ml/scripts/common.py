"""Shared helpers for the training scripts."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / "ml" / "configs" / "mango_leaf.yaml"


def resolve_data_yaml(path: str | Path = DEFAULT_DATA) -> str:
    """Write a copy of the dataset YAML whose `path` is absolute.

    Ultralytics resolves relative dataset paths against its own datasets folder,
    not against the YAML file, so we pin it to the repository root here.
    """
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    root = Path(cfg["path"])
    if not root.is_absolute():
        root = REPO_ROOT / root
    if not root.exists():
        raise FileNotFoundError(f"Dataset folder not found: {root}. See docs/dataset.md.")
    cfg["path"] = str(root)
    tmp = Path(tempfile.gettempdir()) / f"resolved_{Path(path).name}"
    tmp.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return str(tmp)
