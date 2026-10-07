# Letterform priors: refit a low-res letter to lines and arcs before construction (2026-10-06)

**Status: built, wired DEFAULT OFF (Kent's option A, 2026-10-06), judged on
thread pairs.** The geometry and the word prior are
`digitizer/digitizer_core/letterform_priors.py`; the pipeline runs them only
when `PipelineConfig.letterform_priors_k` is set (None by default: the module
is never imported, the output byte-identical — see "The wiring" below for
the proof). No default changed, no stage-6 edit, nothing sewn. The spike's
tools in `digitizer/tools/letterform_priors_spike/` (run, refit, pro, sheet,
batch) import the engine module — one copy of the code. The inputs
(`<logo>.pkl`, `<logo>.result.pkl`), every sheet and every batch JSON live in
`scratch_letterform_priors/` in the lane's worktree, gitignored and NOT
backed up: they hold client artwork and this repo is public. `run.py`
regenerates the inputs (about 7 minutes for all seven on Kent's box).

## The wiring (2026-10-06, after the spike)

- **Flag:** `PipelineConfig.letterform_priors_k: float | None = None`. The
  value is k, the cap in source pixels; 0.75 is the measured one. None is
  off. The config docstring carries the why, the measurements, the price
  and the held-out fixture.
- **Insert point:** `pipeline.build_generation`, after `detect_text_clusters`
  and `regularize_text_clusters` (the tagger and the rescued-door redraw)
  and BEFORE `ocr_suggest_text`, `set_lettering_house_angle` and
  `measure_stitch_widths`, so the OCR read, the house angle (`satin_house_
  from_line` / `satin_house_anchor`) and the width measurement all see the
  polygon that will sew. `src_px_mm = 1 / Prep.input_px_per_mm`,
  `grid_px_mm = 1 / Prep.px_per_mm`. Text-tagged members only; a refused
  letter untouched; `shape_id` and `meta` preserved; the outcome written to
  `meta["letterform_prior"]` as `refit`, `pass:grid` or `refused:<why>`.
- **OFF is byte-identical, proved two ways:** the module is imported inside
  the flag's branch only (an AST check pins it, and an OFF run leaves it out
  of `sys.modules`); and the OFF run on the wired tree hashes every Becker
  region's WKB identically to the pre-wiring `d4c521ec` run
  (`c8fe028706f69cce`, 17 regions, measured 2026-10-06).
- **Tests** (`tests/test_letterform_priors.py`, 15): the eight geometry tests
  above; OFF never imports; ON refits a synthetic 24-px line of letters
  through `run_stages` (ids kept, outcomes on meta, every refit within the
  cap of its trace); a 160-px synthetic line is byte-identical ON; a fused
  blob is refused untouched; and drone / enthusiast / fremont ON == OFF on
  the real fixtures, env-gated (`EMB_SLOW_TESTS=1`) because it is minutes of
  engine time.
- **Eye pairs:** arm `letterform_priors` (`letterform_priors_k=0.75`) in
  `tools/eye_pairs/pairs.py` and the gallery's `ARM_INTENT`; rendered on
  becker, bridge, gaulke, drone, enthusiast, fremont and tires against this
  lane's shipped defaults (no `rembg_isolated/venv` in a worktree, so tires
  is prepped the same way on both sides). Results below under "The pairs".

Brief: `docs/superpowers/specs/2026-10-06-letterform-priors-design.md`
(Kent's pick 2026-10-06). Sibling: `docs/outline-cut-columns-2026-10-05.md`
on `claude/outline-cut-columns`, whose failure class 2 this attacks.

## Why

Kent, 2026-10-05: lettering "looks like worms". The outline-cut spike takes a
column's rails from the outline and found its own ceiling: *"Blob outlines
from low-res input. Bridge, and BECKER's outlined band. The letter is not
letter-shaped before construction starts. No cut rule fixes this."* Becker's
upload is 146 px wide: 0.66 mm per source pixel at 95.7 mm, and stage 4
tracks that raster faithfully. A professional tracing the same blur draws
straight stems, true arcs, one stroke width, one baseline.

## The idea

For each line of lettering, refit every text-tagged member's traced polygon
to straight segments and circular arcs under parameters the word shares
(stem direction from the house line and slant, stroke-width modes, baseline
and cap line), with every vertex move capped at `k x source pixel`, so a
clean upload is untouched and a low-resolution one is redrawn only inside
its own pixel. A letter the primitives do not explain is refused and left
alone. The output is a polygon with the same `shape_id` and `meta`.

## What it does (`fit.py`, `refit.py`)

Per word (`refit.refit_regions`):

- **Grouping**: `textcluster._lettering_groups` (the house pass's groups),
  plus — for text-tagged letters that pass leaves out — the tagger's own
  `text_cluster_id`. Bridge's 8 tagged blobs form no `_lettering_groups`
  group at all (its size/aspect links are stricter than the tagger's); they
  only reach the fit through the cluster id.
- **Line of text**: `_line_of_text_deg(members)`. **Slant**:
  `_stem_slant_deg(_house_chains(members), line)` first; when the median of
  the per-letter DP-chord leans (`fit.letter_lean_deg`) disagrees by more than
  **3 deg** the chord reading wins. Set on Fremont's italic word (engine 0,
  chords 12.8 — the engine's instrument resamples 4-px skeleton chords and
  reads 0.7 on every Becker band letter, which lean up to about 4).
- **Arch**: the trimmed range (middle 60%) of the per-letter leans over
  **6 deg** marks an arched word; each letter then gets its own local line
  from a robust line through (position, lean), and no shared baseline/cap.
  Set on Becker: MARINE's core leans spread under 1 deg (the A's legs read
  -14 and the E's slanted terminals +13 — the reason for the trim and for
  the median inside `letter_lean_deg`). Becker's BECKER band reads a spread
  of 4.7 and is NOT called arched; bridge's blobs are (spread > 6), with no
  width modes to share, harmlessly.
- **Cap**: `tol = k x source_px_mm`, source px = design width over the
  pixels the art box spans. **k = 0.75** (measured; see the k sweep).
- **Grid gate**: when `tol < 1 / result.px_per_mm` (the engine's own working
  grid pixel) the word passes through untouched, same object, same bytes.
  On a source finer than the grid the grid IS the source pixel, so the gate
  is `k < 1` there and the fit touches exactly the uploads stage 1 upscaled
  (becker, bridge, gaulke); drone / enthusiast / fremont are byte-identical
  by this gate, not by the fit being gentle.
- **Width modes**: separations of facing stem/bar edges ACROSS INK (the
  midpoint between them inside the letter: a counter or the gap between
  two stems is not a stroke), at most 2 x the engine's skeleton stroke
  width (`_skeleton_stroke_stats`, the width instrument
  `regularize_text_clusters` uses), 1-D clustered with gap 2 tol, 2 votes
  minimum. Becker MARINE 4.71 mm, BECKER 4.26, gaulke 0.99.
- **Baseline / cap**: median of the members' bottom / top extents along the
  line normal (straight words only).

Per letter, each ring (`fit.fit_ring`):

1. densify the ring at min(tol/4, 0.1) mm; Douglas-Peucker at tol
   (chords within the cap by construction);
2. drop a chord shorter than 2 tol when its two neighbours' intersection
   explains its samples within tol (a raster chamfer becomes a sharp corner);
3. merge runs of chords into ONE primitive: a total-least-squares line
   first (the typographic prior; at a 0.49 mm cap a 6 mm straight arm and an
   r = 8 mm arc both hold the staircase, and the pro's E arms are straight),
   else a circle, only over **at least 3 chords** turning the same way with
   **no single turn over 55 deg** (two chords are a corner — the first
   version smeared the M's shoulders into 98-degree arcs), sweep **40 to
   300 deg**, radius between 2 tol and the ring's extent;
4. chords still shorter than 2 tol are unexplained residue, passed through;
5. snap a line's angle to the stem or line direction within **12 deg**,
   rotating about its midpoint, only if its own source samples stay within
   tol of the rotated line (the cap is always read against the SOURCE, never
   the previous fit, so two moves of tol cannot stack to 2 tol);
6. snap facing edges to the nearest width mode, symmetric, same rule;
7. snap a line-direction edge within tol of the baseline / cap line onto it;
8. rebuild: line-line corners by intersection when the corner is over 8 deg
   and lands within tol of the source ring, line-arc joins on the circle,
   arcs written at 0.02 mm chord error, pass-through verbatim;
9. repair: a primitive the rebuilt ring leaves over the cap is softened
   (arc or merged line back to its DP chords, snapped line back to its
   chord), rebuilt, and what still breaks the cap goes back to the trace
   verbatim.

Per letter (`fit.fit_letter`): a ring that crosses itself (the A's foot
notch, whose roof the baseline snap pinched shut) is repaired at the
crossing — every primitive that wrote a vertex within 2 tol of shapely's
reported point goes back to the trace, up to twice. Then **refuse** when
unexplained residue exceeds **10%** of the outline, the polygon is still
invalid, a hole vanished, or the two-way outline distance exceeds the cap.

Thresholds and where each was set: cap k on Becker (pro delta), bridge
(refusals), with gaulke held out; 12 deg snap, 3-chord / 55-deg / 40-deg arc
rules, the 2 tol chamfer length and the 10% refusal share on Becker's MAR
and BECKER band; the arch spread (6) and slant disagreement (3) on Becker
and Fremont. **Gaulke's 38 letters were never looked at while any of these
was set.** Nothing from the engine was changed; `_lettering_groups`,
`_line_of_text_deg`, `_stem_slant_deg`, `_house_chains`,
`_skeleton_stroke_stats` are called as they are.

## Results (`batch.py --sheets --tag full75`, all seven logos, k = 0.75)

| logo | src px mm | cap mm | letters | refit / pass / refused | WKB byte-identical | prims per letter | stem spread deg (within word) | per-letter width CV | word width CV |
|---|---|---|---|---|---|---|---|---|---|
| becker | 0.660 | 0.495 | 11 | 10 / 0 / 1 | no (expected) | 20.2 -> 17.5 | 4.06 -> 2.67 | 0.415 -> 0.381 | 0.089 -> 0.091 |
| bridge | 0.287 | 0.215 | 8 | 8 / 0 / 0 | no (expected) | 13.0 -> 10.3 | 5.93 -> 2.08 | 0.429 -> 0.422 | 0.249 -> 0.253 |
| gaulke (held out) | 0.213 | 0.160 | 38 | 36 / 0 / 2 | no (expected) | 15.8 -> 10.8 | 2.79 -> 1.90 | 0.309 -> 0.312 | 0.221 -> 0.214 |
| drone | 0.104 | 0.078 | 22 | 0 / 22 / 0 | **yes** | - | - | - | - |
| enthusiast | 0.073 | 0.055 | 24 | 0 / 24 / 0 | **yes** | - | - | - | - |
| fremont | 0.037 | 0.028 | 32 | 0 / 32 / 0 | **yes** | - | - | - | - |
| tires | 0.094 | - | 0 | - | yes (no text) | - | - | - | - |

"Letters" is text-tagged shapes the grouping reached (gaulke 39 tagged, 38
grouped; the rest all of them). Primitives before = the DP chord
count the trace needs at the same cap; after = lines + arcs + pass-through.
Stem spread = length-weighted std of the stem-family (within 12 deg) line
angles within a word, averaged over words. Width CV per letter is
`_skeleton_stroke_stats(...).cv`; word width CV is the CV of the per-letter
mean widths. Becker lines/arcs/passes 176 / 9 / 24; gaulke 345 / 43 / 22.

**Go/no-go 1, clean art untouched:** yes — enthusiast and drone (and
fremont) hash byte-identical with the refit on, by the grid gate.

**Go/no-go 2, against the pro (Becker, `testdata/reference/becker_hat_polo_large_beckers_logolc.dst`, 95.7 mm, the fixture's own width).**
Registration: scale 1.000, y NOT flipped from pystitch's frame, whole-design
raster IoU 0.867; the pro sews MARINE as black satin (his block 3) and the
BECKER band letters as black fill with each letter a hole plus a black
satin ring round it, so a band letter is matched to a HOLE of that block's
satin outline. Per letter, IoU and Hausdorff after centring the pro letter
on ours (placement removed — his file was not digitized from this upload
and the registered frame carries a ~0.3-1 mm offset):

| letter | status | IoU traced -> refit | Hausdorff mm traced -> refit |
|---|---|---|---|
| M | refit | 0.725 -> 0.716 (-0.010) | 2.72 -> 2.74 |
| N | refit | 0.704 -> 0.706 (+0.002) | 3.49 -> 3.40 |
| R | refit | 0.896 -> 0.896 (0) | 0.99 -> 0.99 |
| A | refit | 0.939 -> 0.934 (-0.005) | 0.82 -> 0.87 |
| E | refit | 0.854 -> 0.841 (-0.013) | 1.65 -> 1.61 |
| i | refit | 0.855 -> 0.864 (+0.009) | 1.00 -> 1.05 |
| B (band) | refit | 0.810 -> 0.798 (-0.013) | 6.51 -> 6.31 |
| R (band) | refit | 0.870 -> 0.869 (-0.002) | 5.34 -> 5.28 |
| EC (band, merged) | refused | 0.090 | 11.63 |
| K (band) | refit | 0.294 -> 0.311 (+0.017) | 8.95 -> 8.81 |
| E (band) | refit | 0.260 -> 0.266 (+0.006) | 8.56 -> 8.44 |

Mean delta over the 10 compared letters: IoU -0.0008, Hausdorff -0.05 mm; 4
letters move away by the 0.005 / 0.05 mm bars, 6 toward. **Read this as
neutral.** The pro's letters are a different cut of the same font (his N has
a notched diagonal foot, his M a flared top, his band letters sit on a
different arch — K and E match at 0.3 because his band is elsewhere), and
the per-letter deltas sit inside that. What the pro settled was not a
number but a shape: his M has sharp corners and a flat top, his E's arms
are straight with sharp tips, his R's bowl is one arc. Version 1 of this
fit drew the M's shoulders as 98-degree arcs and the E's arm tips as
semicircles — both within the cap, both wrong — and the arc rules in step
3 were set against his file. The k sweep is the same instrument:

| k | cap on Becker | touched | Becker refit | pro delta IoU (centred) | away / toward |
|---|---|---|---|---|---|
| 0.5 | 0.330 | becker, bridge (gaulke gated: 0.107 < 0.125) | 10/11 | -0.0006 | 2 / 4 |
| **0.75** | 0.495 | becker, bridge, gaulke | 10/11 | -0.0008 | 4 / 6 |
| 1.0 | 0.660 | all seven (tol == grid px on a fine source) | 10/11 | -0.0062 | 7 / 5 |

k = 1.0 moves away from the pro and breaks byte-identity on every clean
upload; k = 0.5 leaves gaulke's 0.21 mm pixels alone. 0.75 is where the
brief put it and the sweep keeps it there.

**Go/no-go 3, structure:** the table above. Primitives per letter fall by
13-32%, stem spread within a word by a third to two thirds, per-letter width
CV barely moves (the skeleton instrument reads junction inflation, which no
outline refit changes); word width CV is unchanged. On the sheets: MARINE
M/N/E/i are 6-16 lines each with sharp corners and parallel stems, R and the
band letters' bowls one or two arcs; gaulke's D/O/G/C/U go from 15-30
chords to 5-9 primitives.

**Go/no-go 4, downstream (stages 5-7 re-run on the traced and on the refit
polygons through `plan_stitches`; `digitizer_core.edge_wobble.analyse_plan`
and `rail_edge.bare_area` on the text shapes; the outline-cut spike's
`oc.letter_columns` with its own over-long / clean checks on the same
polygons).**

| logo | stitches | trims | text stitches | wobble std / p95 mm | bare % of satin text | outline-cut over-long | outline-cut clean |
|---|---|---|---|---|---|---|---|
| becker traced | 9173 | 55 | 4213 | 0.172 / 0.401 | 4.33 | 9.3% | 6/11 |
| becker refit | 9679 | 66 | 4719 | 0.178 / 0.410 | 2.65 | 6.2% | 5/11 |
| bridge traced | 17744 | 98 | 412 | 0.082 / 0.162 | 9.70 | 21.3% | 4/8 |
| bridge refit | 17825 | 102 | 474 | 0.079 / 0.146 | 10.69 | 17.3% | 4/8 |
| gaulke traced (held out) | 7138 | 56 | 2952 | 0.075 / 0.175 | 7.93 | 5.2% | 26/38 |
| gaulke refit | 7120 | 55 | 2944 | 0.075 / 0.156 | 7.94 | 3.1% | 30/38 |
| drone (gated), both arms | 18975 | 139 | 2784 | 0.093 / 0.175 | 4.53 | 0.2% | 20/22 |
| enthusiast (gated), both arms | 3420 | 17 | 2444 | 0.086 / 0.167 | 6.81 | 0.6% | 17/24 |
| fremont (gated), both arms | same | same | same | 0.029 / same | 7.83 | 2.2% -> 2.1% | |

Drone, enthusiast and fremont re-plan identically on both arms (the same
stitch count, wobble and bare area to the last digit), which is the
byte-identity of go/no-go 1 seen from the other end of the pipeline. The
one number that moved on fremont, outline-cut 2.2 -> 2.1%, moved on
IDENTICAL polygons: **the sibling's `oc.letter_columns` is not
deterministic** — three calls on one fremont letter gave two different
stitch sets on 4 of the 6 letters tried (`M`, `R`, `E`, `E`; `H` and `N`
stable). That is a finding for the outline-cut lane (its `build_shape_field`
call or a set iteration, not looked into here), and it puts a noise floor
of about 0.1 point under every outline-cut column above.

The outline-cut numbers are this lane's re-implementation of the sibling's
check (shapely coverage at 0.4 mm thread, not its 30 px/mm raster); compare
its two arms with each other, not with the sibling's table. The sibling's
Becker read 9.5% over-long and bridge 21.5% after its second look; the
traced arms here read 9.3 and 21.3, so the instrument agrees with it.

So: the outline-cut check moves the right way on both fixtures it named
(Becker 9.3 -> 6.2%, bridge 21.3 -> 17.3%) and on the held-out logo (gaulke
5.2 -> 3.1%, clean 26 -> 30 of 38), bridge does not get worse, and today's
stage 6 sews Becker's MARINE with **more** columns and trims (R 7 -> 10, A 7
-> 9, E 5 -> 9; +506 stitches) at a third less bare area — the satin
decomposition responds to the sharp junctions by cutting more. On gaulke
today's stage 6 is neutral (stitches -18, trims -1, bare +0.01%). Rail
wobble std is unchanged everywhere (it is the rail model's floor,
`rail-wobble-is-the-models-floor-2026-09-21`, not the outline's); its p95
drops on bridge and gaulke.

## Failure classes, largest first

1. **Bridge is lost two stages earlier, and a refit cannot find it.** Its 8
   "letters" are segmentation blobs of "BAR & RESTAURANT" (OCR reads them
   as `g # . h S \`): a fragment of an R, half a U. The fit refits a blob
   into a cleaner blob — 8/8 "refit", over-long 21 -> 17% — but no outline
   prior makes a letter out of a fragment that lost its other half at
   stage 2 (DOCTRINE 2026-09-30, "count the source pixels per letter
   first"; the work grid is the lever that was found). The sibling's "bridge
   gets worse" is a stage-2 fact, and this lane cannot answer it.
2. **Today's stage 6 cuts a cleaner letter into more columns.** Becker R /
   A / E gain 2-4 satin runs and 2-4 trims each when the junctions are
   sharp. That is the decomposition the outline-cut lane exists to replace;
   with today's satin the refit buys coverage (bare 4.3 -> 2.7%) and pays in
   trims (55 -> 66). Wiring this before outline-cut is sewable means paying
   that.
3. **Compound regions are refused, correctly, and stay blobs.** Becker's
   "EC" (two band letters in one region, unexplained 11%), gaulke's first S
   (a blob at the top, 11%) and a dash-like fragment (66%). Refusal is the
   designed behaviour; the letter is no better for it.
4. **The pro is a different cut, so the number is mute.** Centred IoU moves
   inside +/-0.013 on every compared letter; only the shape said anything.
5. **Small residues survive as pass-through.** The A's foot notch after the
   repair, a nub on gaulke's O, the N's top-right notch: 24 pass-through
   pieces on Becker, 22 on gaulke, each under 2 tol long, verbatim trace.

## Tried and backed out

- **Arcs merged greedily from two chords** (version 1): the M's shoulders
  became 98-degree arcs of r = 5.6, the E's arm tips semicircles, all within
  the cap and all away from the pro. Now a line is tried first and an arc
  needs three chords, a consistent turn and no corner-sized turn.
- **Checking a snap against the previous fit instead of the source**: a
  chord already at tol then shifted tol landed at 2 tol and three Becker
  letters refused on the cap. Every move is now checked against the samples.
- **A circle through the member centroids to detect an arch**: five points
  fit anything within a tenth of the letter height; it called the B's line
  -27 deg and the R's +26. Replaced by per-letter leans with a trimmed
  range, then a robust line.
- **Per-letter lean from the engine's `_stem_slant_deg`**: 0.7 deg on every
  band letter (4-px skeleton chords quantise the reading). Replaced by the
  DP-chord median; the mean read MARINE's E as leaning 8.7 from its
  slanted terminals.
- **Width votes without the across-ink test**: the gap between two stems
  (14-16 mm) and a letter's full height voted as stroke widths.
- **Refusing a letter outright when the rebuilt ring broke the cap**: the N
  lost its diagonal to a junction trim. Softening first (arc / merged line
  back to chords) keeps the N.

## Not built

A stem/hairline pair from a bimodal width histogram (the clustering allows
two modes, no fixture produced two); counter-opening as a rule of its own
(the self-intersection repair is what stands in for it); anything for
script lettering (not text-tagged, ruled out), the tube-letter width floor
(ROADMAP gate 1) or halo strands (defect C); a Studio surface for the flag;
a warning that reads `meta["letterform_prior"]`. No sew-out. The wiring and
the labelled thread pairs are built (see "The wiring" and "The pairs").

## Caveats

- Every polygon came from a run on this lane's engine at `d4c521ec`
  (current `origin/main` at the time), configs `target_width_mm` /
  `garment_id` / `max_colors=6` as the sibling's `CASES`.
- The downstream numbers inject the refit AFTER `finish_generation` (the
  regions `digitize()` returns) and re-run `plan_stitches`. A wired version
  would sit after stage 4, before `measure_stitch_widths` and the house
  angle; the house pass would then read the refit polygons. Not measured.
- `_skeleton_stroke_stats` is memoized on the polygon object; the refit
  polygon is a new key, so its "after" CV is a fresh measurement.
- Sheets actually looked at: Becker MARINE and the band (every version),
  bridge (all 8), gaulke word 0's first nine letters. Gaulke's remaining
  29 and its second word were not looked at; drone / enthusiast / fremont
  are byte-identical and have nothing to look at.
- The pro comparison registers the whole design on a 6 px/mm raster and
  refines per block on 10 px/mm; the refined block IoU is 0.48 (MARINE
  block) and 0.21 (the white block). Hausdorff in the registered frame is
  dominated by that; quote the centred columns.
- Patent note (counsel's question, no full claims read): Adobe US11704848
  covers filled path -> medial axis -> stroke width -> stroked path. This
  fit never builds a medial axis or strokes a path; it fits lines and arcs
  to the outline and moves the outline. The nearest adjacent idea seen is
  classical polygonal/arc approximation of digitised curves (Douglas-Peucker
  1973, Rosin-West 1989 segmentation into lines and arcs), which is prior
  art, not a claim. Nothing else looked adjacent.

## How to pick this up

The worktree has no venv; use the main checkout's Python.

```bash
cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/.claude/worktrees/letterform-priors/digitizer/tools/letterform_priors_spike"
PY="C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe"
"$PY" run.py                                    # rebuild the seven inputs into ../../../scratch_letterform_priors/ (~25 min)
"$PY" batch.py --no-downstream --no-oc          # the fit + pro on all seven, ~30 s
"$PY" batch.py --sheets --tag full75            # + stages 5-7 both arms, outline-cut, per-word sheets (~15 min)
"$PY" batch.py --k 0.5 --no-downstream --no-oc  # the k sweep
cd ../.. && "$PY" -m pytest -q tests/test_letterform_priors.py
```

- `fit.py` the geometry (`word_prior`, `fit_letter`, `polygon_wkb_hash`);
  `refit.py` the per-logo driver (`refit_logo`, `apply`, `summarize`) and
  the piece that would be wired; `pro.py` the pystitch reader, satin
  outline and registration; `sheet.py` the per-letter sheets; `batch.py`
  the table and `batch_<tag>.json`; `run.py` the inputs.
- The outline-cut check needs the sibling's `oc.py` dropped into
  `scratch_letterform_priors/oc/` (`git show
  claude/outline-cut-columns:digitizer/tools/outline_cut_spike/oc.py`);
  `batch.py` skips it when absent.
- Sheets: `scratch_letterform_priors/sheets/full75_<logo>_w<word>.png`
  — per letter: artwork / traced / refit (lines blue, arcs orange, corners
  dotted, a refused attempt in magenta) / pro where matched.

## Open questions

- Where to wire it, if at all: after `stage4_vectorize` and before the
  house angle and `measure_stitch_widths`, behind a default-OFF
  `cfg.letterform_priors` (k as its value, 0 = off); or inside
  `regularize_text_clusters` beside the rescued-door redraw. The second
  keeps one lettering-geometry pass; the first lets the house angle read
  the refit stems.
- Whether the trims stage 6 adds on a sharp letter (failure class 2) are a
  cost Kent accepts before outline-cut lands, or whether this waits for it.
- Whether a refused letter should fall to a softer fit (lines only, no
  snaps) rather than the trace; gaulke's first S would.
