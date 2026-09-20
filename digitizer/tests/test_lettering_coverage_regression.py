"""A wordmark must not sew FATTER, and must not buy that by sewing LESS.

(The module name is stale: this began as a coverage guard and the premise did
not survive being measured. The repo's worktree hook refuses a rename under
`.claude/worktrees/`, so the name stayed and the docstring carries the truth.)

**What this fixture is actually made of.** `dropped_elements`' `lost_frac` is
a SUM of two unrelated defects, and this one is entirely a single half.
Measured 2026-09-20, `enthusiast_logo.png` at 80 mm left_chest, shipped
engine:

    lost_frac 0.3006  =  unsewn_frac 0.0000  +  overshoot_frac 0.3006

Zero mm2 of artwork went unsewn. All 118.7 mm2 is thread standing on cloth
the artwork leaves bare -- the letters sew fatter than they are drawn. All 32
regions read `ink=False` with `cover` about 0.99 (thread present, no ink
beneath), and `tools/rail_edge.py --bare`, the geometric coverage instrument,
does not move at all across the change that moved the total.

**Where the number came from.** Bisected one commit at a time via
`tools.eye_pairs` with `ref_0827` arms:

    09-02 baseline (e2aa965d)  artfid_nc 72.7   lost_frac 0.2509
    + 1cac4d25 hairline bean   72.7             0.2509   (byte-identical)
    + bbb7009f curve refine    72.7             0.2509   (byte-identical)
    + 768de79e rail-to-edge    72.0             0.2702   <== THE STEP
    + 14f99580 no-50um-skip    72.0             0.2702   (no change)
    TODAY                      71.2             0.3006

Confirmed in TODAY's tree, not only at that commit: neutralising 768de79e's
boundary-crossing branch in `_rail_points.place` on current `main` moves
lost_frac 0.3006 -> 0.2584. That commit is the actor. What it does: an
overshooting rail goes onto the nearest boundary crossing instead of stepping
in 15%. Measured, 242 firings here out of 1436 satin penetrations, placing at
a median 0.980 of the requested width -- so the rail lands ON the shape edge.
The 16.6 mm2 it adds is 100% within 1.0 mm of the ink edge, median 0.30 mm
OUTSIDE it; three quarters along free edges, a quarter closing the counters
of E, N and T.

**Why three bars, and why none may be traded for another.** Three cures were
measured on 2026-09-20 and every one bought one instrument with another:

    candidate                lost_frac  jitter enth/becker  bare(93mm)
    shipped                     0.3006     0.0227 / 0.0246     3.94%
    revert the branch           0.2584     0.0413 / 0.0447     3.94%
    inset the branch 0.20 mm    0.2430     0.0401 / 0.0539     3.99%
    global corridor cap         0.2420     0.0280 / 0.0287     5.58%

The revert and the inset hand back 768de79e's jitter win -- the inset is
worse than a full revert on becker, because the branch fires at only 17% of
stations and offsetting a subset is a step against its neighbours. The
corridor cap holds jitter and pays in real coverage, and drops `max_out`
0.541 -> 0.300 mm, which is pull compensation, gate 1. Kent's ruling
2026-09-20: keep 768de79e's placement and pin what actually regressed.

**`unsewn_frac` alone is NOT enough, and that was measured, not assumed.**
This file first pinned overshoot plus `unsewn_frac <= 0.02` and claimed that
made the corridor cap fail. Run against the corridor cap it read **0.0028**
and sailed through: `dropped_elements` only counts disagreement regions of
1 mm2 or more, after a 0.5 mm opening, so coverage lost as a thin rind along
every column never forms a region it can see. `rail_edge.bare_area` -- satin
artwork outside a thread's width of the sewn crosses -- sees exactly that,
and reads 5.50% -> 7.22% on the same pair at this fixture's own config. So
both are pinned, because they fail on different shapes of loss:

    unsewn_frac    a whole element gone   (logo_bridge_bar reads 0.089)
    bare_frac      a thin rind everywhere (the corridor cap, +1.7 points)

**Bars are set from measurement, not from a target.** Each sits just above
today's accepted reading. This is a tripwire against drift, not a demand that
today's engine change; lowering the overshoot is real work and is not what
this file asks for.
"""
from __future__ import annotations

import functools
from pathlib import Path

from tools.eye_pairs.features import base_cfg, digitize_once, features_full
from tools.rail_edge import bare_area

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "testdata" / "photo" / "enthusiast_logo.png"

# The fixture's own Studio settings. Changing either invalidates every number
# in the docstring -- they are not free parameters.
WIDTH_MM = 80.0
GARMENT = "left_chest"

# Thread standing on cloth the artwork leaves bare, as a fraction of ink area.
# Today's accepted reading plus ~5% headroom so ordinary churn does not flap
# the test. Kent accepted this LEVEL on 2026-09-20 when he kept 768de79e's
# rail placement; he did not accept its growth. Verified to fire:
# `satin_rails_follow_edge=True` reads 0.3555 here.
OVERSHOOT_TODAY = 0.3006
OVERSHOOT_BAR = 0.315

# Satin artwork outside a thread's width of the sewn crosses. Today 5.50% of
# 350 mm2 of satin art at this config (NOT the 3.94% `tools/rail_edge.py
# enthusiast` prints -- that case runs 93 mm with no garment). Verified to
# fire: the corridor-cap candidate reads 7.22% here.
BARE_TODAY = 0.0550
BARE_BAR = 0.060

# A whole element never sewn. Today's reading is 0.0 -- not "small", zero.
# This bar is deliberately loose: it exists to catch an element vanishing, and
# `bare_frac` above is what catches thin loss. See the docstring.
UNSEWN_TODAY = 0.0
UNSEWN_BAR = 0.02


@functools.lru_cache(maxsize=1)
def _measure() -> dict:
    """One pipeline run for all three assertions (about 35 s)."""
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    cfg = base_cfg(WIDTH_MM, GARMENT)
    gen, result, plan, design = digitize_once(FIXTURE, cfg)
    row = features_full(FIXTURE, cfg, gen, result, plan, design)
    assert row["overshoot_frac"] is not None and row["unsewn_frac"] is not None, (
        "dropped_elements refused to score this design, so the guard did not "
        f"run at all: {row.get('refusals')}")
    polys = {r.shape_id: r.polygon for r in result.regions}
    num, den = bare_area(polys, plan)
    assert den > 0, "no satin runs on this fixture, so bare area says nothing"
    return {"overshoot_frac": row["overshoot_frac"],
            "unsewn_frac": row["unsewn_frac"],
            "bare_frac": num / den}


def test_a_wordmark_does_not_sew_fatter_than_its_artwork():
    """Thread standing on cloth the artwork leaves bare.

    This is the half of `lost_frac` that `enthusiast` is made of -- 100% of
    it, measured. It grows when satin rails move outward, which is why it is
    pinned against a commit that moved them.
    """
    got = _measure()["overshoot_frac"]
    assert got <= OVERSHOOT_BAR, (
        f"{FIXTURE.name} at {WIDTH_MM:g} mm sews {got:.4f} of its ink area in "
        f"thread that stands on bare cloth, against a {OVERSHOOT_BAR} bar "
        f"(shipped engine measured {OVERSHOOT_TODAY} when this bar was set).\n"
        f"The letters are sewing fatter than they are drawn. See this "
        f"module's docstring: 768de79e moved overshooting rails onto the "
        f"artwork edge, and this is the instrument that sees it.\n"
        f"Do NOT raise the bar to make this pass.")


def test_the_columns_do_not_get_narrower_to_pay_for_it():
    """Satin artwork outside a thread's width of the sewn crosses.

    Narrowing every column would lower `overshoot_frac` by sewing less of the
    letter. This is the reading that catches it -- `unsewn_frac` does not,
    measured: the corridor-cap candidate read 0.0028 there and 7.22% here.
    """
    got = _measure()["bare_frac"]
    assert got <= BARE_BAR, (
        f"{FIXTURE.name} at {WIDTH_MM:g} mm now leaves {100 * got:.2f}% of its "
        f"satin artwork outside a thread's width of any cross, against a "
        f"{100 * BARE_BAR:.2f}% bar (shipped engine measured "
        f"{100 * BARE_TODAY:.2f}%).\n"
        f"Something bought a narrower column by dropping artwork. Check "
        f"`tools/rail_edge.py enthusiast becker --bare` and its jitter line "
        f"alongside before concluding anything.")


def test_no_element_of_the_wordmark_goes_unsewn():
    """A whole element never sewn -- the failure Kent named on seven designs.

    Loose on purpose; `bare_frac` above is the sensitive one. This fires on
    the shape of loss that instrument cannot see: a limb or a word missing
    outright, which reads 0.089 on `logo_bridge_bar`.
    """
    got = _measure()["unsewn_frac"]
    assert got <= UNSEWN_BAR, (
        f"{FIXTURE.name} at {WIDTH_MM:g} mm now leaves {got:.4f} of its ink "
        f"unsewn, against a {UNSEWN_BAR} bar (the shipped engine measured "
        f"{UNSEWN_TODAY} -- zero -- when this bar was set).\n"
        f"Run `python -m tools.dropped_elements photo/enthusiast_logo.png "
        f"--detail` to see which element went missing.")
