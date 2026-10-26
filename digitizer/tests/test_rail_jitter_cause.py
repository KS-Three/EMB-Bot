"""tools/rail_jitter_cause: what a high `letter_band.rail_jitter` reading is.

Synthetic satin columns on synthetic outlines -- one per bin, so a change to
the classifier's rule shows up here before it moves a number in
`.claude/memory/marine-stem-rails-2026-10-25.md`.
"""
import numpy as np
from shapely.geometry import Polygon

from tools import letter_band
from tools import letter_pieces as LP
from tools import rail_jitter_cause as rjc

PULL = 0.3


def _column(y0, y1, left, right=4.0, pitch=0.4):
    """An upright zigzag: left rail at `left(y)` (minus the pull), right rail at
    `right` (plus the pull), a needle every `pitch / 2` mm down the column."""
    pts, y, on_left = [], y0, True
    while y <= y1:
        pts.append((left(y) - PULL, y) if on_left else (right + PULL, y))
        y += pitch / 2
        on_left = not on_left
    return np.array(pts, float)


def _rect(y0=0.0, y1=20.0):
    return Polygon([(0, y0), (4, y0), (4, y1), (0, y1)])


def test_one_reader_with_letter_band():
    """The stations classified are the stations #1052 counted."""
    assert rjc.WIN is letter_band.WIN
    col = _column(0, 20, lambda y: 0.0)
    assert len(rjc.stations([col], fused=False)) == len(letter_band.rail_jitter([col]))


def test_straight_column_reads_nothing():
    res = rjc.classify(_rect(), [_column(0, 20, lambda y: 0.0)])
    assert res["stations"] > 40
    assert res["over"] == 0 and res["p90"] < 1e-9


def test_a_rail_turning_a_notch_is_a_corner():
    """MARINE's slab: the outline steps 0.8 mm out at y = 10, the rail follows."""
    poly = Polygon([(0, 0), (4, 0), (4, 20), (-0.8, 20), (-0.8, 10), (0, 10)])
    res = rjc.classify(poly, [_column(0, 20, lambda y: -0.8 if y >= 10 else 0.0)])
    assert res["over"] > 0
    assert res["corner"] == res["over"] and res["straight"] == 0 and res["stray"] == 0


def test_a_penetration_off_the_rail_is_a_stray():
    """A short stitch ending mid-column, read as a rail point."""
    col = _column(0, 20, lambda y: 0.0)
    k = int(np.argmin(np.abs(col[:, 1] - 10.0)))
    k -= k % 2                                   # a left-rail point
    col[k, 0] = 1.5
    res = rjc.classify(_rect(), [col], fused=False)
    assert res["stray"] > 0 and res["straight"] == 0


def test_a_rail_off_a_straight_edge_is_wobble():
    """The one bin that IS wobble: a rail point 0.25 mm off a straight outline."""
    col = _column(0, 20, lambda y: 0.0)
    k = int(np.argmin(np.abs(col[:, 1] - 10.0)))
    k -= k % 2
    col[k, 0] -= 0.25
    res = rjc.classify(_rect(), [col], fused=False)
    assert res["straight"] > 0 and res["corner"] == 0 and res["stray"] == 0
    assert max(res["straight_mm"]) > 0.15


def test_corners_ignore_flat_vertices():
    poly = Polygon([(0, 0), (2, 0.1), (4, 0), (4, 4), (0, 4)])   # a 5.7 deg kink on the base
    C = rjc.corners(poly)
    assert len(C) == 4 and not np.any(np.all(np.isclose(C, (2, 0.1)), axis=1))


def _letter(monkeypatch, pts):
    monkeypatch.setattr(LP, "runs_of", lambda _p: [{"block": 0, "pts": pts}])
    Ls = rjc.file_letters("synthetic", rows=(0.0, 1.0), min_height=5.0)
    assert len(Ls) == 1
    return Ls[0]


def test_stem_window_straight_stem(monkeypatch):
    sw = rjc.stem_window(_letter(monkeypatch, _column(0, 14, lambda y: 0.0)))
    assert len(sw) == 2 and max(sw) < 1e-9


def test_stem_window_skips_the_slab(monkeypatch):
    """A notch in the top 25% (the slab) is outside the window: the stem still reads straight."""
    sw = rjc.stem_window(_letter(monkeypatch, _column(0, 14, lambda y: -0.8 if y < 3.0 else 0.0)))
    assert len(sw) == 2 and max(sw) < 1e-9


def test_stem_window_sees_a_wobbling_stem(monkeypatch):
    rng = np.random.default_rng(7)
    noise = dict()
    sw = rjc.stem_window(_letter(monkeypatch, _column(
        0, 14, lambda y: noise.setdefault(round(y, 3), float(rng.uniform(-0.2, 0.2))))))
    assert max(sw) > 0.08 and min(sw) < 1e-9
