"""`THREAD_MATCH_POOR` does not judge the thread of an enclosed-background
region — and the trap that made this look like a much bigger fix than it is.

`_region_color_errors` built a row for every `result.regions` entry, including
the ones marked `enclosed_background`. Those are unstitched by default and
their colour IS the background's, so scoring their thread against the artwork
under them is exactly the category error `stage4_vectorize.revalidate_threads`
already refuses to make: *"re-matching it to the bg-coloured pixels it covers
is both a no-op and a category error."*

**It is a hardening, not a rescue, and these tests say so.** Measured
2026-09-06 across the whole 26-fixture x 2-garment matrix it removes ONE
finding: `logo_gaulke_roofing`'s `4174`, 24.5 dE00 on a 6.16 mm2 region
(F 0 -> F 4, blocks 3 -> 2). No grade letter moves anywhere.

TWO THINGS THIS FILE EXISTS TO STOP SOMEONE REDOING.

1. **A plan-derived denominator.** The first build skipped regions the plan
   emits no run for. On `gaulke_roofing` that is the identical set — all 46
   runless regions are enclosed background — but it empties this function
   whenever the caller passes a plan that is not this design's, and
   `tests/test_preflight.py` does that deliberately in ten places, including
   *"the single-row path must survive an empty plan"*. The region's own flag
   says the same thing without making the row set depend on the plan.

2. **`StitchRun.jump` is not travel.** It means *"the machine must lift the
   needle to reach `points[0]`"*; the run is still a needle-down path. An
   instrument that skipped jump runs reported 11 of 25 blocking findings as
   riding on shapes that sew nothing. The real number is 0 — every one of them
   sews, several only 23-30 stitches, because a small isolated shape is
   precisely the one the router must jump to.
"""

import collections

import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import (_owning_region_id, _region_color_errors,
                                      run_preflight)
from digitizer_core.stage1_prep import prep

from .conftest import TESTDATA

GAULKE = "photo/logo_gaulke_roofing.png"
# The fixture the one real change lands on, a fixture with no runless regions
# at all (a control that must not move), and a flat-lane control.
FIXTURES = [GAULKE, "photo/logo_bridge_bar.jpg", "logo_alpha.png"]


def _digest(fixture: str):
    art = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    return art, cfg, result, plan


def _sewn_stitches(result, plan) -> collections.Counter:
    """Emitted stitches per REGION.

    Two rules, both load-bearing: resolved through `_owning_region_id`
    (a blend region's bands are named `<shape_id>-blend<i>`, so a literal
    match finds none of them), and jumps NOT filtered (`jump` describes how
    the needle arrived, not what the run is).
    """
    ids = {r.shape_id for r in result.regions}
    out: collections.Counter = collections.Counter()
    for _block, run in plan.iter_runs():
        rid = _owning_region_id(run.shape_id, ids)
        if rid is not None:
            out[rid] += len(run.points)
    return out


def _base(shape_id: str) -> str:
    """A finding labels a shade row `"<shape_id> shade <number>"` for its
    message. That is not a shape id — reading it literally reports every
    gradient band as unsewn, the artefact PR #363 flagged in its own
    instrument."""
    return shape_id.split(" shade ")[0]


@pytest.mark.parametrize("fixture", FIXTURES)
def test_no_row_is_scored_for_an_enclosed_background_region(fixture):
    art, cfg, result, plan = _digest(fixture)
    rows = _region_color_errors(prep(art, cfg), result, plan, cfg)
    enclosed = {r.shape_id for r in result.regions
                if r.meta.get("enclosed_background")}
    scored = {_base(r["shape_id"]) for r in rows}
    assert not (scored & enclosed), sorted(scored & enclosed)


@pytest.mark.parametrize("fixture", FIXTURES)
def test_no_finding_names_an_enclosed_background_region(fixture):
    art, cfg, result, plan = _digest(fixture)
    report = run_preflight(result, plan, cfg, image=art)
    enclosed = {r.shape_id for r in result.regions
                if r.meta.get("enclosed_background")}
    for f in report["findings"]:
        if f.get("code") != "THREAD_MATCH_POOR":
            continue
        extra = f["extra"]
        assert _base(extra["worst_shape_id"]) not in enclosed
        for row in extra.get("regions", []):
            assert _base(row["shape_id"]) not in enclosed


def test_gaulke_drops_the_one_finding_this_change_removes():
    """The single measured effect, pinned so it cannot silently regrow.

    `logo_gaulke_roofing` graded F 0 on three `THREAD_MATCH_POOR:block`
    findings — 1375, 3971 and 4174. `4174` rode a 6.16 mm2 enclosed-background
    region and is gone; the other two ride shapes that really sew (162 and 60
    stitches) and MUST remain, because the point is a correct denominator, not
    a smaller number.
    """
    art, cfg, result, plan = _digest(GAULKE)
    report = run_preflight(result, plan, cfg, image=art)
    threads = sorted(f["extra"]["thread_number"] for f in report["findings"]
                     if f.get("code") == "THREAD_MATCH_POOR"
                     and f.get("severity") == "block")
    assert threads == ["1375", "3971"]


def test_every_surviving_block_rides_a_shape_that_really_sews():
    """The claim the plan-derived denominator was built on, measured properly.

    Filtering `run.jump` said 11 of 25 blocking findings sat on shapes that
    sew nothing. Counting every needle-down run says 0 — this asserts the 0.
    """
    for fixture in FIXTURES:
        art, cfg, result, plan = _digest(fixture)
        report = run_preflight(result, plan, cfg, image=art)
        sewn = _sewn_stitches(result, plan)
        for f in report["findings"]:
            if (f.get("code") != "THREAD_MATCH_POOR"
                    or f.get("severity") != "block"):
                continue
            worst = _base(f["extra"]["worst_shape_id"])
            assert sewn.get(worst, 0) > 0, f"{fixture}: {worst} sews nothing"


def test_jump_runs_are_sewing_not_travel():
    """The trap, pinned directly rather than only described: on
    `gaulke_roofing` at least one blocking shape's runs are all reached BY a
    jump, so the wrong filter calls it unsewn while the machine sews it."""
    art, cfg, result, plan = _digest(GAULKE)
    ids = {r.shape_id for r in result.regions}
    with_jumps = _sewn_stitches(result, plan)
    without: collections.Counter = collections.Counter()
    for _block, run in plan.iter_runs():
        if run.jump:
            continue
        rid = _owning_region_id(run.shape_id, ids)
        if rid is not None:
            without[rid] += len(run.points)
    report = run_preflight(result, plan, cfg, image=art)
    worst = [_base(f["extra"]["worst_shape_id"]) for f in report["findings"]
             if f.get("code") == "THREAD_MATCH_POOR"
             and f.get("severity") == "block"]
    assert worst, "fixture no longer blocks; re-derive this test"
    assert all(with_jumps.get(s, 0) > 0 for s in worst)
    assert any(without.get(s, 0) == 0 for s in worst), (
        "no blocking shape is reached by a jump any more — the trap this "
        "test guards may have moved, re-derive it rather than deleting it")
