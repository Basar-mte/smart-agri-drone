"""Onboard loop for the Raspberry Pi 5.

camera frame -> YOLOv8 -> spray decision -> relay pulse + geo-tagged log

The flight itself is flown by the Pixhawk (AUTO / MISSION mode, see `agri-mission`);
this process only reads the position and switches the pump.
"""

from __future__ import annotations

import argparse
import logging
import signal
import time

from .config import load_config
from .decision import SprayController
from .geotag import GeoTagLogger
from .hardware import Camera, Sprayer, open_link

log = logging.getLogger("agri-drone")


def run(config_path: str | None, dry_run: bool, show: bool) -> None:
    from .detector import LeafDiseaseDetector

    cfg = load_config(config_path)
    detector = LeafDiseaseDetector(cfg.model)
    camera = Camera(cfg.camera)
    link = open_link(cfg.mavlink)
    sprayer = Sprayer(cfg.spray, dry_run=dry_run)
    controller = SprayController(cfg.spray)
    tagger = GeoTagLogger(cfg.logging.directory)

    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    frames, t0 = 0, time.monotonic()
    log.info("Running. Logging to %s", tagger.dir)
    try:
        while not stop:
            frame = camera.read()
            if frame is None:
                log.info("Camera stream ended")
                break
            now = time.monotonic()
            pos = link.poll()
            detections, result = detector.detect(frame)
            decision = controller.update(detections, now, pos)

            if decision.spray:
                sprayer.pulse(cfg.spray.duration_s, now)
            sprayer.tick(now)

            if decision.confirmed and decision.top is not None and (decision.spray or not sprayer.spraying):
                frame_name = ""
                if cfg.logging.save_frames:
                    import cv2

                    frame_name = f"{frames:06d}_{decision.top.cls}.jpg"
                    cv2.imwrite(str(tagger.frames_dir / frame_name), result.plot())
                tagger.log(decision.top, pos, sprayed=decision.spray, frame=frame_name)
                log.info("%s (%.2f) -> %s", decision.top.cls, decision.top.confidence, decision.reason)

            if show:
                import cv2

                cv2.imshow("Smart Agri-Drone", result.plot())
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frames += 1
            if frames % 100 == 0:
                log.info("%.1f FPS", frames / (time.monotonic() - t0))
    finally:
        sprayer.close()
        camera.close()
        link.close()
        geojson = tagger.close()
        log.info("Infected-zone map written to %s", geojson)


def main() -> None:
    p = argparse.ArgumentParser(description="Smart Agri-Drone onboard detection and spraying")
    p.add_argument("--config", default="configs/drone.yaml", help="YAML config file")
    p.add_argument("--dry-run", action="store_true", help="detect and log, but never switch the pump")
    p.add_argument("--show", action="store_true", help="show the annotated video (needs a display)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(args.config, args.dry_run, args.show)


if __name__ == "__main__":
    main()
