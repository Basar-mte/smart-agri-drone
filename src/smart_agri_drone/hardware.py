"""Hardware adapters: camera, Pixhawk MAVLink link and spray pump relay.

Each adapter imports its driver lazily, so the rest of the package (and the tests)
run on a laptop without picamera2, pymavlink or GPIO access.
"""

from __future__ import annotations

import logging
import time

from .config import CameraConfig, MavlinkConfig, SprayConfig
from .geo import Position

log = logging.getLogger(__name__)


# --- Camera -------------------------------------------------------------------
class Camera:
    """Raspberry Pi camera via picamera2, or any OpenCV source (webcam index / video file)."""

    def __init__(self, cfg: CameraConfig) -> None:
        self._picam = None
        self._cap = None
        if cfg.source == "picamera2":
            from picamera2 import Picamera2

            self._picam = Picamera2()
            # "RGB888" in picamera2 yields BGR-ordered arrays, which is what YOLO/OpenCV expect.
            config = self._picam.create_preview_configuration(
                main={"size": (cfg.width, cfg.height), "format": "RGB888"}
            )
            self._picam.configure(config)
            self._picam.start()
            time.sleep(1.0)  # let auto-exposure settle
        else:
            import cv2

            src = int(cfg.source) if cfg.source.isdigit() else cfg.source
            self._cap = cv2.VideoCapture(src)
            if not self._cap.isOpened():
                raise RuntimeError(f"Cannot open camera source {cfg.source!r}")
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)

    def read(self):
        if self._picam is not None:
            return self._picam.capture_array()
        ok, frame = self._cap.read()
        return frame if ok else None

    def close(self) -> None:
        if self._picam is not None:
            self._picam.stop()
        if self._cap is not None:
            self._cap.release()


# --- Flight controller link -----------------------------------------------------
class MavlinkLink:
    """Reads the latest GPS position from the Pixhawk (TELEM2 -> Pi UART)."""

    def __init__(self, cfg: MavlinkConfig) -> None:
        from pymavlink import mavutil

        log.info("Connecting to flight controller on %s @ %d", cfg.connection, cfg.baud)
        self.master = mavutil.mavlink_connection(cfg.connection, baud=cfg.baud)
        self.master.wait_heartbeat(timeout=30)
        self._fix_type = 0
        self._pos: Position | None = None

    def poll(self) -> Position | None:
        """Drain pending messages without blocking and return the newest position."""
        while True:
            msg = self.master.recv_match(type=["GLOBAL_POSITION_INT", "GPS_RAW_INT"], blocking=False)
            if msg is None:
                return self._pos
            if msg.get_type() == "GPS_RAW_INT":
                self._fix_type = msg.fix_type
            else:
                self._pos = Position(
                    lat=msg.lat / 1e7,
                    lon=msg.lon / 1e7,
                    alt_m=msg.relative_alt / 1000.0,
                    fix_type=self._fix_type,
                )

    def close(self) -> None:
        self.master.close()


class NullLink:
    """Stand-in used on the bench when no flight controller is connected."""

    def poll(self) -> Position | None:
        return None

    def close(self) -> None:
        pass


def open_link(cfg: MavlinkConfig) -> MavlinkLink | NullLink:
    return NullLink() if cfg.connection.lower() == "none" else MavlinkLink(cfg)


# --- Spray pump -------------------------------------------------------------------
class Sprayer:
    """Drives the 12 V pump through a relay on a Pi GPIO pin. Non-blocking pulses."""

    def __init__(self, cfg: SprayConfig, dry_run: bool = False) -> None:
        self._off_at: float | None = None
        self._relay = None
        if dry_run:
            log.warning("Dry run: the pump will not be switched")
            return
        from gpiozero import OutputDevice

        self._relay = OutputDevice(cfg.relay_pin, active_high=cfg.active_high, initial_value=False)

    @property
    def spraying(self) -> bool:
        return self._off_at is not None

    def pulse(self, duration_s: float, now: float) -> None:
        self._off_at = now + duration_s
        if self._relay is not None:
            self._relay.on()
        log.info("Spraying for %.1f s", duration_s)

    def tick(self, now: float) -> None:
        if self._off_at is not None and now >= self._off_at:
            self.off()

    def off(self) -> None:
        self._off_at = None
        if self._relay is not None:
            self._relay.off()

    def close(self) -> None:
        self.off()
        if self._relay is not None:
            self._relay.close()
