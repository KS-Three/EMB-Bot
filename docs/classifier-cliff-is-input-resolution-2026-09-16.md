# The satin/fill size cliff is an input-resolution artefact, not a threshold problem

Kent asked for a margin rule. The measurement says a margin is the wrong fix,
names what the cliff actually is, and hands the remaining question to the one
number that is frozen.

## The defect, restated

Resize the same artwork by a millimetre and the design changes character:
becker at 87 mm sews 12 satin shapes of 18 and 7,567 stitches; at 88 mm it
sews 10 and **13,402**. The 2026-09-12 gap audit measured the swing at ≥ 17
points of sewn satin share over nine 1 mm steps and called it *"a sub-pixel
raster artefact"*, with area-weighting as the surviving candidate cure.

`tools/classifier_cliff.py` measures it directly: one fixture, every
millimetre, the SEWN satin share read off the emitted plan.

## Four candidate cures, three refuted

Becker, 80–100 mm unless noted. "Worst step" is the largest 1 mm move, which
is the statistic the cliff is about.

| arm | span | worst 1 mm step | verdict |
|---|---|---|---|
| shipped | 0.080–0.482 (0.402) | 0.288 at 87→88 | the defect |
| `classify_area_weighted` | 0.097–0.482 (0.385) | 0.288 at 87→88 | **no effect** |
| three-pitch median (prototype, reverted) | 0.080–0.482 (0.402) | 0.292 at 87→88 | **no effect** |
| simplification scaled to design size | 0.085–0.472 (0.387) | 0.310 at 87→88 | **no effect** |
| **resolution floor 8 px/mm** (85–90 mm) | 0.118–0.149 (**0.031**) | **0.018** | **cures it** |

**Why a margin cannot work.** The gate metrics do not DRIFT across their
thresholds, they JITTER. The rope border's `explained`, every 0.5 mm from 86
to 89: 0.8172, 0.8082, 0.8057, **0.7937**, **0.7943**, 0.8279, 0.8248 — under
the 0.80 promote floor at 87.5–88.0 and back ABOVE where it started at 88.5.
The 266 mm² shape's p90 jitters 4.77, 5.00, **5.22**, **5.01**, 4.92 across
the 5.0 mm cap. A widened threshold moves the edge to wherever the jitter
lands next; it does not make the reading stable.

## What it actually is

Cliff amplitude is not a smooth function of source resolution — it is
concentrated on the artwork that stage 1 has to invent:

| fixture | source px/mm at 80 mm | span, 85–90 mm | worst 1 mm step |
|---|---:|---:|---:|
| `becker_marine_logo` | **1.8** | 0.301 | **0.288** |
| `logo_bridge_bar` | 5.0 | 0.053 | 0.053 |
| `logo_gaulke_roofing` | 16.1 | 0.072 | 0.063 |
| `enthusiast_logo` | 17.5 | 0.090 (85–95 mm) | 0.044 |

Becker is **4–6× more unstable than any other fixture measured**, and it is
the corpus's only source far below `min_px_per_mm` = 4.0 (146 × 91 px — its
own `INPUT_LOW_RESOLUTION` warning fires at 1.81 px/mm, defect 32). Stage 1
Lanczos-upscales such a source to the floor, so the upscale FACTOR changes
with every target width and the vectorizer traces a differently-invented
polygon at each size. Pinning the floor at 8 px/mm stops the factor moving
and the cliff goes with it: **span 0.301 → 0.031, worst step 0.288 → 0.018.**

## The sting, and where it leaves the question

The stabilised state is the LOW-satin one — 0.12–0.15 against the shipped
0.36–0.43. At 8 px/mm becker's letters are measured at their true width, and
`docs/quality-review-2026-09-08.md` §2b already established what that width
is: MARINE's letters are **5.4–7.1 mm columns**, refused by
`SATIN_MAX_WIDTH_MM` = 5.0 as `dt_p90_cap`. So the high-satin readings at
85–87 mm were the coarse raster under-reading a letter's width, not a
verdict worth stabilising.

That lands the question on the cap, where the census already put it: the pro
satins those letters (his own p90 is 5.00 mm with a tail to 9.1), we refuse
them at 5.0, and **the number is frozen behind gate 1 until a sew-out settles
it**. Nothing in the classifier can route around that.

## What not to build

- A margin, dead-band or hysteresis on `_PROMOTE_EXPLAINED_MIN`,
  `SATIN_MAX_WIDTH_MM` or the cv gate. Measured: the jitter is the same size
  as the gap, so the edge just moves.
- A finer classifier raster alone (the three-pitch median). Built, measured,
  reverted — it re-reads the same invented polygon.
- Scaling `simplify_tol_mm` with the design. Measured, slightly worse.

## What might be worth building, and its price

Raising `min_px_per_mm` / `upscale_cap` is a real cure for the instability,
and it is a PRODUCT call, not a tuning one: it re-tiers every design whose
source sits under the floor (becker loses two thirds of its satin share), it
costs upscale time on every such job, and it makes the engine's verdict match
what the low-resolution source actually supports rather than what a coarse
raster suggested. Kent's, with a render and a sew-out behind it.

*(measured 2026-09-16 — `tools/classifier_cliff.py`, arms `shipped`,
`area`, `tol_scaled`, `upscale_8`; the three-pitch median was prototyped as
`cfg.classify_multiscale` and reverted in the same session)*
