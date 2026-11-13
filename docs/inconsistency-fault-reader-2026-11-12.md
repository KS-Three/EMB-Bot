# Inconsistency reader vs Kent's pins (2026-11-12)

The fifth fault reader scored by `digitizer/tools/fault_reader_harness.py`
against Kent's defect-marks pins: **like features sewn unlike their
siblings**. Reader `digitizer/tools/inconsistency_fault_reader.py`, harness
`--fault inconsistency`, pins `inconsistency-fault-reader-2026-11-12/pins.json`.

**Status of this page.** The PRE-REGISTRATION section below was committed
before the reader was run on any item that holds a selected pin; the reader
was developed on unpinned items only (dev set below). The RESULT section is
appended after the score and changes nothing above it. Every figure is an
instrument reading beside its chance figure (ROADMAP gate 4), not a quality
claim.

## Pre-registration

### This is NOT a hold-out

The target was defined by reading the notes on these same two sittings, and
the reader's feature families were chosen with those notes in view (no
constant was read off a pin, and no reader output on a pinned item was seen
before this commit). A result here says whether the idea finds the faults it
was written for. A hold-out needs a fresh sitting, scored with this commit's
code and constants frozen, on designs that carry repeated features (words
with repeated letters, icon sets, mirrored limbs, rows of equal shapes), with
enough notes to decide (below). `defect-marks-1112` is the letter and space
readers' hold-out and is not touched here.

### Target: which of Kent's notes count

Read from `docs/defect-marks-2026-11-10/marks.json` (L_ items; the four P_
photos carry no such note) and `docs/defect-marks-2026-11-11/marks.json`
(C_ items). Rule `select_inconsistency_pins` in the harness, in order:

1. **Sibling contrast.** The note sets one place against its like
   siblings: the in-fill rule's contrast words (`CONTRAST_RE`: "some ...
   while / others", "only", "doesn't match", "different from", "inconsistent
   from", "look / be the same", "select spots") or "correct ... but" ("the M
   is correct, but the F is wrong"). Unlike the in-fill rule, a THREAD
   COLOUR contrast counts: colour is a treatment.
2. **Not against the pro or the art.** A note naming the pro(s), the image
   or the photo compares with a reference, not with a sibling.
3. **Bare pins** join a note by its range ("#1-#28", "(#5-#6)", "#2-#3") or
   by "same as / same issue". Each pin carries `note_pin`.
4. **No pin is ceded** to another reader; overlap is reported instead.

Wording classes, counted (10 notes, 39 pins, 7 items):

| class | notes | pins | where |
|---|---|---|---|
| "the only ..." (one sibling unlike the rest) | 3 | 4 | Bridge 4 (thin letter), devanagari 1, devanagari 5 (+6) |
| "some ... while others don't" | 2 | 29 | kanji seal 1 (+27 bare), pixel art 1 |
| "doesn't match" / "inconsistent from" (one of a pair) | 2 | 2 | emoji 3 (legs), gradient mascot 1 (nostrils) |
| "should be the same" / "different from each other" | 2 | 4 | gradient mascot 2 (+3, feet colour), Bridge 1 (wheel handles) |
| "X is correct, but Y is wrong" | 1 | 1 | MFab 5 (cross stitches over the F, not the M) |

Per item: `C_kanji_seal` 1 note / 28 pins; `C_devanagari_logo` 2 / 3;
`C_gradient_mascot` 2 / 3; `L_bridge_hat` 2 / 2; `L_mfab_hat` 1 / 1;
`C_pixel_art_sprite` 1 / 1; `C_flat_emoji_icon` 1 / 1.

Considered and OUT: Becker 17 "stitching directions and angles are very
inconsistent here" and Becker 19 "the angles are completely different"
(inconsistency within ONE place, no sibling named); Drone 3 and ProSeal 1
"border ... changing colors too much" (variation along one feature); low
poly 2 (border colour change, "matches the photo"); MFab 3 and Bridge 8
(against the pro); Bridge 3 (against the image); MFab 9 (preview colour).

### Power: what these notes can decide

10 notes on 7 items, pooled per note against `chance_pick` with the
harness's item bootstrap. Simulated (binary note hits, the real
notes-per-item layout, pick 0.3, 200 runs x 2,000 resamples): median 95% CI
width about 0.5, and the lower bound clears 0 in 54% of runs at a true gain
of +0.3, 69% at +0.4, 86% at +0.5. **A verdict is possible, but only a large
effect can be shown; "not shown" here does not exclude a moderate one.** A
hold-out of 20 notes over 10 items narrows the width to about 0.4 (95% power
at +0.4); 16 items, about 0.35.

### The reader (rule and every constant)

Two families of feature, both grouped by geometry only:

**F1, sewn shapes (new).** Per thread colour class, each 8-connected
component of the top thread (the in-fill reader's `thread` raster, 12 px/mm)
whose deepest point is at least `MIN_HALF_MM` = 0.4 mm (= `THREAD_MM`: two
filaments across) from its edge. Two shapes are alike when areas are within
`AREA_RATIO` = 1.5 x, elongations (sqrt of the second-moment eigenvalue
ratio) within `ELONG_RATIO` = 1.25 x, and solidities (pixels / convex-hull
pixels) within `SOLIDITY_DIFF` = 0.10. Colour, rotation and mirror are
ignored on purpose. Groups = connected components of the alike graph. Those
three tolerances have no source in the repo: round numbers fixed before any
run, checked only on the dev items to group visibly alike shapes.

Four treatments per shape:

- **colour**: its thread class.
- **kind**: commonest top run kind on it among fill, satin, run, bean,
  border (the in-fill raster's `kind`).
- **angle**: the length-weighted axial mean of the stored design's fill and
  satin needle segments (each at least `THREAD_MM` long) whose midpoint
  lies on the shape in its own colour, judged with at least
  `ANGLE_MIN_SEGS` = 3 segments and resultant `ANGLE_MIN_R` = 0.5 (the
  doubled-angle resultant: a direction exists; a priori). Two shapes both at
  least `ROUND_ELONG` = 1.5 elongated (a priori) are compared relative to
  their own axes, folded to [0, 90] (a rotated or mirrored copy sewn the
  same way agrees); otherwise absolute, mod 180. Disagree past
  `ANGLE_TOL_DEG` = 45 (halfway from parallel to perpendicular). Shapes of
  different run kinds are not compared on angle (a dev fix on
  `L_becker_hat_large`: a fill row against a satin swing is a `kind`
  difference already).
- **rim**: `outlined` when at least `OUTLINED` = 0.25 of the band within
  `RIM_MM` = 0.4 mm of its edge (both sides) is topped by a line run (run,
  bean, border), `plain` at most `PLAIN` = 0.05, else not judged: the
  in-fill reader's rim constants, applied to ink.

A shape is **odd** on a treatment when it disagrees with more than half of
the judged, comparable members of its group (a disagreeing pair: both; A, A,
B: only B; A, B, C: all). Every odd shape is flagged; strength = the number
of treatments it is odd on (1-4).

**F2, empty spaces (the in-fill reader, frozen).** Its stored flags and
candidates from `eye_pairs_out/infill_reader/<item>.flags.json` (pre-
registration `ba01dcb7`, tree `950855bf`), verbatim. Where the in-fill
reader refused an item (`L_mfab_hat`) there is no F2.

**Flags and candidates.** Flags spread over each odd F1 shape on a
`SPACING_MM` = 2.0 mm grid (= the edge reader's merge distance), at its
deepest point when no grid node lands on it. Candidates (the anchors of
`chance_pick`) are spread the same way over every F1 shape in a group of two
or more, plus F2's candidates. `cand` mask = those shapes' pixels plus F2's.

**Inputs.** No pipeline. The in-fill reader's `labels.npz` (`thread`,
`kind`) and `mask.npz`, and the stored designs
(`defect-marks-1110/pro_run`, `defect-marks-1111/logo_run`), whose stitch
hash must equal the in-fill record's `stitches_sha256` (the letter reader's
for `L_mfab_hat`), and whose render frame must equal the rasters' shape;
else the item is refused.

### Scoring

- Radius 3.0 mm (`RADIUS_MM`); 2 and 5 mm reported, never the verdict.
- **Verdict line:** per note (each note weighs one), hit rate against
  `chance_pick` (random candidate anchors), item-bootstrap 95% CI on the
  difference (`pool_notes`, 5,000 draws, seed 20261110).
  **Shown** if the lower bound is above 0; **not shown** if the interval
  holds 0; **no verdict** if fewer than two items carry scored pins (no
  interval).
- Also reported, none of them the verdict: per pin; `chance_area` and
  `chance_cand`; precision against `precision_pick`; strength AUC; F1 alone
  (F2 removed); leave-one-item-out; per pin, whether the letter, space and
  in-fill readers' stored flags lie within 3 mm.

Predicted, before the run: devanagari 1 and 5 hit through F2 (the in-fill
reader hit 3/3 there); kanji hits 9/28 through F2 against a pick near 1.0;
Bridge 4 (letters of different shapes never group), Bridge 1 (handles sewn
in different shapes may not group) and MFab 5 (travel is not a treatment)
are likely misses; pixel art, emoji, nostrils and feet depend on F1 grouping
the siblings at all.

### Items and dev set

Run: every item with rasters in `eye_pairs_out/infill_reader` (31: 10 L_,
21 C_; `L_gaulke_roofing_hat` has none). An item with no stitch-hash record
(the in-fill reader's, else the letter reader's) is refused; no pinned item
is in that set. Pooled figures cover the 7 pinned items; flags on the others
are reported as unpinned flags only. Dev items (read
while building, before this commit): `C_neon_outline_sign`,
`C_outline_lineart_logo`, `L_toat_beanie`, `L_tires_hat_3d`, `C_low_poly`,
`L_becker_hat_large`, `C_heraldic_crest`, `C_isometric_icon`,
`L_proseal_hat`; none holds a target pin.

Commands (`E` = the primary checkout's `digitizer/eye_pairs_out`):

    python -m tools.inconsistency_fault_reader run --labels $E/infill_reader \
        --design-run $E/defect-marks-1110/pro_run --design-run $E/defect-marks-1111/logo_run \
        --letter $E/defect-marks-1110/letter_reader --out $E/inconsistency_reader --only <item> ...
    python -m tools.inconsistency_fault_reader analyse --out $E/inconsistency_reader \
        --marks ../docs/defect-marks-2026-11-10/marks.json --prefix L_ \
        --marks ../docs/defect-marks-2026-11-11/marks.json --prefix C_ \
        --reader letters=$E/defect-marks-1110/letter_reader --reader letters=$E/defect-marks-1111/letter_reader \
        --reader space=$E/space_reader --reader infill=$E/infill_reader \
        --json ../docs/inconsistency-fault-reader-2026-11-12/score.json
