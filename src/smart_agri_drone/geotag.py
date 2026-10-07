"""Geo-tagged log of infected zones (CSV during flight, GeoJSON for mapping)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .decision import Detection
from .geo import Position

FIELDS = ["timestamp", "lat", "lon", "alt_m", "disease", "confidence", "sprayed", "frame"]


class GeoTagLogger:
    def __init__(self, directory: str | Path) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.dir = Path(directory) / stamp
        self.frames_dir = self.dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.dir / "infections.csv"
        self._fh = self.csv_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=FIELDS)
        self._writer.writeheader()

    def log(self, det: Detection, pos: Position | None, sprayed: bool, frame: str = "") -> None:
        self._writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lat": f"{pos.lat:.7f}" if pos else "",
            "lon": f"{pos.lon:.7f}" if pos else "",
            "alt_m": f"{pos.alt_m:.1f}" if pos else "",
            "disease": det.cls,
            "confidence": f"{det.confidence:.3f}",
            "sprayed": int(sprayed),
            "frame": frame,
        })
        self._fh.flush()  # survive a power cut mid-flight

    def close(self) -> Path:
        self._fh.close()
        out = self.dir / "infections.geojson"
        out.write_text(json.dumps(csv_to_geojson(self.csv_path), indent=2), encoding="utf-8")
        return out


def csv_to_geojson(csv_path: str | Path) -> dict:
    features = []
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row["lat"] or not row["lon"]:
                continue
            props = {k: row[k] for k in FIELDS if k not in ("lat", "lon")}
            props["confidence"] = float(props["confidence"])
            props["sprayed"] = bool(int(props["sprayed"]))
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(row["lon"]), float(row["lat"])]},
                "properties": props,
            })
    return {"type": "FeatureCollection", "features": features}
