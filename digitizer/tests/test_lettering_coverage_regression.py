"""The fidelity guard that commit 768de79e did not have.

**THE MECHANISM IN THIS DOCSTRING WAS WRONG UNTIL 2026-09-20, AND THE WRONG
VERSION IS THE INTERESTING PART.** It said the rails "stopped COVERING the
letter strokes". They did not. They moved OUTWARD and the letters now sew
about **0.3 mm fatter than drawn** — thread standing on bare cloth. Coverage
never fell. It is corrected below; the shape of the error is recorded because
`lost_frac` sums two OPPOSITE defects and reads the same either way, so the
next person to move this number can make the same mistake in one step.

**Why this exists.** 768de79e (2026-09-03, defect 23, *"an overshooting rail
goes onto the artwork edge instead of stepping in by 15%"*) replaced
`_rail_points.place`'s 0.85x ladder with placement on the nearest boundary
crossing. It measured itself thoroughly — rail jitter, median cross width,
same-rail holes, thread, wall time — and every one of those improved
(ENTHUSIAST jitter 0.0421 -> 0.0241 mm). It did not measure what it cost:
**spill**, thread laid outside the artwork it is meant to fill.

Bisected 2026-09-20, `enthusiast` at 80 mm left_chest, one commit apart, via
`tools.eye_pairs.render` with `__ref__` arms:

    09-02 baseline          artfid_nc 72.7   lost_frac 0.2509
    + 1cac4d25 hairbean     72.7             0.2509   (byte-identical)
    + bbb7009f curve refine 72.7             0.2509   (byte-identical)
    + 768de79e rail-to-edge 72.0             0.2702   <== THE STEP
    + 14f99580 no-50um-skip 72.0             0.2702   (no change)
    TODAY                   71.2             0.3006

The two commits before it are byte-identical on this fixture and the one after
changes nothing, so the step is 768de79e alone. Stitch count FALLS across it
(2356 -> 2349): it does not add or remove thread, it MOVES rails outward.

**What that actually costs, measured 2026-09-20 and adversarially re-derived
four independent ways** (none of them reading the PR that first said so):

    across 768de79e      uncovered ink  7.6 -> 7.5 mm2   (it went DOWN)
    across the window    uncovered ink  9.1 -> 3.6 mm2   (it HALVED)
    across 768de79e      ink that LOST thread      0.01 mm2
    across 768de79e      spill (thread off ink)   +7.6 mm2
                         100% of it within 0.87 mm of the ink edge,
                         median 0.30 mm OUTSIDE it

So every millimetre of the move is thread growing outward. The clincher, on
the instrument that carries the word: `artfid coverage` is an IoU, so spill
lowers it with no loss of intersection — `satin_rails_follow_edge=True` covers
the MOST artwork of any arm (ink recall 0.9942) and scores the WORST
`lost_frac` (0.3555). **A falling `lost_frac` does not mean thread is
missing.** The commit's own message records the residual and left it open:
*"The 8-24% of lettering rail points still > 0.1 mm inside the art are the
symmetric-offset rail model ... recorded open, Kent's call."*

**Three flags were tested one variable at a time and NONE recovers it**
(2026-09-20, today's engine, `enthusiast`): `design_ramp=False` and
`keep_thin_strokes=False` are byte-identical to the shipped default;
`curve_turn_deg=None` recovers about a quarter of the gap (0.3006 -> 0.2889)
and makes `hausdorff_mm` worse. `satin_rails_follow_edge=True` — the "open
half" of defect 23 — makes `lost_frac` WORSE still (0.3555), while improving
the geometric bare-area reading. So this is unconditional code, not a toggle.

**The two instruments were never in conflict; they measure different things.**
This docstring used to say they "disagree about the cure", which was the same
error as above wearing a different hat. `rail_edge --bare` is COVERAGE — ink
with no thread on it. `lost_frac` is DISAGREEMENT — every pixel where the
stitch-out does not look like the artwork, which includes thread on cloth that
should be bare. `satin_rails_follow_edge` pushes rails further out, so it
improves bare and worsens `lost_frac`, exactly as both definitions predict.
Neither is lying.

**What this test pins, and what it deliberately does not.** It pins
`lost_frac` — `tools/dropped_elements`, per-pixel CIEDE2000 between the
artwork painted on white cloth and the RENDER, opened at half a millimetre —
because that is the metric that moved and the one a customer sees. It does NOT
pin `rail_edge --bare`: bare area is FLAT across 768de79e (measured at the
named commits, 5.45% -> 5.45% at 80 mm), so a bare-area guard would not have
caught this at all. A cure must move THIS number; if someone argues bare-area
instead, they are changing the claim, not passing the test.

**This is a RED test on purpose.** It is expected to fail on today's engine.
Do not "fix" it by moving the bar. See the caveats below before touching it.

**Two causes were found and fixed on 2026-09-20, and the bar is still not
met.** `stage6_satin`'s density refinement had its clearance floor inside
`if in_taper:`, so the short-stitch guard was free to retract stations
inward in a column body (0.3006 → 0.2882), and `stage7_sequence._cap_thread`
voted the cap's cone over the whole silhouette rather than the stretch it
actually sews (0.2882 → **0.2748**). Both are in DOCTRINE 2026-09-20 with
their counter-trades.

That leaves **0.0239 over the 2026-09-02 baseline**. ~0.0069 is 768de79e's own
recorded open item, the symmetric-offset rail model (`tools/rail_edge.py`
still reads 17.6% of this fixture's rail points more than 0.1 mm inside the
art). The other ~0.0170 was bisected the same day over all 91 engine commits
in the window (DOCTRINE 2026-09-20 has the table): the biggest step is PR
#455, whose entire engine diff is `config.py` flipping the edge cap ON by
default, and the next is 5d2db084's `satin_junction_stack` /
`satin_lettering_split` flips.

**Do not read either as a lever.** Turning the cap off on today's engine gives
back 0.0045, not the 0.0230 it cost when it landed, and the junction stack
0.0005 against 0.0093 — the vote fix above took part of the first and later
work absorbed the rest. With BOTH off this fixture still reads 0.2698, over
the bar, so what is left is unconditional code and not a default anyone can
switch. Those defaults are Kent's calls, made for other reasons; they are
priced here, not second-guessed.

**It is marked `xfail(strict=True)` rather than left hard-red, and that is
the only concession made to it.** The bar, the fixture and the assertion are
byte-for-byte what they were; `digitizer` is a required check on `main`, and
a required check that can never go green blocks every PR behind it rather
than reminding anyone of anything. Strict is the point: the day the residual
is closed this test XPASSes and goes RED, and whoever sees that deletes the
marker. **Raising `LOST_FRAC_BAR` is still not an option.**
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.eye_pairs.features import base_cfg, digitize_once, features_full

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "testdata" / "photo" / "enthusiast_logo.png"

# The fixture's own Studio settings, matching the bisect above. Changing
# either invalidates the baseline — they are not free parameters.
WIDTH_MM = 80.0
GARMENT = "left_chest"

# Measured on the 2026-09-02 engine (e2aa965d), the last commit before the
# rail change, on this machine: lost_frac 0.2509. The bar carries ~4% of
# headroom over it so that ordinary churn does not flap the test, and sits
# far below today's 0.3006 — the failure is not marginal.
LOST_FRAC_BAR = 0.26

# Today's measured value, recorded so a future reader can tell a PARTIAL cure
# from a full one rather than reading a bare pass/fail. 0.3006 was the shipped
# engine when this test was written; 0.2748 is what the two 2026-09-20 fixes
# leave. Both are kept — the pair is the only thing that says how much of the
# gap those fixes actually closed.
LOST_FRAC_WHEN_WRITTEN = 0.3006
LOST_FRAC_TODAY = 0.2748


@pytest.mark.xfail(strict=True, reason=(
    "0.2748 against a 0.26 bar. Two causes fixed 2026-09-20 (satin rail "
    "clearance floor, edge-cap thread vote); the 0.0239 residual is "
    "768de79e's own open symmetric-offset rail model plus drift bisected the "
    "same day to defaults that do NOT give it back when switched off (both "
    "off still reads 0.2698). STRICT: if this XPASSes the residual is closed "
    "and the marker should be deleted, not the test."))
def test_lettering_coverage_has_not_regressed_since_the_rail_change():
    """A lettering fixture must not disagree with its artwork more than the
    engine did before 768de79e moved the satin rails.

    The production change that makes this pass: satin rails that sit ON the
    letter's edge instead of ~0.3 mm outside it, WITHOUT giving back that
    commit's jitter win (which is real — check `tools/rail_edge.py` alongside,
    and do not trade one instrument for the other).

    Read the failure as SPILL, not as missing thread. `lost_frac` sums two
    opposite defects; on this fixture it is ~100% overshoot and ~0% unsewn.
    """
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"

    cfg = base_cfg(WIDTH_MM, GARMENT)
    gen, result, plan, design = digitize_once(FIXTURE, cfg)
    row = features_full(FIXTURE, cfg, gen, result, plan, design)

    lost_frac = row["lost_frac"]
    assert lost_frac is not None, (
        "dropped_elements refused to score this design, so the guard did not "
        f"run at all: {row.get('refusals')}")

    assert lost_frac <= LOST_FRAC_BAR, (
        f"lettering fidelity regression: {FIXTURE.name} at {WIDTH_MM:g} mm "
        f"disagrees with its artwork over {lost_frac:.4f} of its ink against a "
        f"{LOST_FRAC_BAR} bar (the 2026-09-02 engine measured 0.2509; the "
        f"engine measured {LOST_FRAC_WHEN_WRITTEN} when this test was written "
        f"and {LOST_FRAC_TODAY} after the two 2026-09-20 fixes).\n"
        f"Bisected to 768de79e — see this module's docstring. The rails moved "
        f"onto the nearest boundary crossing to kill jitter, and the letters "
        f"now sew about 0.3 mm FATTER than drawn.\n"
        f"READ THIS AS SPILL, NOT AS MISSING THREAD: on this fixture the "
        f"number is ~100% overshoot and ~0% unsewn, and uncovered ink actually "
        f"FELL across that commit (7.6 -> 7.5 mm2). A cure moves thread back "
        f"onto the letter's edge; it does not add coverage.\n"
        f"Do NOT raise the bar to make this pass.")
