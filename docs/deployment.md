# Deployment and flight

## 1. Raspberry Pi 5

1. Flash **Raspberry Pi OS (64-bit, Bookworm)**.
2. Enable the UART and disable the serial console:
   `sudo raspi-config` → *Interface Options* → *Serial Port* → login shell **No**, hardware **Yes**. Then add `dtparam=uart0=on` to `/boot/firmware/config.txt` and reboot. The port appears as `/dev/ttyAMA0`.
3. Install the software:

   ```bash
   sudo apt update && sudo apt install -y python3-picamera2 python3-venv
   git clone <this-repo> && cd <this-repo>
   python -m venv --system-site-packages .venv && source .venv/bin/activate   # system packages give access to picamera2
   pip install -e ".[onboard]"
   ```
4. Copy `models/best_ncnn_model/` (or `best.pt`) from the training machine and set `model.weights` in `configs/drone.yaml`.
5. Check the camera with `rpicam-hello`.

## 2. Pixhawk

Configure with Mission Planner (ArduCopter) or QGroundControl (PX4):

| Setting                  | ArduCopter                           | PX4                        |
| ------------------------ | ------------------------------------ | -------------------------- |
| TELEM2 protocol          | `SERIAL2_PROTOCOL = 2` (MAVLink 2) | `MAV_1_CONFIG = TELEM 2` |
| TELEM2 baud              | `SERIAL2_BAUD = 57`                | `SER_TEL2_BAUD = 57600`  |
| Stream rate for position | `SR2_POSITION = 5`                 | default                    |
| Failsafe on RC loss      | `FS_THR_ENABLE = 1` (RTL)          | `NAV_RCL_ACT = 2` (RTL)  |
| Low-battery failsafe     | `BATT_FS_LOW_ACT = 2` (RTL)        | `COM_LOW_BAT_ACT = 3`    |

Calibrate the accelerometer, compass, radio and ESCs, then do a manual hover test **before** any autonomous flight.

## 3. Bench test (props off)

```bash
agri-drone --config configs/drone.yaml --dry-run -v
```

Check that the log shows GPS fixes and that a diseased leaf held in front of the camera is logged. Then run without `--dry-run`: the relay should click and the pump run for `spray.duration_s`.

## 4. Mission

```bash
# From a CSV of waypoints
agri-mission --waypoints missions/example_orchard.csv --connect /dev/ttyAMA0

# Or generate a survey over a rectangle (opposite corners)
agri-mission --survey LAT1 LON1 LAT2 LON2 --alt 5 --spacing 6 --hold 2 --save missions/today.csv --connect /dev/ttyAMA0
```

Add `--firmware px4` for PX4. Add `--start` to arm and start from the script (it asks for confirmation). Otherwise start the mission from the RC transmitter or ground station.

Pick the altitude so the camera footprint covers one tree row, and set `--spacing` to roughly the row spacing of the orchard.

## 5. Run as a service (optional)

```ini
# /etc/systemd/system/agri-drone.service
[Unit]
Description=Smart Agri-Drone detection and spraying
After=network.target

[Service]
WorkingDirectory=/home/pi/smart-agri-drone
ExecStart=/home/pi/smart-agri-drone/.venv/bin/agri-drone --config configs/drone.yaml
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now agri-drone
journalctl -u agri-drone -f
```

## 6. After the flight

Each run writes `runs/flights/<timestamp>/` containing `infections.csv`, `infections.geojson` and the annotated frames.

```bash
python tools/plot_infection_map.py runs/flights/<timestamp>/infections.csv
```

## Safety checklist

- [ ] Props off for every bench test
- [ ] Pilot holding the RC with a mode switch ready for manual/RTL
- [ ] Battery charged and balanced; failsafes tested
- [ ] GPS 3D fix with enough satellites before arming
- [ ] Spray tank sealed; correct, approved chemical at the correct dilution
- [ ] Permission from the landowner; follow local drone regulations
