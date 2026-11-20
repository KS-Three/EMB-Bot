"""`cfg.extra["dark_ink_bean_by_core"]` (built OFF 2026-11-19).

The Nevada seal at 90 mm: bold serif ring letters and solid stars on a gold
ring are dark ink; judged by mean width (2 x area / perimeter) the group
read 0.51 mm -- serifs and star points are long outline round little ink --
and every stroke sewed as a one-line bean. Their CORE (the widest circle
inside each) reads 1.18. ON, `bean_dark_ink(by_width=True)` gates a group
on its median core width against two minimum satin crosses.
"""
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import machine
from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.regions import Region
from digitizer_core.thin_ink import (DARK_INK_BEAN_MAX_CORE_MM, DARK_INK_BEAN_MAX_WIDTH_MM,
                                     DARK_INK_CORE_MIN_STROKES, _core_width_mm, bean_dark_ink)

LINE = DARK_INK_CORE_MIN_STROKES


def _reg(sid, poly, thread, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": 1, **meta})


def _star(cx, cy, r_out=1.0, r_in=0.45):
    import math
    pts = [(cx + (r_out if i % 2 == 0 else r_in) * math.sin(math.pi * i / 5),
            cy + (r_out if i % 2 == 0 else r_in) * math.cos(math.pi * i / 5)) for i in range(10)]
    return Polygon(pts)


def _serif_i(x):
    """A bold stem (1.1 mm) with hairline serifs (0.15 mm) top and bottom."""
    return unary_union([box(x, 0.3, x + 1.1, 3.7),
                        box(x - 0.9, 0.0, x + 2.0, 0.3), box(x - 0.9, 3.7, x + 2.0, 4.0)])


def _seal(shapes):
    ground = box(-5, -5, 4.0 * len(shapes) + 5, 10)
    for s in shapes:
        ground = ground.difference(s)
    return [_reg("Sground", ground, 0)] + [
        _reg(f"S{i}", s, 5, dark_ink=True) for i, s in enumerate(shapes)]


def test_the_gate_is_two_satin_crosses():
    assert DARK_INK_BEAN_MAX_CORE_MM == 2.0 * machine.SATIN_MIN_CROSS_MM


def test_a_solid_star_reads_thin_by_mean_and_bold_by_core():
    star = _star(0, 0)
    assert 2 * star.area / star.length < DARK_INK_BEAN_MAX_WIDTH_MM
    assert _core_width_mm(star) >= DARK_INK_BEAN_MAX_CORE_MM * 0.8


def test_off_serif_letters_bean_on_they_do_not():
    letters = [_serif_i(4.0 * i) for i in range(LINE)]
    assert all(2 * p.area / p.length < DARK_INK_BEAN_MAX_WIDTH_MM for p in letters)
    off = _seal(letters)
    bean_dark_ink(off, by_width=True)
    assert all(r.meta.get(BEAN_LETTER_KEY) for r in off[1:])
    on = _seal(letters)
    bean_dark_ink(on, by_width=True, by_core=True)
    assert not any(r.meta.get(BEAN_LETTER_KEY) for r in on[1:])


def test_on_a_pen_line_still_beans():
    """NOAA-like strokes: 0.45 mm lines, core under the gate."""
    lines = [box(4.0 * i, 0.0, 4.0 * i + 0.45, 4.0) for i in range(LINE)]
    on = _seal(lines)
    bean_dark_ink(on, by_width=True, by_core=True)
    assert all(r.meta.get(BEAN_LETTER_KEY) for r in on[1:])


def test_a_small_group_keeps_the_mean_width():
    """Hotel Fremont's EAT | STAY | PLAY (6 strokes) turned to blobs read by core."""
    letters = [_serif_i(4.0 * i) for i in range(LINE - 1)]
    on = _seal(letters)
    bean_dark_ink(on, by_width=True, by_core=True)
    assert all(r.meta.get(BEAN_LETTER_KEY) for r in on[1:])


def test_core_width_of_a_disc_is_its_diameter():
    assert abs(_core_width_mm(Point(0, 0).buffer(1.0, 64)) - 2.0) < 0.05


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("dark_ink_bean_by_core")
