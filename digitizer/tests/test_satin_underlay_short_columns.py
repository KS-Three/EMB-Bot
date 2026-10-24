"""`cfg.satin_underlay_short_columns` (2026-10-22, built OFF): the centre run
the pro puts under his short satin columns, under ours.

Read on his 27 job DSTs with `tools/pro_satin_underlay.py` (the 3D puff
file aside): a centre run under 83-97% of satin columns in every length and
width band, columns under 5 mm long bare 0-13% per job. Ours leave them
bare two ways -- a shape whose artwork extent is under
`machine.SATIN_UNDERLAY_MIN_EXTENT_MM` sews every column bare (stage 7, law
50's first rung), and a stroke whose spine is under
`machine.UNDERLAY_STITCH_MM` gets no run (`stage6_satin._stroke_underlay`).
Underlay is a physical constant (ROADMAP gate 1), so the flag waits on a
sew-out and Kent's flip; OFF is the engine byte for byte, and the OFF md5
pins elsewhere (`test_detail_spokes.FREMONT_80_OFF_MD5`,
`test_column_small_bold.OFF_LANE_MD5`) are what guard that.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric, machine, stitches
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_satin import satin_shape
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART

# The pro's smallest column with a run under it: 2 mm long, 1 mm wide. Its
# skeleton spine is 1.0 mm (half a width short of each cap).
COLUMN_2x1 = Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])


def _underlay(runs):
    return [r for r in runs if r.kind == stitches.UNDERLAY]


def _length(r) -> float:
    return sum(math.dist(a, b) for a, b in zip(r.points, r.points[1:]))


def test_default_is_off():
    assert PipelineConfig().satin_underlay_short_columns is False


def test_off_a_2mm_column_sews_bare_and_on_it_carries_a_centre_run():
    off, _ = satin_shape(COLUMN_2x1, "S", underlay_style="center_run", trim_at_mm=3.0)
    on, _ = satin_shape(COLUMN_2x1, "S", underlay_style="center_run", trim_at_mm=3.0,
                        short_column_underlay=True)
    assert [r.kind for r in off] == [stitches.SATIN]
    assert [r.kind for r in on] == [stitches.UNDERLAY, stitches.SATIN]
    ul = _underlay(on)[0]
    # one run stitch, the engine's shortest, down the column's spine
    assert machine.MIN_STITCH_MM - 1e-6 <= _length(ul) <= machine.UNDERLAY_STITCH_MM
    assert all(abs(y - 0.5) < 0.05 for _x, y in ul.points), "the run sits on the spine"
    assert all(0.0 <= x <= 2.0 for x, _y in ul.points), "and inside the column"
    # the column itself is the same thread either way -- entered at the end
    # the run leaves it at, so possibly reversed (`satin_underlay_on_column`'s
    # nearest-first rule), never re-cast
    assert on[-1].points in (off[-1].points, off[-1].points[::-1])


def test_the_run_uses_the_underlay_stitch_pitch_not_a_new_one():
    """A longer column's run keeps `UNDERLAY_STITCH_MM`: the flag lowers
    the floor, it does not change the pitch (the pro's 1.1-1.3 mm zigzag
    advance and 1.4-1.7 mm run stitch are NOT built here)."""
    col = Polygon([(0, 0), (12, 0), (12, 1), (0, 1)])
    off, _ = satin_shape(col, "S", underlay_style="center_run", trim_at_mm=3.0)
    on, _ = satin_shape(col, "S", underlay_style="center_run", trim_at_mm=3.0,
                        short_column_underlay=True)
    assert [r.points for r in _underlay(on)] == [r.points for r in _underlay(off)]


def test_none_style_stays_none_under_the_flag():
    on, _ = satin_shape(COLUMN_2x1, "S", underlay_style="none", trim_at_mm=3.0,
                        short_column_underlay=True)
    assert not _underlay(on)


# --- stage 7: law 50's small-shape rung -----------------------------------

def _small_letter() -> Region:
    # 4 mm tall, under SATIN_UNDERLAY_MIN_EXTENT_MM, 1 mm wide: a small 'l'
    poly = Polygon([(0, 0), (1, 0), (1, 4), (0, 4)])
    return Region(shape_id="Sl", polygon=poly, thread_index=5,
                  thread_number=CHART[5].number, area_mm2=poly.area,
                  meta={"layer": 0, "forced_tier": "satin"})


def _plan(**cfg_kw):
    cfg_kw.setdefault("edge_cap", "none")
    fab = get_fabric("structured_cap")
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps([_small_letter()], fab, c)
    blocks, _w = sequence(planned, fab, c)
    return [r for b in blocks for r in b.runs]


def test_a_small_shape_keeps_the_fabric_s_underlay_only_under_the_flag():
    assert machine.SATIN_UNDERLAY_MIN_EXTENT_MM == 5.0, "the rung this test is written against"
    off = _plan()
    on = _plan(satin_underlay_short_columns=True)
    assert stitches.SATIN in {r.kind for r in off}, "the letter is satin to begin with"
    assert not _underlay(off), "law 50's first rung: a 4 mm shape sews bare"
    assert _underlay(on), "ON: the structured cap's centre run goes under it"
    sat_on = [stitches.strip_ties(r.points) for r in on if r.kind == stitches.SATIN]
    sat_off = [stitches.strip_ties(r.points) for r in off if r.kind == stitches.SATIN]
    assert len(sat_on) == len(sat_off) == 1
    # the same crosses (the lock legs move to the run that now leads in),
    # entered at the end the run leaves it at, so reversed
    assert sat_on[0] in (sat_off[0], sat_off[0][::-1]), "the satin does not move"


def test_underlay_off_still_means_none():
    assert not _underlay(_plan(satin_underlay_short_columns=True, underlay=False))


# --- the Column lane's own floor ------------------------------------------

def test_the_column_lane_walks_a_span_that_holds_one_stitch_only_under_the_flag():
    """Fremont's H at 92.5 mm kept 13 bare spans of 1.1-2.0 mm (its serif
    blocks) with the satin tier's floor lowered: the lane's `_centre_underlay`
    has its own, `2 * _UNDERLAY_INSET_MM + MIN_STITCH_MM` = 1.8 mm."""
    from digitizer_core import columns
    assert columns._UNDERLAY_INSET_MM == 0.4 and machine.MIN_STITCH_MM == 1.0
    short = [(0.0, 0.0), (0.75, 0.0), (1.5, 0.0)]       # a 1.5 mm serif block
    assert columns._centre_underlay(short) is None, "off: under the lane's 1.8 mm floor"
    walk = columns._centre_underlay(short, short_columns=True)
    assert walk is not None
    xs = [x for x, _y in walk]
    assert min(xs) >= -1e-9 and max(xs) <= 1.5 + 1e-9, "inside the span"
    assert max(xs) - min(xs) >= machine.MIN_STITCH_MM - 1e-6, "one full stitch of it"
    tiny = [(0.0, 0.0), (0.4, 0.0), (0.8, 0.0)]
    assert columns._centre_underlay(tiny, short_columns=True) is None, "a span under one stitch stays bare"
    long = [(0.0, 0.0), (3.0, 0.0), (6.0, 0.0)]
    assert columns._centre_underlay(long, short_columns=True) == columns._centre_underlay(long), \
        "a span over the floor walks exactly as shipped"
