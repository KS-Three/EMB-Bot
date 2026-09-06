"""`THREAD_MATCH_POOR` names an already-loaded spool on EVERY route.

`_best_loaded_spool_error` used to run only on the photo route, because that
route is also SCORED on excess over it (2026-08-24). Off it the finding said
*"Pick a closer thread or a different brand before sewing"* **without ever
looking at the design's own cone list** — and all seven F-grade fixtures are
`gradient`, which is where real logo art routes.

Counted over those seven with `tools/spool_remedy.py`: of **24 blocking
findings, 5 name a spool the design ALREADY LOADS.**

    gaulke_roofing  3971 Silver       63.6 -> 1375 Dark Charcoal, 58.6 closer
    screenshot      0111 Whale        33.0 -> 0015 White,         32.4 closer
    bridge_bar      6156 Olive        21.3 -> 1375 Dark Charcoal, 10.3 closer
    screenshot      2776 Black Chrome 17.3 -> 1776 Blackberry,     5.0 closer
    drone_render    0111 Whale        12.8 -> 0142 Sterling,       9.0 closer

The first two are the headline numbers of the whole F-wall decomposition. The
other 19 genuinely need a cone the design does not carry, and still say so.

**WHAT JUDGES IS UNCHANGED.** Excess is reported everywhere; only the photo
route is scored on it. Whether the gradient lane should also be JUDGED on
excess is a product call (a logo's palette can be changed, a photograph's
cannot) — disagreement 4 in `docs/yardstick-disagreements-2026-09-06.md`, and
deliberately not taken here. `test_no_severity_moves_anywhere` is the
load-bearing test: it fails if this ever becomes a scoring change.
"""

from functools import lru_cache

import pytest

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

from .conftest import TESTDATA

TINY = "photo/logo_gaulke_roofing.png"      # 4 cones, the 63.6 -> 58.6 case
BRIDGE = "photo/logo_bridge_bar.jpg"        # 8 cones, the 21.3 -> 10.3 case
PHOTO = "photo/photo_dof_meadow.png"        # photo route: must be untouched

# Measured 2026-09-06 on the shipped engine, BEFORE this change. Severity may
# not move, so these are pinned rather than recomputed.
SEVERITY = {TINY: (2, 1), BRIDGE: (3, 1), PHOTO: (0, 1)}   # (block, warn)


@lru_cache(maxsize=None)
def _findings(fixture: str):
    """One digitize + preflight per fixture, reused by every test here.

    Hands back the live finding dicts because every test only reads them. If
    one ever needs to mutate, give it an uncached run rather than making this
    return copies — the same rule as the other cached thread suites.
    """
    art = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    report = pf.run_preflight(result, plan, cfg, image=art)
    return [f for f in report["findings"]
            if f.get("code") == "THREAD_MATCH_POOR"]


@pytest.mark.parametrize("fixture", [TINY, BRIDGE, PHOTO])
def test_no_severity_moves_anywhere(fixture):
    """THE load-bearing test. This change is message prose plus two payload
    fields; the moment a block or warn count moves it has become a scoring
    change, which is a product call nobody has taken."""
    found = _findings(fixture)
    got = (sum(1 for f in found if f["severity"] == "block"),
           sum(1 for f in found if f["severity"] == "warn"))
    assert got == SEVERITY[fixture]


def test_the_gradient_lane_now_names_a_loaded_spool():
    """`gaulke_roofing` carries only four cones, and one of them is 58.6 dE00
    closer than the one the plan assigned. Before this change the finding told
    the operator to go buy thread."""
    named = [f for f in _findings(TINY)
             if (f["extra"] or {}).get("better_spool")]
    assert len(named) == 1, [f["message"] for f in _findings(TINY)]
    extra = named[0]["extra"]
    assert extra["better_spool"] == "1375"
    assert extra["excess_delta_e"] == pytest.approx(58.6, abs=0.15)
    assert "already loaded for this design" in named[0]["message"]


def test_excess_is_the_excess_and_not_the_raw_distance():
    """Off the photo route `_score` stays RAW, so the payload has to read
    `_excess`. Reading `_score` would print the raw distance under an
    "excess" label — caught while writing this, not after."""
    for fixture in (TINY, BRIDGE):
        for f in _findings(fixture):
            extra = f["extra"] or {}
            if extra.get("better_spool") is None:
                continue
            assert extra["excess_delta_e"] < extra["delta_e"], (fixture, extra)


def test_a_finding_with_nothing_closer_still_says_so():
    """The other 19 blocking findings across the F-wall genuinely need a cone
    the design does not carry. Over-claiming on those would be worse than the
    silence this replaces."""
    unnamed = [f for f in _findings(TINY)
               if not (f["extra"] or {}).get("better_spool")]
    assert unnamed, "fixture drift: every finding now names a spool"
    for f in unnamed:
        assert f["extra"]["excess_delta_e"] is None
        assert "Pick a closer thread" in f["message"]


def test_a_named_spool_is_never_the_thread_being_complained_about():
    """`delta_e` and `_best_loaded_spool_error` are the same median CIEDE2000
    over the same pixels, so the assigned spool scores its own raw distance
    and excess 0 — it can never be the alternative. Asserted rather than
    trusted, because a future change to either formula would break it
    silently and the message would read as nonsense."""
    for fixture in (TINY, BRIDGE, PHOTO):
        for f in _findings(fixture):
            extra = f["extra"] or {}
            if extra.get("better_spool") is not None:
                assert extra["better_spool"] != extra["thread_number"]


def test_the_photo_route_is_unchanged():
    """It already named spools; this change must not alter what it says."""
    named = [f for f in _findings(PHOTO)
             if (f["extra"] or {}).get("better_spool")]
    assert len(named) == 1
    assert "already loaded for this design" in named[0]["message"]


@pytest.mark.parametrize("fixture,want", [
    (TINY, "raw"), (BRIDGE, "raw"), (PHOTO, "excess"),
])
def test_the_payload_states_which_yardstick_judged_it(fixture, want):
    """The replacement for an inference this change invalidated.

    `test_preflight.test_non_photo_routes_keep_the_raw_yardstick_untouched`
    used to read "excess_delta_e is None" as "this was judged on raw". With
    the excess reported everywhere that inference is wrong, so the finding
    now says so outright — and both values are pinned here, because a field
    that only ever takes one value in the tests is not really checked.
    """
    found = _findings(fixture)
    assert found, fixture
    for f in found:
        assert f["extra"]["yardstick"] == want
