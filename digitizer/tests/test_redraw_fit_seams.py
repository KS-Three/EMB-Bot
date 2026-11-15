"""A Cancel lands inside one ring's fit and cap check (review 2026-11-14).

`outline_redraw_k` is 0.75 by default since #1515, which put seams in
`_worst_breach` only. On To a T's beanie (100 mm, the shared laptop) one
`fit_ring_plain` still ran 7.1 s and one `_cap_check` 6.1 s with no check
between, one shapely distance per sample: `letterform_priors._offenders`
and `_cap_check` had no seam, nor `outline_redraw._merge_runs`. A check
reads a clock and moves no number, so an unarmed fit is pinned identical.
"""
from __future__ import annotations

import threading

import cv2
import numpy as np
import pytest

from digitizer_core import deadline
from digitizer_core import letterform_priors as lp
from digitizer_core import outline_redraw as orw

PX_MM = 0.25            # an upscaled 4 px/mm source


def _staircase_disc(radius_mm: float) -> np.ndarray:
    """The traced outline of a disc rasterised at `PX_MM`: the staircase the
    redraw exists for."""
    n = int(2 * radius_mm / PX_MM) + 4
    xs = (np.arange(n) - n / 2) * PX_MM
    X, Y = np.meshgrid(xs, xs)
    cs, _ = cv2.findContours((X ** 2 + Y ** 2 <= radius_mm ** 2).astype(np.uint8),
                             cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cs, key=len)[:, 0, :].astype(float) * PX_MM - n / 2 * PX_MM
    return np.vstack([c, c[:1]])


RING = _staircase_disc(12.0)
TOL = orw.redraw_cap_mm(PX_MM, 0.1, 0.75)


def _cancelled():
    ev = threading.Event()
    ev.set()
    return deadline.scope(None, cancel=ev)


def test_a_cancel_lands_inside_one_rings_fit():
    with _cancelled(), pytest.raises(deadline.Cancelled):
        orw.fit_ring_plain(RING, TOL)


def test_a_cancel_lands_inside_the_offender_read():
    S = lp.densify_ring(RING, lp.sample_step(TOL))
    prims = orw.primitives_plain(S, TOL)
    R, own = lp._rebuild(S, prims, TOL)
    with _cancelled(), pytest.raises(deadline.Cancelled) as caught:
        lp._offenders(S, prims, R, own, TOL)
    assert caught.value.stage == lp.RING_FIT_SEAM


def test_a_cancel_lands_inside_the_cap_check():
    fit = orw.fit_ring_plain(RING, TOL)
    with _cancelled(), pytest.raises(deadline.Cancelled) as caught:
        lp._cap_check([RING], [fit.coords], TOL, lp.sample_step(TOL))
    assert caught.value.stage == lp.RING_FIT_SEAM


def test_the_seams_are_close_together(monkeypatch):
    seen = []
    real = deadline.check
    monkeypatch.setattr(deadline, "check", lambda stage: (seen.append(stage), real(stage)))
    fit = orw.fit_ring_plain(RING, TOL)
    lp._cap_check([RING], [fit.coords], TOL, lp.sample_step(TOL))
    samples = len(lp.densify_ring(RING, lp.sample_step(TOL)))
    # every 256 samples at least, in the offender read and in each cap pass
    assert seen.count(lp.RING_FIT_SEAM) >= 2 * samples // lp._SEAM_EVERY


def test_an_armed_but_unset_scope_moves_nothing():
    bare = orw.fit_ring_plain(RING, TOL)
    cap = lp._cap_check([RING], [bare.coords], TOL, lp.sample_step(TOL))
    with deadline.scope(600.0, cancel=threading.Event()):
        armed = orw.fit_ring_plain(RING, TOL)
        cap_armed = lp._cap_check([RING], [armed.coords], TOL, lp.sample_step(TOL))
    assert np.array_equal(bare.coords, armed.coords)
    assert [(p.kind, p.i0, p.i1) for p in bare.prims] == [(p.kind, p.i0, p.i1) for p in armed.prims]
    assert cap == cap_armed
