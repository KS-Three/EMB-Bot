# Digitizer Step 4 — Satin Subsystem (written with the work, 2026-07-30)

Blueprint: Kent's Auto-Digitizing Engine Blueprint v2.1/v2.2. Builds on steps
1 and 3. This doc records what was built and why, including the defects found
and fixed along the way — it was written alongside the implementation rather
than ahead of it, at Kent's "just go" direction.

## What satin is here

Ribbons (lettering, borders, thin strokes) sew as zigzag columns perpendicular
to a medial-axis spine, not as tatami fill. Classification is per shape:
`is_satin_candidate` = ribbon width (2·area/perimeter) ≤ 3.0 mm AND estimated
length ≥ 3× width. Classified on the ARTWORK polygon so fabric choice (pull
comp) cannot flip the same logo between satin and fill structures; sewn on the
stage-5 grown polygon.

## Pipeline (stage6_satin.py)

raster (adaptive scale: ≥8 px across the ribbon wall, capped 900 px) →
`skimage.medial_axis(rng=0)` (skeleton + distance transform = free local
half-widths) → crossing-number node detection → spur pruning → edge walk →
junction welding → per-stroke: smooth, trim node ends to junction edge + 0.4 mm
tuck, extend free ends to the cap, resample at 0.4 mm, unwrapped smoothed
normals, ray-cast rails capped to the local corridor, short-stitch guard,
zigzag emit. Underlay (center_run / zigzag per fabric preset) from the same
spines, inset inside the column.

## Defects found by smoke-testing and adversarial review (all fixed + pinned)

1. **Unseeded `medial_axis` is nondeterministic** — random tie-breaking gave
   different skeletons per call; same artwork digitized to different stitches.
   `rng=0`. This would have shipped without the determinism test.
2. **Phantom closed loops** (review's confirmed-high): the cycle scan closed
   any leftover path unconditionally, sewing a satin band across up to 12 mm
   of bare fabric. Cycles now close only if the walk returns to its start.
3. **Node-slip double emission**: the walk could step diagonally past a
   junction pixel and re-traverse another stroke's corridor — up to 4×
   multiplicity, 2.2× thread density on Arial glyphs. Walks now stop at any
   node neighbour and consume non-node pixels globally.
4. **Merge orientation**: welding chains through junctions oriented by the
   original edge's flags, wrong after the first weld. Now oriented by the weld
   node pixel itself.
5. **Cap loss**: medial axis stops half a width inside each cap AND the old
   end-trim cut further — 1.8 mm bare fabric per bar end. Free ends now extend
   to the boundary; the terminal cross lands on the cap corners (square end).
6. **Corridor cap ate cap crosses** (distance transform ≈ 0 on the boundary):
   floor at 0.75× stroke half-width.
7. **Rail smoothing stretched past the boundary** where the ribbon narrows:
   smoothing may only shorten (clamp to the ray hit).
8. **Fallback rails could land outside the shape**: shrink until covered.
9. **Underlay runs chained needle-down across gaps** (>12.1 mm DST ceiling on
   wide letters): every consecutive run pair is now linked with jump/trim, and
   `report["jumps"]` counts every lift, matching the fill path.
10. **The O shattered into 300 identical loops** (snapshotted candidate list),
    and thin ribbons (<8 px) shattered into confetti (raster scale now adapts).
11. **T sewed as two half-bars with a mid-bar gap** after junction yielding:
    collinear arms (tangent dot < −0.5) weld into one through-stroke; only
    true side-arms yield. An X sews as one through diagonal + two tucked arms
    — the professional treatment.

## Known limitations (accepted for step 4)

- Corner-hit geometry leaves ~0.1–0.25 mm at cap corners vs the theoretical
  edge (inside test tolerance, invisible on fabric).
- No slant (italic) satin — the browser engine has it; port when lettering
  integration (step 10) needs it.
- Junction fan on an X's through-stroke: crosses fan slightly where the spine
  bends through the crossing. Sews correctly; a human digitizer's X does the
  same.
- `SHAPE_TOO_THIN_TO_FILL` now means "thin but not stroke-like enough for
  satin" — compact thin blobs, worth review-screen eyes.

## Verification

51 → 69 tests. New: classification, perpendicularity, cap coverage, density,
escape containment, DST ceiling, O=1 closed loop, T=through-bar+stem, stem
tuck, short-stitch guard, underlay containment, report contract, degenerate
sliver, skeleton-prunes-away fallback, same-shape determinism (incl. T),
plus the cross-process DST byte-identity check run manually.
