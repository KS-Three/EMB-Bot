"""The edge cap's bill, on REAL artwork, across SIZE — and what it does when
the bill is big (`cfg.edge_cap_over_budget`, `EDGE_CAP_BUDGET_PCT`).

`tests/test_edge_cap.py` is the cap's own suite and it is green; it is also
why a +58.7% bill shipped on a DEFAULT-ON flag for a month. It builds its
geometry from synthetic `bar(15, 30)` polygons fed straight into
`resolve_overlaps`/`sequence` — it never calls `digitize`, never touches real
artwork, and never sweeps size, so it cannot see a bill whose value depends on
how the artwork TIERED. This file is the missing half: one real fixture, three
widths, and the two fields that read the situation wrong.

**The measurement this file pins** (`docs/edge-cap-cliff-2026-09-12.md`,
reproduced on this tree 2026-09-12):

| becker @ | cap st | cap % | gate saved | omit cover | `edges` old / new |
|---|---|---|---|---|---|
| 80 mm | 1,011 | +18.1% | 82.5% | 1,355.6 mm² | 18 / 16 |
| 88 mm | 4,949 | **+58.7%** | **12.0%** | 394.7 mm² | 19 / 16 |
| 95.7 mm | 5,979 | +56.6% | 2.9% | 85.7 mm² | 16 / 17 |
| 110 mm | 7,114 | +53.4% | **0.0%** | **none at all** | 17 / 17 |

One shape — the "BECKER" banner — carries ~94% of this design's linear cover,
its satin/fill verdict is not monotone in design size, and when it tiers to
fill the gate's input evaporates and the cap reverts to the pre-gate
+8.6-100.4% regime the gate was built to kill. **That cause is NOT fixed here
and this file does not test it.** Kent's ruling 2026-09-12 was to cap the COST
and leave `stage6_satin.classify_ribbon` alone: the banner still flips, and
the point of the change under test is that the flip stops being expensive and
silent.

Cost of this file: one `digitize` per row above plus four cheap controls —
1m40s serial on this tree. That is the price of testing a size-dependent bill
at all; the synthetic suite is fast precisely because it measures nothing
about artwork. `_run`'s cache is per PROCESS, so under `-n auto` a fixture
touched by tests that land on different workers is digitized once per worker
(two, on CI's two-core runners). Prefer adding assertions to an existing test
here over adding a test that needs a fresh width.
"""
from __future__ import annotations

from functools import lru_cache

import pytest

from digitizer_core import PipelineConfig, stitches
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_border import (EDGE_CAP_BUDGET_PCT,
                                          EDGE_CAP_OVER_BUDGET_ACTIONS)
from digitizer_core.warnings_codes import (EDGE_CAP_APPLIED,
                                           EDGE_CAP_OVER_BUDGET)

from .conftest import TESTDATA

BECKER = "becker_marine_logo.png"
WHITEBG = "logo_whitebg.png"

# The three widths that matter, and why each one is here.
CHEAP = 80.0        # the only width the flip was ever measured at
CLIFF = 88.0        # +58.7%, eight millimetres up, gate saving 72% -> 12%
NO_GATE = 110.0     # `_sewn_linear_cover` returns None: no gate at all


@lru_cache(maxsize=None)
def _run(fixture: str, width: float, cap: str = "bean",
         over_budget: str = "warn"):
    """One `digitize` per (fixture, width, knobs), cached.

    Cached for the reason `test_resnap_mask_matches_grader` records: CI
    runners are 2-core and becker at 88 mm is a 17-second design. Every test
    below reuses these.
    """
    _result, plan = digitize(
        TESTDATA / fixture,
        PipelineConfig(target_width_mm=width, edge_cap=cap,
                       edge_cap_over_budget=over_budget))
    return plan


def _bill(plan) -> dict | None:
    for w in plan.warnings:
        if w["code"] == EDGE_CAP_APPLIED:
            return w
    return None


def _over(plan) -> dict | None:
    for w in plan.warnings:
        if w["code"] == EDGE_CAP_OVER_BUDGET:
            return w
    return None


def _cap_block(plan):
    for b in plan.blocks:
        if any(r.shape_id == "__edge_cap__" for r in b.runs):
            return b
    return None


def _coords(plan):
    return tuple((round(x, 4), round(y, 4), r.kind, r.jump, r.trim)
                 for _b, r in plan.iter_runs() for x, y in r.points)


# --- the fields say what they mean --------------------------------------------

@pytest.mark.parametrize("width", [CHEAP, CLIFF, NO_GATE])
def test_the_bill_splits_whole_rings_from_arcs_and_both_add_up(width):
    """`edges` used to be `loops + bean_loops`, and `run_outline` increments
    `loops` once per emitted RUN — one per arc where the gate splits a ring,
    one per whole ring where it does not. So the field an operator reads as
    "how fragmented is this" read 18 / 19 / 17 across these widths while the
    bill went +18% / +59% / +53%, moving for reasons that have nothing to do
    with fragmentation.

    Two identities pin the replacement, and they are what make the split
    checkable rather than merely plausible:
      * `whole_loops + arcs` is the number of RUNS the cap emitted, which is
        countable from the block itself.
      * `whole_loops + yielded` is the number of RINGS it went around, which
        is what `edges` now carries.
    """
    plan = _run(BECKER, width)
    bill, block = _bill(plan), _cap_block(plan)
    assert bill is not None and block is not None

    outline_runs = [r for r in block.runs if r.kind != stitches.TRAVEL]
    assert bill["whole_loops"] + bill["arcs"] == len(outline_runs), (
        f"{width} mm: the bill's run split {bill['whole_loops']}+"
        f"{bill['arcs']} does not add up to the {len(outline_runs)} outline "
        "runs the cap block actually carries")
    assert bill["edges"] == bill["whole_loops"] + bill["yielded"]
    assert bill["stitches"] == block.stitch_count


def test_the_ring_count_no_longer_falls_as_the_cap_gets_more_expensive():
    """The specific defect: `edges` FELL precisely because the cap got dearer.

    becker's silhouette is the same shape at every width in this sweep — the
    cliff doc measured `sil_parts = 10` and `interiors_pre = 7` at all of
    80-110 mm, and ring length scaling smoothly +41%. A fragmentation field
    that swings while the silhouette does not is not reporting fragmentation.
    """
    bills = {w: _bill(_run(BECKER, w)) for w in (CHEAP, CLIFF, NO_GATE)}
    pcts = [b["percent"] for b in bills.values()]
    edges = [b["edges"] for b in bills.values()]

    assert max(pcts) - min(pcts) > 30.0, (
        f"the sweep no longer swings the bill ({pcts}) — this test is not "
        "watching the situation it was written for")
    assert max(edges) - min(edges) <= 1, (
        f"`edges` moved {edges} across a sweep whose silhouette does not "
        "change: it is counting runs again, not rings")
    # ...and the runs DO swing, which is what the old field was reading.
    runs = [b["whole_loops"] + b["arcs"] for b in bills.values()]
    assert max(runs) - min(runs) >= 2, (
        f"run counts {runs} are flat too — then `edges` being flat proves "
        "nothing and this test is vacuous")


def test_the_bill_reports_what_the_gate_saved_and_it_collapses_with_size():
    """`1 - gated/ungated`, the one number that would have made this visible
    at a glance (cliff doc §8 item 3).

    82.5% at 80 mm, 12.0% at 88 mm, and at 110 mm the design has no linear
    stitching on its own edge at all — `_sewn_linear_cover` returns `None`,
    the gate does not exist, and the cap is back in the pre-gate regime.
    """
    cheap = _bill(_run(BECKER, CHEAP))
    cliff = _bill(_run(BECKER, CLIFF))
    none = _bill(_run(BECKER, NO_GATE))

    assert cheap["gate_saved_pct"] > 50.0, cheap["gate_saved_pct"]
    assert cheap["omit_cover_mm2"] > 1000.0, cheap["omit_cover_mm2"]

    assert cliff["gate_saved_pct"] < 25.0, cliff["gate_saved_pct"]
    assert cliff["gate_saved_pct"] < cheap["gate_saved_pct"] - 50.0

    # The headline: a bigger design, and the gate has nothing to work with.
    assert none["omit_cover_mm2"] == 0.0
    assert none["gate_saved_pct"] == 0.0
    assert none["percent"] > 40.0, (
        "the no-gate width stopped being expensive — re-read the sweep "
        "before relaxing this, the cap reverting to full cost IS the defect")


# --- the ceiling ---------------------------------------------------------------

def test_the_ceiling_sits_in_the_gap_between_the_two_measured_regimes():
    """The constant's justification, as an assertion rather than a comment.

    Every bill measured in this repo with the gate WORKING: 4.4-26.6%
    (`enthusiast_logo` 4.4-6.9, `logo_hotel_fremont` 5.5-8.6, `logo_whitebg`
    21.2-26.3, becker's own cheap widths 18.1 and 26.6). Every bill measured
    with it collapsed or absent: 53.4% and up, plus `drone_render`'s pre-gate
    +56.9% and DOCTRINE's +60% blanket-border negative. Nothing lands
    between. A future edit to this number has to clear both sides on purpose.
    """
    assert 26.6 < EDGE_CAP_BUDGET_PCT < 53.4
    assert EDGE_CAP_OVER_BUDGET_ACTIONS == ("warn", "drop")


@pytest.mark.parametrize("width", [CLIFF, NO_GATE])
def test_a_cap_over_the_ceiling_says_so_out_loud(width):
    """`EDGE_CAP_APPLIED` fires on every run, so the one design where the cap
    costs half the artwork again read exactly like the ninety that cost a
    tenth. This is the code that only fires when it matters, and it carries
    the diagnosis with it."""
    plan = _run(BECKER, width)
    bill, loud = _bill(plan), _over(plan)

    assert bill["over_budget"] is True
    assert loud is not None, f"{width} mm bills +{bill['percent']}% in silence"
    assert loud["percent"] == bill["percent"]
    assert loud["budget_pct"] == EDGE_CAP_BUDGET_PCT
    assert loud["gate_saved_pct"] == bill["gate_saved_pct"]
    assert loud["omit_cover_mm2"] == bill["omit_cover_mm2"]
    assert loud["dropped"] is False        # warn is the default: nothing moved
    # The Studio has no translation for this code yet (`app/` is another
    # lane's file), so the panel ships this sentence verbatim to a customer.
    # It has to read like one.
    assert "stitches" in loud["message"] and "%" in loud["message"]
    for jargon in ("silhouette", "omit", "gate", "polygon", "tatami"):
        assert jargon not in loud["message"].lower(), jargon


def test_the_cheap_width_stays_quiet():
    plan = _run(BECKER, CHEAP)
    assert _bill(plan)["over_budget"] is False
    assert _over(plan) is None


@pytest.mark.parametrize("width", [CHEAP, NO_GATE])
def test_the_ceiling_does_not_fire_on_a_design_that_honestly_costs_a_quarter(width):
    """`logo_whitebg` is the false-positive control and it is not optional.

    It is a `width_cap` fill design that was never a ribbon candidate, so
    nothing about it flips with size: it bills +26.3% at 80 mm and +21.2% at
    110 mm, the highest legitimate bill on the sheet, and the flip was made
    with that number in hand. A ceiling that fires here is wrong, whatever it
    catches on becker.
    """
    plan = _run(WHITEBG, width)
    bill = _bill(plan)
    assert 20.0 < bill["percent"] < 27.0, bill["percent"]
    assert bill["over_budget"] is False
    assert _over(plan) is None
    assert bill["percent"] < EDGE_CAP_BUDGET_PCT / 1.4, (
        "the control is within 40% of the ceiling — too close to call this a "
        "margin")


# --- the refusal is opt-in, and off is the engine it always was ----------------

def test_dropping_is_off_by_default_and_the_drop_never_executes(monkeypatch):
    """The off-path claim as an EXECUTION fact, not an output comparison —
    the model `test_resnap_mask_matches_grader` set the same day.

    `_over_budget_action` is called from exactly ONE place, only when the
    bill is over the ceiling, and its `"drop"` is the only thing that skips
    the cap block's append. So counting its answers IS the guard. The ceiling
    is monkeypatched to 1.0 so a five-second fixture reaches that call site
    at all; without the patch this test would need a 17-second one to prove a
    negative.
    """
    import digitizer_core.stage7_sequence as S

    seen: dict[str, list[str]] = {}
    real = S._over_budget_action
    for mode in ("warn", "drop"):
        answers: list[str] = []

        def spy(cfg, _real=real, _answers=answers):
            a = _real(cfg)
            _answers.append(a)
            return a

        monkeypatch.setattr(S, "EDGE_CAP_BUDGET_PCT", 1.0)
        monkeypatch.setattr(S, "_over_budget_action", spy)
        plan = digitize(TESTDATA / WHITEBG,
                        PipelineConfig(target_width_mm=CHEAP, edge_cap="bean",
                                       **({"edge_cap_over_budget": mode}
                                          if mode != "warn" else {})))[1]
        monkeypatch.undo()
        seen[mode] = answers
        assert (_cap_block(plan) is None) is (mode == "drop"), (
            f"{mode}: the cap block's presence does not match the action")

    assert seen["warn"] == ["warn"], (
        f"the DEFAULT config answered {seen['warn']} — a default-off flag "
        "that can return 'drop' is not default-off")
    assert seen["drop"] == ["drop"], (
        f"the flag is set to drop and the call site answered {seen['drop']}, "
        "so this test is not watching the branch it claims to watch")


def test_the_warning_moves_no_stitch(monkeypatch):
    """Warning is not a behaviour change, proved on a design forced over the
    ceiling: same fixture, same width, ceiling at 1.0% instead of 40%, and
    the plan is the identical stream of stitches plus one warning."""
    import digitizer_core.stage7_sequence as S

    monkeypatch.setattr(S, "EDGE_CAP_BUDGET_PCT", 1.0)
    _result, forced = digitize(
        TESTDATA / WHITEBG,
        PipelineConfig(target_width_mm=CHEAP, edge_cap="bean"))
    monkeypatch.undo()

    assert _over(forced) is not None, "the forced ceiling did not fire"
    assert _coords(forced) == _coords(_run(WHITEBG, CHEAP))


def test_a_dropped_cap_is_exactly_the_cap_off_engine():
    """What "drop" means, at the only resolution that settles it: byte for
    byte, a dropped cap is `edge_cap="none"` — not merely a smaller plan.

    becker at 88 mm: 13,386 stitches with the cap, 8,437 without, and the
    8,437 the refusal leaves are the SAME 8,437.
    """
    dropped = _run(BECKER, CLIFF, "bean", "drop")
    off = _run(BECKER, CLIFF, "none")

    assert _cap_block(dropped) is None
    assert _coords(dropped) == _coords(off)
    assert dropped.stats.stitch_count == off.stats.stitch_count

    # The bill is still rendered — a refusal the operator cannot see is the
    # silence this whole change is against.
    bill, loud = _bill(dropped), _over(dropped)
    assert bill["dropped"] is True and loud["dropped"] is True
    assert bill["stitches"] > 0
    assert (dropped.stats.stitch_count + bill["stitches"]
            == _run(BECKER, CLIFF).stats.stitch_count), (
        "the refusal did not remove exactly the stitches it billed for")
