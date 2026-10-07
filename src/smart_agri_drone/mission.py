"""Mission planning and upload for the Pixhawk.

Builds a takeoff -> waypoints -> return-to-launch mission, either from a CSV of
waypoints or as a serpentine ("lawn-mower") survey over an orchard rectangle, and
uploads it with the standard MAVLink mission protocol (works on ArduPilot and PX4).
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from dataclasses import dataclass
from pathlib import Path

from .geo import local_extent_m, offset

log = logging.getLogger("agri-mission")

# MAVLink constants (copied so planning does not need pymavlink installed)
MAV_FRAME_GLOBAL_RELATIVE_ALT_INT = 6
MAV_CMD_NAV_WAYPOINT = 16
MAV_CMD_NAV_RETURN_TO_LAUNCH = 20
MAV_CMD_NAV_LAND = 21
MAV_CMD_NAV_TAKEOFF = 22
MAV_CMD_MISSION_START = 300
MAV_MISSION_ACCEPTED = 0


@dataclass(frozen=True)
class Waypoint:
    lat: float
    lon: float
    alt_m: float
    hold_s: float = 0.0  # hover time at the waypoint (lets the camera scan the canopy)


@dataclass(frozen=True)
class MissionItem:
    command: int
    lat: float = 0.0
    lon: float = 0.0
    alt_m: float = 0.0
    param1: float = 0.0


def load_waypoints(path: str | Path) -> list[Waypoint]:
    """CSV with header lat,lon,alt_m[,hold_s]."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("lat", "").strip()]
    if not rows:
        raise ValueError(f"No waypoints in {path}")
    return [
        Waypoint(float(r["lat"]), float(r["lon"]), float(r["alt_m"]), float(r.get("hold_s") or 0))
        for r in rows
    ]


def survey_grid(
    corner1: tuple[float, float],
    corner2: tuple[float, float],
    alt_m: float,
    spacing_m: float,
    hold_s: float = 0.0,
) -> list[Waypoint]:
    """Serpentine passes running east-west across the rectangle, `spacing_m` apart (north-south)."""
    if spacing_m <= 0:
        raise ValueError("spacing_m must be positive")
    lat0, lon0 = corner1
    north, east = local_extent_m(lat0, lon0, *corner2)
    passes = max(1, math.floor(abs(north) / spacing_m) + 1)
    step = math.copysign(spacing_m, north) if north else 0.0
    wps: list[Waypoint] = []
    for i in range(passes):
        n = i * step
        ends = [(n, 0.0), (n, east)]
        if i % 2:
            ends.reverse()
        for dn, de in ends:
            lat, lon = offset(lat0, lon0, dn, de)
            wps.append(Waypoint(lat, lon, alt_m, hold_s))
    return wps


def build_mission(waypoints: list[Waypoint], takeoff_alt_m: float, firmware: str = "ardupilot",
                  land_at_end: bool = False) -> list[MissionItem]:
    items: list[MissionItem] = []
    if firmware == "ardupilot":
        # ArduPilot treats item 0 as home and overwrites it, so send a placeholder.
        first = waypoints[0]
        items.append(MissionItem(MAV_CMD_NAV_WAYPOINT, first.lat, first.lon, 0.0))
    items.append(MissionItem(MAV_CMD_NAV_TAKEOFF, waypoints[0].lat, waypoints[0].lon, takeoff_alt_m))
    items += [MissionItem(MAV_CMD_NAV_WAYPOINT, w.lat, w.lon, w.alt_m, param1=w.hold_s) for w in waypoints]
    if land_at_end:
        last = waypoints[-1]
        items.append(MissionItem(MAV_CMD_NAV_LAND, last.lat, last.lon, 0.0))
    else:
        items.append(MissionItem(MAV_CMD_NAV_RETURN_TO_LAUNCH))
    return items


def write_waypoints(path: str | Path, waypoints: list[Waypoint]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["lat", "lon", "alt_m", "hold_s"])
        for wp in waypoints:
            w.writerow([f"{wp.lat:.7f}", f"{wp.lon:.7f}", wp.alt_m, wp.hold_s])


# --- MAVLink side -------------------------------------------------------------------
def connect(connection: str, baud: int):
    from pymavlink import mavutil

    master = mavutil.mavlink_connection(connection, baud=baud)
    master.wait_heartbeat(timeout=30)
    log.info("Heartbeat from system %d component %d", master.target_system, master.target_component)
    return master


def upload(master, items: list[MissionItem], timeout_s: float = 5.0) -> None:
    from pymavlink import mavutil

    ts, tc = master.target_system, master.target_component
    master.mav.mission_clear_all_send(ts, tc)
    master.recv_match(type="MISSION_ACK", blocking=True, timeout=timeout_s)
    master.mav.mission_count_send(ts, tc, len(items), mavutil.mavlink.MAV_MISSION_TYPE_MISSION)

    sent: set[int] = set()
    while True:
        msg = master.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"],
                                blocking=True, timeout=timeout_s)
        if msg is None:
            raise TimeoutError(f"Flight controller stopped requesting items ({len(sent)}/{len(items)} sent)")
        if msg.get_type() == "MISSION_ACK":
            if msg.type != MAV_MISSION_ACCEPTED or len(sent) < len(items):
                raise RuntimeError(f"Mission rejected (MAV_MISSION_RESULT={msg.type})")
            log.info("Mission accepted: %d items", len(items))
            return
        it = items[msg.seq]
        master.mav.mission_item_int_send(
            ts, tc, msg.seq, MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, it.command,
            0, 1, it.param1, 0, 0, 0,
            int(it.lat * 1e7), int(it.lon * 1e7), it.alt_m,
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
        )
        sent.add(msg.seq)


def start(master, firmware: str) -> None:
    """Arm and start the uploaded mission. The pilot must keep the RC transmitter in hand."""
    master.set_mode("GUIDED" if firmware == "ardupilot" else "LOITER")
    master.arducopter_arm()
    master.motors_armed_wait()
    log.info("Armed")
    master.set_mode("AUTO" if firmware == "ardupilot" else "MISSION")
    master.mav.command_long_send(master.target_system, master.target_component,
                                 MAV_CMD_MISSION_START, 0, 0, 0, 0, 0, 0, 0, 0)
    log.info("Mission started")


def main() -> None:
    p = argparse.ArgumentParser(description="Plan and upload a Smart Agri-Drone spraying mission")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--waypoints", help="CSV with lat,lon,alt_m[,hold_s]")
    src.add_argument("--survey", nargs=4, type=float, metavar=("LAT1", "LON1", "LAT2", "LON2"),
                     help="opposite corners of the orchard rectangle")
    p.add_argument("--alt", type=float, default=5.0, help="survey altitude above home, m")
    p.add_argument("--spacing", type=float, default=6.0, help="distance between survey passes, m")
    p.add_argument("--hold", type=float, default=0.0, help="hover time at each waypoint, s")
    p.add_argument("--takeoff-alt", type=float, default=5.0)
    p.add_argument("--firmware", choices=["ardupilot", "px4"], default="ardupilot")
    p.add_argument("--land", action="store_true", help="land at the last waypoint instead of RTL")
    p.add_argument("--save", help="write the generated waypoints to this CSV")
    p.add_argument("--connect", help="MAVLink connection, e.g. /dev/ttyAMA0, COM5 or udp:127.0.0.1:14550")
    p.add_argument("--baud", type=int, default=57600)
    p.add_argument("--start", action="store_true", help="arm and start the mission after upload")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.waypoints:
        wps = load_waypoints(args.waypoints)
    else:
        lat1, lon1, lat2, lon2 = args.survey
        wps = survey_grid((lat1, lon1), (lat2, lon2), args.alt, args.spacing, args.hold)
    items = build_mission(wps, args.takeoff_alt, args.firmware, args.land)
    log.info("Planned %d waypoints (%d mission items)", len(wps), len(items))
    if args.save:
        write_waypoints(args.save, wps)
        log.info("Waypoints saved to %s", args.save)

    if not args.connect:
        return
    master = connect(args.connect, args.baud)
    upload(master, items)
    if args.start:
        answer = input("Props clear, pilot ready on RC? Type 'yes' to arm and start: ")
        if answer.strip().lower() == "yes":
            start(master, args.firmware)
        else:
            log.info("Not started")


if __name__ == "__main__":
    main()
