"""Small geodesy helpers (no external dependencies)."""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Position:
    """A GPS fix from the flight controller."""

    lat: float
    lon: float
    alt_m: float = 0.0  # altitude relative to home
    fix_type: int = 3  # MAVLink GPS_FIX_TYPE; >= 3 means a 3D fix

    @property
    def has_fix(self) -> bool:
        return self.fix_type >= 3


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS-84 points, in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def offset(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    """Move a point by a local north/east offset (flat-earth approximation, fine for fields)."""
    dlat = north_m / EARTH_RADIUS_M
    dlon = east_m / (EARTH_RADIUS_M * math.cos(math.radians(lat)))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


def local_extent_m(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """North and east extent (metres) of the box spanned by two corners."""
    north = haversine_m(lat1, lon1, lat2, lon1) * (1 if lat2 >= lat1 else -1)
    east = haversine_m(lat1, lon1, lat1, lon2) * (1 if lon2 >= lon1 else -1)
    return north, east
