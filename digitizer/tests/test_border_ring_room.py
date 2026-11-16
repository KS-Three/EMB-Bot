"""`cfg.border_significant_ring_room` (2026-11-14, ON since Kent's 2026-11-15
flip, "Both ON, keep 5.0"; PRE_FLIP pins it OFF): the photo
lanes' "significant" border earns no ring where the ring has no room for a
column (`stage6_border.ring_has_room`, `stage7_sequence._border_wanted`'s
`room`).

Kent's MFab pin "random stitch in the middle": MFab classes `photo_scene`, so
"significant" borders its shapes. The A's counter, a 3.35 mm white triangle,
is too narrow for the 1.7 mm border column, and the ring lightened to a
three-pass bean loop 0.85 mm inside the counter's own fill, on top of it.
It covers no edge. The pro sews the counter as one piece. With the flag on,
MFab hat at 104.9 mm changes on that one shape only: the loop is gone and the
fill stays (`eye_pairs_out/mfab-triangle-1114/`).
"""
from __future__ import annotations

import inspect

from shapely.geometry import Polygon, box

from digitizer_core import stage7_sequence as s7
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_border import border_runs, ring_has_room
from tests.conftest import PRE_FLIP

#: MFab's A counter at 104.9 mm, near enough: a 5.5 x 6 mm right triangle, its
#: inscribed circle 3.35 mm across (the column ring needs 3.8: 2 x (0.85 + 0.85 + 0.2))
COUNTER = Polygon([(0, 6.0), (5.5, 6.0), (5.5, 0.0)])
FIELD = box(0, 0, 30, 20)


def _region(poly, **meta):
    return Region("S1", poly, 1, "1", float(poly.area), meta=dict(meta))


def test_room_reads_the_rings_own_geometry():
    assert ring_has_room(FIELD) is True
    assert ring_has_room(COUNTER) is False
    assert ring_has_room(box(0, 0, 30, 1.2)) is False         # a strip: no centreline, or no core
    # the same verdict the emitter reaches: no room <-> no column ring, only a bean
    runs, rep = border_runs(COUNTER, "S1", entry=None, trim_at_mm=2.0)
    assert rep["loops"] == 0 and rep["arcs"] == 0
    runs, rep = border_runs(FIELD, "S1", entry=None, trim_at_mm=2.0)
    assert rep["loops"] + rep["arcs"] > 0


def test_significant_earns_no_ring_without_room():
    args = ("significant", FIELD.area + COUNTER.area, 0.0, 3.5)
    assert s7._border_wanted(_region(COUNTER), *args)[0] is True          # today: earned
    assert s7._border_wanted(_region(COUNTER), *args, room=lambda: ring_has_room(COUNTER))[0] is False
    assert s7._border_wanted(_region(FIELD), *args, room=lambda: ring_has_room(FIELD))[0] is True


def test_per_shape_intent_still_beats_the_room_test():
    args = ("significant", FIELD.area, 0.0, 3.5)
    never = lambda: False  # noqa: E731
    assert s7._border_wanted(_region(COUNTER, border=True), *args, room=never)[0] is True
    assert s7._border_wanted(_region(COUNTER, border="bean"), *args, room=never) == (True, "bean")


def test_other_modes_never_read_the_room():
    def boom():
        raise AssertionError("room read outside the significant mode")
    for mode in ("auto", "off", "bean"):
        s7._border_wanted(_region(COUNTER), mode, 1.0, 0.0, 3.5, room=boom)


def test_both_readers_pass_the_same_room_and_only_under_the_flag():
    """The seam-ownership prediction and the border block read
    `_border_wanted` alike (its docstring's rule), and neither passes `room`
    unless `ring_room` (the flag, on a significant plan) is set."""
    src = inspect.getsource(s7)
    assert src.count("functools.partial(ring_has_room,") == 2
    assert src.count("if ring_room else {}") == 2
    assert "bool(cfg.border_significant_ring_room)" in src


def test_flag_is_on_and_pinned_off():
    """Kent's flip 2026-11-15 ("Both ON, keep 5.0"): the default is ON; the
    OFF arm, the border as it was, is pinned in `tests/conftest.py`."""
    assert PipelineConfig().border_significant_ring_room is True
    assert PRE_FLIP["border_significant_ring_room"] is False
