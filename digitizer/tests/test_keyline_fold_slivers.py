"""`cfg.keyline_fold_slivers` (built OFF 2026-10-26): a sewn white field's
slivers fold back into it.

MFab's keyline is drawn with a dark hairline along its inner edge, so the
tracer returns the field plus 31 (hat) / 51 (LC) white slivers 0.1-0.3 mm wide
on the letters' side of it, each its own run with a cut either side; the pro's
keyline satin covers every one (`docs/mfab-recipe-trims-2026-10-26.md`). This
pins which pieces fold (the field's thread, not routed by `sew_enclosed_white`,
no text, under a thread wide, within a thread of the field) and what the fold
does to the field: one polygon, its hole moved onto the letter.
"""
from __future__ import annotations

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import machine
from digitizer_core.regions import Region
from digitizer_core.silhouette_underfill import FOLDED_KEY, fold_keyline_slivers

T = machine.COVERAGE_THREAD_W_MM
BODY = box(10, 10, 30, 30)                 # the letter: the field's hole


def _reg(sid, poly, thread=1, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(4000 + thread),
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _field(hole=box(9.0, 9.0, 31.0, 31.0)):
    return _reg("Sfield", Polygon(box(5, 5, 35, 35).exterior.coords, [hole.exterior.coords]),
                sew_enclosed_white="field")


def _sliver(sid="Ssliver", width=0.2, gap=0.15, thread=1, **meta):
    """A strip inside the field's hole along its left edge, `gap` in from it."""
    x1 = 9.0 + gap
    meta.setdefault("stitch_width_measured_mm", width)
    return _reg(sid, box(x1, 12, x1 + width, 28), thread=thread, **meta)


def test_a_sliver_folds_into_the_field_and_the_hole_moves_onto_it():
    f, s = _field(), _sliver()
    out, folded = fold_keyline_slivers([f, s, _reg("Sbody", BODY, thread=0)])
    assert folded == {"Sfield": ["Ssliver"]}
    assert [r.shape_id for r in out] == ["Sfield", "Sbody"]
    grown = out[0]
    assert grown.polygon.geom_type == "Polygon" and grown.meta[FOLDED_KEY] == ["Ssliver"]
    # the sliver and the strip between are field now: the hole lost them
    assert grown.polygon.covers(s.polygon)
    assert grown.polygon.area > f.polygon.area + s.polygon.area
    assert len(grown.polygon.interiors) == 1
    # copies: the input field is untouched
    assert f.polygon.area == _field().polygon.area


def test_what_does_not_fold():
    f = _field()
    cases = {
        "wide": _sliver(sid="Swide", width=0.5, stitch_width_measured_mm=T + 0.05),
        "far": _sliver(sid="Sfar", gap=T + 0.1),
        "text": _sliver(sid="Stext", text_cluster_id="TC1"),
        "routed": _sliver(sid="Scounter", sew_enclosed_white="counter_in_field"),
        "unsewn": _sliver(sid="Sunsewn", stitched=False),
        "unmeasured": _reg("Sbare", box(9.15, 12, 9.35, 28)),
        "colour": _sliver(sid="Sblack", thread=0),
    }
    for name, s in cases.items():
        out, folded = fold_keyline_slivers([f, s])
        assert folded == {}, name
        assert out == [f, s], name


def test_no_sewn_field_no_fold():
    plain = _reg("Sfield", _field().polygon)          # white, but not routed as a field
    s = _sliver()
    regs = [plain, s]
    out, folded = fold_keyline_slivers(regs)
    assert out is regs and folded == {}


def _c_sliver(pocket_w):
    """A C-shaped sliver 0.2 mm wide, open toward the field's left hole edge
    0.15 mm away: it closes a pocket `pocket_w` deep against the field."""
    x0, x1 = 9.15, 9.15 + pocket_w + 0.2
    c = unary_union([box(x0, 12.0, x1, 12.2), box(x0, 15.0, x1, 15.2),
                     box(x1 - 0.2, 12.0, x1, 15.2)])
    return _reg("Sc", c, stitch_width_measured_mm=0.2)


def test_a_slit_the_fold_closes_is_filled():
    f = _field()
    out, folded = fold_keyline_slivers([f, _c_sliver(0.2)])
    assert folded == {"Sfield": ["Sc"]}
    assert len(out[0].polygon.interiors) == 1           # the letter's hole only


def test_a_sliver_that_would_split_a_hole_does_not_fold():
    # a 1.5 mm pocket closed off would be a new hole: that sliver runs
    # across the hole, it does not hug the field's edge
    f = _field()
    out, folded = fold_keyline_slivers([f, _c_sliver(1.5)])
    assert folded == {} and len(out) == 2
    across = _reg("Sacross", box(9.0, 19.9, 31.0, 20.1), stitch_width_measured_mm=0.2)
    out, folded = fold_keyline_slivers([f, across])
    assert folded == {}


def test_two_slivers_both_fold():
    f = _field()
    a = _sliver(sid="Sa")
    b = _reg("Sb", box(12, 9.15, 28, 9.35), stitch_width_measured_mm=0.2)   # along the top edge
    out, folded = fold_keyline_slivers([f, a, b])
    assert sorted(folded["Sfield"]) == ["Sa", "Sb"]
    assert [r.shape_id for r in out] == ["Sfield"]
    assert out[0].polygon.covers(a.polygon) and out[0].polygon.covers(b.polygon)
