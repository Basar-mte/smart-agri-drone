"""Spray decision logic.

Kept free of hardware imports so it can be unit-tested on any machine. A spray is
triggered only when a target disease is seen in enough recent frames, the pump is
not cooling down, and the current location has not already been treated.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .config import SprayConfig
from .geo import Position, haversine_m


@dataclass(frozen=True)
class Detection:
    cls: str
    confidence: float
    xyxy: tuple[float, float, float, float]


@dataclass
class Decision:
    spray: bool
    confirmed: bool  # disease confirmed over the frame window (logged even when not sprayed)
    reason: str
    top: Detection | None = None


@dataclass
class SprayController:
    cfg: SprayConfig
    _history: deque[bool] = field(init=False)
    _last_spray_t: float | None = field(default=None, init=False)
    sprayed_at: list[Position] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._history = deque(maxlen=self.cfg.window)

    def update(self, detections: list[Detection], now: float, pos: Position | None) -> Decision:
        targets = [d for d in detections if d.cls in self.cfg.target_classes]
        top = max(targets, key=lambda d: d.confidence, default=None)
        self._history.append(top is not None)

        if sum(self._history) < self.cfg.min_hits:
            return Decision(False, False, "not enough diseased frames", top)
        if self._last_spray_t is not None and now - self._last_spray_t < self.cfg.cooldown_s:
            return Decision(False, True, "cooling down", top)
        if self.cfg.require_gps_fix and (pos is None or not pos.has_fix):
            return Decision(False, True, "no GPS fix", top)
        if pos is not None and self._near_previous(pos):
            return Decision(False, True, "already treated nearby", top)

        self._last_spray_t = now
        self._history.clear()
        if pos is not None:
            self.sprayed_at.append(pos)
        return Decision(True, True, "spray", top)

    def _near_previous(self, pos: Position) -> bool:
        return any(
            haversine_m(pos.lat, pos.lon, p.lat, p.lon) < self.cfg.min_separation_m
            for p in self.sprayed_at
        )
