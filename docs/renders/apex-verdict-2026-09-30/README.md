# The A's apex is a real hole — 2026-09-30

Kent's pick, 2026-09-30: *"Settle whether the apex is a real defect."* Two
instruments disagreed. `tools/bare_anatomy.py` reported a **3.61 mm²** gap at
the apex of ENTHUSIAST's **A**; `tools/dropped_elements.py`'s `unsewn_frac`
read **0.0000** on that fixture in every arm. One of them had to be wrong.

**Verdict: the hole is real, `bare_anatomy` over-reports it by 1.7x, and
`unsewn_frac` is structurally incapable of seeing it.** Defect 49 stands.

## The pictures

`apex_thread_path.png` — a 6.4 mm crop at 60 px/mm, three panels
(`tools/thread_path_render.py enthusiast`):

| | |
|---|---|
| left | the stitch-out as the Studio previews it (`lit=True`) |
| middle | the same design on **magenta** cloth, unlit — every magenta pixel is cloth no thread reached |
| right | the middle panel with the shape's **artwork polygon** outlined in black |

`apex_context.png` is the same three panels over 13 mm, for where the letter
sits. `apex_outlined.png` is the right-hand panel on its own.

**Why these count as evidence and the 2026-09-29 render did not.** That render
drew the same shapely cross-buffers `bare_anatomy` measures, so the picture and
the number were one model restated — it could not disagree with itself. Every
panel here comes out of `stitchviz.render_design`, which walks the design's
actual stitch stream (underlay, run, travel and fill included) and breaks the
thread at jumps and trims. Nothing here buffers a cross.

Panel 2 is a **picture, not a measurement**: `stitchviz.coverage`'s docstring
rejects a sentinel background as a metric, because anti-aliased fringe reads as
bare in one direction and as covered in the other. The numbers are below.

## The numbers

Shipped engine, ENTHUSIAST at 80 mm `left_chest`
(`satin_rail_comp` ON, `satin_tip_caps` ON, 2,474 stitches, 15 trims):

| reading | value |
|---|---|
| `bare_anatomy` worst component, satin only | **3.61 mm²**, max inscribed half 0.706 mm |
| the same region against **every** thread kind | **2.17 mm²**, largest connected part 1.93 mm² @ 0.464 mm |
| — of which underlay covers | 1.39 mm² (38.4%) |
| — of which travel covers | 0.17 mm² (4.7%) |
| — fill, run | 0.00 mm² |
| after a 0.50 mm morphological opening | **1.72 mm² — survives** |
| `dropped_elements` `uncovered_worst_mm2` | **0.97 mm²**, at (23.09, −3.48) mm |
| the apex component's centroid (shapely) | (23.05, −3.16) mm — **0.33 mm away** |
| `uncovered_elements` (threshold `MIN_ELEMENT_MM2` 1.0) | **0** |
| `lost_frac` | 0.2573 = unsewn **0.0000** + overshoot 0.2573 |

Two instruments that share no code agree on the location. `bare_anatomy` works
in shapely on the plan's geometry; `dropped_elements`' `uncov = A_ink & ~thread`
is a raster mask difference over a `stitchviz` render at 10 px/mm, with no
CIEDE2000, no opening and no colour. Its **largest uncovered-ink component in
the whole design** sits 0.33 mm from the apex. The next one is 0.70 mm² and
**35 mm away**.

## Why `unsewn_frac` reads 0.0 and always will here

Three independent reasons, none of them "the engine is fine":

1. **The on-ink vote cannot fire on this fixture.** `unsewn_frac` classifies a
   *disagreement region* as on-ink by `A_ink[region].mean() > 0.5`, and on
   ENTHUSIAST the largest per-region ink fraction is 0.33. The tool's own
   docstring says so: *"it could not have returned True whatever the engine
   did."*
2. **It is a fraction of a total the pedestal dominates.** ENTHUSIAST's
   `lost_frac` is 100% overshoot — `pique_knit`'s `pull_comp_mm` 0.30 plus
   `stitchviz.THREAD_MM` 0.40 puts a correctly-sewn shape 0.50 mm proud of its
   artwork. A 1 mm² hole is ~0.2% of that total.
3. **`uncovered_elements`, the reading built to say "an element was lost",
   misses it by 0.03 mm².** The apex is the largest uncovered component in the
   design at 0.97 mm²; `MIN_ELEMENT_MM2` is 1.0. That threshold was set to
   separate an element from a rim, and this is a 1 mm notch at the peak of a
   capital letter — it is neither.

`uncovered_worst_mm2` **is** sensitive here and is the reading to watch when a
build tries to close the apex. `unsewn_frac` is not, and a future session
should not take its 0.0 as evidence that nothing is missing.

## What this does NOT overturn

The 2026-09-30 retraction stands. The widened gate was retracted because it
pushed `lost_frac` 0.2573 → 0.2661 past the bar in
`tests/test_lettering_coverage_regression.py`, at 100% overshoot — it bought
this hole by spilling more thread outside the artwork elsewhere. That trade was
bad and is still bad. What this settles is only that the hole it was aimed at
is real, so defect 49 is a defect and not an artefact.

## Reproduce

```bash
cd digitizer
.venv/bin/python tools/bare_anatomy.py enthusiast --arms on              # 3.61
.venv/bin/python tools/bare_anatomy.py enthusiast --arms on --all-thread # 1.93
.venv/bin/python tools/thread_path_render.py enthusiast --out /tmp/apex
.venv/bin/python -m pytest tests/test_apex_is_real.py -q
```
