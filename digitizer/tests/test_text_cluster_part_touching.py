"""`cfg.text_cluster_part_touching` (2026-10-25, built OFF): two more ways a
letter misses the text tagger, both read on MFab's AND WELDING at the pro's
widths. The hat's I and N of WELDING touch at a neck under 0.08 mm and trace
as ONE region of aspect 1.03, which the letter door admits as one glyph (the
wide-letter neck split only looks past aspect 1.4). The face's N and G
overshoot the cap height: the left chest's AND N is 7.90 mm beside 6.25 mm
letters, a height ratio of 0.79 against `LETTER_HEIGHT_RATIO` 0.8, so it is
never tagged.

ON: the neck split looks at every letter-height region beside a line and
parts a touch narrower than `TOUCH_MAX_MM` into pieces each at least 0.8 of
the line's cap height; a glyph taller than a line member that spans its cap
band, down to `HEIGHT_BAND_MIN`, joins the line and never makes one
(`_adopt_band`). OFF: neither runs, byte for byte.
"""
from __future__ import annotations

import hashlib
import inspect
import json

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize
from digitizer_core import textcluster as tc
from digitizer_core.regions import Region

from .conftest import TESTDATA


def _region(sid: str, poly) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=float(poly.area))


def _bar(x0: float, y0: float = 0.0, h: float = 6.0, t: float = 1.0):
    return box(x0, y0, x0 + t, y0 + h)


def _ell(x0: float, w: float = 4.0, h: float = 6.0, t: float = 1.0):
    """An L: stem at x0, foot along the bottom (y down: the foot at y=h)."""
    return unary_union([box(x0, 0.0, x0 + t, h), box(x0, h - t, x0 + w, h)])


def _touching(x0: float, neck: float = 0.05):
    """An I and an L 0.6 mm apart whose tops touch through a `neck` mm
    sliver: one region 5.6 x 6 mm, aspect 0.93 -- the door admits it as ONE
    letter (MFab hat's IN of WELDING, aspect 1.03)."""
    return unary_union([_bar(x0), _ell(x0 + 1.6), box(x0 + 0.9, 0.0, x0 + 1.7, neck)])


def _tall(y0: float, h: float, x0: float = 10.0):
    """A glyph 4 mm wide, `h` tall, from `y0`: two stems and a top bar."""
    return unary_union([_bar(x0, y0, h), _bar(x0 + 3.0, y0, h), box(x0, y0, x0 + 4.0, y0 + 1.0)])


def _line(*extra: Region) -> list[Region]:
    """Three 6 mm bars, a line of lettering at cap height 6 (y 0..6)."""
    return [_region(f"B{i}", _bar(20.0 + 3.0 * i)) for i in range(3)] + list(extra)


def _tags(regions):
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


# --- the touch --------------------------------------------------------------------

def test_the_touching_pair_is_one_region_the_door_admits():
    pair = _touching(10.0)
    assert pair.geom_type == "Polygon"
    x0, y0, x1, y1 = pair.bounds
    assert (x1 - x0) / (y1 - y0) <= tc.ASPECT_RATIO_MAX        # the wide pass never sees it


def test_off_the_pair_is_tagged_as_one_letter():
    regions = _line(_region("P", _touching(10.0)))
    tc.detect_text_clusters(regions, None, wide_letters=True)
    tags = _tags(regions)
    assert set(tags) == {"B0", "B1", "B2", "P"}
    assert tags["P"] is not None and tags["P"] == tags["B0"]


def test_on_the_pair_becomes_two_letters_of_the_line():
    regions = _line(_region("P", _touching(10.0)))
    tc.detect_text_clusters(regions, None, wide_letters=True, part_touching=True)
    assert "P" not in {r.shape_id for r in regions}
    pieces = sorted((r for r in regions if r.meta.get("neck_split_from") == "P"),
                    key=lambda r: r.polygon.bounds[0])
    assert len(pieces) == 2
    for r, want in zip(pieces, (_bar(10.0), _ell(11.6))):
        assert r.polygon.symmetric_difference(want).area < 0.06     # the neck goes to one side
    assert abs(sum(r.polygon.area for r in pieces) - _touching(10.0).area) < 1e-9
    line = {r.meta.get("text_cluster_id") for r in regions}
    assert len(line) == 1 and None not in line
    assert len({r.shape_id for r in regions}) == len(regions)


def test_on_works_without_the_wide_pass_too():
    regions = _line(_region("P", _touching(10.0)))
    tc.detect_text_clusters(regions, None, part_touching=True)
    assert len([r for r in regions if r.meta.get("neck_split_from") == "P"]) == 2


def test_on_a_join_wider_than_the_touch_bound_stays_one_letter():
    # 0.3 mm of joint is a stroke, not a touch: over TOUCH_MAX_MM (0.15)
    regions = _line(_region("P", _touching(10.0, neck=0.3)))
    tc.detect_text_clusters(regions, None, wide_letters=True, part_touching=True)
    assert "P" in {r.shape_id for r in regions}
    assert _tags(regions)["P"] is not None


def test_on_a_spike_is_never_cut_off_its_letter():
    # an L with a 2 mm spike above it, joined through a 0.1 mm neck: the neck
    # opens, but the spike is not a letter-height piece, so nothing is offered
    spiked = unary_union([_ell(10.0), box(10.0, -2.2, 11.0, -0.05), box(10.45, -0.06, 10.55, 0.01)])
    assert spiked.geom_type == "Polygon"
    stats = tc._skeleton_stroke_stats(_region("S", spiked))
    assert len(tc._neck_split(spiked, stats.mean_mm, r_max=tc.TOUCH_MAX_MM / 2)) == 2
    regions = _line(_region("S", spiked))
    tc.detect_text_clusters(regions, None, wide_letters=True, part_touching=True)
    assert "S" in {r.shape_id for r in regions}


def test_on_a_split_with_no_line_is_undone():
    regions = [_region("P", _touching(10.0))]
    tc.detect_text_clusters(regions, None, part_touching=True)
    assert [r.shape_id for r in regions] == ["P"]
    assert "text_cluster_id" not in regions[0].meta


# --- the height band ---------------------------------------------------------------

def test_a_glyph_overshooting_the_cap_band_joins_its_line_on_only():
    """7.8 mm from y -0.9 to 6.9 beside 6 mm letters: ratio 0.77, spanning
    the band (MFab LC's AND N: 7.90 against 6.25, 0.79)."""
    g = _tall(-0.9, 7.8)
    assert not tc._similar(7.8, 6.0, tc.LETTER_HEIGHT_RATIO)
    off = _line(_region("N", g))
    tc.detect_text_clusters(off, None, wide_letters=True)
    assert _tags(off)["N"] is None and _tags(off)["B0"] is not None
    on = _line(_region("N", _tall(-0.9, 7.8)))
    tc.detect_text_clusters(on, None, wide_letters=True, part_touching=True)
    tags = _tags(on)
    assert tags["N"] is not None and tags["N"] == tags["B0"]


@pytest.mark.parametrize("y0, h", [(3.0, 7.8),       # sits below the band: another line
                                   (-2.3, 10.6)])    # ratio 0.57, under HEIGHT_BAND_MIN
def test_a_tall_glyph_off_the_band_or_past_its_floor_is_not_adopted(y0, h):
    regions = _line(_region("N", _tall(y0, h)))
    tc.detect_text_clusters(regions, None, wide_letters=True, part_touching=True)
    assert _tags(regions)["N"] is None and _tags(regions)["B0"] is not None


def test_an_overshooting_glyph_never_makes_a_line():
    regions = [_region("B0", _bar(20.0)), _region("B1", _bar(23.0)),
               _region("N", _tall(-0.9, 7.8))]
    tc.detect_text_clusters(regions, None, part_touching=True)
    assert all(v is None for v in _tags(regions).values())


def test_spans_reads_the_cap_band():
    line = (0.0, 0.0, 1.0, 6.0)
    assert tc._spans((0.0, -0.9, 4.0, 6.9), line)
    assert not tc._spans((0.0, 3.0, 4.0, 10.8), line)           # below it
    assert not tc._spans((0.0, -2.3, 4.0, 8.3), line)           # too tall for the band
    assert not tc._spans((0.0, 0.0, 4.0, 6.0), (0.0, 0.0, 1.0, 0.0))


# --- wiring and OFF ---------------------------------------------------------------

def test_the_flag_is_off_and_the_pipeline_passes_nothing_when_off():
    assert PipelineConfig().text_cluster_part_touching is False
    assert inspect.signature(tc.detect_text_clusters).parameters["part_touching"].default is False
    from digitizer_core import pipeline
    src = inspect.getsource(pipeline)
    assert '**({"part_touching": True} if cfg.text_cluster_part_touching else {})' in src


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
    touching or overshooting letter."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            text_cluster_part_touching=on))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
