# MFab recipe trims: where the cuts sit, how the pro avoids each, what cuts them (2026-10-26)

Kent saw the v2 flip sheet of the MFab recipe and chose (2026-10-26) **"Prepare
the flip"**. Three things happen before he flips the switches, all from one sheet:

1. A worker cuts the recipe's extra trims.
2. The same switches are rendered on every other job they touch.
3. Kent flips.

This page is the first. The recipe is d2 + panels + mitre:
`silhouette_underfill` + `sew_enclosed_white` + `enclosed_white_keyline` +
`silhouette_underfill_panels` + `outline_loop_mitre`. It cut 61 trims on the hat
and 65 on the LC, against the pro's 19 / 20 (#1094's table).

## Instruments

- **Same reader on both DSTs:** `tools/sequence_pro.py` (#1072) and
  `tools/inpiece_cuts.py` (#1091). They give pieces, stretches, cuts inside a
  piece, and stitch character either side of a cut.
- **Ours, cut by cut:** each cut belongs to the plan run it follows: the thread
  it ends. Underlay and travel stand for their own shape's top stitching, as
  `inpiece_cuts._top` reads them. The DST stream is `inpiece_cuts.attributed`.
- **Exposed travel:** `tools/travel_cover.travel_exposure`, travel that no
  thread sewn after it covers.
- **Bare thread:** `tools/hairline_travel.scan`.
- **Arms:** stages 0-4 are digitized once per job, then `plan_stitches` runs
  per arm. The first arm reproduces the recipe byte for byte: hat plan
  `b5bff100` / DST `7b1e20a8`, LC `351920cc` / `85ac48f5`.
- **Hat route:** `PHOTO_BACKGROUND_REMOVED` on every hat digitize. rembg runs
  from the main checkout's venv, timeout 900 s.

## How the pro avoids each cut

**1. The black under-fill: one stretch, no lift at all.** His first block is
9,199 penetrations in ONE needle-down stretch:

- 0 trims, 0 needle-up moves, one piece.
- It walks round the panel hole inside itself. Black under his small letters
  reads 0.13-0.15, so the hole is there.

Ours cuts 12 times inside the under-fill on the hat and 8 on the LC:

- Most are the underlay's ring hops: `edge_lattice` walks each hole's ring as
  its own path.
- The rest are fill sections.

This is #1091's class, and #1091's flag `fill_section_travel` (OFF) is the
cure: a route inside the shape under rows still to sew.

**2. The white keyline: a few long satin chains.** His white block is 7
stretches (6 cuts) over 3 pieces:

- Two stretches carry most of the keyline: 1,692 and 2,082 penetrations, each
  several letters' satin.
- Each starts with a run walk that the satin then covers.

Ours sews one loop per letter (`stage6_border.keyline_runs`, nearest first) and
lifts between loops wherever `travel_path` finds no route inside the band: 9
satin-to-satin cuts on each job.

- His loops merge into one band, so his walk between letters lies under satin
  still to come.
- Ours are about 2 mm wide (`art_outline.outline_width_mm`: MFab 2.02 / 1.92
  against his 2.40 / 2.13). But the field's rest-fill is sewn first, and the
  gap between two loops is that rest, so nothing later covers a walk across
  it.

**Not built here:** loop order and the walk between loops are
`stage6_border.py`, which belongs to another lane.

**3. Sub-millimetre white specks: he has none.**

- The tracer splits MFab's keyline into the field plus **31 (hat) / 51 (LC)
  white slivers** 0.1-0.3 mm wide along its inner edge.
- Each sliver is `rescued_small_shape` and is sewn as its own run, with a cut
  either side.
- Every one of our sliver stitches lies within 0.3 mm of the pro's white
  thread: his keyline satin passes over all of them.
- Our own field's loops and fill already cover 62% (hat) and 95% (LC) of the
  sliver area. They are sewn after the slivers on the hat and before them on
  the LC.

So most slivers are a second layer of white under or on top of white, and
their cuts buy nothing.

**Why ours misses them: a dark hairline.** The art draws the keyline with a
dark hairline along its inner edge. The tracer therefore returns, in order from
the letter outward:

- the letter body;
- a thin white sliver;
- the hairline (0.1-0.25 mm);
- the field.

Our loop rides the field's hole, which is the hairline's outer edge, and its
crosses go outward, so it never reaches the sliver. The pro's rail sits on the
letter, and his satin spans the sliver, the hairline and the field
(`hat_M_before_after_pro_true.jpg`).

## What was built (all OFF, byte-identical at defaults)

| change | kind | what it does |
|---|---|---|
| `skip_covered_shapes` | own flag (generic stage 7: it can drop any shape) | A shape whose whole thread lies on its own colour block's other thread is not sewn. Cover is other shapes' non-travel runs, sewn before or after, every 0.1 mm at the centre and both edges of the thread, within half a thread (`_UnderThread`'s samples, same block only). Shapes are judged last first. A shape that covers a dropped one is never dropped after it. The Column lane's order pass drops nothing; without that, the dropped slivers lost their rank and re-ordered the riders. |
| `keyline_fold_slivers` | own flag (read only with `sew_enclosed_white`) | A sewn white field's slivers fold back into it, before the art outlines are read. A sliver is in the field's thread, not routed by `sew_enclosed_white`, no text, measured under a thread wide, and within a thread of the field. It joins with the strip between them. A slit thinner than a thread that the fold closes is filled. A fold may shrink a hole but never split one: on the MFab hat a sliver ran across the lower line's hole and cut its panel in three. |
| `fill_section_travel` | existing flag (#1091), unchanged | Routes the under-fill's underlay ring hops and fill sections inside the shape, under rows still to sew. |

`trim_bury_under_later` is Kent's ruled flip (#1057, not merged when this ran),
so the "ruled" base below carries it.

## Result

**Ruled base: the recipe plus #1057's 16 ruled defaults** (`BASE` in
`tools/sewout_card_v7.py`, with `tie_in_off`), i.e. what ships once #1057
lands. Cuts are by where they sit. Ours: each cut belongs to the plan run it
follows. The pro: the DST rule from #1094 (block tone + stitch construction).
The DST column is the trim count read back from the file.

| | DST trims | black under-fill | white loops | white panel / fill | white slivers | black riders | stitches | exposed travel mm | bare mm |
|---|---|---|---|---|---|---|---|---|---|
| hat before | 41 | 3 | 9 | 4 | 16 | 7 | 21,314 | 23.1 | 0.0 |
| hat + `fill_section_travel` | 39 | 1 | 9 | 4 | 16 | 7 | 21,407 | 23.1 | 0.0 |
| hat + `skip_covered_shapes` | 41 | 3 | 9 | 4 | 16 | 7 | 21,029 | 23.1 | 0.0 |
| hat + `keyline_fold_slivers` | 30 | 4 | 11 | 4 | 4 | 7 | 20,352 | 42.5 | 0.0 |
| **hat after (all three)** | **27** | 3 | 11 | 4 | 2 | 7 | **20,270** | 42.5 | 0.0 |
| hat pro | 19 | 0 | 5 | 1 | 0 | 13 | 17,568 | n/a | n/a |
| LC before | 54 | 5 | 5 | 3 | 31 | 9 | 20,415 | 32.7 | 0.0 |
| LC + `fill_section_travel` | 54 | 5 | 5 | 3 | 31 | 9 | 20,433 | 32.7 | 0.0 |
| LC + `skip_covered_shapes` | 48 | 5 | 7 | 2 | 24 | 9 | 19,842 | 32.7 | 0.0 |
| LC + `keyline_fold_slivers` | 33 | 3 | 7 | 3 | 10 | 9 | 18,289 | 23.3 | 0.0 |
| **LC after (all three)** | **29** | 3 | 9 | 2 | 5 | 9 | **18,072** | 23.3 | 0.0 |
| LC pro | 20 | 0 | 6 | 0 | 0 | 14 | 15,786 | n/a | n/a |

**Recipe on main** (no #1057), the 61 / 65 in #1094's table:

| | DST trims | under-fill | loops | panel / fill | slivers | riders | stitches | exposed travel mm |
|---|---|---|---|---|---|---|---|---|
| hat before | 61 | 12 | 11 | 4 | 23 | 9 | 21,767 | 26.1 |
| hat after (fst + skip + fold) | 35 | 5 | 11 | 5 | 5 | 9 | 20,627 | 48.7 |
| LC before | 65 | 8 | 7 | 3 | 37 | 9 | 19,746 | 28.5 |
| LC after (fst + skip + fold) | 38 | 8 | 9 | 3 | 7 | 10 | 17,473 | 13.9 |

### What each change does

- **The fold is the lever:** −11 cuts on the hat and −21 on the LC; slivers
  16 → 4 and 31 → 10.
- **The keyline now reads as one band.** The M's loops sit on the letter and
  the stray thin runs inside them are gone (`*_M_before_after_pro_true.jpg`,
  before | after | pro).
- **Stitches fall:** −962 on the hat and −2,126 on the LC, toward the pro's
  17,568 / 15,786.
- **`skip_covered_shapes`** takes the LC −6 with bury on. On the hat it saves
  285 stitches and no cuts: there bury already hid the hops round the covered
  slivers.
- **`fill_section_travel`** takes the hat's under-fill 3 → 1. It moves
  nothing on the LC once `fill_underlay_cross` (ruled ON) has changed the
  underlay.

### Exposed travel: a real cost on the hat

Exposed travel is read with `travel_cover`: travel that no thread sewn after
it covers. Every leg is on thread; bare thread is 0.0 in every arm.

- **Hat: up** by 19.4 mm on the ruled base and 22.6 mm on main.
- **LC: down** by 9.4 mm and 14.6 mm.
- **Hat, leg by leg** (`exposed_runs.py`):
  - three new legs in the black under-fill's own fill (15.4 mm), lying on its
    finished rows;
  - more legs in the field's rest and panel fill, white on white.
- **Why the under-fill moved at all:** the fold reshapes the panel hole, and
  the under-fill gives up the panel. Its stage-5 polygon moved by 5 mm² (24
  pieces, the largest 1.1 mm²), and the fill tier's section order and travel
  changed with it.
- So the hat's rise is the fill tier's travel reacting to a small change in
  shape, not travel the fold lays. It is still more needle-down thread on top
  of finished fill on the hat: judge it in
  `hat_travel_and_cuts_before_after.jpg` (green: travel over thread; magenta
  dots: exposed samples; black rings: cuts).

## What is left (hat 27 / LC 29 against 19 / 20)

- **Loop to loop, 11 / 9 (pro 5 / 6):** one loop per letter, a lift between.
  This is construction in `stage6_border.keyline_runs`, another lane's file.
- **Riders, 7 / 9 against the pro's 13 / 14:** fewer than his already.
- **Under-fill, 3 / 3 against 0:** the pro's is one stretch.
- **Slivers, 2 / 5:** wider than a thread, further than a thread, or running
  across a hole.

## Byte-identity and tests

- **Recipe, new flags OFF:** both flags OFF plan the recipe exactly as before.
  The hat recipe re-digitized on this branch (main merged) gives plan
  `b5bff100`, the LC `351920cc`: the pre-change arms' md5s.
- **Defaults:** every default path is gated. The OFF md5 pins in
  `test_silhouette_underfill*.py` pass.
- **Targeted tests:** 64 passed:
  - `test_skip_covered_shapes.py`, `test_keyline_fold_slivers.py`
  - `test_silhouette_underfill*.py`, `test_white_fields_fill.py`
  - `test_trim_bury_under_later.py`, `test_enclosed_white_faces.py`
  - the two flags' `test_off_flags_smoke` cases

Scripts (scratch, not in the repo): `arm3.py` digitizes once and plans per arm;
`measure.py`, `exposed_runs.py`, `crops.py`, `same_cover.py`,
`sliver_vs_pro.py`.
