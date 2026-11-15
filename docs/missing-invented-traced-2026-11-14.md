# Missing and invented elements, traced (2026-11-14)

Two of Kent's pin families from the 11-10 to 11-12 defect-marks sittings:

- an element of the art **missing** from what we sew: class 6 of the
  agent-eye census, 14 groups, 19 pins, 9 designs;
- an element we **invented** that the art does not have: class 7, 6 groups,
  41 pins, 6 designs.

Each pin was put beside the original art and the pro's file where one exists,
first on the kit's render (tree `950855bf`, 11-10) and then re-run on `main`
at `66b11432` (11-14, after PR #1515's flips), so a pin already cured by a
later flip is not counted as open.

The class labels come from the census's blind matcher
(`agent-eye-1113/census.json`). Pins, pictures and runs sit gitignored in the
primary checkout under `digitizer/eye_pairs_out/` (`defect-marks-111x/`,
`agent-eye-1113/`, `missing-1114/`). A cloud session does not have them.

Counts here are counts. No agreement figure is claimed (ROADMAP gate 4).

## The answer

- **The largest invented cause is already cured on main.** Kanji seal's 28
  in-fill pins and the neon sign's counter (29 of the 41 invented pins) were
  `sew_enclosed_white` laying white thread in areas the PNG leaves
  transparent. Kent flipped `enclosed_white_skip_transparent` ON on 11-11,
  after the kit was rendered; on main every pinned space is open.
- **The largest cause still open was low_poly's seven "Random Black Spot"
  pins.** It is fixed here behind a new flag, `speck_prune`, built OFF.
- **Two more causes are already built OFF by sibling PRs.**
  - To a T's speed lines (5 pins): `fine_bar_survive`, PR #1513.
  - QR code's finder squares (3 pins): `proofread_guard_clipped`, PR #1487.
- The rest are 1 to 3 pins each, spread over separate causes (table below).

## Every pin

`main?` is what the pin shows on main `66b11432`:
- *cured*: gone on main;
- *open*: still there;
- *kit only*: not re-run (heavy pro jobs), so read from the kit render.

| Pin (design, group, n) | What, by eye | main? | Stage and evidence | Seen by |
|---|---|---|---|---|
| kanji_seal G1, 28 | white in-fill in the seal's empty spaces, some spaces and not others | cured | stage 6 `sew_enclosed_white` on transparent areas; on main the spaces at pins 1-4 are open fabric (10,799 stitches) | proof-read: yes (it misread them as hollow ink first, retracted 11-14) |
| neon_outline_sign G2, 1 | grey fill inside the "a" counter | cured | same rule; open on main | not checked |
| low_poly G4, 7 | black dots on the grey facets at line crossings | **open → fixed here** | stage 3 `keep_thin_strokes` rescue. Each pin is a `rescued_small_shape` on the black thread, 0.13-0.30 mm2 and measured 0.06-0.21 mm wide. Mean width 0.44-1.58 source px. Sewn as run loops (`SMALL_SHAPES_AS_RUN` 25) | element-drop: n/a (an addition, not a loss); proof-read: not checked |
| k_line G2, 2 | red fill outside the red box's satin border | open | stage 6 outline-loop tier: the red box sews as a satin band round an enlarged white K, with fill at another angle inside | proof-read: yes ("red box sewn as a satin band hugging an enlarged white K") |
| k_line G4, 1 | the red box's top edge missing | open | same construction as G2 | proof-read: yes |
| isometric_icon G7, 2 | a shading band on the sausage sewn as its own coloured stripe | open | stage 2 tonal quantize of a gradient (not traced further) | not checked |
| gradient_mascot G1, 1 | a short orange tail off the left nostril | open | not traced | not checked |
| To a T machine G1/G2/G3, beanie G1; 5 | speed lines broken, a gap, the top bar lost | kit only | stages 2-4 split the 0.3 mm bar; stage 5 drops the piece under-fill covers (the thin-bars worker's trace) | proof-read guard brought the beanie's third line back (#1487) |
| qr_code G1, 3 | the bottom-left finder square and black modules gone | open | stage 5 clip (`clipped_stage5`) | element-drop: yes, `clipped` 864 mm2 (11-01); proof-read census: yes |
| heraldic_crest G1, 2 | the lions' eyes (white + pupil, about 1.5 mm) gone | open | not traced: small detail lost before stage 6 | not checked |
| heraldic_crest G2, 1 | the crown unreadable: its dark keylines gone, one yellow mass | open | not traced: thin keylines lost | not checked |
| arabic_calligraphy G2, 2 | the thin stems between leaves gone | open | not traced: a same-colour thin stroke, so not the contrast rescue | not checked |
| precision_drone G1, 1 (ruins) | tree silhouettes against the sky gone | kit only | stage 2: tonal art; the pro redrew the trees as silhouettes | not checked |
| precision_drone G5, 1 | propeller blades merge into the body | kit only | stage 2 tonal, as G1 | not checked |
| becker_hat_large G5, 1 | the black stroke pinches to a neck where it meets the other stroke | kit only | shape detail at a junction (the shape-detail family) | not checked |
| becker_hat_large G10, 1 | a notch in the border satin | kit only | stage 6 border construction | not checked |
| gaulke_roofing_hat G5, 1 | a chunk of the D missing where it meets the N | kit only | letter separation at a merged pair (the merged-letters family) | not checked |

## Tally by cause (Kent's pins)

| Cause | Pins | Designs | State |
|---|---|---|---|
| white in-fill on transparent enclosed areas | 29 | 2 | cured on main (`enclosed_white_skip_transparent` ON 11-11) |
| hairline crossings kept as black run loops (stage 3 rescue) | 7 | 1 | **this PR, `speck_prune` OFF** |
| thin speed lines broken or dropped | 5 | 2 | built OFF, #1513 (`fine_bar_survive`) |
| stage 5 clip | 3 | 1 | built OFF, #1487 (`proofread_guard_clipped`) |
| box sewn as satin band plus inner fill | 3 | 1 | open |
| small detail and keylines lost on the crest | 3 | 1 | open, not traced |
| tonal art flattened | 2 | 1 | open (Phase 4, gate 2) |
| thin same-colour stems lost | 2 | 1 | open, not traced |
| shading band as a stripe | 2 | 1 | open |
| one each: nostril tail, neck pinch, border notch, D chunk | 4 | 4 | open; the last three belong to the shape-detail and merged-letter families |

The census also counted reader-found faults its adjudicator judged real
(+3 missing, +2 invented items). All of them are photos or tonal art:
- comic_halftone: beads, and a border round the poster;
- duotone_poster: stray scraps;
- architecture: a lone satin stroke;
- bw_street: the hands lost;
- distressed_grunge: the R's leg.

None was traced; they sit with the "should this be sewn" question (Phase 4).

## The fix: `speck_prune` (built OFF)

**Where.** `sliver_prune.prune_specks`, called in `pipeline.py` after
`sliver_prune` and before stage 4 traces the masks. It runs on the flat and
gradient classes and is its own flag.

**What.** A mask is a speck when it:
1. is under stage 3's detail floor and still clears the run tier's floors
   (it would be sewn as a run);
2. is not a dot rung, cored counter, floor-rescued stroke or spoked mark;
3. averages under 2 source pixels wide (2 x area / rim);
4. is narrower, inscribed, than the sewing thread (0.4 mm at 40 wt);
5. is wedged in the figure, as a tendril is;
6. is 10 dE00 or more off the mask it lies in.

Its pixels go to the mask it has the most rim on.

**Why those widths.** Both are reads of the raster against existing measures:
the source pixel (the tendril's own "one to two source pixels") and
`thread_profile().width_mm`, the weight `RUN_MIN_AREA_MM2` already squares.
No new stitch value is added, so gate 1 does not apply.

**Why not `sliver_prune`.** low_poly is at the work grid (x1.01), and
`sliver_prune` runs only on rasters enlarged x1.25 or more. Its two halves
also look for page slivers and tendrils, not specks inside the figure. The
thread test is what keeps a coarse source safe: on Becker one source pixel is
already 0.7 mm of real stroke.

**Measured, 80 mm left chest:**
- low_poly: all 7 pinned dots gone. 10,539 -> 10,325 stitches, 97 -> 76 trims.
- At pin 4 a fabric gap of well under 1 mm shows where the dot was. The
  facets' own seam gaps are there OFF as well.
- Controls: see the PR body.

**Sheets** (`art | OFF | ON`, no pro file for these designs):
`digitizer/eye_pairs_out/missing-1114/sheets/` in the primary checkout.

## Limits

- One design carries the cured family; the rule is general, but only low_poly
  has been looked at with it ON beside the controls.
- Pins on the four pro jobs (Becker, Gaulke, Drone, To a T) were read from
  the kit render, not re-run on main.
- "Seen by" was checked against the record (the 11-01 element-drop census,
  the proof-read worker's notes). It was not re-run per pin, so "not checked"
  means not checked, not "missed".
