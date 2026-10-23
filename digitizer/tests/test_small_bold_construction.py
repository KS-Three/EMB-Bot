"""`cfg.lettering_columns_small_bold`'s construction of ~4 mm bold letters,
the way the pro's Hotel Fremont patch sews them (2026-10-23).

Read off the pro's patch DST (needle paths, `tools/column_harness.py`): each
stroke is ONE column with crosses square to it, and a serif is never a
piece of its own -- a T's stem zigzag widens through its foot, an E's arm
crosses grow taller at the tip. Three rules under the flag:

- `outline_cut._absorb_serifs`: a small piece at a straight column's end
  is scanned with it along the column's axis (`SERIF_MAX_AREA_W2`,
  `SERIF_MAX_CROSS_W`);
- `find_cuts` reads a junction corner's edge direction as a chord
  (`_chord_dir`, `CHORD_W`), so the grown outline's corner chamfers no
  longer keep a T's two under-bar corners from their through cut;
- `_mitre_ends` ignores a face narrower than `SMALL_BOLD_MITRE_SPAN` of the
  column (a corner chamfer), which fanned the last crosses at every corner.

OFF is untouched: every rule sits behind the `_SMALL_BOLD` context, and
`test_column_small_bold.test_off_is_byte_identical_to_base` pins it.
"""
import math
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import columns
from digitizer_core import outline_cut as oc

KW = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.4, pull_floor_mm=1.5, square_ends=True,
          inside_connectors=True, fold_cuts=True, rail_axis=True)
CUT_KW = dict(pitch_mm=0.4, fold_cuts=True, mitre_ends=True, rail_axis=True)
LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "fremont92_reset_letters.json"


def traced(shape):
    """A drawn shape as the grown trace hands it over: corners rounded by
    0.15 mm and simplified at 0.06, which leaves a chamfer at every one."""
    return (shape.buffer(0.15, join_style=1).buffer(-0.15, join_style=1)
            .buffer(-0.12, join_style=1).buffer(0.12, join_style=1).simplify(0.06))


@pytest.fixture(scope="module")
def slab_t():
    """A 4 mm slab-serif T: bar 4.0 x 0.9 with 0.35 mm tabs under its ends,
    stem 0.9 wide, foot 1.6 x 0.4."""
    bar = box(0, 3.1, 4.0, 4.0)
    tabs = unary_union([box(0, 2.8, 0.35, 3.1), box(3.65, 2.8, 4.0, 3.1)])
    return traced(unary_union([bar, tabs, box(1.55, 0, 2.45, 3.1), box(1.2, 0, 2.8, 0.4)]))


def test_a_slab_serif_t_is_a_bar_and_a_stem_each_with_its_serifs(slab_t):
    cut = oc.letter_columns(slab_t, small_bold=True, **CUT_KW)
    assert len(cut.columns) == 2 and not cut.unsewn
    assert all(c.kind == "straight" for c in cut.columns)
    stem = min(cut.columns, key=lambda c: c.piece.bounds[1])
    bar = max(cut.columns, key=lambda c: c.piece.bounds[1])
    assert stem.piece.covers(Point(1.3, 0.2)) and stem.piece.covers(Point(2.7, 0.2))   # the foot
    assert bar.piece.covers(Point(0.17, 2.95)) and bar.piece.covers(Point(3.83, 2.95))  # the tabs
    assert abs(stem.axis[1]) > 0.99 and abs(bar.axis[0]) > 0.99
    # the stem's crosses widen through the foot, the pro's foot
    widths = [math.dist(a, b) for a, b in stem.stations]
    assert max(widths[:3] + widths[-3:]) > 1.3 > 1.1 > min(widths[3:-3])
    assert all(oc.pivot_sweep(c.stations) == 0 for c in cut.columns)     # no corner fan


def test_off_still_cuts_the_foot_off_and_fans_into_it(slab_t):
    cut = oc.letter_columns(slab_t, **CUT_KW)
    assert len(cut.columns) == 3
    assert max(oc.pivot_sweep(c.stations) for c in cut.columns) > 25


def test_the_t_sews_without_a_knot(slab_t):
    runs, rep = columns.lettering_columns_shape(slab_t, "t", **KW, small_bold=True)
    assert rep["columns"] == 2 and rep["columns_unsewn"] == 0
    assert tuple(int(v) for v in oc.sewn_knots(runs)) == (0, 0, 0)
    _r, off = columns.lettering_columns_shape(slab_t, "t", **KW)
    assert off["columns"] == 3


def test_a_crossbar_is_never_absorbed_into_a_stem():
    # an H's 0.35 mm bar is as small as a serif; scanned with a stem it would
    # cross both, so it stays a column of its own
    H = traced(Polygon([(0, 0), (0.8, 0), (0.8, 1.8), (1.7, 1.8), (1.7, 0), (2.5, 0), (2.5, 4),
                        (1.7, 4), (1.7, 2.15), (0.8, 2.15), (0.8, 4), (0, 4)]))
    cut = oc.letter_columns(H, small_bold=True, **CUT_KW)
    assert len(cut.columns) == 3 and not cut.unsewn
    W = oc.stroke_width(cut.poly)
    for c in cut.columns:
        assert max(math.dist(a, b) for a, b in c.stations) < oc.SERIF_MAX_CROSS_W * W


def test_chord_direction_is_the_outline_past_a_chamfer():
    # a square concave corner with a 0.2 mm chamfer: the edge meeting the
    # corner is the chamfer, the chord over half a stroke is the real edge
    ring = [(0, 0), (3, 0), (3, 1), (1.2, 1), (1.0, 1.2), (1, 3), (0, 3)]
    d_in = oc._unit((1.2 - 3, 0))                                   # the long edge, pointing in
    assert oc._chord_dir(ring, 3, -1, 0.5) == pytest.approx(d_in, abs=1e-9)
    # the chord from the far side runs back along the edge leaving the corner
    assert oc._chord_dir(ring, 3, 1, 0.5)[0] == pytest.approx(math.cos(math.atan2(-0.2 - 0.0, 0.2 + 0.0 - 0.0)), abs=0.5)


@pytest.fixture(scope="module")
def fremont():
    from tools.column_harness import load_letters
    return load_letters(LETTERS)


def test_mitre_face_must_span_the_column(fremont, monkeypatch):
    # the tagline E's stem and arms end on the grown outline's corner
    # chamfers: with the span guard off the mitre turns their last crosses
    # into a fan at the corner (pivot 34-38 deg on 2026-10-23); with it on
    # they end square
    poly, _kw = fremont["S5c2d8e5a"]

    def worst():
        cut = oc.letter_columns(poly, small_bold=True, **CUT_KW)
        return max(oc.pivot_sweep(c.stations) for c in cut.columns)
    assert worst() == 0
    monkeypatch.setattr(oc, "SMALL_BOLD_MITRE_SPAN", 0.0)
    assert worst() > 20


def test_fremonts_tagline_t_is_a_bar_across_and_a_stem_down(fremont):
    # the chamfered under-bar corners paired through the stem (the chord
    # rule); the foot in the stem's column (serif absorption)
    poly, _kw = fremont["Sd3e6b4c8"]
    cut = oc.letter_columns(poly, small_bold=True, **CUT_KW)
    assert [c.kind for c in cut.columns] == ["straight", "straight"]
    bar, stem = sorted(cut.columns, key=lambda c: c.piece.bounds[1])
    assert abs(bar.axis[0]) > 0.99 and abs(stem.axis[1]) > 0.99
    x0, y0, x1, y1 = poly.bounds
    assert stem.piece.covers(Point((x0 + x1) / 2, y1 - 0.15))             # the foot
    assert all(oc.pivot_sweep(c.stations) == 0 for c in cut.columns)


def test_the_21_letters_cut_to_fewer_columns_and_no_fan(fremont):
    # 73 columns on 2026-10-22 (every serif a block of its own); the pro's
    # EAT STAY PLAY is 2-4 columns a letter
    n, worst = 0, 0.0
    for sid, (poly, kw) in fremont.items():
        cut = oc.letter_columns(poly, pitch_mm=kw["spacing_mm"], fold_cuts=kw["fold_cuts"],
                                mitre_ends=kw["square_ends"], rail_axis=kw["rail_axis"],
                                small_bold=True)
        assert not cut.unsewn, sid
        n += len(cut.columns)
        worst = max([worst] + [oc.pivot_sweep(c.stations) for c in cut.columns if c.kind != "ring"])
    assert n <= 56, n
    assert worst <= oc.SMALL_BOLD_FAN_DEG
