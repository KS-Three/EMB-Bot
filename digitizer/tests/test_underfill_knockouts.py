"""Two `silhouette_underfill` defects the MFab recipe showed on other jobs
(2026-10-26, recipe bystander run over 20 paired jobs).

* Fremont hat: the white star (0.22 mm2) inside the black state is a white
  shape of the ground's colour. Merged into the white under-fill, it was sewn
  over by the state's black fill; with the under-fill off it sews on its own,
  on top. A shape of the under-fill's colour that inner shapes of OTHER colours
  cover is no longer merged (`COVERED_KEEP_MIN`). MFab's black letters, in the
  HOLES of the white keyline field, still merge.
* Becker (all five jobs): a LETTER hosts the under-fill and filled the black
  ring's whole outline. On the lower band the ring's art runs 2-4 mm past the
  loops `border_from_outline` sews round the letters, so the white rows ran
  past the black, and the edge cap took the white's thread there. The letter
  host now fills no further than the loops reach, less half a loop width
  (`LETTER_HOST_INSET_W`), pulled in at the outer edge only so the fill stays
  one piece across the bars between letters.
"""
from __future__ import annotations

from types import SimpleNamespace

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import silhouette_underfill as su
from tests.test_silhouette_underfill import _holed, _reg, becker, mfab


def fremont():
    """A white ground round a black state that holds a white star in its
    fill, and a white mark of its own (not covered)."""
    state, star, mark = box(12, 6, 38, 24), box(20, 12, 21, 13), box(40, 10, 48, 20)
    return [_reg("Sstate", state, 1, 1), _reg("Sstar", star, 0, 2), _reg("Smark", mark, 0, 1),
            _reg("Sground", _holed(box(0, 0, 60, 30), box(10, 5, 50, 25)), 0, 0)]


def test_a_mark_another_colour_covers_is_never_merged():
    (ring, host, _o, merged, _i), = su.plan(fremont())
    assert ring.shape_id == host.shape_id == "Sground"
    assert "Sstar" not in merged
    # a mark of the ground's colour nothing covers merges as before
    assert "Smark" in merged
    out, _ = su.apply(fremont())
    assert "Sstar" in {r.shape_id for r in out}


def test_mfab_letters_in_the_fields_holes_still_merge():
    (_r, host, _o, merged, _i), = su.plan(mfab())
    assert host.shape_id == "Sring" and sorted(merged) == ["Sl1", "Sl2"]


W = 2.0


def _becker_with_a_shadow():
    """Becker's ring round two white letters (more white than black: a letter
    hosts), its lower band drawn 6 mm deep (a drop shadow) where the loops
    round the letters reach `W`; the bar between the letters is 2 mm."""
    b1, b2 = box(2, 2, 29, 22), box(31, 2, 58, 22)
    ring = _holed(box(0, 0, 60, 28), b1, b2)
    return [_reg("Sb1", b1, 1, 0), _reg("Sb2", b2, 1, 0), _reg("Sring", ring, 0, 1)], b1, b2


def test_without_outlines_a_letter_host_fills_the_whole_outline_as_before():
    regs, _b1, _b2 = _becker_with_a_shadow()
    (_r, host, outline, _m, _i), = su.plan(regs)
    assert host.shape_id == "Sb1"
    assert abs(outline.area - 60 * 28) < 1e-6


def test_a_letter_host_fills_no_further_than_the_loops_reach():
    regs, b1, b2 = _becker_with_a_shadow()
    outlines = {"Sring": [("Sb1", b1, W), ("Sb2", b2, W)]}
    (_r, host, outline, _m, _i), = su.plan(regs, outlines=outlines)
    assert host.shape_id == "Sb1"
    loops = unary_union([b1.buffer(W), b2.buffer(W)])
    # inside the loops' reach, pulled in by half a width at the outer edge ...
    assert outline.difference(loops.buffer(-0.5 * W + 1e-6)).area < 1e-3
    # ... so none of the shadow: the loops end 24 mm down, the white at 23
    assert outline.intersection(box(0, 23.0 + 1e-3, 60, 28)).area < 1e-6
    # ... the letters whole, and one piece across the 2 mm bar between them
    assert outline.contains(b1) and outline.contains(b2)
    assert outline.geom_type == "Polygon"


def test_a_ring_host_is_never_clipped():
    # MFab: the ring hosts its own under-fill and covers its outline itself
    regs = mfab()
    ring = next(r for r in regs if r.shape_id == "Sring")
    outlines = {"Sring": [("Skey", Polygon(h), 1.0) for h in ring.polygon.interiors]}
    (_r, host, outline, _m, _i), = su.plan(regs, outlines=outlines)
    assert host.shape_id == "Sring"
    assert abs(outline.area - 60 * 24) < 1e-6


def test_apply_cfg_hands_the_outlines_to_the_plan_without_riders():
    regs, b1, b2 = _becker_with_a_shadow()
    outlines = {"Sring": [("Sb1", b1, W), ("Sb2", b2, W)]}
    cfg = SimpleNamespace(silhouette_underfill_panels=False, sew_enclosed_white=True,
                          border_from_outline=True, overlap_mm=0.3)
    out, report, outl = su.apply_cfg(regs, (), cfg, outlines)
    assert outl is outlines
    host = next(r for r in out if r.shape_id == "Sb1")
    assert host.meta[su.UNDERFILL_KEY].area < 60 * 28 - 100
    assert report[0]["outline_mm2"] < 60 * 28 - 100


def test_the_becker_fixture_without_outlines_is_unchanged():
    (_r, host, outline, merged, _i), = su.plan(becker())
    assert (host.shape_id, merged) == ("Sb1", ["Sb2"])
    assert abs(outline.area - 60 * 24) < 1e-6
