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

---

## ADDENDUM 2026-09-22 — SUPERSEDED. `subpixel_edges_upscaled` already cured this.

**Do not build the resolution-floor raise this document recommends.** The
cliff it measures was cured on 2026-09-18 by Kent's flip of
`subpixel_edges_upscaled` — two days after this was written — and the
`upscale_8` arm no longer stabilises anything. Everything above was TRUE WHEN
WRITTEN; none of it is true of today's engine.

Re-measured 2026-09-22, same fixture, same tool, 80–100 mm step 1,
`left_chest`:

| arm | span | worst 1 mm step |
|---|---|---|
| `shipped` — **as this doc measured it, 2026-09-16** | 0.080–0.482 (0.402) | 0.288 at 87→88 |
| `shipped` — **today** | 0.400–0.571 (**0.171**) | **0.076** at 81→82 |
| `upscale_8` — **as this doc measured it** | 0.118–0.149 (0.031) | 0.018 |
| `upscale_8` — **today** | 0.356–0.559 (**0.203**) | 0.066 at 80→81 |
| `subpixel_edges_upscaled=False` | 0.132–0.652 (**0.520**) | **0.425** at 88→89 |
| `alpha_edge_extend=False` | 0.377–0.565 (0.188) | 0.055 at 93→94 |
| both off | 0.133–0.645 (0.512) | 0.389 at **87→88** |

**Attribution is clean.** Turning `alpha_edge_extend` off leaves the cliff
cured (0.188). Turning `subpixel_edges_upscaled` off brings it back at 0.520
— *larger* than this doc's original 0.402 — and "both off" reproduces the
cliff at **exactly the 87→88 mm step** named above. This doc's `shipped`
column is the pre-flip engine, nothing more.

`alpha_edge_extend` was the obvious suspect and it is the wrong one: it
flipped ON 2026-09-20 (`be347512`) gated precisely to the under-floor
upscale, which is becker and nothing else here. Measured, not assumed.

**Three consequences.**

1. **`upscale_8` is now a REGRESSION on the statistic this doc is about** —
   span 0.203 against shipped's 0.171. It no longer cures the cliff because
   there is no longer a cliff to cure.
2. **§"The sting" no longer holds.** The predicted collapse to a stabilised
   low-satin state (0.118–0.149, "becker loses two thirds of its satin") does
   not happen: at 100 mm the floor raise moves becker 0.409 → 0.356. The
   argument that this lands on `SATIN_MAX_WIDTH_MM` still stands on its own
   evidence (the 5.4–7.1 mm census) — but it is no longer *this* change that
   forces the question.
3. **`min_px_per_mm` is not one knob, and this doc's recommendation never
   said so.** `alpha_edge.upscale_expected` (called at `alpha_edge.py:107`)
   gates `alpha_edge_extend_upscaled_only` on `cfg.min_px_per_mm`. Raising
   the floor 4.0 → 8.0 therefore widens `alpha_edge_extend`'s reach to every
   alpha cutout between 4.0 and 8.0 px/mm — a default flip nobody decided,
   travelling on a constant. Anyone who does move this floor in future must
   price that half separately.

**The general lesson, which is the part that survives.** A doc that names a
cure is executable, and this one was executed six days later against an
engine that had moved underneath it. The tell was cheap and was available
before any code changed: *re-run the instrument the doc names and check its
own baseline row still reproduces.* One 15-minute run of
`tools/classifier_cliff.py` would have caught it. Same class as
`crossval-stitch-formats.mjs` telling its reader to un-fix the DST axis
(memory: `stale-diagnostics-and-two-flips-2026-09-13`).

*(measured 2026-09-22 — `tools/classifier_cliff.py` for the first two rows;
the three attribution arms on a throwaway driver with the identical `_one`
measurement, since `classifier_cliff.ARMS` cannot be monkeypatched across a
`ProcessPoolExecutor` on Windows)*
