import json

import pytest

from smart_agri_drone import DISEASE_CLASSES
from smart_agri_drone.config import load_config
from smart_agri_drone.decision import Detection
from smart_agri_drone.geo import Position
from smart_agri_drone.geotag import GeoTagLogger


def test_repo_configs_load():
    drone = load_config("configs/drone.yaml")
    assert drone.mavlink.connection == "/dev/ttyAMA0"
    assert drone.spray.target_classes == list(DISEASE_CLASSES)
    bench = load_config("configs/bench.yaml")
    assert bench.mavlink.connection == "none"
    assert bench.spray.require_gps_fix is False
    assert bench.model.imgsz == 640  # default kept for unspecified keys


def test_unknown_key_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("spray:\n  pump_speed: 3\n")
    with pytest.raises(ValueError, match="pump_speed"):
        load_config(bad)


def test_min_hits_cannot_exceed_window(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("spray:\n  min_hits: 6\n  window: 5\n")
    with pytest.raises(ValueError):
        load_config(bad)


def test_geotag_logger_writes_csv_and_geojson(tmp_path):
    tagger = GeoTagLogger(tmp_path)
    det = Detection("gall_midge", 0.87, (0, 0, 1, 1))
    tagger.log(det, Position(24.364, 88.628, 5.0), sprayed=True, frame="000001.jpg")
    tagger.log(det, None, sprayed=False)  # no GPS -> kept in CSV, skipped in GeoJSON
    out = tagger.close()

    rows = tagger.csv_path.read_text().strip().splitlines()
    assert len(rows) == 3
    gj = json.loads(out.read_text())
    assert len(gj["features"]) == 1
    feat = gj["features"][0]
    assert feat["geometry"]["coordinates"] == [88.628, 24.364]
    assert feat["properties"]["sprayed"] is True
    assert feat["properties"]["disease"] == "gall_midge"
