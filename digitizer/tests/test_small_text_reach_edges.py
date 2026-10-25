"""`cfg.small_text_cap_reach_edges` (2026-10-24, L8, built OFF): the re-set
(`small_text_cap_letter_gap_mm`) reaches the two kinds of small line it
refused as `no_room`.

The census (`tools/small_text_floor_census.py`, one reader on both machine
files, each in its own frame) found the professional sews NO line under ~4 mm
as drawn, as a run or not at all. ProSeal's "SPRAY FOAM + COATINGS" goes
3.0 -> 4.55 mm satin on the 86 mm hat and 2.6 -> 4.0 on the 75 mm beanie; the
re-set left both as 3 mm bean lines, `no_room`, blocked by `design_edge` (the
line sits on the design's bottom edge, and the 0.8 mm clearance halo was
asked to fit inside it) and, for SPRAY, by its own A (traced in a thread of
its own, so in no cluster and in the way).

The synthetic scene is `tests/test_small_text.py`'s: tan 2 mm lettering on a
white raster, one solid polygon per glyph as the tracer hands them over.
"""
from __future__ import annotations

import hashlib

from shapely.geometry import box

from digitizer_core import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.small_text import enlarge_small_text
from tests.test_small_text import _glyphs, _scene, _tag
from tests.test_small_text_reset import KW, _heights

#: md5 of `_edge_scene()` re-set WITHOUT the flag -- regions and report --
#: captured on main's engine (25e11ed7), before this flag existed.
OFF_MD5 = "a0c2fe9ab779cee0c486d16dfc4228c4"


#: the rule over the line, as far above it as ProSeal's teal bar (1.85 mm
#: over a 3.0 mm line on the 86 mm hat), scaled to the scene's 1.7 mm cap
BAR_GAP_MM = 2.0


def _edge_scene():
    """The 1895 line standing ON the design's bottom edge -- the ground it
    sits on ends where the letters do, as ProSeal's tagline ends its design
    -- with a rule across the design above it, so it cannot just move up."""
    regions, p = _scene()
    g = _glyphs(regions)
    bottom = max(r.polygon.bounds[3] for r in g)
    top = min(r.polygon.bounds[1] for r in g)
    base = next(r for r in regions if r.shape_id == "Sbase")
    base.polygon = box(-20, -10, 20, bottom)
    regions.append(Region("Srule", box(-20, top - BAR_GAP_MM - 0.5, 20, top - BAR_GAP_MM), 2, "2", 20.0))
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    return regions, p, bottom


def _md5(regions, rep) -> str:
    h = hashlib.md5()
    for r in regions:
        h.update(repr((r.shape_id, r.thread_index, r.polygon.wkb.hex(), sorted(r.meta.items()))).encode())
    h.update(repr(rep).encode())
    return h.hexdigest()


# --- OFF -------------------------------------------------------------------------

def test_on_by_default():
    # Kent's flip 2026-10-24 (wave-2 flip sheet, PR #1069); inert while the
    # re-set (`small_text_cap_letter_gap_mm`) is unset
    assert PipelineConfig().small_text_cap_reach_edges is True


def test_off_is_byte_identical_to_main():
    a, p, _ = _edge_scene()
    rep_a = enlarge_small_text(a, p, **KW)
    b, p, _ = _edge_scene()
    rep_b = enlarge_small_text(b, p, **KW, reach_edges=False)
    assert _md5(a, rep_a) == _md5(b, rep_b) == OFF_MD5


def test_off_a_line_on_the_design_edge_has_no_room():
    regions, p, _ = _edge_scene()
    row = next(r for r in enlarge_small_text(regions, p, **KW) if r["cluster"] == "TCtest")
    assert row.get("skipped") == "no_room" and "design_edge" in row["blocked_by"], row


# --- ON --------------------------------------------------------------------------

def test_on_a_line_on_the_design_edge_grows_inside_it():
    regions, p, bottom = _edge_scene()
    row = next(r for r in enlarge_small_text(regions, p, **KW, reach_edges=True) if r["cluster"] == "TCtest")
    assert "skipped" not in row, row
    hs = _heights(regions)
    assert abs(sorted(hs)[len(hs) // 2] - KW["cap_mm"]) < 0.4, hs
    # past the edge by at most half the growth: the line grew about its centre
    cap = row["cap_mm"]
    assert max(r.polygon.bounds[3] for r in _glyphs(regions)) <= bottom + 0.5 * (row["scale"] - 1) * cap + 1e-6
    # and still clear of the rule above by the halo
    rule = next(r for r in regions if r.shape_id == "Srule")
    assert min(r.polygon.distance(rule.polygon) for r in _glyphs(regions)) >= 0.8 - 1e-6


def test_on_a_letter_of_another_thread_inside_the_line_joins_it():
    regions, p = _scene()
    g = _glyphs(regions)
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    g[1].thread_index, g[1].thread_id = 9, "9"          # ProSeal's A of SPRAY
    off = next(r for r in enlarge_small_text(regions, p, **KW) if r["cluster"] == "TCtest")
    assert g[1].meta.get("small_text_enlarged") is None, off
    regions, p = _scene()
    g = _glyphs(regions)
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    g[1].thread_index, g[1].thread_id = 9, "9"
    row = next(r for r in enlarge_small_text(regions, p, **KW, reach_edges=True) if r["cluster"] == "TCtest")
    assert row.get("joined") == 1 and row["letters"] == 4, row
    assert g[1].meta.get("small_text_enlarged") == row["scale"] and g[1].thread_index == 9
    hs = _heights(regions)
    assert max(hs) - min(hs) < 0.5


def test_on_a_bar_inside_the_line_is_not_joined_as_a_letter():
    regions, p, _ = _edge_scene()
    g = _glyphs(regions)
    y0 = min(r.polygon.bounds[1] for r in g)
    y1 = max(r.polygon.bounds[3] for r in g)
    x = 0.5 * (g[1].polygon.bounds[2] + g[2].polygon.bounds[0])
    regions.append(Region("Sbar", box(x - 0.1, y0, x + 0.1, y1), 3, "3", 0.4))
    rep = enlarge_small_text(regions, p, **KW, reach_edges=True)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert row.get("joined") is None, row
