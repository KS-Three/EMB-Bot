"""`cfg.text_cluster_wide_letters` (2026-10-23, built OFF): a wide letter
reaches the text tagger. MFab's W of WELDING at 104.9 mm never reached the
Column lane: its right vertex touches the E's foot through the keyline, so
W and E traced as one 17.5 x 6.9 mm region (aspect 2.55), and the W alone is
still aspect 1.58 -- both past the letter door's `ASPECT_RATIO_MAX` 1.4.

ON: `_neck_split` cuts a too-wide region at a neck under a quarter of its
stroke and the pieces replace it only when every one is tagged with a line;
`_adopt_wide` lets a glyph up to `WIDE_LETTER_ASPECT_MAX` join a line it
links to, never make one. OFF: neither runs, byte for byte.
"""
from __future__ import annotations

import hashlib
import inspect
import json

import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize
from digitizer_core import textcluster as tc
from digitizer_core.regions import Region

from .conftest import TESTDATA


def _region(sid: str, poly) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=float(poly.area))


def _ell(x0: float, w: float = 4.0, h: float = 6.0, t: float = 1.0) -> Polygon:
    """An L: stem at x0, foot along the bottom (y down: the foot at y=h)."""
    return unary_union([box(x0, 0.0, x0 + t, h), box(x0, h - t, x0 + w, h)])


def _bar(x0: float, h: float = 6.0, t: float = 1.0) -> Polygon:
    return box(x0, 0.0, x0 + t, h)


def _wide_u(x0: float, w: float = 9.6, h: float = 6.0, t: float = 1.0) -> Polygon:
    """A U 1.6 times as wide as it is tall: two stems and a floor."""
    return unary_union([box(x0, 0.0, x0 + t, h), box(x0 + w - t, 0.0, x0 + w, h),
                        box(x0, h - t, x0 + w, h)])


def _pinched_pair(x0: float) -> Polygon:
    """Two L's 0.5 mm apart whose foot tip touches the next stem through a
    0.05 mm neck: one region, aspect 8.5 / 6 = 1.42."""
    return unary_union([_ell(x0), _ell(x0 + 4.5), box(x0 + 3.9, 5.2, x0 + 4.6, 5.25)])


def _line(*extra: Region) -> list[Region]:
    return [_region(f"B{i}", _bar(20.0 + 3.0 * i)) for i in range(3)] + list(extra)


# --- the neck split -------------------------------------------------------------

def test_a_pinched_pair_splits_into_two_pieces_that_tile_it():
    pair = _pinched_pair(0.0)
    assert pair.geom_type == "Polygon"
    pieces = tc._neck_split(pair, 0.5)
    assert pieces is not None and len(pieces) == 2
    assert pieces[0].bounds[0] < pieces[1].bounds[0]          # left to right
    assert abs(sum(p.area for p in pieces) - pair.area) < 1e-9
    assert unary_union(pieces).symmetric_difference(pair).area < 1e-9
    for p, want in zip(pieces, (_ell(0.0), _ell(4.5))):
        assert p.symmetric_difference(want).area < 0.06       # the neck goes to one side


def test_no_neck_no_split_and_a_stroke_is_not_a_neck():
    assert tc._neck_split(_ell(0.0), 0.5) is None
    assert tc._neck_split(_wide_u(0.0), 0.5) is None
    # a 0.4 mm bridge on a 1 mm stroke: wider than a quarter of the stroke
    joined = unary_union([_ell(0.0), _ell(4.5), box(3.9, 5.0, 4.6, 5.4)])
    assert tc._neck_split(joined, 0.5) is None


# --- the tagger -----------------------------------------------------------------

def _tagged(regions):
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


def test_off_the_pinched_pair_stays_one_untagged_region():
    regions = _line(_region("P", _pinched_pair(10.0)))
    tc.detect_text_clusters(regions, None)
    tags = _tagged(regions)
    assert set(tags) == {"B0", "B1", "B2", "P"}
    assert tags["P"] is None and tags["B0"] is not None


def test_on_the_pair_becomes_two_letters_of_the_line():
    regions = _line(_region("P", _pinched_pair(10.0)))
    tc.detect_text_clusters(regions, None, wide_letters=True)
    assert "P" not in {r.shape_id for r in regions}
    pieces = [r for r in regions if r.meta.get("neck_split_from") == "P"]
    assert len(pieces) == 2
    line = {r.meta.get("text_cluster_id") for r in regions}
    assert len(line) == 1 and None not in line
    assert abs(sum(r.polygon.area for r in pieces) - _pinched_pair(10.0).area) < 1e-9
    assert len({r.shape_id for r in regions}) == len(regions)


def test_on_a_split_with_no_line_is_undone():
    """Alone, the pieces cannot make a line of three: the region stays whole."""
    regions = [_region("P", _pinched_pair(10.0))]
    tc.detect_text_clusters(regions, None, wide_letters=True)
    assert [r.shape_id for r in regions] == ["P"]
    assert "text_cluster_id" not in regions[0].meta


def test_on_a_wide_glyph_joins_its_line_but_never_makes_one():
    u = _wide_u(10.0)
    x0, y0, x1, y1 = u.bounds
    assert tc.ASPECT_RATIO_MAX < (x1 - x0) / (y1 - y0) <= tc.WIDE_LETTER_ASPECT_MAX
    off = _line(_region("U", u))
    tc.detect_text_clusters(off, None)
    assert _tagged(off)["U"] is None
    on = _line(_region("U", _wide_u(10.0)))
    tc.detect_text_clusters(on, None, wide_letters=True)
    tags = _tagged(on)
    assert tags["U"] is not None and tags["U"] == tags["B0"]
    # three wide glyphs and one bar: no line of three ordinary letters
    alone = [_region(f"U{i}", _wide_u(12.0 * i)) for i in range(3)] + [_region("B", _bar(40.0))]
    tc.detect_text_clusters(alone, None, wide_letters=True)
    assert all(v is None for v in _tagged(alone).values())


def test_on_past_the_wide_bound_is_still_refused():
    u = _wide_u(10.0, w=11.4)                                  # aspect 1.9
    regions = _line(_region("U", u))
    tc.detect_text_clusters(regions, None, wide_letters=True)
    assert _tagged(regions)["U"] is None


# --- wiring and OFF ---------------------------------------------------------------

def test_the_flag_is_on_and_the_pipeline_passes_nothing_when_off():
    # ON by default since 2026-10-24 (Kent, the flip sheet); the function's own
    # default stays off, so a caller that passes nothing gets the old door
    assert PipelineConfig().text_cluster_wide_letters is True
    assert inspect.signature(tc.detect_text_clusters).parameters["wide_letters"].default is False
    from digitizer_core import pipeline
    src = inspect.getsource(pipeline)
    assert '**({"wide_letters": True} if cfg.text_cluster_wide_letters else {})' in src


GOLDEN_MD5 = {
    "logo_alpha.png": "554e898c04a65643c086b43be64b9e2c",
    "logo_whitebg.png": "d53de4bbf6881dc8465caec31e93e7c9",
    "ribbon_curve.png": "98bf128674db0f829a210f32264318e6",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("on", [False, True])
def test_goldens_are_byte_identical_off_and_on(fixture, on):
    """OFF is the engine as it was. ON too: the three flat goldens carry no
    wide or pinched letter, so there is nothing to split or adopt."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            text_cluster_wide_letters=on))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
