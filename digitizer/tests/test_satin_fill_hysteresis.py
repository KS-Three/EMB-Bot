"""`cfg.extra["satin_fill_hysteresis"]` (default OFF): a satin-vs-fill gate
whose reading sits inside a margin band round its line abstains, and the gates
clear of their own bands decide (`stage6_satin.classify_ribbon(hysteresis=True)`).

What is pinned here: OFF is the one reading it always was; the aspect band
hands a near-line shape to the distance transform, and back to the aspect
refusal when the DT cannot read it; the cv band sends a near-line shape down
the irregular branch, where the promotion test decides both ways; the bands
stop at their edges; and the physical caps (the 5.0 mm p90 cap, Law 31's
1.0 mm photo floor) carry no band at all (ROADMAP gate 1). The default-path
md5 pins in the rest of the suite are what prove OFF byte-identical on real
designs.
"""
from __future__ import annotations

import math

import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon

import digitizer_core.stage6_satin as s6
from digitizer_core import PipelineConfig, machine
from digitizer_core.config import satin_fill_hysteresis
from digitizer_core.stage6_satin import (
    _DtStats,
    _classify_ribbon_once,
    classify_ribbon,
    is_satin_candidate,
)

CAP = machine.SATIN_MAX_WIDTH_MM
BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])          # aspect 13, clear of every band
BLOB = Point(0, 0).buffer(8.0)                              # aspect 2.14, clear of the aspect band


def _aspect(poly) -> float:
    return _classify_ribbon_once(poly, CAP).metrics["aspect"]


def _ellipse_at_aspect(target: float, minor: float = 1.0) -> Polygon:
    """An ellipse (minor semi-axis `minor` mm) whose perimeter aspect reads
    `target`, found by bisection on the major axis, so the test pins the band's
    edge rather than a hand-measured shape. A rectangle cannot do this: its
    aspect `L + 1 + 1/L` (W = 1) never reads under 3."""
    circle = Point(0, 0).buffer(1.0, quad_segs=64)
    lo, hi = 1.0, 6.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _aspect(affinity.scale(circle, mid * minor, minor)) < target:
            lo = mid
        else:
            hi = mid
    return affinity.scale(circle, 0.5 * (lo + hi) * minor, minor)


def _stats(cv: float, *, p90: float = 2.0, explained: float = 0.9,
           elongation: float = 12.0) -> _DtStats:
    return _DtStats(mean=1.0, std=cv, p90_mm=p90, spine_len_mm=24.0,
                    explained=explained, elongation=elongation)


def _with_stats(monkeypatch, stats):
    monkeypatch.setattr(s6, "_dt_stats", lambda poly, **kw: stats)


# ----------------------------------------------------------------- OFF path
@pytest.mark.parametrize("poly", [BAR, BLOB, _ellipse_at_aspect(2.95)],
                         ids=["bar", "blob", "near-aspect"])
def test_off_is_the_one_reading_as_drawn(poly):
    once = _classify_ribbon_once(poly, CAP)
    default = classify_ribbon(poly, CAP)
    explicit = classify_ribbon(poly, CAP, hysteresis=False)
    for v in (default, explicit):
        assert (v.satin, v.reason, v.metrics) == (once.satin, once.reason, once.metrics)
        assert not any(k.startswith("hyst_") for k in v.metrics)
    assert is_satin_candidate(poly, CAP) == once.satin


def test_the_flag_is_an_extra_key_and_defaults_off():
    assert satin_fill_hysteresis(PipelineConfig()) is False
    assert satin_fill_hysteresis(PipelineConfig(extra={"satin_fill_hysteresis": True})) is True
    assert satin_fill_hysteresis(PipelineConfig(extra={"satin_fill_hysteresis": False})) is False
    # the vote's key does not turn the bands on
    assert satin_fill_hysteresis(PipelineConfig(extra={"satin_fill_vote": True})) is False


def test_clear_shapes_do_not_move():
    for poly in (BAR, BLOB):
        off, on = classify_ribbon(poly, CAP), classify_ribbon(poly, CAP, hysteresis=True)
        assert (on.satin, on.reason) == (off.satin, off.reason)
        assert not any(k.startswith("hyst_") for k in on.metrics)


# ------------------------------------------------------------- aspect band
def test_a_near_line_aspect_refusal_is_handed_to_the_distance_transform():
    poly = _ellipse_at_aspect(2.95)
    assert _aspect(poly) == pytest.approx(2.95, abs=1e-6)
    off = classify_ribbon(poly, CAP)
    on = classify_ribbon(poly, CAP, hysteresis=True)
    assert off.reason == "aspect" and off.satin is False
    assert on.metrics["hyst_aspect"] == 1.0
    assert on.reason != "aspect"
    # what decided it is the DT, read the same way it reads every other shape
    assert on.metrics["dt_mean"] > 0
    assert on.reason in ("satin", "dt_irregular", "promoted_ribbon", "dt_p90_cap")


def test_the_aspect_band_stops_at_its_edge():
    edge = 3.0 * (1.0 - s6._HYST_ASPECT_REL)
    outside = _ellipse_at_aspect(edge - 0.02)
    assert classify_ribbon(outside, CAP, hysteresis=True).reason == "aspect"
    inside = _ellipse_at_aspect(edge + 0.02)
    assert classify_ribbon(inside, CAP, hysteresis=True).reason != "aspect"


def test_a_banded_aspect_shape_the_dt_cannot_read_keeps_the_aspect_refusal(monkeypatch):
    poly = _ellipse_at_aspect(2.95)
    _with_stats(monkeypatch, None)
    on = classify_ribbon(poly, CAP, hysteresis=True)
    assert (on.satin, on.reason) == (False, "aspect")
    # a shape the aspect gate PASSED still defers to satin exactly as shipped
    assert classify_ribbon(BAR, CAP, hysteresis=True).reason == "dt_degenerate"


# ----------------------------------------------------------------- cv band
def test_a_near_line_regular_shape_must_earn_promotion(monkeypatch):
    # cv 0.495: shipped satin on the regularity gate alone; in the band it
    # abstains, and a compact shape (elongation 5) fails the promotion test
    _with_stats(monkeypatch, _stats(0.495, elongation=5.0))
    assert classify_ribbon(BAR, CAP).reason == "satin"
    on = classify_ribbon(BAR, CAP, hysteresis=True)
    assert (on.satin, on.reason) == (False, "dt_irregular")
    assert on.metrics["hyst_cv"] == 1.0


def test_a_near_line_ribbon_is_promoted_both_sides_of_the_line(monkeypatch):
    for cv in (0.495, 0.505):
        _with_stats(monkeypatch, _stats(cv))
        on = classify_ribbon(BAR, CAP, hysteresis=True)
        assert (on.satin, on.reason) == (True, "promoted_ribbon"), cv


def test_past_the_line_nothing_changes(monkeypatch):
    # cv >= 0.5 already takes the irregular branch; the band adds nothing there
    for cv, elong in ((0.505, 5.0), (0.505, 12.0), (0.6, 5.0), (0.6, 12.0)):
        _with_stats(monkeypatch, _stats(cv, elongation=elong))
        off, on = classify_ribbon(BAR, CAP), classify_ribbon(BAR, CAP, hysteresis=True)
        assert (on.satin, on.reason) == (off.satin, off.reason), (cv, elong)


def test_the_cv_band_stops_at_its_edge(monkeypatch):
    below = 0.5 - s6._HYST_CV_ABS - 0.002
    _with_stats(monkeypatch, _stats(below, elongation=5.0))
    on = classify_ribbon(BAR, CAP, hysteresis=True)
    assert (on.satin, on.reason) == (True, "satin")
    assert "hyst_cv" not in on.metrics


# --------------------------------------------------- the caps carry no band
@pytest.mark.parametrize("p90", [CAP + 0.02, CAP + 0.08])
def test_the_p90_cap_is_not_banded(monkeypatch, p90):
    _with_stats(monkeypatch, _stats(0.3, p90=p90))
    for hyst in (False, True):
        assert classify_ribbon(BAR, CAP, hysteresis=hyst).reason == "dt_p90_cap"


def test_the_photo_floor_is_not_banded(monkeypatch):
    floor = s6.PHOTO_MIN_SATIN_WIDTH_MM
    for p90, want in ((floor - 0.02, "photo_width_floor"), (floor + 0.02, "satin")):
        _with_stats(monkeypatch, _stats(0.3, p90=p90))
        for hyst in (False, True):
            v = classify_ribbon(BAR, CAP, design_class="photo_scene", hysteresis=hyst)
            assert v.reason == want, (p90, hyst)


def test_the_width_cap_is_not_banded():
    wide = Polygon([(0, 0), (60, 0), (60, CAP * 1.3), (0, CAP * 1.3)])
    assert wide.area > 0 and not math.isinf(CAP)
    for hyst in (False, True):
        assert classify_ribbon(wide, CAP, hysteresis=hyst).reason == "width_cap"


# ------------------------------------------------------------- with the vote
def test_the_vote_bands_every_reading(monkeypatch):
    seen = []
    real = s6._classify_ribbon_once

    def spy(poly, max_w, **kw):
        seen.append(kw.get("hysteresis"))
        return real(poly, max_w, **kw)

    monkeypatch.setattr(s6, "_classify_ribbon_once", spy)
    classify_ribbon(BAR, CAP, vote=True, hysteresis=True)
    assert len(seen) == 5 and all(seen)


# ------------------------------- a banded shape the DT reads AND refuses
# (#1311 follow-up) The aspect band hands a near-line shape to the DT. When the
# DT reads it and refuses, the refusal the shape carries out has to stay
# "aspect": stage 7's compact-solid satin rescue (`compact_solids_satin`,
# default ON) runs on `reason == "aspect"` only, so a band that changes the
# reason without changing the bool still moves a sewn tier (one satin blob ->
# tatami plus the bean edge cap), and `ribbon_stability` / `satin_vote_flips`,
# which compare `.satin`, would call it unchanged.
def _star(outer: float = 1.0, inner: float = 0.75) -> Polygon:
    return Polygon([((outer if i % 2 == 0 else inner) * math.cos(math.pi / 2 + i * math.pi / 5),
                     (outer if i % 2 == 0 else inner) * math.sin(math.pi / 2 + i * math.pi / 5))
                    for i in range(10)])


@pytest.mark.parametrize("hyst", [True, s6.HYST_ASPECT_ONLY], ids=["both", "aspect-only"])
def test_a_banded_aspect_shape_the_dt_refuses_keeps_the_aspect_refusal(hyst):
    star = _star()          # 2.2 mm2, aspect 2.958; the DT reads cv ~0.52
    off = classify_ribbon(star, CAP)
    assert (off.satin, off.reason) == (False, "aspect")
    assert off.metrics["aspect"] == pytest.approx(2.958, abs=0.01)
    on = classify_ribbon(star, CAP, hysteresis=hyst)
    assert (on.satin, on.reason) == (False, "aspect")
    assert on.metrics["hyst_aspect"] == 1.0
    assert on.metrics["dt_mean"] > 0          # the DT did read it


@pytest.mark.parametrize("stats", [_stats(0.6, elongation=5.0), _stats(0.3, p90=CAP + 0.5)],
                         ids=["dt_irregular", "dt_p90_cap"])
def test_every_dt_refusal_of_a_banded_shape_reads_as_aspect(monkeypatch, stats):
    poly = _ellipse_at_aspect(2.95)
    _with_stats(monkeypatch, stats)
    on = classify_ribbon(poly, CAP, hysteresis=True)
    assert (on.satin, on.reason) == (False, "aspect")
    # the same refusal on a shape the aspect gate PASSED keeps the DT's reason
    assert classify_ribbon(BAR, CAP, hysteresis=True).reason != "aspect"


def test_the_band_leaves_the_compact_solid_satin_rescue_where_off_has_it():
    """End to end through stage 7: OFF sews the banded star as one satin blob
    (`compact_solids_satin`, default ON); ON must too. Before the fix ON sewed
    it tatami ("fill") while `.satin` read False both ways."""
    from digitizer_core import stitches
    from digitizer_core.fabrics import fabric_for_garment
    from digitizer_core.regions import Region
    from digitizer_core.stage5_overlap import PlannedRegion
    from digitizer_core.stage7_sequence import sequence

    star = affinity.scale(_star(), 1.5, 1.5)        # ~5 mm2, still aspect 2.958

    def kinds(**cfg_kw):
        reg = Region(shape_id="Sstar", polygon=star, thread_index=0,
                     thread_number="4101", area_mm2=star.area, source="test",
                     meta={"layer": 0})
        blocks, _w = sequence([PlannedRegion(region=reg, polygon=star, sew_index=0)],
                              fabric_for_garment("hat_front"),
                              PipelineConfig(underlay=False, **cfg_kw))
        return [r.kind for b in blocks for r in b.runs if r.shape_id == "Sstar"]

    off = kinds()
    assert off == [stitches.SATIN], off
    for key in ("satin_fill_hysteresis", "satin_fill_hysteresis_aspect_only"):
        assert kinds(extra={key: True}) == off, key
