#!/usr/bin/env python
"""Does cropping flip `alpha_edge_extend` by moving px_per_mm across the floor?

`alpha_edge_extend_upscaled_only` gates on `alpha_edge.upscale_expected`,
which compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm`. Cropping changes that ratio. So a crop can turn the
extension on or off without anyone deciding to -- which is a flag Kent
flipped ON on 2026-09-20 precisely BECAUSE it was gated to the under-floor
regime.

Three arms, same fixture and same crop ladder:

  * SWEEP A, UNDER-FLOOR (100 mm) -- the original sweep. Becker's own
    resolution already sits at 1.45 px/mm against a 4.0 floor at this
    width, so every crop in the ladder only pushes it further under.
    `gate` cannot move here; it is a documented negative on the
    under-floor regime, not a test of the coupling.
  * SWEEP B, STRADDLING (25 mm), shipped config -- picked by discovery, not
    guessed: at 25 mm the UNCROPPED artwork reads 5.8 px/mm (gate False,
    comfortably above the 4.0 floor), and the same crop ladder that does
    nothing at 100 mm pushes it below the floor by the
    (0.2, 0.2, 0.8, 0.8) inset. This is the arm that shows the coupling
    firing -- `gate` flips here.
  * SWEEP C, STRADDLING (25 mm), `alpha_edge_extend=False` -- the
    counterfactual: same fixture, same width, same crop ladder as B, but
    with the extension forced off, so it can never apply no matter what
    the crop does to px/mm. B vs C, crop by crop, isolates what the gate
    ACTUALLY COSTS: where the two arms agree, the crop alone explains the
    move; where they diverge, the extension firing is what moved it.

Usage (cwd digitizer/):
  .venv/Scripts/python tools/crop_floor_coupling.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize          # noqa: E402
from digitizer_core.alpha_edge import upscale_expected       # noqa: E402
from digitizer_core.stage1_prep import _load, prep           # noqa: E402

# An alpha cutout under the floor at its census width: the population the
# gate was built for.
FIXTURE = "becker_marine_logo.png"
WIDTH_MM = 100.0

# Same fixture, a width discovered (not guessed) so the UNCROPPED artwork
# sits comfortably above `min_px_per_mm` (5.8 vs 4.0) -- the arm that gives
# the crop ladder a boundary to actually cross. Found by printing
# `Prep.input_px_per_mm` across a width ladder (10-100 mm): becker's
# uncropped gate flips between 35 mm (4.14, False) and 40 mm (3.62, True),
# so 25 mm leaves headroom on the False side for the crop ladder to close.
STRADDLE_WIDTH_MM = 25.0

# Shared crop ladder for both sweeps: no crop, an explicit full-frame crop
# (inertness control), then progressively tighter insets.
CROPS = (None, (0.0, 0.0, 1.0, 1.0), (0.1, 0.1, 0.9, 0.9),
         (0.2, 0.2, 0.8, 0.8), (0.3, 0.3, 0.7, 0.7))


def run_sweep(fixture: str, width_mm: float, label: str,
              *, alpha_edge_extend: bool = True) -> tuple[bool, list[tuple]]:
    """Runs the crop ladder at one target width; returns (whether `gate`
    changed across it, the per-crop rows for a caller to compare)."""
    art = ROOT / "testdata" / fixture
    print(f"{label}: {fixture} @ {width_mm} mm\n")
    print("{:>26}{:>10}{:>9}{:>9}{:>9}{:>8}".format(
        "crop", "px/mm", "gate", "regions", "stitches", "trims"))
    gates = []
    rows = []
    for crop in CROPS:
        cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest",
                             crop=crop, alpha_edge_extend=alpha_edge_extend)
        _rgb, alpha = _load(art, cfg.strip_letterbox, cfg.crop)
        gate = (upscale_expected(alpha, cfg.target_width_mm, cfg.min_px_per_mm)
                if alpha is not None else None)
        # `input_px_per_mm` is what the SOURCE delivered for this crop, before
        # the floor upscale -- which is the number the gate compares, so it is
        # the one to print. `px_per_mm` would show the post-upscale value and
        # make the gate look inconsistent with its own input.
        ppm = prep(art, cfg).input_px_per_mm
        result, plan = digitize(art, cfg)
        gates.append(gate)
        row = (str(crop), ppm, gate, len(result.regions),
               plan.stats.stitch_count, plan.stats.trims)
        rows.append(row)
        print("{:>26}{:>10.2f}{:>9}{:>9}{:>9}{:>8}".format(
            row[0], row[1], str(row[2]), row[3], row[4], row[5]))
    moved = len(set(gates)) > 1
    print(f"\n`gate` {'CHANGED' if moved else 'held constant'} across this sweep.")
    return moved, rows


def run_counterfactual(b_rows: list[tuple]) -> bool:
    """SWEEP C: same fixture/width/crop ladder as sweep B, `alpha_edge_extend`
    forced off so the extension can never apply. Prints C's own table, then a
    B-vs-C diff per crop -- agreement means the crop alone explains sweep B's
    move at that row; divergence is the gate's own contribution. Returns
    whether any row diverged."""
    print()
    _, c_rows = run_sweep(FIXTURE, STRADDLE_WIDTH_MM,
                          "SWEEP C (straddling, alpha_edge_extend=False)",
                          alpha_edge_extend=False)
    print()
    print("SWEEP B vs SWEEP C -- same crop, same width, only "
          "alpha_edge_extend differs:")
    print("{:>26}{:>9}{:>10}{:>10}{:>9}{:>9}{:>9}{:>9}".format(
        "crop", "gate", "B stitch", "C stitch", "d_st", "B trim",
        "C trim", "d_trim"))
    diverged = False
    for b, c in zip(b_rows, c_rows):
        crop, _ppm, gate, _b_reg, b_st, b_tr = b
        _c_crop, _c_ppm, _c_gate, _c_reg, c_st, c_tr = c
        d_st, d_tr = b_st - c_st, b_tr - c_tr
        if d_st != 0 or d_tr != 0:
            diverged = True
        print("{:>26}{:>9}{:>10}{:>10}{:>9}{:>9}{:>9}{:>9}".format(
            crop, str(gate), b_st, c_st, d_st, b_tr, c_tr, d_tr))
    print(f"\nSweep B/C {'DIVERGED' if diverged else 'agree'} on at least one row.")
    return diverged


def main() -> int:
    under_floor_moved, _ = run_sweep(FIXTURE, WIDTH_MM, "SWEEP A (under-floor)")
    print()
    straddle_moved, b_rows = run_sweep(FIXTURE, STRADDLE_WIDTH_MM,
                                       "SWEEP B (straddling, shipped)")
    counterfactual_diverged = run_counterfactual(b_rows)
    print("\nA `gate` column that CHANGES across crops is the coupling firing.")
    print(f"Sweep A moved: {under_floor_moved}. Sweep B moved: {straddle_moved}. "
          f"B/C diverged: {counterfactual_diverged}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
