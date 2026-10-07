from smart_agri_drone.config import SprayConfig
from smart_agri_drone.decision import Detection, SprayController
from smart_agri_drone.geo import Position, offset

SICK = [Detection("anthracnose", 0.9, (0, 0, 10, 10))]
BASE = Position(24.3640, 88.6280, 5.0)


def controller(**kw) -> SprayController:
    cfg = SprayConfig(**{"min_hits": 3, "window": 5, "cooldown_s": 5.0, "min_separation_m": 3.0, **kw})
    return SprayController(cfg)


def test_needs_min_hits_before_spraying():
    c = controller()
    assert not c.update(SICK, 0.0, BASE).spray
    assert not c.update(SICK, 0.1, BASE).spray
    d = c.update(SICK, 0.2, BASE)
    assert d.spray and d.top.cls == "anthracnose"


def test_ignores_non_target_classes():
    c = controller(target_classes=["gall_midge"])
    for t in range(5):
        d = c.update(SICK, t * 0.1, BASE)
    assert not d.spray and not d.confirmed


def test_cooldown_blocks_repeat_spray():
    c = controller()
    far = Position(*offset(BASE.lat, BASE.lon, 50, 0), 5.0)
    for t in (0.0, 0.1, 0.2):
        c.update(SICK, t, BASE)
    for t in (1.0, 1.1, 1.2):
        d = c.update(SICK, t, far)
    assert not d.spray and d.reason == "cooling down"
    assert c.update(SICK, 6.0, far).spray


def test_does_not_respray_same_spot():
    c = controller(cooldown_s=0.0)
    for t in (0.0, 0.1, 0.2):
        c.update(SICK, t, BASE)
    near = Position(*offset(BASE.lat, BASE.lon, 1.0, 1.0), 5.0)
    for t in (10.0, 10.1, 10.2):
        d = c.update(SICK, t, near)
    assert not d.spray and d.reason == "already treated nearby"


def test_requires_gps_fix():
    c = controller()
    no_fix = Position(BASE.lat, BASE.lon, 5.0, fix_type=1)
    for t in (0.0, 0.1, 0.2):
        d = c.update(SICK, t, no_fix)
    assert not d.spray and d.reason == "no GPS fix"
    for t in (0.3, 0.4, 0.5):
        d = c.update(SICK, t, None)
    assert not d.spray


def test_bench_mode_without_gps():
    c = controller(require_gps_fix=False)
    for t in (0.0, 0.1, 0.2):
        d = c.update(SICK, t, None)
    assert d.spray
