"""`cfg.extra["satin_fill_hysteresis_aspect_only"]` (default OFF): PR #1311's
option 3, the aspect band of `satin_fill_hysteresis` ALONE
(`stage6_satin.classify_ribbon(hysteresis=HYST_ASPECT_ONLY)`).

What is pinned here: the key reads as the aspect-only mode and nothing else
turns it on; with both keys set the full flag wins; the aspect band behaves
exactly as it does under the full flag (handed to the DT, back to the aspect
refusal when the DT cannot read it, stops at its edge); the cv band does NOT
fire, so a near-line regular shape keeps its shipped verdict; and the full
flag's own behaviour is unchanged. The default-path md5 pins in the rest of the
suite are what prove OFF byte-identical on real designs.
"""
from __future__ import annotations

import pytest

import digitizer_core.stage6_satin as s6
from digitizer_core import PipelineConfig, machine
from digitizer_core.config import satin_fill_hysteresis
from digitizer_core.stage6_satin import HYST_ASPECT_ONLY, classify_ribbon
from tests.test_satin_fill_hysteresis import BAR, BLOB, _aspect, _ellipse_at_aspect, _stats, _with_stats

CAP = machine.SATIN_MAX_WIDTH_MM
ASPECT = HYST_ASPECT_ONLY


def test_the_key_reads_as_the_aspect_only_mode():
    assert HYST_ASPECT_ONLY == "aspect"
    assert satin_fill_hysteresis(PipelineConfig(extra={"satin_fill_hysteresis_aspect_only": True})) == ASPECT
    assert satin_fill_hysteresis(PipelineConfig(extra={"satin_fill_hysteresis_aspect_only": False})) is False
    # the full flag is the superset and wins when both are set
    both = {"satin_fill_hysteresis": True, "satin_fill_hysteresis_aspect_only": True}
    assert satin_fill_hysteresis(PipelineConfig(extra=both)) is True
    # the vote's key does not turn it on
    assert satin_fill_hysteresis(PipelineConfig(extra={"satin_fill_vote": True})) is False


def test_clear_shapes_do_not_move():
    for poly in (BAR, BLOB):
        off, on = classify_ribbon(poly, CAP), classify_ribbon(poly, CAP, hysteresis=ASPECT)
        assert (on.satin, on.reason, on.metrics) == (off.satin, off.reason, off.metrics)


def test_the_aspect_band_is_the_full_flags_band():
    poly = _ellipse_at_aspect(2.95)
    assert _aspect(poly) == pytest.approx(2.95, abs=1e-6)
    full = classify_ribbon(poly, CAP, hysteresis=True)
    only = classify_ribbon(poly, CAP, hysteresis=ASPECT)
    assert classify_ribbon(poly, CAP).reason == "aspect"
    assert only.metrics["hyst_aspect"] == 1.0 and only.reason != "aspect"
    # this shape's cv sits outside the cv band, so the two modes must agree exactly
    assert abs(full.metrics["dt_cv"] - 0.5) > s6._HYST_CV_ABS
    assert (only.satin, only.reason, only.metrics) == (full.satin, full.reason, full.metrics)


def test_the_aspect_band_stops_at_its_edge():
    edge = 3.0 * (1.0 - s6._HYST_ASPECT_REL)
    assert classify_ribbon(_ellipse_at_aspect(edge - 0.02), CAP, hysteresis=ASPECT).reason == "aspect"
    assert classify_ribbon(_ellipse_at_aspect(edge + 0.02), CAP, hysteresis=ASPECT).reason != "aspect"


def test_a_banded_aspect_shape_the_dt_cannot_read_keeps_the_aspect_refusal(monkeypatch):
    _with_stats(monkeypatch, None)
    on = classify_ribbon(_ellipse_at_aspect(2.95), CAP, hysteresis=ASPECT)
    assert (on.satin, on.reason) == (False, "aspect")


@pytest.mark.parametrize("cv", [0.495, 0.5 - s6._HYST_CV_ABS + 0.0005, 0.505])
def test_the_cv_band_does_not_fire(monkeypatch, cv):
    # a compact near-line shape (elongation 5): the full flag sends cv 0.495
    # down the irregular branch to fill; aspect-only keeps the shipped verdict
    _with_stats(monkeypatch, _stats(cv, elongation=5.0))
    off = classify_ribbon(BAR, CAP)
    only = classify_ribbon(BAR, CAP, hysteresis=ASPECT)
    assert (only.satin, only.reason) == (off.satin, off.reason)
    assert "hyst_cv" not in only.metrics
    if cv < 0.5:
        full = classify_ribbon(BAR, CAP, hysteresis=True)
        assert (off.reason, full.reason) == ("satin", "dt_irregular")
        assert full.metrics["hyst_cv"] == 1.0


@pytest.mark.parametrize("p90", [CAP + 0.02, CAP + 0.08])
def test_the_p90_cap_is_not_banded(monkeypatch, p90):
    _with_stats(monkeypatch, _stats(0.3, p90=p90))
    assert classify_ribbon(BAR, CAP, hysteresis=ASPECT).reason == "dt_p90_cap"


def test_the_vote_bands_every_reading_aspect_only(monkeypatch):
    seen = []
    real = s6._classify_ribbon_once

    def spy(poly, max_w, **kw):
        seen.append(kw.get("hysteresis"))
        return real(poly, max_w, **kw)

    monkeypatch.setattr(s6, "_classify_ribbon_once", spy)
    classify_ribbon(BAR, CAP, vote=True, hysteresis=ASPECT)
    assert seen == [ASPECT] * 5
