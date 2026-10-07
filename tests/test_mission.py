import pytest

from smart_agri_drone.geo import haversine_m
from smart_agri_drone.mission import (
    MAV_CMD_NAV_LAND,
    MAV_CMD_NAV_RETURN_TO_LAUNCH,
    MAV_CMD_NAV_TAKEOFF,
    MAV_CMD_NAV_WAYPOINT,
    build_mission,
    load_waypoints,
    survey_grid,
    write_waypoints,
)

C1 = (24.3640, 88.6280)
C2 = (24.36436, 88.62830)  # ~40 m north, ~30 m east


def test_survey_grid_is_serpentine_and_spaced():
    wps = survey_grid(C1, C2, alt_m=5, spacing_m=10)
    assert len(wps) % 2 == 0 and len(wps) >= 8
    # consecutive passes are ~10 m apart
    assert haversine_m(wps[0].lat, wps[0].lon, wps[3].lat, wps[3].lon) == pytest.approx(10, abs=0.2)
    # pass 2 runs in the opposite direction to pass 1
    assert wps[1].lon > wps[0].lon and wps[3].lon < wps[2].lon
    assert all(w.alt_m == 5 for w in wps)


def test_survey_grid_rejects_bad_spacing():
    with pytest.raises(ValueError):
        survey_grid(C1, C2, 5, 0)


def test_build_mission_ardupilot_has_home_placeholder_and_rtl():
    wps = survey_grid(C1, C2, 5, 10)
    items = build_mission(wps, takeoff_alt_m=4)
    assert items[0].command == MAV_CMD_NAV_WAYPOINT  # home placeholder
    assert items[1].command == MAV_CMD_NAV_TAKEOFF and items[1].alt_m == 4
    assert items[-1].command == MAV_CMD_NAV_RETURN_TO_LAUNCH
    assert len(items) == len(wps) + 3


def test_build_mission_px4_land():
    wps = survey_grid(C1, C2, 5, 10)
    items = build_mission(wps, 4, firmware="px4", land_at_end=True)
    assert items[0].command == MAV_CMD_NAV_TAKEOFF
    assert items[-1].command == MAV_CMD_NAV_LAND
    assert len(items) == len(wps) + 2


def test_waypoint_csv_round_trip(tmp_path):
    wps = survey_grid(C1, C2, 5, 10, hold_s=2)
    path = tmp_path / "wps.csv"
    write_waypoints(path, wps)
    loaded = load_waypoints(path)
    assert len(loaded) == len(wps)
    assert loaded[0].lat == pytest.approx(wps[0].lat, abs=1e-7)
    assert loaded[-1].hold_s == 2


def test_example_mission_loads():
    wps = load_waypoints("missions/example_orchard.csv")
    assert len(wps) == 6
