---
name: bridge-anchor-wave-weld-2026-11-10
description: Bridge anchor's "extra arms/legs" = the two wave lines welded to it in the 400 px JPEG (gaps under 1 px); one black component from stage 2 on; Kent 11-10 "Keep as manual edit", no build
metadata:
  type: project
---

Kent 2026-11-10: "the bridge Bar anchor ... always has extra arms/legs that
don't exist in the logo itself". Measured on main `950855bf`, the Studio
request (`tools.pro_pair.request`), `testdata/photo/logo_bridge_bar.jpg` at
64 hat / 76.5 left chest / 113.5 hat.

- **The limbs are the waves.** The art is 400 px; the anchor is ~40 px tall,
  strokes 2.8-4 px, and the gaps between the two wave lines and the anchor are
  under one pixel. At a luminance threshold of 110-140 the bowl, both waves and
  the anchor are ONE connected component in the source itself. The engine
  traces one black region (88 / 127 / 276 mm2) and sews one satin network: the
  upper wave reads as two arms off the ring, the lower as two legs off the
  flukes.
- **The joins are blur, not ink.** At threshold 80 (dark cores only) the same
  window is 5 components.
- **Fattening adds to it at hat size.** 64 mm: art stroke 0.58-0.81 mm, sewn
  0.98 (pull 0.4 in it); fluke cells shrink to pinholes, the crossbar to stubs.
  113.5 mm: art 1.02-1.43, sewn 1.72; the shape reads, the limbs stay.
- Not stage 6/7: stage 5 geometry already matches the traced blob.

**Kent's ruling 2026-11-10: "Keep as manual edit".** No engine build. The
costed alternative he passed over: an OFF flag that cuts thin black line art
where a join is lighter than the stroke cores (risk: cuts real joins on other
logos; does not touch the fattening). Not tested: whether a larger or vector
source separates on its own.

**Why:** the weld is in the upload's pixels; the pro redrew the art with no
waves at all ([[border-from-outline-line-art-guard-2026-10-25]]).

**How to apply:** do not open a Bridge-anchor engine task from this symptom;
point to the Studio edit (delete or reshape the waves) or ask for a bigger
source. **Trap hit:** a bare `PipelineConfig(target_width_mm=...)` run is NOT
what the Studio sends (`max_colors` 12 against 6, no garment): it gave 10-11
threads and olive/green ramp strokes over the anchor, a different defect from
the one Kent sees. Reproduce a Studio complaint with `pro_pair.request`.

Related: [[bridge-census-2026-10-27]], [[flat-fringe-soft-ramp-2026-11-06]],
[[tm-mark-golden-tee-2026-10-26]].
