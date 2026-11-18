"""Script strokes' pull read off each stroke's own width
(`cfg.script_strokes_pull_by_stroke`, built OFF 2026-11-18).

`pull_comp_by_stroke` reads the Column lane's letters; a script word took the
preset's fixed pull on every rail. On Tires' 4.7 mm pen that is 0.4 mm into
each counter. ON, a script stroke's rails get `columns.pull_for_width` of its
own width, never above the preset's pull, on the hat / LC / beanie presets.
OFF is byte-identical (the md5 below is the engine on main, 2026-11-18).
"""
from __future__ import annotations

from shapely.affinity import scale
import math

from shapely.geometry import Point, box

from digitizer_core import PipelineConfig
from digitizer_core import script_strokes as SS
from digitizer_core.fabrics import fabric_for_garment, pull_by_stroke_for
from tests.test_script_strokes import LOOPS, _md5, _runs

PULL = 0.4
WIDE = box(0, 0, 30, 4.7)
THIN = box(0, 0, 30, 0.85)


def _y_reach(poly, **kw):
    runs, _ = SS.script_strokes_shape(poly, "Sword", trim_at_mm=3.0, spacing_mm=0.4, pull_mm=PULL, **kw)
    ys = [p[1] for r in runs if str(r.kind).endswith("satin") for p in r.points[10:-10]]
    return min(ys), max(ys)


def test_default_off():
    assert PipelineConfig().script_strokes_pull_by_stroke is False


def test_off_is_byte_identical():
    assert _md5(_runs(LOOPS)) == _md5(_runs(LOOPS, script_strokes_pull_by_stroke=False))


def test_a_wide_stroke_gets_less_pull():
    lo0, hi0 = _y_reach(WIDE)
    lo1, hi1 = _y_reach(WIDE, pull_by_stroke=True)
    assert (hi1 - lo1) < (hi0 - lo0) - 0.3          # about 0.15 mm a side less on 4.7 mm
    assert 4.3 < hi1 - lo1 < 4.8                    # the drawn 4.7 mm, not 4.7 + 0.8
    assert hi0 - lo0 > 5.2                          # OFF: 0.4 mm past each edge


def test_a_thin_stroke_keeps_the_presets_pull():
    a, b = _y_reach(THIN), _y_reach(THIN, pull_by_stroke=True)
    assert abs((a[1] - a[0]) - (b[1] - b[0])) < 0.15


def test_only_the_by_stroke_presets_read_it():
    assert pull_by_stroke_for(fabric_for_garment("hat_front"), True)
    assert not pull_by_stroke_for(fabric_for_garment("hat_front"), False)


def test_flag_reaches_the_sequencer():
    fat = scale(LOOPS, 3.0, 3.0)                    # the same word drawn with a 3x pen
    on = _md5(_runs(fat, script_strokes_pull_by_stroke=True))
    assert on != _md5(_runs(fat, script_strokes_pull_by_stroke=False))


# ------------------------------------------------------- "counter" mode
RING = Point(0, 0).buffer(8.0).difference(Point(0, 0).buffer(3.3))      # a 4.7 mm pen round a counter


def _radii(**kw):
    runs, _ = SS.script_strokes_shape(RING, "Sword", trim_at_mm=3.0, spacing_mm=0.4, pull_mm=PULL, **kw)
    r = [math.hypot(*p) for run in runs if str(run.kind).endswith("satin") for p in run.points]
    return min(r), max(r)


def test_counter_mode_keeps_the_outer_pull_and_spares_the_counter():
    off_in, off_out = _radii()
    on_in, on_out = _radii(pull_by_stroke="counter")
    assert abs(on_out - off_out) < 0.02              # the outer rail keeps the full pull
    assert on_in > off_in + 0.2                      # the counter-facing rail reaches less far in
