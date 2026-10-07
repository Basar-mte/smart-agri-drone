"""Typed configuration loaded from a YAML file (see configs/drone.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from . import DISEASE_CLASSES


@dataclass
class ModelConfig:
    weights: str = "models/best.pt"
    imgsz: int = 640
    confidence: float = 0.5
    iou: float = 0.45
    device: str = "cpu"


@dataclass
class CameraConfig:
    source: str = "picamera2"  # "picamera2", a device index such as "0", or a video file path
    width: int = 1280
    height: int = 720


@dataclass
class MavlinkConfig:
    connection: str = "/dev/ttyAMA0"  # "none" disables the link (bench testing)
    baud: int = 57600


@dataclass
class SprayConfig:
    relay_pin: int = 17  # BCM numbering
    active_high: bool = False  # most opto-isolated relay boards are active-low
    duration_s: float = 2.0
    cooldown_s: float = 5.0
    min_hits: int = 3  # diseased frames needed inside `window` before spraying
    window: int = 5
    min_separation_m: float = 3.0  # do not re-spray within this radius
    require_gps_fix: bool = True
    target_classes: list[str] = field(default_factory=lambda: list(DISEASE_CLASSES))


@dataclass
class LoggingConfig:
    directory: str = "runs/flights"
    save_frames: bool = True


@dataclass
class DroneConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    mavlink: MavlinkConfig = field(default_factory=MavlinkConfig)
    spray: SprayConfig = field(default_factory=SprayConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _build(cls: type, data: dict[str, Any]) -> Any:
    known = {f.name: f for f in fields(cls)}
    unknown = set(data) - set(known)
    if unknown:
        raise ValueError(f"Unknown keys for {cls.__name__}: {sorted(unknown)}")
    kwargs = {}
    for name, value in data.items():
        sub = cls.__dataclass_fields__[name].default_factory  # type: ignore[attr-defined]
        if isinstance(value, dict) and callable(sub) and is_dataclass(sub):
            kwargs[name] = _build(sub, value)
        else:
            kwargs[name] = value
    return cls(**kwargs)


def load_config(path: str | Path | None = None) -> DroneConfig:
    """Load a config file; missing keys fall back to the defaults above."""
    if path is None:
        return DroneConfig()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    cfg = _build(DroneConfig, data)
    if cfg.spray.min_hits > cfg.spray.window:
        raise ValueError("spray.min_hits cannot exceed spray.window")
    return cfg
