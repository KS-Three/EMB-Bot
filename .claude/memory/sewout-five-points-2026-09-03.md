# The five sew-out findings, and the density story finally read as rows — 2026-09-03

Kent redirected: *work on the general tool, logos are reference points.* He
brought five findings another Claude chat made from his sew-out macros. Record:
`docs/sewout-findings-2026-09-03.md`. What changes what you do:

- **Density is settled as a MECHANISM, not yet as a constant.** Read as rows
  (`tools/row_pitch_union.py`, the union of every pass), the professional's
  fills are **0.14–0.17 mm** adjacent-row pitch on three commissioned files;
  ours 0.40 everywhere, blend bands included. `fill_pitch.py`'s per-pass
  autocorrelation over-reads a pro tatami ~2.7× (penetration cycle), which is
  why scope-history 09-02 said the pro "does not support half coverage" —
  retracted. Do not quote the per-pass number for a professional file. Gate 1
  still sets `FILL_ROW_MM` by cloth; the card's block 2 arms (0.40 / 0.20 /
  interleave) stop short of the pro's 0.15 — add an arm before sewing it.
- **Seams:** stage 5 already underlaps earlier-under-later by `overlap_mm`
  0.25 — "no overlap" is false in code; whether 0.25 survives pique pull is
  untested, and the card has no seam block. Blend bands overlap 2% of ramp;
  same-thread shapes have no seam logic.
- **Palette on the sew-out was operator threading** (DST carries none) — not
  a defect; do not chase defect 16 for it.
- **Blocky bands = SLIC superpixels splitting a smooth ramp** on the gradient
  lane (repro: 10 regions for a 2-element icon); the blend bands themselves
  follow the ramp. The fix is routing (one region per connected colour area
  when the design ramp fits), Kent's call.
- **Trims:** the plan trims every jump > 3 mm; DST trims are 3 jump records
  (pystitch `trim_at`); tails on cloth are a machine setting or uncut ends.
