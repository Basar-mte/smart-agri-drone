"""Draw the geo-tagged infections from a flight log on an interactive map.

    python tools/plot_infection_map.py runs/flights/<stamp>/infections.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import folium

COLOURS = {
    "anthracnose": "darkred",
    "bacterial_canker": "orange",
    "cutting_weevil": "purple",
    "die_back": "black",
    "gall_midge": "red",
    "powdery_mildew": "gray",
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", type=Path)
    p.add_argument("--out", type=Path, help="HTML file (default: next to the CSV)")
    args = p.parse_args()

    with args.csv.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["lat"] and r["lon"]]
    if not rows:
        raise SystemExit("No geo-tagged rows in the log")

    centre = (sum(float(r["lat"]) for r in rows) / len(rows), sum(float(r["lon"]) for r in rows) / len(rows))
    fmap = folium.Map(location=centre, zoom_start=19, max_zoom=22,
                      tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                      attr="Esri World Imagery")
    for r in rows:
        sprayed = r["sprayed"] == "1"
        folium.CircleMarker(
            location=(float(r["lat"]), float(r["lon"])),
            radius=7 if sprayed else 5,
            color=COLOURS.get(r["disease"], "blue"),
            fill=True,
            fill_opacity=0.9 if sprayed else 0.4,
            tooltip=f"{r['disease']} ({float(r['confidence']):.2f}){' - sprayed' if sprayed else ''}",
        ).add_to(fmap)

    out = args.out or args.csv.with_suffix(".html")
    fmap.save(str(out))
    print(f"Map with {len(rows)} points written to {out}")


if __name__ == "__main__":
    main()
