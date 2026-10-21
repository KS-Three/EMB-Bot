# The professional digitizer's rules, read across every job (2026-10-21)

Research only. No engine file changed, no flag flipped, no constant touched.

**Why this exists.** Until today everything EMB-Bot copied from the professional came
from ONE file, the Hotel Fremont patch (92.5 mm): small words raised to a ~4 mm cap,
condensed, re-set as bold satin; the rope replaced by satin bands; the field filled.
PR #1024 and PR #1025 built some of that OFF. Kent chose on 2026-10-21 to read the
pro's habits across ALL his files first, and encode only what holds across jobs. This
is that reading.

**What was read.** Every machine file in the repo-root `Embroidery Files.zip`: 29 pro
files from 11 jobs (Hotel Fremont patch + hat; Becker Marine at four sizes plus a
beanie; Golden Tee; Gaulke Plowing logo, hat, LC, beanie; Gaulke Roofing hat, LC,
beanie, multi-colour; Precision Drone; Proseal hat + beanie; Tires 3D; MFab hat + LC;
To a T Machine hat, LC, beanie, plus a second To a T beanie). `Test Files/` is a
third-party sample corpus with no artwork and no job, so it is left out.

Artwork exists in the repo for 9 of the 11 jobs (`digitizer/testdata/`, paired the way
`tools/pro_parity/prep_both.py` and `blockcensus.py` pair them). No art: Gaulke
Plowing (pro-only rows below) and Proseal (customer art is only in Kent's gitignored
`scratch_kent/proseal.jpg`; its numbers were read from that copy, and **no Proseal
artwork is rendered into this PR**). Our side: `tools/pro_pair.py --art A --pro P
--width W --garment G` on today's `main` (`bd25aabb`), one run per job with art, at
the pro's own width.

## How it was measured (and the trap it avoids)

Letters were read **by connected pieces in each side's own frame**, never inside a box
mapped from the other side (the trap that misled the 2026-10-20 session twice).

- **Pro:** one colour block at a time, needle-down stitches of 6 mm or less drawn
  0.4 mm wide at 20 px/mm, then opened by 0.55 mm so the run stitches that travel
  between letters fall away; each remaining piece is a letter or a joined pair. Cap
  height is the median height of pieces at least 0.7 of the tallest; heights are
  given as **penetration extent** (0.4 mm of thread taken off). Bars, dashes and
  underlines (wider than 3x their height) are dropped on both sides.
- **Art:** ink pieces (alpha and non-white) in a hand-picked band of the art's own
  pixels, converted to mm by one scale per job, from the art ink width to the pro's
  design width (the pro rescales hat to LC as a whole, below).
- **Sewn column width:** the satin crosses whose midpoint lies in the line's band —
  a cross is a needle-to-needle segment flanked by reversals, with the crosses two
  back and two ahead parallel and of similar length. Spacing is the same-rail advance
  (two crosses).
- **Art stroke width:** 2 x the distance transform along the medial axis of the band.
  **Resolution caveat:** the Roofing, Machine and MFab artwork are the vendors' own
  preview panels at 0.21-0.26 mm/px, Becker's is 146 px wide (0.52-0.70 mm/px), so
  their stroke widths carry an error of a pixel: about +/-0.25 mm on the first three
  and +/-0.6 mm on Becker. Fremont (0.037), Drone (0.081), Golden Tee (0.043) and
  Proseal (0.109) are good to a few hundredths.
- **Economy:** read from each job's DST, so every file is counted the same way. PES
  trims are not comparable: `pystitch` reports a TRIM at every PES jump, which makes
  Fremont's patch read 53 "trims" as PES and 20 as DST. The 2026-10-20 note's
  "21 trims" is the DST figure. Ours is our own `ours.dst` read the same way.
- **Fill rows and underlay:** the existing `tools/pro_fill_underlay.py` and
  `tools/row_pitch_union.py` (pro fills read as ROWS, per the 2026-09-03 finding;
  `fill_pitch.py` over-reads them and is not used).

Scripts are throwaway, in the session scratchpad; the readings are reproducible with
the method above, and every number in a table is one reading of one file.

## 1. Per job

### 1a. Lettering, art vs pro at the pro's size

Cap heights in mm. Width ratio is the line's ink extent, pro over art. Sewn column
is the median satin cross (p10 in brackets). Gap is the median VISIBLE gap between
adjacent letter pieces (on the pro side, the 0.4 mm thread is taken into account).

| job | line | art cap | pro cap | pro/art | width pro/art | art stroke | pro column | gap art → pro | ours cap |
|---|---|---|---|---|---|---|---|---|---|
| Fremont patch | EST | 1.89 | 3.90 | **2.06x** | 1.42 | 0.30 | 0.90 (0.71) | (joined) | ~1.7 |
| Fremont patch | 1895 | 1.93 | 3.70 | **1.92x** | 1.54 | 0.30 | 0.92 (0.77) | 0.37 → 0.15 | ~1.7 |
| Fremont patch | THE | 3.12 | 3.65 | **1.17x** | 1.05 | 0.52 | 0.90 (0.80) | 0.97 → 0.25 | 2.65 |
| Fremont patch | EAT STAY PLAY | 2.56 | 3.85 | **1.50x** | 1.15 * | 0.31 | 0.90 (0.72) | — | 2.3 |
| Fremont patch | HOTEL FREMONT | 6.87 | 7.45 | 1.08x | 1.00 | 0.89 | 1.43 (1.36) | 0.63 → 0.35 | 6.9 |
| Fremont hat | EST 1895 | 1.93 | 4.25 | **2.20x** | 1.45 | 0.30 | 0.90 (0.73) | — | — |
| Fremont hat | EAT STAY PLAY | 2.56 | 4.10 | **1.60x** | 1.20 * | 0.31 | 0.89 (0.72) | — | — |
| Fremont hat | HOTEL FREMONT | 6.88 | 7.45 | 1.08x | 1.00 | 0.89 | 1.43 (1.36) | — | — |
| Drone | PRECISION | 6.02 | 6.30 | 1.05x | 1.00 | (gradient) | 2.06 (1.66) | 0.90 → 0.30 | 6.5 |
| Drone | THERMAL | 4.56 | 4.65 | 1.02x | 0.99 | 1.30 | 1.76 (1.20) | 0.65 → 0.50 | 4.9 |
| Drone | AND DRONE | 2.36 | 3.70 | **1.57x** | 1.01 | 0.59 | 1.26 (1.00) | 1.38 → 0.32 | 2.75 |
| Proseal (art not in repo) | PROSEAL | 9.35 | 9.45 | 1.01x | 1.00 | 2.61 | 2.98 (2.31) | 1.30 → 0.95 | — |
| Proseal (art not in repo) | SPRAY FOAM + COATINGS | 3.26 | 4.20 | **1.29x** | 1.09 | 0.61 | 1.26 (1.02) | 1.20 → 0.25 | — |
| Roofing hat | C GOLKE INDUSTRIES | 6.90 | 6.65 | 0.96x | 1.00 | 2.04 | 2.00 (1.57) | 0.51 → 0.45 | 6.7 |
| Roofing hat | STEEL ROOFING & SUPPLY | 6.64 | 6.20 | 0.93x | 1.00 | 1.53 | 1.53 (1.26) | 0.51 → 0.40 | 6.3 |
| Roofing LC | C GOLKE INDUSTRIES | 5.75 | 5.65 | 0.98x | 1.01 | 1.70 | 1.75 (1.36) | 0.43 → 0.40 | — |
| Roofing LC | STEEL ROOFING & SUPPLY | 5.54 | 5.30 | 0.96x | 1.00 | 1.28 | 1.35 (1.12) | 0.43 → 0.40 | — |
| Machine hat | To a T | 12.33 | 11.40 | 0.92x | 0.96 | 1.58 | 2.02 (0.98) | — | — |
| Machine hat | LLC | 7.15 | 6.50 | 0.91x | 1.23 | 1.38 | 1.49 (0.90) | 0.49 → 0.45 | — |
| Becker hat small | MARINE | 12.58 | 13.20 | 1.05x | 1.01 | 4.19 | 4.02 (3.23) | 1.57 → 1.20 | — |
| Becker hat large | MARINE | 16.75 | 17.50 | 1.04x | 1.01 | 5.58 | 5.20 (4.30) | 2.09 → 1.83 | — |
| Golden Tee | ™ | 0.94 | ~0.9-1.1 | ~1.0x | 1.2 | 0.17 | **run stitch** | — | — |
| Plowing hat (no art) | C GOLKE INDUSTRIES | — | 6.45 | — | — | — | 2.00 (1.60) | — | — |
| Plowing hat (no art) | SNOW PLOWING DIVISION | — | 4.95 | — | — | — | 1.60 (1.30) | — | — |
| Plowing LC (no art) | C GOLKE INDUSTRIES | — | 5.40 | — | — | — | 1.70 (1.34) | — | — |
| Plowing LC (no art) | SNOW PLOWING DIVISION | — | 4.15 | — | — | — | 1.30 (1.08) | — | — |
| MFab hat | AND WELDING | (white-on-black, not read) | ~7-8 | ~1.0 by eye | — | — | 1.55 (1.32) | — | — |

\* Fremont's tagline art span includes the two `|` separator bars, which the pro
dropped, so its true width growth is a little larger than 1.15/1.20.

"Ours cap" is read off our `ours.dst` the same way; we sew the art's size.
Render: `docs/renders/pro-rules-2026-10-21/small_text_art_vs_pro.png` (art above,
pro below, both at 20 px/mm) and `proseal_tagline_pro_only.png`.

### 1b. Layout and design changes, per job

| job | what the pro changed against the art | ours |
|---|---|---|
| Hotel Fremont (patch, hat) | Rope border removed, replaced by stacked satin bands; the white field inside the hexagon filled; EST/1895 moved down into free space; the tagline's `|` bars dropped; small text raised (1a) | sews the art literally: rope chevrons, field left as fabric |
| Becker Marine (5 files) | BECKER drawn as hollow letters with a black keyline: the pro FILLS the letter interiors (tatami, cross underlay) and satins the keyline; MARINE kept as drawn | sews the keyline, interiors left as fabric |
| Golden Tee | Gradients, bevel and drop shadow flattened: GT is one solid fill plus satin outlines, GOLF one solid satin colour; the ball arc's two thin strokes become one satin band with an outline; the ™ kept tiny as a run | traces the bevel/shadow layers as separate colours |
| Precision Drone | Photographic scene redrawn as flat colour regions (8 threads over 23 blocks); the frame ring kept as a satin ring; reticle simplified; gradient letters made flat | stacks many grey/orange regions, 112 trims |
| Gaulke Roofing | Roof mark tightened toward the text (art 2.79:1 vs pro 2.35:1, per `pro-parity-real-art-2026-08-15.md` §3); text left at size | sews the art layout |
| Gaulke Plowing | (no art) | — |
| Proseal | Hat: no field added. Beanie: knockdown (1d) | — |
| Tires 3D | One satin path per stroke for 3D puff, satin spacing 0.14 mm | sews flat |
| MFab | The white letters and white keyline are sewn as solid fills, not left as fabric | traces black around white |
| To a T Machine (hat, LC, beanie) and To a T beanie | The white badge interior is filled; border satin; speed lines kept as columns | badge interior left as fabric |

Renders: `docs/renders/pro-rules-2026-10-21/<job>_art_ours_pro.png` for the ten
jobs with art (art | ours | pro, from `tools/pro_pair.py`).

### 1c. Economy, pro vs ours (DST read)

| job | garment | size mm | pro stitches | pro trims | pro colour changes | ours stitches | ours trims | ours colour changes |
|---|---|---|---|---|---|---|---|---|
| Fremont | patch | 92.5 x 50.8 | 15,458 | 20 | 8 | 20,768 | 45 | 3 |
| Fremont | hat | 92.6 x 50.9 | 17,067 | 20 | 10 | — | — | — |
| Becker large | hat | 101.9 x 62.1 | 12,356 | 9 | 4 | 9,411 | 27 | 0 |
| Becker large | LC | 95.7 x 58.3 | 11,274 | 11 | 3 | — | — | — |
| Becker small | hat | 76.5 x 46.8 | 8,694 | 10 | 4 | 5,928 | 15 | 0 |
| Becker small | LC | 76.5 x 46.8 | 8,694 | 11 | 3 | — | — | — |
| Becker | beanie | 79.8 x 50.1 | 11,411 | 10 | 5 | — | — | — |
| Golden Tee | hat | 74.9 x 62.3 | 5,973 | 9 | 6 | 8,339 | 30 | 8 |
| Plowing (JB logo) | large | 178.5 x 95.9 | 32,665 | 88 | 20 | — | — | — |
| Plowing | hat | 108.0 x 52.3 | 11,271 | 50 | 6 | — | — | — |
| Plowing | LC | 89.4 x 47.8 | 9,255 | 49 | 6 | — | — | — |
| Plowing | beanie | 110.5 x 54.9 | 14,576 | 50 | 7 | — | — | — |
| Roofing | hat | 114.2 x 48.5 | 6,138 | 41 | 0 | 8,116 | 33 | 2 |
| Roofing | LC | 95.2 x 42.1 | 5,151 | 41 | 0 | — | — | — |
| Roofing | beanie | 93.8 x 43.4 | 7,051 | 41 | 1 | — | — | — |
| Roofing multi | hat | 114.2 x 48.8 | 6,149 | 39 | 2 | — | — | — |
| Drone | hat | 62.6 x 63.8 | 14,552 | 58 | 22 | 14,802 | 112 | 9 |
| Proseal | hat | 85.9 x 63.3 | 5,894 | 53 | 4 | — | — | — |
| Proseal | beanie | 75.0 x 55.4 | 7,117 | 47 | 5 | — | — | — |
| Tires 3D | hat | 114.3 x 42.2 | 5,555 | 9 | 1 | 8,075 | 9 | 0 |
| MFab | hat | 104.9 x 40.2 | 17,568 | 18 | 4 | 12,152 | 59 | 3 |
| MFab | LC | 96.7 x 36.9 | 15,786 | 19 | 4 | — | — | — |
| Machine | hat | 89.5 x 61.6 | 13,886 | 30 | 1 | 8,736 | 46 | 2 |
| Machine | LC | 89.5 x 61.6 | 13,875 | 30 | 1 | — | — | — |
| Machine | beanie | 81.0 x 55.8 | 14,817 | 30 | 2 | — | — | — |
| To a T | beanie | 82.3 x 57.0 | 15,111 | 30 | 2 | 6,734 | 40 | 1 |

Trims, ours over pro, on the ten paired jobs: 2.25, 3.0, 1.5, 3.3, 0.8 (Roofing),
1.9, 1.0 (Tires), 3.3, 1.5, 1.3. Median 1.7.

Sew order by colour block (PES): the largest fills go first (Fremont's field, MFab's
field, Machine's badge fill, every beanie knockdown); per element the pro sews the
fill and then its satin outline, and then moves on (Becker: BEC fill, BEC outline,
KER fill, KER outline); text and fine detail come after the fills they sit on.

### 1d. Density and underlay

| file | top fill rows (mm) | underlay under the fill | satin spacing, same rail (mm) |
|---|---|---|---|
| Fremont patch | 0.15 | CROSS, 0.93 pitch, 4.0 stitch, 90°, 16% | 0.40 (HOTEL FREMONT 0.36) |
| Becker hat small (2 fills) | 0.17, 0.18 | CROSS, 0.97-0.99, 4.0, 89°, 16-17% | 0.40 |
| Becker beanie | 0.16 | CROSS, as the hat | **0.36** |
| Golden Tee | 0.17 | CROSS, 0.98, 3.8, 89°, 17% | 0.41 |
| Plowing hat / beanie | 0.19 / 0.17 | CROSS, 0.93-0.99, 3.6-3.8, 86-88°, 18-20% | 0.40 |
| Drone (2 fills) | 0.16, 0.18 | CROSS, 0.97-0.98, 3.1-3.7, 89°, 8-15% | 0.40 |
| MFab hat (2 fills) | 0.17, 0.19 | CROSS, 0.99, 3.3-4.0, 89°, 8-20% | 0.40 |
| Machine hat / beanie E | 0.18 / 0.17 | CROSS, 0.98-0.99, 4.0, 90°, 17-18% | 0.40 / **0.32** |
| To a T beanie | — | — | **0.36** |
| Roofing, Proseal, Tires | no dense fill | — | 0.40, 0.40, **0.14 (3D puff)** |
| **Beanie knockdown** (Becker, Plowing, Roofing, Proseal, Machine E) | 0.48-0.50 | BARE or RUNONLY — none | — |

`row_pitch_union.py` over the densest 8 mm window agrees (0.11-0.18 mm on every hat
or LC fill).

## 2. Rules that hold across jobs

"Jobs" counts distinct customers; a job's several files (hat, LC, beanie) count once.
Fremont is one job.

| # | rule | jobs supporting | against | strength |
|---|---|---|---|---|
| R1 | **Text at or above ~4.5 mm cap is sewn at the art's size** (pro/art 0.91-1.08, line width 0.96-1.01) | 6: Fremont, Drone, Roofing, Machine, Becker, Proseal | 0 | strong |
| R2 | **Text under ~4 mm cap is raised to about 3.7-4.3 mm** (1.17x-2.2x; landing caps 3.65, 3.70, 3.70, 3.85, 3.90, 4.10, 4.20, 4.25) | 3: Fremont, Drone, Proseal — every job that HAS sub-4 mm text | Golden Tee's ™ (0.9 mm, kept as a run) — a symbol, not a word | strong, small n |
| R3 | **Raised text grows taller than wider** — width grows 0.64-0.90 of the height growth (Drone's AND DRONE kept its width exactly, 1.01) | 3: Fremont, Drone, Proseal | 0 | strong, small n |
| R4 | **Raised text is re-set bold: sewn column 0.9-1.26 mm (stroke 0.23-0.34 of the cap), and the gaps between letters close to 0.15-0.35 mm** | 3: Fremont, Drone, Proseal | 0 | strong, small n; the numbers are gate-1 constants (below) |
| R5 | **Lettering is satin**, at every size, up to strokes of ~5 mm (Becker MARINE 4.0-5.2 mm columns); wider letter bodies are filled with a satin outline (Becker's BECKER, MFab's M-FAB, Golden Tee's GT); no word is a run | 10: every job with lettering | Golden Tee's ™ (a run) | strong |
| R6 | **Column width does NOT grow by a fixed pull on wide strokes.** At art strokes of 1.3 mm or more the sewn cross equals the art within about +/-0.4 mm (Roofing -0.04 to +0.07, Machine LLC +0.11 and To a T +0.44, Becker -0.17/-0.38, Proseal +0.37, Drone THERMAL +0.46). The large additions are on THIN strokes, which are raised to a floor (R4). | 5: Roofing, Machine, Becker, Proseal, Drone | Fremont's HOTEL FREMONT +0.54 at 0.89 mm sits between the two regimes | moderate (art resolution, §How) |
| R7 | **Satin spacing 0.40 mm (same rail)** on every hat, LC and patch file | 10 (all) | Tires 3D puff 0.14 (a different technique) | strong |
| R8 | **Every dense fill has a cross underlay**: ~1.0 mm pitch, ~4 mm stitches, ~90° to the top rows, 8-20% of the fill's thread; top rows 0.15-0.19 mm | 7: Fremont, Becker, Golden Tee, Plowing, Drone, MFab, Machine (every job with a dense fill) | 0 | strong |
| R9 | **A beanie gets a knockdown**: a sparse fill (0.48-0.50 mm rows, no underlay) under the whole design, about 1.5 mm past its outline, sewn first | 5: Becker, Plowing, Roofing, Proseal, To a T (both beanie files) — every beanie job | 0 | strong |
| R10 | **Hat and LC are one design rescaled** (text, columns and spacing scale with it; LC text 0.85x of hat on Roofing against a 0.83x design) | 5: Becker, Plowing, Roofing, MFab, Machine | 0 | strong (also `pro-parity-real-art-2026-08-15.md` §5b) |
| R11 | **White or hollow areas inside the design are sewn, not left as fabric**: badge fields, hollow outlined letters, white letters and keylines | 5: Fremont, Machine/To a T, Becker, MFab, Golden Tee | Roofing (the gaps in the roof mark stay open: they are gaps, not enclosed areas) | strong |
| R12 | **Colours are repeated to keep layer order** — fill then outline per element, so the same thread comes back (Fremont 9 blocks of 4 threads, Becker grey/black/grey/black/grey, MFab black/white/black/white/black, Golden Tee 7 blocks of 3, Drone 23 blocks of 8) | 5: Fremont, Becker, MFab, Golden Tee, Drone | 0 | strong |
| R13 | **Biggest fills first, then outlines and text on top**; a knockdown before everything | 8: Fremont, MFab, Machine, Becker, Golden Tee; Plowing, Roofing, Proseal through their beanie knockdown | 0 | strong |
| R14 | **Fewer trims than ours**: median ours/pro 1.7 over ten paired jobs. The pro trims between separate letters on bare fabric (Roofing 41, Plowing 50, Proseal 53, for 25-35 letters plus a mark each) and travels under or along the work where a fill sits beneath (Fremont 20, MFab 18) | 8 of 10 paired jobs | Roofing (ours 33 vs pro 41), Tires (equal) | moderate — it is a count, not yet a rule we can encode |
| R15 | **Gradients, bevels and shadows are flattened** to one flat colour per region | 2: Golden Tee, Drone (the only two jobs with gradient art) | 0 | strong for what it covers, small n |

## 3. Fremont-only, or inconsistent

- **Rope border replaced by stacked satin bands** — Fremont only (no other job has a
  rope). A design change, so a customer-facing option, not engine behaviour.
- **Serifs kept, bolded (slab)** on the raised small text — Fremont is the only serif
  job, so "keep serifs" vs "simplify serifs" is untested.
- **Elements moved** — Fremont moved EST/1895 down into free space; Roofing tightened
  the mark toward the text. Two jobs, two different reasons; no rule.
- **Separator bars dropped** (Fremont's tagline `|`). Proseal kept its underline bar,
  Drone kept its dashes. Inconsistent.
- **Big text +8%** (HOTEL FREMONT 7.45 vs 6.87) — every other job keeps big text
  within -9% to +5%. Treat as noise.
- **Beanie satin density** — 0.36 on Becker and To a T, 0.32 on Machine E, unchanged
  0.40 on Roofing, Plowing and Proseal. 3 of 6 beanie files; inconsistent.
- **Pull on mid-width strokes** — HOTEL FREMONT +0.54 at 0.89 mm, THERMAL +0.46 at
  1.30, against +0.0 to +0.11 on Roofing and Machine at similar widths. Inconsistent;
  partly the art resolution caveat.

## 4. What this says about what to build

- **R1-R5 confirm the Fremont lettering habit is general.** Every job with sub-4 mm
  words raises them to ~4 mm, condensed, bold satin; every job leaves bigger text
  alone. PR #1024's `small_text_cap_*` flags and PR #1025's
  `lettering_columns_small_bold` are pointed the right way. What they still lack is
  the column construction (the 2026-10-20 note: a fixed per-rail pull on a 0.85 mm
  stroke bloats or drops strokes); R6 says the pro does NOT use a fixed pull — he
  sets thin columns to a floor and leaves wide ones at the art's width.
- **R9 (beanie knockdown) is new, clean, and holds on 5 of 5 beanie jobs.** We have
  nothing like it.
- **R11 (sew enclosed white) and R15 (flatten gradients) are design changes**, so,
  per Kent's 2026-10-21 framing, a customer-facing option rather than silent engine
  behaviour.
- **R7, R8 are already ours** (satin 0.4 mm spacing; fill rows 0.15 mm ruled
  2026-09-03; `cross_tatami` built 2026-10-05, in no preset).
- **R12-R14 (layer order, repeated colours, trims)** are economy and sequencing
  habits; a trim rule needs its own study before any constant.

**ROADMAP gate 1.** The floors in R4 (0.9-1.26 mm column, 0.15-0.35 mm gap) and the
knockdown pitch in R9 (0.5 mm) are physical constants read from a pro's files; they
are candidates, not settled, until a sew-out. The raise-to-~4 mm cap height is a
design/legibility choice the pro makes on every job, and Kent already ruled "match the
pro" on it (2026-10-21).
