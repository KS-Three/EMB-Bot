# Fill row spacing is settled — 0.15 mm, Kent's ruling 2026-09-03

- `machine.FILL_ROW_MM` = 0.15 (was 0.40). Evidence: his sew-out at 0.40
  showed cloth between rows; the pro's commissioned files read as ROWS are
  0.141–0.169 (`tools/row_pitch_union.py`). Standing ruling in DOCTRINE;
  ROADMAP gate 1 no longer lists fill row spacing.
- Coverage numbers changed base: one fill = `COVERAGE_FILL_LAYER_UNITS`
  (2.67 physical units); warn/block are 6.67 / 9.33. Anything quoted before
  this date is 2.67× smaller than the same stack reads now. Do not compare
  across the date without converting.
- `COVERAGE_ACROSS_SAMPLES` is 8 (was 2): two half-ribbon samples beat
  against the 0.15 pitch and read 2.4/2.8 on a plain fill. If a pitch that
  0.05 does not divide ever ships, the sampler must move again. Edge cells
  now read their true fraction, so `uncovered_*` moved a little everywhere.
- The contour tier did NOT follow: `machine.CONTOUR_RING_MM` = 0.40 keeps
  the gated-OFF ring tier and its bare-circle instrument byte-identical;
  whether rings should sit at 0.15 is that tier's instrument rebuild.
- Fill stitch counts rise 2.67×; whole designs 43–147%. Preflight grades
  held (A on the flat fixtures).
- The JS engine FOLLOWED on 2026-09-04: `src/digitize.js` now carries
  `FILL_ROW_MM = 0.15` and `SATIN_SPACING_MM = 0.4` (exported on `EMB`), and
  the one `densityMm` option that fed BOTH pitches is split into `fillRowMm`
  / `satinSpacingMm`. `densityMm` is still honoured as "both at this number"
  so every pinned snapshot is byte-identical; only the no-option default
  moved (fill 0.45 → 0.15, satin 0.4 unchanged). The Studio's image /
  manual / shape elements pass no spacing and take the engine defaults. A
  test reads machine.py and fails if the two engines drift.
- The card's block 2 now VERIFIES 0.15 rather than deciding it; its A arm
  (0.40) is the old engine, B (0.20) is coarser than the ruling.
