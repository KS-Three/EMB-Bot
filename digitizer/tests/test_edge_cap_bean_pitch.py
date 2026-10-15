"""`cfg.edge_cap_bean_pitch_mm` (built OFF 2026-10-15): the bean edge cap's
station pitch, on the cap ONLY.

The short-stitch census (docs/short-stitch-sources-2026-10-15.md) found
`stage6_border.run_outline` the worst source per stitch, and priced a
1.5 mm bean pitch there on BOTH bean tiers. This knob takes the cap half
alone: the run tier (small lettering outlines, where a long chord on a tight
curve shows) keeps `machine.BEAN_STITCH_MM`. Every pitch is a gate-1
candidate; nothing here settles one.

Pinned: the default is None; None is byte-identical (md5 of the three
flat-lane goldens with the cap off, as `test_small_dot_rung.py` pins them,
and of two default-config plans WITH the bean cap, measured on origin/main
dcc54a11 before this change); ON re-spaces only `role=edge_cap` runs and
leaves every other run, the run tier's included, as it was; the satin cap
ignores it.
"""
from __future__ import annotations

import hashlib
import json
import math

import pytest
from shapely.geometry import Point, box

from digitizer_core import PipelineConfig, digitize, machine, stitches
from digitizer_core.stage6_border import run_outline, silhouette_cap

from .conftest import TESTDATA


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def _coords(plan):
    return [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
            for _, r in plan.iter_runs() for x, y in r.points]


def _steps(runs):
    return [math.dist(p, q) for r in runs for p, q in zip(r.points, r.points[1:])
            if math.dist(p, q) > 1e-9]


def test_default_is_off_and_the_constant_is_untouched():
    assert PipelineConfig().edge_cap_bean_pitch_mm is None
    assert machine.BEAN_STITCH_MM == 0.73
    assert machine.BEAN_PASSES == 3


# --- the emitters -------------------------------------------------------------------

def test_run_outline_none_is_the_constant():
    ring = Point(0, 0).buffer(4.0, 64)
    a, _ = run_outline(ring, "s", entry=(5.0, 0.0), trim_at_mm=3.0)
    for off in (None, 0.0, -1.0, machine.BEAN_STITCH_MM):
        b, _ = run_outline(ring, "s", entry=(5.0, 0.0), trim_at_mm=3.0, stitch_mm=off)
        assert [r.points for r in a] == [r.points for r in b]


@pytest.mark.parametrize("pitch", [1.0, 1.2, 1.5])
def test_run_outline_spaces_stations_at_the_pitch(pitch):
    ring = Point(0, 0).buffer(4.0, 64)
    runs, rep = run_outline(ring, "s", entry=None, trim_at_mm=3.0, stitch_mm=pitch)
    assert rep["loops"] == 1
    n = max(3, round(ring.exterior.length / pitch))
    assert len(runs[0].points) == n * machine.BEAN_PASSES + 1
    steps = _steps(runs)
    assert pitch * 0.9 <= sorted(steps)[len(steps) // 2] <= pitch * 1.1


def test_silhouette_cap_bean_takes_the_pitch_and_satin_ignores_it():
    poly = box(0, 0, 30, 20)
    off, _ = silhouette_cap(poly, "S", style="bean", entry=None, trim_at_mm=3.0)
    on, rep = silhouette_cap(poly, "S", style="bean", entry=None, trim_at_mm=3.0,
                             bean_stitch_mm=1.5)
    assert all(r.role == stitches.ROLE_EDGE_CAP for r in on) and rep["style"] == "bean"
    assert sum(map(len, (r.points for r in on))) < 0.6 * sum(map(len, (r.points for r in off)))
    assert max(_steps(on)) <= 1.5 * 1.05
    s_off, _ = silhouette_cap(poly, "S", style="satin", entry=None, trim_at_mm=3.0)
    s_on, _ = silhouette_cap(poly, "S", style="satin", entry=None, trim_at_mm=3.0,
                             bean_stitch_mm=1.5)
    assert [r.points for r in s_off] == [r.points for r in s_on]


def test_the_gate_still_cuts_at_the_new_pitch():
    """An `omit` stretch is still dropped: the gate judges the new stations."""
    poly = box(0, 0, 30, 20)
    omit = box(-1, -1, 31, 1)            # the bottom edge is already sewn
    runs, rep = silhouette_cap(poly, "S", style="bean", entry=None, trim_at_mm=3.0,
                               omit=omit, bean_stitch_mm=1.5)
    assert rep["yielded"] == 1 and rep["arcs"] >= 1
    assert not any(y < 0.5 for r in runs for _x, y in r.points)


# --- the whole pipeline: OFF byte-identical, ON moves the cap only ----------------------

# The flat-lane goldens' stitch streams with the cap off (`test_small_dot_rung.py`).
GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}

# Default config (the bean cap ON) at 80 mm, measured on origin/main dcc54a11
# before this change and on this branch with the knob None: equal.
CAP_OFF_MD5 = {
    "logo_alpha.png": "4dcdb09e4982ab02544e29d38e6cf1e7",
    "logo_whitebg.png": "298d30eb9815f36d33964ff32c897d9e",
}


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("pitch", [None, 1.5])
def test_cap_off_goldens_are_byte_identical_either_way(fixture, pitch):
    """With no cap the knob has nothing to touch -- and logo_alpha and
    logo_whitebg each sew two run-tier runs, which stay put at 1.5."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       edge_cap_bean_pitch_mm=pitch))
    assert _md5(_coords(plan)) == GOLDEN_MD5[fixture]


@pytest.mark.parametrize("fixture", sorted(CAP_OFF_MD5))
def test_bean_cap_off_is_byte_identical_and_on_moves_only_the_cap(fixture):
    _r, off = digitize(TESTDATA / fixture, PipelineConfig(target_width_mm=80.0))
    assert _md5(_coords(off)) == CAP_OFF_MD5[fixture]
    _r, on = digitize(TESTDATA / fixture,
                      PipelineConfig(target_width_mm=80.0, edge_cap_bean_pitch_mm=1.5))
    assert _md5(_coords(on)) != CAP_OFF_MD5[fixture]

    def split(plan):
        cap = [r for _, r in plan.iter_runs() if r.role == stitches.ROLE_EDGE_CAP]
        rest = [(r.kind, r.role, r.jump, r.trim, r.points)
                for _, r in plan.iter_runs() if r.role != stitches.ROLE_EDGE_CAP]
        return cap, rest

    cap_off, rest_off = split(off)
    cap_on, rest_on = split(on)
    assert rest_on == rest_off
    assert stitches.RUN in {k for k, *_ in rest_on}       # the run tier, untouched
    assert len(cap_on) == len(cap_off)
    med = sorted(_steps(cap_on))[len(_steps(cap_on)) // 2]
    assert 1.35 <= med <= 1.55
    assert on.stats.stitch_count < off.stats.stitch_count
