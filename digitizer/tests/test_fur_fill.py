"""The "fur" fill (2026-10-14): tatami with a random start offset per row and
a random length per stitch, seeded by `cfg.seed`.

What is pinned here:

- every step ALONG a row is at least `MIN_STITCH_MM` and at most the style's
  stitch length, on the row function and on a whole sewn shape;
- the same inputs sew the same stitches, and another seed sews others;
- both traversals of a row give the same points (the stream belongs to the
  row, not to the direction `_fill_paths` happens to walk it);
- the styles are refused by name when unknown;
- every OTHER technique's `stitch_shape` output is byte-identical to before
  fur existed (md5 pins captured on the parent commit, 4022d6f2).

The wiring (design-wide flag and per-shape tier, both vocabularies) rides on
`test_wave_chevron_brick.py`'s parametrized skeleton.

`FUR_STYLES`' numbers are gate-1 candidates; nothing here asserts they are
right, only that the engine honours them.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.stage6_fill import (
    _fill_paths,
    _fur_row_points,
    clear_fill_reorder_memo,
    fur_style,
    stitch_shape,
)

RECT = Polygon([(0, 0), (30, 0), (30, 12), (0, 12)])
ELL = Polygon([(0, 0), (24, 0), (24, 6), (8, 6), (8, 20), (0, 20)])
DISC = Polygon([(math.cos(t / 48 * 2 * math.pi) * 9, math.sin(t / 48 * 2 * math.pi) * 9)
                for t in range(48)])


def _sew(poly, technique="fur", seed=0, style="short", angle=0.0):
    clear_fill_reorder_memo()
    runs, _ = stitch_shape(poly, "S", angle_deg=angle, row_mm=machine.FILL_ROW_MM,
                           stitch_mm=machine.FILL_STITCH_MM, underlay_style="none",
                           trim_at_mm=3.0, technique=technique, seed=seed,
                           fur_style_name=style)
    return runs


def _md5(runs) -> str:
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for r in runs for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def _row_frame(p, angle):
    """A point in the fill's row frame, where rows run along x."""
    t = math.radians(-angle)
    return (p[0] * math.cos(t) - p[1] * math.sin(t), p[0] * math.sin(t) + p[1] * math.cos(t))


def _fill_steps(runs, angle):
    """(length, same_row) for every FILL stitch; `same_row` when both ends
    share a y in the row frame -- the steps the random lengths make. The
    others are row turns, one row spacing long on a square edge, as in plain
    tatami."""
    out = []
    for r in runs:
        if r.kind != stitches.FILL:
            continue
        pts = [_row_frame(p, angle) for p in r.points]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            out.append((math.hypot(bx - ax, by - ay), abs(ay - by) < 1e-6))
    return out


# --- the styles ---------------------------------------------------------------

def test_every_style_keeps_its_split_pieces_above_the_floor():
    """`_fur_row_points` splits a step longer than L into pieces over L / 2,
    so L must be at least two minimum stitches for the floor to hold."""
    for name, (length, rand, offset) in machine.FUR_STYLES.items():
        assert length >= 2 * machine.MIN_STITCH_MM, name
        assert 0.0 < rand < 1.0, name
        assert 0.0 < offset <= 1.0, name


def test_an_unknown_style_is_refused():
    with pytest.raises(ValueError, match="fur_style"):
        fur_style("mohair")
    with pytest.raises(ValueError, match="fur_style"):
        _sew(RECT, style="mohair")


def test_the_config_defaults_are_tatami_and_short_fur():
    c = PipelineConfig()
    assert c.fill_technique == "tatami"
    assert c.fur_style == "short"


# --- one row ------------------------------------------------------------------

@pytest.mark.parametrize("style", sorted(machine.FUR_STYLES))
def test_row_steps_lie_between_the_floor_and_the_stitch_length(style):
    length, rand, offset = fur_style(style)
    rng = np.random.default_rng(7)
    seen = []
    for i in range(400):
        x0 = float(rng.uniform(-50, 50))
        span = float(rng.uniform(2 * machine.MIN_STITCH_MM, 60))
        pts = _fur_row_points(x0, x0 + span, 1.5, i, length, 4, False,
                              seed=3, random_frac=rand, offset_frac=offset)
        assert pts[0] == (x0, 1.5) and pts[-1] == (x0 + span, 1.5)
        steps = [b[0] - a[0] for a, b in zip(pts, pts[1:])]
        assert min(steps) >= machine.MIN_STITCH_MM - 1e-9
        assert max(steps) <= length + 1e-9
        seen.extend(steps)
    # And it is random: the lengths spread over the style's range rather than
    # sitting on one value the way tatami's interior grid does.
    assert np.std(seen) > 0.1 * length
    assert min(seen) < length * (1 - rand / 2)


def test_short_spans_follow_the_tatami_boundary_rule():
    """Under two minimum stitches the row is the single stitch across it,
    under `TINY_STITCH_MM` its midpoint -- `_row_points_at_phase`'s rule."""
    assert _fur_row_points(0.0, 0.3, 2.0, 0, 4.0, 4, False) == [(0.15, 2.0)]
    assert _fur_row_points(0.0, 1.5, 2.0, 0, 4.0, 4, False) == [(0.0, 2.0), (1.5, 2.0)]


def test_a_row_is_the_same_walked_either_way():
    fwd = _fur_row_points(-3.0, 41.0, 5.0, 12, 4.0, 4, False, seed=9)
    back = _fur_row_points(-3.0, 41.0, 5.0, 12, 4.0, 4, True, seed=9)
    assert back == list(reversed(fwd))


def test_neighbouring_rows_do_not_share_their_holes():
    a = _fur_row_points(0.0, 40.0, 0.0, 0, 4.0, 4, False, seed=1)
    b = _fur_row_points(0.0, 40.0, 0.15, 1, 4.0, 4, False, seed=1)
    assert [x for x, _ in a[1:-1]] != [x for x, _ in b[1:-1]]


# --- a whole shape ----------------------------------------------------------------

@pytest.mark.parametrize("style", sorted(machine.FUR_STYLES))
@pytest.mark.parametrize("poly", [RECT, ELL, DISC], ids=["rect", "ell", "disc"])
@pytest.mark.parametrize("angle", [0.0, 30.0])
def test_no_stitch_along_a_row_is_under_the_floor(style, poly, angle):
    """The randomness adds no stitch under `MIN_STITCH_MM`. The only short
    stitches along a row are the rows too narrow for an interior point (under
    two minimum stitches: one stitch edge to edge, at a tapering tip), and
    those are exactly plain tatami's, row for row -- the same row grid, the
    same boundary rule. Every stitch along a row is at most the style's
    length."""
    floor = machine.MIN_STITCH_MM - 1e-6
    fur = [d for d, same_row in _fill_steps(_sew(poly, style=style, angle=angle), angle)
           if same_row]
    tatami = [d for d, same_row in _fill_steps(_sew(poly, technique="tatami", angle=angle),
                                                angle) if same_row]
    assert fur, "fur sewed no fill"
    assert max(fur) <= fur_style(style)[0] + 1e-6
    fur_short = sorted(round(d, 6) for d in fur if d < floor)
    assert fur_short == sorted(round(d, 6) for d in tatami if d < floor)
    assert all(d < 2 * machine.MIN_STITCH_MM for d in fur_short)


def test_the_same_seed_sews_the_same_file_and_another_does_not():
    a = _md5(_sew(ELL, seed=0))
    b = _md5(_sew(ELL, seed=0))
    c = _md5(_sew(ELL, seed=1))
    assert a == b
    assert a != c


def test_fur_differs_from_tatami_and_long_from_short():
    tatami = _md5(_sew(RECT, technique="tatami"))
    short = _md5(_sew(RECT))
    long_ = _md5(_sew(RECT, style="long"))
    assert len({tatami, short, long_}) == 3


def test_the_seed_and_style_are_inert_for_every_other_technique():
    for technique in ("tatami", "wave", "chevron", "brick", "crosshatch"):
        assert _md5(_sew(ELL, technique=technique, seed=0)) == \
            _md5(_sew(ELL, technique=technique, seed=5, style="long"))


def test_fill_paths_defaults_to_short_fur():
    clear_fill_reorder_memo()
    a = _fill_paths(RECT, 0.0, 0.15, 4.0, 4, technique="fur")
    b = _fill_paths(RECT, 0.0, 0.15, 4.0, 4, technique="fur", fur=fur_style("short"))
    assert a == b


# --- every other technique, byte-identical to before fur ----------------------

# md5 of `stitch_shape` at angle 0, underlay "none" and "edge_lattice",
# captured on 4022d6f2 (the parent commit) and re-measured identical after.
OTHER_TECHNIQUE_MD5 = {
    "disc/brick/edge_lattice": "bf63572d78f0c84177dba23d3ac8bbc0",
    "disc/brick/none": "23324a9673fc8703fdde19bc09bd6904",
    "disc/chevron/edge_lattice": "de760c2429cb2904eb06804fc8887135",
    "disc/chevron/none": "fb06eb05853a9cc2bb7bc15b2f6d53be",
    "disc/crosshatch/edge_lattice": "f9df56f8213811aa9c8948e4167b6031",
    "disc/crosshatch/none": "53fdfc38719d4adf6bcf74fe8c7d2c09",
    "disc/tatami/edge_lattice": "088013882312d0b6f6498cbcd8371732",
    "disc/tatami/none": "9ef6170c96d50de86ff7606715833c28",
    "disc/wave/edge_lattice": "80644f76dd03e3e51b8868a1f4c2bf8e",
    "disc/wave/none": "0c022a54f06528a99a648c78038c4b4c",
    "ell/brick/edge_lattice": "2f6e5c7d3517469468568fcaf26f0c0d",
    "ell/brick/none": "2ee8b29224a47ee7da10a85c3224183a",
    "ell/chevron/edge_lattice": "e662b3b4fc290e5a28db191c2bdac913",
    "ell/chevron/none": "1ef994485360177f60c49d97001080c1",
    "ell/crosshatch/edge_lattice": "1a381e375b2f847b0e265b39a3f9ccb0",
    "ell/crosshatch/none": "555a483783776cbd636e80352c6f7eae",
    "ell/tatami/edge_lattice": "6dd2bee69e51a42f53611fa4249229d4",
    "ell/tatami/none": "5c78dba948d30bf0e5b79604ad2cdc8f",
    "ell/wave/edge_lattice": "e71dd04de8808a528b7184278bd8d0d5",
    "ell/wave/none": "7a3888317ba46d6ba9be7597c3d698c6",
    "rect/brick/edge_lattice": "db101ebf36a659dd3be4d8385808f77a",
    "rect/brick/none": "1feef0a27e66bdbef2397e4d4b67ea90",
    "rect/chevron/edge_lattice": "ca84254e0c98474711425426acdfbdc2",
    "rect/chevron/none": "c7a66b55fa046ff7f28e20716bec2c80",
    "rect/crosshatch/edge_lattice": "6b2882bfb291010c1a09a1c07cdb5456",
    "rect/crosshatch/none": "5e49bd203f78073b3450d57ed4635dc5",
    "rect/tatami/edge_lattice": "cfd043b33f28196692e6738f9f6509a3",
    "rect/tatami/none": "92329ff82dad2778e643df31677856f3",
    "rect/wave/edge_lattice": "479790c71fc33e92d320d39cd775db8c",
    "rect/wave/none": "a109cd5d15cb4f5f3414ceabb369fe02",
}


@pytest.mark.parametrize("key", sorted(OTHER_TECHNIQUE_MD5))
def test_other_techniques_are_byte_identical_to_before_fur(key):
    name, technique, underlay = key.split("/")
    poly = {"rect": RECT, "ell": ELL, "disc": DISC}[name]
    clear_fill_reorder_memo()
    runs, _ = stitch_shape(poly, "S", angle_deg=0.0, row_mm=machine.FILL_ROW_MM,
                           stitch_mm=machine.FILL_STITCH_MM, underlay_style=underlay,
                           trim_at_mm=3.0, technique=technique)
    assert _md5(runs) == OTHER_TECHNIQUE_MD5[key]
