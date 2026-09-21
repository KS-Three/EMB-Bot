"""`tools/pro_parity/regsweep.py` — the registration study's harness.

The study it re-runs was lost because its script was never committed. These
tests exist so the replacement cannot rot silently: they pin the two pieces
that would make its numbers wrong rather than merely absent — the exhaustive
scan actually finding a known offset, and the "old search" switch actually
switching something off and putting it back.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.pro_parity import regsweep as rs
from tools.pro_parity import scorecard as sc


def _mask(h, w, boxes):
    m = np.zeros((h, w), dtype=bool)
    for y0, x0, y1, x1 in boxes:
        m[y0:y1, x0:x1] = True
    return m


def test_the_exhaustive_scan_finds_a_known_offset():
    """A blob and the same blob moved: the argmax must be that move.

    In array terms `_exhaustive` reports the shift that takes OURS onto PRO,
    so a copy sitting 4 cells further along x and 2 along y must come back as
    a negative shift of the same size, scaled by `REG_RES`.
    """
    pc = _mask(60, 60, [(20, 20, 30, 30)])
    oc = _mask(60, 60, [(22, 24, 32, 34)])
    dx, dy, inter = rs._exhaustive(pc, oc)
    assert inter > 0
    assert (dx, dy) == pytest.approx((-4 * sc.REG_RES, -2 * sc.REG_RES))


def test_the_exhaustive_scan_says_zero_when_nothing_can_overlap():
    """The degenerate reading has to be distinguishable from a real peak —
    it is what tells a caller "these two share nothing" rather than "they
    align here"."""
    pc = _mask(400, 400, [(0, 0, 3, 3)])
    oc = _mask(400, 400, [(390, 390, 393, 393)])
    _dx, _dy, inter = rs._exhaustive(pc, oc)
    assert inter == 0.0


def test_the_old_search_switch_removes_the_seeds_and_restores_them():
    """`_no_corr_seeds` is the whole old-vs-new comparison. If it silently
    stopped suppressing anything, every arm would report "no change" and the
    sweep would look like a clean bill of health."""
    real = sc._corr_seeds
    with rs._no_corr_seeds():
        assert sc._corr_seeds is not real
        assert sc._corr_seeds(None, None) == []
    assert sc._corr_seeds is real


def test_the_old_search_switch_restores_on_an_exception():
    real = sc._corr_seeds
    with pytest.raises(RuntimeError):
        with rs._no_corr_seeds():
            raise RuntimeError("boom")
    assert sc._corr_seeds is real


def test_fill_ratio_is_a_fraction_and_tracks_density():
    """The study sorts by this, so a broken one would re-order its whole
    argument. A solid bar must read denser than the same thread spread over
    a wider frame."""
    dense = [(0.0, 0.0, 10.0, 0.0, 10.0, 0, False),
             (0.0, 1.0, 10.0, 1.0, 10.0, 0, False)]
    sparse = [(0.0, 0.0, 10.0, 0.0, 10.0, 0, False),
              (0.0, 40.0, 10.0, 40.0, 10.0, 0, False)]
    d, s = rs._fill_ratio(dense), rs._fill_ratio(sparse)
    assert 0.0 < s < d <= 1.0


def test_fill_ratio_is_zero_rather_than_dividing_by_zero():
    """A single stitch has no bbox area; the sweep must rank it, not die."""
    assert rs._fill_ratio([]) == 0.0
    assert rs._fill_ratio([(1.0, 1.0, 1.0, 1.0, 0.0, 0, False)]) == 0.0
