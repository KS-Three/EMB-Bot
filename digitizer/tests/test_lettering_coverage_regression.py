"""The coverage guard that commit 768de79e did not have.

**Why this exists.** 768de79e (2026-09-03, defect 23, *"an overshooting rail
goes onto the artwork edge instead of stepping in by 15%"*) replaced
`_rail_points.place`'s 0.85x ladder with placement on the nearest boundary
crossing. It measured itself thoroughly — rail jitter, median cross width,
same-rail holes, thread, wall time — and every one of those improved
(ENTHUSIAST jitter 0.0421 -> 0.0241 mm). It did not measure COVERAGE, and
coverage is what it cost.

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
(2356 -> 2349): it does not add or remove thread, it moves rails, and the
artwork they no longer cover is the cost. The commit's own message records the
residual and left it open: *"The 8-24% of lettering rail points still > 0.1 mm
inside the art are the symmetric-offset rail model ... recorded open, Kent's
call."*

**Three flags were tested one variable at a time and NONE recovers it**
(2026-09-20, today's engine, `enthusiast`): `design_ramp=False` and
`keep_thin_strokes=False` are byte-identical to the shipped default;
`curve_turn_deg=None` recovers about a quarter of the gap (0.3006 -> 0.2889)
and makes `hausdorff_mm` worse. `satin_rails_follow_edge=True` — the "open
half" of defect 23 — makes `lost_frac` WORSE still (0.3555), while improving
the geometric bare-area reading (3.94% -> 3.31%). So this is unconditional
code, not a toggle, and the two coverage instruments disagree about the cure.

**What this test pins, and what it deliberately does not.** It pins
`lost_frac` — `tools/dropped_elements`, per-pixel CIEDE2000 between the
artwork painted on white cloth and the RENDER, opened at half a millimetre —
because that is the metric that moved and the one a customer sees. It does NOT
pin `rail_edge --bare` (geometric, satin-scoped), because the two disagree
under `satin_rails_follow_edge` and picking the one that flatters a fix is how
this repo has been burned before. A cure must move THIS number; if someone
argues bare-area instead, they are changing the claim, not passing the test.

**This is a RED test on purpose.** It is expected to fail on today's engine.
Do not "fix" it by moving the bar. See the caveats below before touching it.
"""
from __future__ import annotations

from pathlib import Path

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
# from a full one rather than reading a bare pass/fail.
LOST_FRAC_TODAY = 0.3006


def test_lettering_coverage_has_not_regressed_since_the_rail_change():
    """A lettering fixture must not lose more artwork than the engine lost
    before 768de79e moved the satin rails.

    The production change that makes this pass: satin rail placement covering
    letter strokes as completely as the pre-2026-09-03 engine did, WITHOUT
    giving back that commit's jitter win (which is real — check
    `tools/rail_edge.py` alongside, do not trade one instrument for the other).
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
        f"lettering coverage regression: {FIXTURE.name} at {WIDTH_MM:g} mm "
        f"loses {lost_frac:.4f} of its ink against a {LOST_FRAC_BAR} bar "
        f"(the 2026-09-02 engine measured 0.2509; today's shipped engine "
        f"measured {LOST_FRAC_TODAY} when this test was written).\n"
        f"Bisected to 768de79e — see this module's docstring. The rails moved "
        f"onto the nearest boundary crossing to kill jitter and stopped "
        f"covering the letter strokes.\n"
        f"Do NOT raise the bar to make this pass.")
