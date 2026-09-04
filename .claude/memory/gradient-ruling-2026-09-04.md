# The gradient ruling — one region when the design ramp fits — 2026-09-04

Kent's third ruling of 2026-09-03 (the sew-out's "blocky bands"), landed
2026-09-04 after an adversarial review and an independent geometry audit.

- **`design_ramp.py` is the gate and the model.** Gate = a trimmed (75%)
  then consensus (3 robust sigmas, floor 2) PLANE per Lab channel on the
  stitched foreground: consensus r² ≥ 0.4, inlier fraction ≥ 0.6, sigma ≤
  4.0, a sweep ≥ 9 in the winning channel, linear beating radial; winner =
  best r² among channels passing all of it. Repro L 0.80 / 0.78 / 2.3
  passes; `gradient_ramp_linear` passes; `region_blobs` (a 0.49 / 0.88 /
  **9.2**) and Kent's owl (L 0.60 / 0.71 / **5.4**) are refused on scatter;
  every busy logo on r². The sigma gate is the one that matters.
- **Colour = a PROFILE along the sweep** (consensus median in 17 bins of
  t), not the plane: the repro is a hue arc in a*b* (plane scatter 7.9 /
  9.4, profile 0.3 / 0.4). Stage 2 subtracts the profile; `rides` measures
  against it. Do NOT gate on the profile — the owl's L* profile scatter is
  3.6 and it would pass. The ramp's range is the whole foreground's, not
  the sample's (a sample misses a diagonal's corners by 6 mm).
- **The plain fit had silently stopped applying at Studio defaults.** The
  repro is full-bleed; stage 1 refuses to flood it (BACKGROUND_ABSENT, the
  2026-08-11 guards), the white icon is foreground, and the 2026-08-03
  design angle read L r² 0.03 and returned None on its own repro. The test
  passed because it turns the guards off. Now pinned at defaults. The plain
  fit stays as the ANGLE fallback when the gate refuses (`region_blobs`
  keeps -89.7°; without it four blobs sewed at four angles).
- **Stage 2 flattens; stage 6 rides; stage 7 lets it.** `blend_fill` asks
  `region_rides_design_ramp` (≥ 80% of samples within tolerance in all
  three channels AND mean colour within one shade step of the profile —
  the second guard refuses a badge of another hue at the sweep's L*) and
  sews the design's bands via `design_shade_scheme`; the first and last
  bands absorb a region reaching past the range. A riding region skips the
  satin rung (the repro's outer 3.5 mm strip was satin in one thread,
  fuchsia where the source is orange); forced "satin" still wins.
- **Two bugs found on the way, both real on any decomposed region:**
  `_band_clip` anchored a linear ramp's strip on the polygon's bbox centre
  (fixture shifted 30 mm: first band empty, a third less thread; IN SITU
  `gradient_ramp_linear` at 80 mm never sewed 46% of its ramp on the
  committed engine, suite green). And bands sewed at `FILL_ROW_MM * n`
  since the tier's first commit (3ddb87d) — one sparse layer per band
  (union pitch 0.75 on a five-shade fixture, coverage 0.54); the
  plan-contract test weighted each row by n rows and read 1.0. PR #339's
  preflight exemption for shade layers rested on that false premise and is
  gone; `machine.py`'s "union at this pitch" comment corrected.
- **Numbers at 80 mm / left chest:** repro 10 → 8 regions, three ramp
  pieces decompose into five shades (were flat / one-thread satin), rows at
  134°, 16,925 → 21,008 stitches, 3 → 5 blocks; `gradient_ramp_linear` 2 →
  1 region, 1,433 → 9,607 stitches; `region_blobs` untouched by the gate,
  5,250 → 17,072 stitches (bands at the row), angle kept. drone/summit/owl
  byte-identical.
- **Seen, not fixed:** stage 7 hands `blend_fill` the ARTWORK polygon, not
  stage 5's compensated one — blend regions got no pull comp and no seam
  tongue (every gradient seam was a butt joint; Kent's finding 2). **Fixed
  2026-09-04 on his pick:** `blend_fill(polygon=)`, stage 7 passes
  `p.polygon`, colour still from the artwork; the seam instrument reads the
  PLAN and never saw it — `tools/sewn_compensation.py` reads the stitches
  (repro strips 29% → 100%). Costs the repro 4 trims (22 → 26), three of
  them stage 5's own holes/corridor in the sewn outline.
  `result.palette` lists one thread per LAYER; shade threads live on the
  blocks (DST and download read blocks — always right).
- **Radial design ramp built 2026-09-04:** `design_ramp.py` fits a radial
  model too (GN centre, consensus line in radius, profile along radius),
  gated r² ≥ 0.6 + ≤ 2 of 17 blank radius knots + centre no farther
  than one sweep from the foreground (`lo ≤ hi − lo`; a bbox test was
  knife-edge for a half-disc or corner glow); wins only when it beats
  the plane. `gradient_ramp_radial`
  2 → 1 region, 5 shades. `row_angle_deg` is 0.0 for radial (non-riding
  regions sew level). Pass side calibrated on one synthetic fixture — a
  real radial logo is the missing evidence; do not loosen the gate for it. Since 2026-09-04
  the service sends `stats.blocks` (plan.palette + shape_ids) and the
  Studio's Sequencer/quality report/`reviewFromJob` read it. A radial design ramp is still the
  documented gap.
- **Feathered seams built 2026-09-04 (his call):** a 1.5 mm zone per seam
  sewn by both shades on one row lattice, alternating row by row, via a
  row filter on one fill per band (`stitch_shape(keep_row=, row_phase_mm=)`,
  both byte-identical unset). Only where rows run along the seam (the
  design path); crossing rows keep the hard seam. Separate zone pieces
  cost 52 trims vs 23 — do not go back to that. `blend_feather_mm=0` is
  the hard lane. Every band of a region is on ONE row lattice now.
