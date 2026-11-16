# Rule 12 measured: separating outlines around pieces on a ground (2026-11-13/14)

Research only. No repo file changed, no git write, no flag. Scripts and outputs all in this folder.
Full tables: `tables.md` (counts per file, ground-based contrast), `contrast.md` (surround-based contrast).
Per-piece rows: `results.json`. Crops: `crops\` (ring_* = ringed pieces, art beside render; own_* = own-colour ring;
low_* = our lowest-contrast unseparated pieces). Art windows in crops are mapped by whole-design extents, for
LOOKING only; nothing was measured through that map.

## Which code made our DSTs

- `ours\<job>\ours.dst` were generated on **local main 19013abe** (`run_ours.py`, `tools.pro_pair.digitize`,
  one job at a time). All ten are byte-identical (md5) to rule7's DSTs from the same commit.
- `git diff --stat 19013abe 336e2eb3 -- digitizer/digitizer_core src` was NOT empty: `keyline_bean.py` + the
  `border_from_outline_hairline_run` flag (default OFF, every call site gated). I re-ran on a `git archive` copy of
  336e2eb3's `digitizer_core`/`tools`/`digitizer_service`: Fremont, Machine, Drone byte-identical to 19013abe;
  **MFab differed**, but that copy had no `rembg_isolated` model folder beside it (the photo prep's cut-out
  resolves it relative to the package), so the run was not like-for-like. The fixed re-run was cut off by the
  session restart; per the coordinator I did not re-run. So: MFab on 336e2eb3 is UNVERIFIED; the numbers below are
  19013abe. Main has moved further since (e.g. c465aa3e, a border_by_size seam change); not re-run.

## Synthetic check (synth.py, synth.log)

30x30 mm tatami ground; on it satin bars 1x4, 2x10, 4x8, 5x8 mm and an 8x8 tatami square (block 1).

| case | ring read on the 5 pieces |
|---|---|
| bare | 0 of 5 contrast, 0 own (own judged on the 2 pieces >= 4.5 mm wide: cov 0.0) |
| contrast satin ring 1.0 mm, third thread | 5 of 5 (cov 1.0, far 0.0); the ring's own pieces flagged "ring of" and not counted |
| own-colour satin ring 1.0 mm, same block | own-colour 3 of 3 judged (cov 1.0); the 2 pieces under 4.5 mm are NOT judged (blind) |
| run-stitch line on the edge, third thread | 5 of 5 (cov 0.82-1.0) |
| contrast ring 0.2 / 0.3 / 0.5 / 0.7 / 1.5 / 2.0 mm | 5 of 5 at every width |
| own-colour ring 0.5 / 0.7 / 1.5 mm | 3 of 3 judged (cov 1.0 / 1.0 / 0.75-0.84) |

Narrowest ring seen: a single run-stitch pass (thread drawn 0.4 mm). Blind spots: an own-colour ring sewn in the
piece's own block on a piece under 4.5 mm wide; a ring in the ground's own thread sewn inside the ground's own block
(indistinguishable from the ground); a ring sewn in a separate block of the same thread is caught and filed as
own-colour (dE00 < 1 to the piece).

## Method as run

- rule7 reader unchanged (copied as `reader.py`, now also returning its rasters): DST geometry, needle-down segments
  <= 6 mm drawn 0.4 mm at 20 px/mm, each side in its own frame; grounds = tatami components >= 25 mm2; pieces =
  later blocks opened 0.55 mm, >= 0.5 mm2, >= 90 % inside a ground.
- Ring (`ring.py`): another block, sewn after the piece's host ground, whose RAW thread lies within 0.7 mm outside
  the piece's outer silhouette along >= 60 % of its contour, while covering <= 30 % of a band 1.6-2.4 mm out.
  Own-block satin edge: consecutive antiparallel stitches 0.5-2.2 mm, both ends within 2.4 mm of the edge,
  across the edge, covering >= 60 % of the contour; pieces >= 4.5 mm wide only. Constants are geometric, not contrast.
- A ring is "contrast" when its thread differs from the piece's (dE00 >= 1), "own-colour" otherwise.
- Colours: pro = PES twin (pystitch threads, block count and per-block stitch counts checked against the DST,
  worst 3.1 % Drone); ours = plan blocks' rgb (counts matched). No PES = "not read".
- Contrast reported two ways: against the host GROUND thread (as briefed) and against the SURROUND thread (the block
  with most thread 0.8-1.6 mm outside the piece). They differ where a piece sits on an intermediate shape: MFab's
  black letters read dE00 0 to the black ground they stack on, 93 to the white panel round them. I use SURROUND
  for the comparisons below; ground-based numbers are in `tables.md`.
- Pieces under 2 mm2 are reported but called "fragments": the ones I looked at (Drone b5 #234, Fremont #167) are
  specks of texture or band ends, not shapes.
- dE00 between two thread colours says nothing about how the pair looks sewn (sheen, angle, fabric show-through).

## Q1. Pro: pieces on a ground, rings, and was it in the art (by eye)

All 28 pro files: 373 pieces on a ground (284 >= 2 mm2); contrast ring on 32 (16 >= 2 mm2); own-colour ring on 3
(2 >= 2 mm2). The six paired jobs: 133 pieces; contrast ring 12 (3 >= 2 mm2); own-colour 1.

| job | pieces (>= 2 mm2) | contrast ring (>= 2) | own-colour (>= 2) |
|---|---|---|---|
| hotel_fremont_patch | 32 (30) | 2 (1) | 0 |
| mfab_hat | 20 (20) | 0 | 1 (1) |
| machine_hat | 26 (26) | 0 | 0 (2 blocks: no other block can ring) |
| precision_drone | 48 (17) | 9 (1) | 0 |
| becker_hat_large | 3 (3) | 0 | 0 |
| golf_hat | 4 (4) | 1 (1) | 0 |

By-eye calls, every ringed pro piece >= 2 mm2 (crops `ring_pro_*`, `own_pro_*`):

1. golf_hat b1 (39.4 mm2, Tangerine bevel of the "1", ring Black): a real outline; **in the art** (black outline round the bevel).
2. hotel_fremont_patch b4 (97.7 mm2, rope band, ring Black): a stripe on ONE side of the band; **in the art** (black line beside the rope).
3. hotel_fremont_hat b3 (97.7 mm2): same design and call as 2.
4. precision_drone b5 (11.8 mm2, silver crosshair on the water, ring White, cov 0.61): **not an outline**, a tonal neighbour; the art has that tone.
5. mfab_hat b3 / mfab_lc b3 (194.5 / 168.5 mm2, white panel with own-colour satin edge on the black field): **in the art** (the art's white keyline).
6-17. Gaulke Plowing beanie/hat/LC b2-b3 (9 pieces) and Gaulke JB b4/b11/b19 (3): coloured fills enclosed by the
   drawing's line-art strokes (one block). **Cannot call**: no artwork in the repo and no PES (colours not read).
   They look like a drawing's own ink lines, not added halos, but that is not checked against art.

Fragments (< 2 mm2) with a ring: 16 (Gaulke 6, Fremont 2, Drone 8); not called individually.
**Added outline not in the art: 0 found** on the jobs with art.

## Q2. Ours, same jobs, same reader (19013abe)

| job | pieces (>= 2 mm2) | contrast ring (>= 2) | own-colour ring |
|---|---|---|---|
| hotel_fremont_patch | 40 (25) | 0 | 0 |
| mfab_hat | 11 (11) | 3 (3) | 0 |
| machine_hat | 25 (24) | 0 | 0 |
| precision_drone | 47 (36) | 5 (3) | 0 |
| becker_hat_large | 3 (3) | 0 | 0 |
| golf_hat | 3 (3) | 3 (3) | 0 |

By-eye calls (crops `ring_ours_*`):
- mfab_hat b2 x3 (115.5, 84.6, 34.6 mm2, black letters, ring white): the **art's white keyline, kept**.
- precision_drone b3 (13.7) and b5 x2 (5.9, 5.8): **not outlines** (tonal neighbours in the photo-like art, cov 0.66-1.0).
- golf_hat b2 x3 (3.1, 2.1, 2.5 mm2): small bits between the art's coloured arc bands; **not outlines**.
- Fragments: precision_drone b6, b7.

Where the art has an outline: MFab keyline, kept (3 of 3 letter groups ringed). Golden Tee's black outline round the
"1" bevel and Fremont's black stripe beside the rope: the reader finds no ringed piece there on our side; I did not
trace why (the shape may not read as a piece on a ground in ours). **We add one: 0 found.**
Own-colour column: 0 on the paired jobs. Our plans DO carry `role="border"` runs (Fremont block 1 black, 4 runs;
MFab block 1 white, 1 run); the reader found none hugging a piece on a ground. Where they lie was not checked.

## Q3. Contrast of unseparated pairs (no contrast ring), vs the surround thread

| side | n | same thread as surround | different-thread dE00 min / q1 / med / q3 / max | abs dL min / q1 / med / q3 / max |
|---|---|---|---|---|
| pro (colour-read files) | 210 | 1 (golf_hat) | 10.7 / 42.6 / 93.0 / 93.0 / 98.9 | 12.6 / 49.2 / 94.8 / 94.8 / 99.0 |
| ours (paired) | 118 | 3 (mfab_hat) | 17.3 / 27.5 / 71.4 / 73.2 / 100.0 | 26.6 / 39.6 / 80.7 / 82.0 / 100.0 |
| ours cartoons | 16 | 0 | 2.6 / 12.5 / 39.9 / 65.6 / 100.0 | 3.6 / 14.0 / 35.6 / 67.9 / 100.0 |

(a) Lowest different-thread unseparated pair per job, dE00 (dL) [area mm2], plus same-thread count:

| job | pro | ours |
|---|---|---|
| hotel_fremont_patch | 38.3 (-40.2) [25.7]; same 0 | 26.7 (-37.2) [18.4]; same 0 |
| mfab_hat | 93.0 (+94.8) [1549.1]; same 0 | 100.0 (+100.0) [1312.8]; same 3 |
| machine_hat | not read (no PES) | 71.4 (-80.7) [47.1] |
| precision_drone | 10.7 (-12.6) [25.3]; same 0 | 17.3 (+26.6) [123.5]; same 0 |
| becker_hat_large | 42.6 (+56.3) [23.6] | 71.4 (-80.7) [30.7] |
| golf_hat | 31.0 (-21.4) [70.3]; same 1 | no unseparated piece |

(b) Pro minimum over all his colour-read files (different-thread): 10.65 (Drone b21, Gray). Ours paired: **0 of 115**
below it. Ours cartoons: **4 of 16** below it (owl 2.6, 2.6, 8.0, 10.0).

Same-thread pairs (dE00 0): pro 1 (Golden Tee), ours 3 (MFab black letters whose surround is the black field, i.e.
where the white keyline does not reach); these are not "low contrast", they are no colour step at all.

Our ten lowest different-thread unseparated pieces (paired jobs), crops `low_ours_*`: precision_drone b3 x6
(62,63,65 grey on black, dE00 17.3, 123.5 / 11.7 / 7.2 / 1.7 / 0.8 / 8.0 mm2); hotel_fremont_patch b2 x4
(163,150,135 tan on white, dE00 26.7, 18.4 / 13.6 / 0.5 / 0.5 mm2). Full table in `contrast.md`.

## Q4. Ours, four character fixtures (19013abe)

| fixture | pieces (>= 2 mm2) | contrast ring (>= 2) | own-colour ring | lowest different-thread dE00 |
|---|---|---|---|---|
| pooh | 5 (3) | 1 (0, a fragment) | 0 | 13.3 (0.5 mm2), 39.9 at >= 2 mm2 |
| owl_kent | 8 (4) | 1 (0, a fragment) | 1 (31.3 mm2 grey patch, border_by_size-looking satin edge) | 2.6 (2.6 mm2) |
| tux_gradient_mascot | 4 (4) | 0 | 0 | 66.5 (164.7 mm2) |
| bison_flat_emoji | 1 (1) | 0 | 0 | 43.3 (41.2 mm2) |

Ten lowest (crops `low_ours_cartoon_*`): owl b4 x2 (214 on 204 grey, 2.6), owl b3 (204 on 175, 8.0, 65.8 mm2),
owl b4 (214 on 175, 10.0, 31.3 mm2, own-colour ring), pooh b6 (13.3, 0.5 mm2), owl b1 (34.3), pooh b6 x3 (brown on
gold, 39.9), owl b4 (43.0).

## Not read

- Colours: no PES for machine_hat, machine_lc, becker_marine_hat, all Gaulke Plowing/Roofing/JB, Proseal.
- Art: none for Gaulke Plowing/JB and Proseal (Proseal and Roofing have no pieces on a ground anyway).
- MFab on 336e2eb3 (see top). Owl/Pooh/Tux/Bison not re-run on 336e2eb3.
