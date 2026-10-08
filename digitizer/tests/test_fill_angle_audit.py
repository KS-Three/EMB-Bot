"""`tools/fill_angle_audit.findings` -- the two pair/shape rules, on
hand-built polygons so no digitize run is needed."""
import sys
from pathlib import Path

from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "pro_parity"))

from fill_angle_audit import findings  # noqa: E402


def _s(name, poly, deg, thread="1"):
    return {"shape": name, "thread": thread, "poly": poly, "sewn_deg": deg,
            "area_mm2": poly.area, "aspect": 1.0}


def test_touching_same_thread_flip_is_reported():
    a = _s("a", box(0, 0, 10, 10), 0.0)
    b = _s("b", box(10.2, 0, 20, 10), 90.0)
    out = findings([a, b], touch_mm=0.5, flip_deg=30.0, aspect=2.5)
    assert [(f["a"], f["b"], f["diff_deg"]) for f in out["flips"]] == [("a", "b", 90.0)]


def test_other_thread_far_apart_or_agreeing_are_not_flips():
    a = _s("a", box(0, 0, 10, 10), 0.0)
    other = _s("o", box(10.2, 0, 20, 10), 90.0, thread="2")
    far = _s("f", box(30, 0, 40, 10), 90.0)
    near = _s("n", box(0, 10.1, 10, 20), 170.0)    # 10 deg the short way round
    out = findings([a, other, far, near], touch_mm=0.5, flip_deg=30.0, aspect=2.5)
    assert out["flips"] == []


def test_rows_across_a_bar_are_reported_along_it_are_not():
    bar = box(0, 0, 40, 4)
    across = {**_s("x", bar, 90.0), "aspect": 10.0}
    along = {**_s("y", bar, 0.0), "aspect": 10.0}
    out = findings([across, along], touch_mm=0.0, flip_deg=30.0, aspect=2.5)
    assert [s["shape"] for s in out["across"]] == ["x"]
