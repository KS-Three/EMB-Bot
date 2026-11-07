"""`cfg.extra["satin_fill_vote"]` (default OFF): the satin-vs-fill verdict as a
majority over the region at five small perturbations
(`stage6_satin.classify_ribbon(vote=True)` -> `_vote_ribbon`).

What is pinned here: the OFF path is the one reading it always was, the vote
settles a real borderline region by its neighbours, a tie keeps the verdict
as drawn, and clear verdicts are untouched. The default-path md5 pins in the
rest of the suite are what prove OFF is byte-identical on real designs.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core.config import satin_fill_vote
from digitizer_core.stage6_satin import (
    RibbonVerdict,
    _classify_ribbon_once,
    _vote_perturbations,
    classify_ribbon,
    is_satin_candidate,
)
import digitizer_core.stage6_satin as s6

CAP = machine.SATIN_MAX_WIDTH_MM
BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])
BLOB = Point(0, 0).buffer(8.0)

# A 12 x 2.2 mm bar with +/- 0.35 mm of boundary jitter (random.Random(2),
# coordinates rounded to a micron). As drawn, its pooled DT reads `2s >= m`
# by a hair (cv 0.504 against the 0.5 line) and `explained` 0.615 sits under
# the promote floor, so the one reading refuses it: `dt_irregular`. Three of
# its four neighbours (eroded, dilated, scaled +2 %) read satin; only the
# -2 % copy agrees with the refusal. That is the region the vote exists for:
# a verdict its own neighbourhood does not share.
BORDERLINE = Polygon([
    (0.0, 2.519), (0.3, 2.513), (0.6, 1.89), (0.9, 1.909), (1.2, 2.435), (1.5, 2.365),
    (1.8, 2.319), (2.1, 2.066), (2.4, 2.274), (2.7, 2.275), (3.0, 2.257), (3.3, 1.961),
    (3.6, 2.151), (3.9, 2.125), (4.2, 2.356), (4.5, 2.546), (4.8, 2.515), (5.1, 2.231),
    (5.4, 2.161), (5.7, 2.038), (6.0, 1.875), (6.3, 1.869), (6.6, 2.175), (6.9, 2.073),
    (7.2, 2.116), (7.5, 2.474), (7.8, 2.218), (8.1, 2.242), (8.4, 2.015), (8.7, 1.867),
    (9.0, 2.078), (9.3, 1.946), (9.6, 2.207), (9.9, 2.549), (10.2, 2.322), (10.5, 1.977),
    (10.8, 2.476), (11.1, 2.408), (11.4, 2.364), (11.7, 2.485), (12.0, 2.384),
    (12.0, 0.203), (11.7, -0.102), (11.4, 0.337), (11.1, 0.323), (10.8, -0.237),
    (10.5, 0.178), (10.2, 0.151), (9.9, -0.027), (9.6, 0.021), (9.3, -0.007), (9.0, 0.297),
    (8.7, 0.001), (8.4, 0.232), (8.1, -0.102), (7.8, 0.268), (7.5, 0.28), (7.2, -0.027),
    (6.9, 0.047), (6.6, 0.294), (6.3, 0.157), (6.0, -0.009), (5.7, -0.195), (5.4, -0.123),
    (5.1, 0.14), (4.8, -0.234), (4.5, 0.286), (4.2, -0.162), (3.9, 0.288), (3.6, -0.133),
    (3.3, 0.32), (3.0, 0.144), (2.7, 0.003), (2.4, 0.012), (2.1, 0.106), (1.8, 0.062),
    (1.5, -0.132), (1.2, -0.205), (0.9, 0.008), (0.6, 0.304), (0.3, 0.086), (0.0, -0.297),
])


@pytest.mark.parametrize("poly", [BAR, BLOB, BORDERLINE], ids=["bar", "blob", "borderline"])
def test_vote_off_is_the_one_reading_as_drawn(poly):
    once = _classify_ribbon_once(poly, CAP)
    default = classify_ribbon(poly, CAP)
    assert (default.satin, default.reason, default.metrics) == (once.satin, once.reason, once.metrics)
    assert is_satin_candidate(poly, CAP) == once.satin
    assert "vote_n" not in default.metrics


def test_the_flag_is_an_extra_key_and_defaults_off():
    assert satin_fill_vote(PipelineConfig()) is False
    assert satin_fill_vote(PipelineConfig(extra={"satin_fill_vote": True})) is True
    assert satin_fill_vote(PipelineConfig(extra={"satin_fill_vote": False})) is False


def test_a_borderline_region_is_settled_by_its_neighbours():
    once = _classify_ribbon_once(BORDERLINE, CAP)
    assert (once.satin, once.reason) == (False, "dt_irregular")
    neighbours = [_classify_ribbon_once(c, CAP).satin for c in _vote_perturbations(BORDERLINE)]
    assert len(neighbours) == 4 and sum(neighbours) == 3, neighbours

    voted = classify_ribbon(BORDERLINE, CAP, vote=True)
    assert (voted.satin, voted.reason) == (True, "vote_satin")
    assert (voted.metrics["vote_for"], voted.metrics["vote_n"]) == (3.0, 5.0)
    # the once-reading's margins ride along, so the overturn can still be read as one
    assert voted.metrics["dt_cv"] == once.metrics["dt_cv"]
    assert is_satin_candidate(BORDERLINE, CAP, vote=True) is True


def test_the_voted_verdict_is_itself_stable_under_a_pixel_of_erosion():
    """The point of the flag: the same shape a raster pixel smaller must not
    swing the answer. `_RASTER_PX_PER_MM` is the classifier's own pitch."""
    eroded = BORDERLINE.buffer(-1.0 / s6._RASTER_PX_PER_MM)
    assert classify_ribbon(eroded, CAP, vote=True).satin is True
    assert classify_ribbon(BORDERLINE, CAP, vote=True).satin is True


@pytest.mark.parametrize("poly,satin", [(BAR, True), (BLOB, False)], ids=["bar", "blob"])
def test_clear_verdicts_are_returned_untouched(poly, satin):
    once = classify_ribbon(poly, CAP)
    voted = classify_ribbon(poly, CAP, vote=True)
    assert voted.satin is satin
    assert voted is once or (voted.satin, voted.reason, voted.metrics) == (once.satin, once.reason, once.metrics)


def test_a_tie_keeps_the_verdict_as_drawn_and_a_majority_overturns_it(monkeypatch):
    """The arithmetic, with the classifier stubbed: an erosion that empties a
    shape drops that voter, so the panel can be even."""
    scripted = iter([False, True, True, False])          # as drawn, then three neighbours
    monkeypatch.setattr(s6, "_vote_perturbations", lambda poly: [poly, poly, poly])
    monkeypatch.setattr(s6, "_classify_ribbon_once",
                        lambda poly, cap, **kw: RibbonVerdict(next(scripted), "stub", {}))
    tied = classify_ribbon(BAR, CAP, vote=True)
    assert (tied.satin, tied.reason) == (False, "stub")  # 2 : 2 keeps the reading as drawn

    scripted = iter([False, True, True, True])
    won = classify_ribbon(BAR, CAP, vote=True)
    assert (won.satin, won.reason, won.metrics) == (True, "vote_satin", {"vote_for": 3.0, "vote_n": 4.0})


def test_perturbations_read_the_largest_piece_and_drop_an_emptied_one():
    hairline = Polygon([(0, 0), (30, 0), (30, 0.1), (0, 0.1)])   # a half-pixel erosion empties it
    kept = _vote_perturbations(hairline)
    assert 3 <= len(kept) <= 4 and all(p.geom_type == "Polygon" and not p.is_empty for p in kept)
    dumbbell = Point(0, 0).buffer(2).union(Point(10, 0).buffer(2)).union(
        Polygon([(0, -0.05), (10, -0.05), (10, 0.05), (0, 0.05)]))
    pieces = _vote_perturbations(dumbbell)
    assert all(p.geom_type == "Polygon" for p in pieces)
