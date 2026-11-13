# Negative-space fault reader (2026-11-12)

The fourth reader scored against Kent's defect-marks pins, by
`digitizer/tools/fault_reader_harness.py` (`--fault space`). Reader:
`digitizer/tools/space_fault_reader.py`; tests:
`digitizer/tests/test_space_fault_reader.py`. Part 1 (the pre-registration)
was committed in its own commit before the reader was run on any item that
holds a target pin. Part 2 (the result) was added after, and part 1 was not
edited.

# Part 1: what is fixed before any score

## Why this reader

The letter reader (`docs/letter-fault-reader-2026-11-11.md`) compares
TOPOLOGY per thread colour: counters lost, shapes joined, bays closed into
holes. A bay filled SOLID changes no hole count, so it cannot see it. Its
write-up names its misses on these same pins: both "the S doesn't have spacing
between the curves" pins (Gaulke 6, ProSeal 2), Bridge's B holes and the TOAT
T into the border. This reader reads the SPACES instead: the midline of the
negative space of each colour, and whether that colour's thread covers it.

## What was looked at before this page

- The letter, edge and in-fill readers' write-ups and memory notes, which
  name the letter reader's hits and misses on these pins (above). Pin
  positions were not compared with anything this reader computes.
- The pin list below (notes and rules, printed by `select_letter_pins`).
- Dev runs on the five sitting-1 items with NO target pin (`L_becker_hat_large`,
  `L_goldentee_hat`, `L_precision_drone`, `L_tires_hat_3d`,
  `L_toat_machine_hat`), with overlay pictures of flags and candidates on
  the scratchpad (not committed). One change came from them, a bug, not a
  constant (below, "Dev runs").

So this is NOT a hold-out: the idea came from the letter reader's misses on
these pins. What the pre-registration fixes is the rule and every number, so
the score cannot be tuned to the pins.

## Which pins count (targets)

Exactly the letter reader's pins: `select_letter_pins` (a closure word in the
note, or a read word on a letter; its rule 3 shares Gaulke 3 with the edge
rule; its rule 4 lets bare pins inherit a "same issue" note). This is the
brief's "closed/merged-letter and unreadable-letter notes", and using the
letter reader's own list makes the overlap table a like-for-like comparison.
The harness's `select_space_pins` adds `note_pin` (the pin whose note
admitted it) so each NOTE can weigh one. List: `space-fault-reader-2026-11-12/pins.json`,
pinned by a test.

| sitting | item | target pins | notes | note (abridged) |
|---|---|---|---|---|
| 11-10 | `L_bridge_hat` | 2, 5, 6, 9, 10, 12 | 6 | B missing its holes; can't tell the &; B and R merge; can't read the e; no space between the eye's body and dot; N and T merged |
| 11-10 | `L_gaulke_roofing_hat` | 2, 3, 6 | 3 | not enough spacing in the E; white spacing not apparent (+ jagged); S has no spacing between the curves |
| 11-10 | `L_hotel_fremont_hat` | 1, 2 | 2 | the A is hard to read; the pro makes the lettering larger, easier to read |
| 11-10 | `L_mfab_hat` | 10 | 1 | can't read the G, no spacing between the lettering |
| 11-10 | `L_proseal_hat` | 2 | 1 | the S has no spacing between the curves |
| 11-10 | `L_toat_beanie` | 4 | 1 | the T intersects the border |
| 11-11 | `C_silhouette_logo` | 3-32 | 1 | lettering extremely hard to read, extra green stitches (pin 3; 29 bare pins "same issue") |

**44 pins, 7 items, 15 notes.** Sitting 1 holds 14 pins on 6 of its 11
items; sitting 2 holds 30 pins on 1 of its 21 (the rule was written in
sitting 1's words; see `defect-marks-sitting-2-2026-11-11`). Not used: the
`defect-marks-1112` kit, its pins and anything under its out dir (the letter
reader's hold-out, being sat now).

Predicted, by design and not the verdict: Gaulke 6 and ProSeal 2 (an S's
bays) and Gaulke 2 (the E's mouths) are the pins this reader exists for.
They are reported one by one.

## The reader

Input: the letter reader's stored rasters for each item
(`<item>.labels.npz`: `art` = the stage-1 raster, each pixel the nearest
thread class or unsewn by `bg_mask`, warped into the render grid; `thread` =
the top thread class at each pixel, every filament of the stored design at
`render_design`'s width, in sew order, no anti-alias; 12 px/mm, pad 2 mm, the
pins' frame) and its `<item>.mask.npz` (thread pixels). These were written by
`tools.letter_fault_reader run` on tree `950855bf`, which refused any item
whose re-run stitches differed from the stored design; the stitch sha in each
record was re-checked against the stored job file for all 12 items on
2026-11-12 (all match). The reader runs no pipeline and no service.

Per thread class `c`: `S` = the art's `c` pixels, 8-connected shapes of at
least `MIN_SHAPE_MM2`; a shape is JUDGED when at least `SEWN_FRAC` of its art
pixels carry `c` thread. `T` = the thread's `c` pixels.

1. **Space ridge**, two parts:
   - **bay**: per judged shape, the skeleton of (its convex hull less `S`):
     `glyph_read`'s `space` rule;
   - **gap**: the Voronoi line between two judged shapes (pixels whose
     nearest `S` pixel belongs to different shapes, both pixels off the ink),
     kept inside the convex hull of the pair.
   Both kept where the ridge point is at least `SPACE_MIN_HALF_MM` from any
   `S` pixel, and only where its clear circle (radius = that distance) fits
   inside the hull (the pair's, for a gap) with `SPACE_KEEP_HALF_MM` to
   spare (`enclosed`).
2. **Closed**: a ridge point with `T` within `SPACE_KEEP_HALF_MM`.
3. **Fault**: an 8-connected run of closed ridge points of more than
   `BRIDGE_MIN_MM` (pixel count / 12 as length). Flags along it greedily,
   widest art space first, no two within `SPACING_MM`; strength = the run's
   length, mm; each flag records `bay` or `gap`.
4. **Candidates** (the places it could flag, for `chance_pick`): every
   8-connected ridge run (closed or not) of more than `BRIDGE_MIN_MM`, spread
   the same way; `cand` mask = those ridge pixels.

### Every constant, and where it comes from

| constant | value | source |
|---|---|---|
| `PXMM`, `PAD_MM` | 12, 2.0 | the review render and pins' frame (`letter_fault_reader`) |
| `THREAD_MM` | 0.4 | `stitchviz.THREAD_MM` |
| `SPACE_MIN_HALF_MM` | 0.15 | `glyph_read.SPACE_MIN_HALF_MM` (a space is read when this circle fits) |
| `SPACE_KEEP_HALF_MM` | 0.10 | `glyph_read.SPACE_KEEP_HALF_MM` (it survives with this clear circle) |
| `MIN_SHAPE_MM2` | 0.12 | `glyph_read.MIN_GLYPH_MM2`, as the letter reader |
| `SEWN_FRAC` | 0.5 | `letter_fault_reader.SEWN_FRAC` |
| `BRIDGE_MIN_MM` | 0.6 | `letter_fault_reader.BRIDGE_MIN_MM`, 1.5 filaments: one running stitch across a space is travel |
| `SPACING_MM` | 2.0 | `edge_fault_reader.MERGE_MM` |

A test asserts each equals its source. Nothing was fitted.

## Scoring

The harness, unchanged in method, with the in-fill reader's candidate nulls:

- **Radius 3.0 mm** (all earlier readers'); 2.0 and 5.0 reported, never the verdict.
- **Verdict null `chance_pick`**: each pin placed on a candidate anchor drawn
  uniformly (exact mean over anchors): among the places this reader could
  flag, does it flag the ones Kent pinned. Reported beside it, not the
  verdict: `chance_cand` (random points on candidate ridge pixels),
  `chance_area` (random thread pixels: the letter reader's null, for
  comparison), `chance_edge` (reported only; 0 by definition inside sewn fields).
- **Weighting**: per NOTE (each of the 15 notes weighs one: its pins' hit
  rate minus its item's null) is the verdict's figure; per pin (the
  harness's pin-weighted pool) is reported and also has to clear.
- **Intervals**: 95% bootstrap over ITEMS, 5,000 draws, seed 20261110.
- **Precision** (share of flags on target items within 3 mm of a target pin)
  beside `precision_pick`.

## What counts as shown

At 3.0 mm, against `chance_pick`:

1. at least **4 of the 7 target items** scored (not refused);
2. the per-note hit rate above `chance_pick`, item-bootstrap 95% lower bound
   above 0;
3. the per-pin pool's lower bound above 0 as well.

- **Shown**: 1, 2 and 3 hold. If leaving any one item out takes either lower
  bound to 0 or below, it is written "shown, fragile".
- **No verdict**: fewer than 4 target items scored, or `chance_pick`
  undefined on a scored target item.
- **Not shown**: otherwise.

## Also reported (not the verdict)

- Per item and per note: pins, hit, `chance_pick`, `chance_area`, nearest flag.
- Leave one item out, per-note and per-pin figure with its interval.
- **Overlap with the letter reader**, per pin and per note at 3 mm: hit by
  both, space only, letter only, neither. Letter flags: the committed run
  (`eye_pairs_out/defect-marks-1110/letter_reader`, and
  `docs/defect-marks-2026-11-11/C_silhouette_logo.flags.json`).
- The three predicted pins (two S, one E), one by one.
- Flag counts on the 5 non-target items with letter-reader rasters (the dev
  items), to show what it says where Kent did not point at this fault. The
  20 non-target corpus rows of sitting 2 have no art raster on disk and are
  not run (no target pin, no score).

## Dev runs (no target pin)

On the five items above. First run: 112 / 114 / 329 / 45 / 140 flags; most
on Becker sat in shallow dents of the outer outline and of the lettering
edges, on the skeleton line midway between the ink and the hull's edge,
which the render's thread spill always reaches. That is `glyph_read`'s hull
rule applied to a field instead of a glyph. Fix (a rule, no new number): the
`enclosed` test above. Second run: 13 / 27 / 182 / 5 / 66 flags (Becker's
outline flags gone; Drone's on its visibly merged THERMAL / AND DRONE
lettering and its scene). No constant was changed. Becker's art raster puts
its letters and field in one class (a letter-reader raster limit, known), so
its letters' spaces are not read; it carries no target pin.

# Part 2: result (2026-11-12, after `837c105d`)

Run on the 12 items with letter-reader rasters (tree `950855bf`, every stitch
sha re-checked), no constant or rule changed after the pre-registration
commit. Command lines at the end. Full output:
`space-fault-reader-2026-11-12/score.json`.

## Verdict: shown (not fragile), on a non-hold-out

At 3.0 mm against `chance_pick`, all 7 target items scored:

| weighting | hit | `chance_pick` | diff | kappa | 95% CI (items) |
|---|---|---|---|---|---|
| **per note (verdict)**, 15 notes | 0.798 | 0.483 | **+0.315** | 0.61 | **[+0.22, +0.47]** |
| per pin, 44 pins | 0.909 | 0.616 | +0.293 | 0.76 | [+0.24, +0.44] |

12 of 15 notes beat their item's null. All three conditions hold. Leaving any
one item out keeps both lower bounds at +0.21 or above (table below), so it is
not "fragile" by the page's test.

**Read it for what it is.** This is not a hold-out: the reader was designed
from the letter reader's misses on these same pins, and the pins' rule was
written in sitting 1's words. The pre-registration stops the numbers being
tuned to the pins; it does not make these pins fresh. Replication on
pins the reader has never met (a sitting such as `defect-marks-1112`, once
its letter-reader hold-out is done, with this reader frozen at `837c105d`)
is what would make it a measurement.

It is also BROAD. On target items it flags about half the places it could
(`chance_pick` 0.48 per note), and of its 519 flags on those items 20% lie
within 3 mm of a target pin, against 12% for the same number of candidates
picked at random (precision diff +0.08, CI [+0.005, +0.19]). It finds the
pinned spaces more often than the unpinned ones; most of what it flags Kent
did not pin. On the five items with no target pin it raises 13 (Becker), 27
(Golden Tee), 182 (Drone), 5 (Tires) and 66 (TOAT machine) flags.

## Other nulls and radii (not the verdict)

| null, 3.0 mm | per note diff, CI | per pin diff, CI |
|---|---|---|
| `chance_cand` | +0.29 [+0.19, +0.45] | +0.27 [+0.21, +0.43] |
| `chance_area` (the letter reader's) | +0.45 [+0.36, +0.64] | +0.66 [+0.36, +0.76] |

`chance_pick` at 2.0 mm: per note +0.37 [+0.21, +0.59]; at 5.0 mm: +0.10
[+0.01, +0.25] (at 5 mm the flags cover most candidates: pick 0.70).

## Per item and per note (3.0 mm)

| item | pins | flags | candidates | hit | `chance_pick` | misses (nearest flag, mm) |
|---|---|---|---|---|---|---|
| `L_bridge_hat` | 6 | 40 | 269 | 4 | 0.48 | 2 B's holes (6.8), 12 N+T merged (7.4) |
| `L_gaulke_roofing_hat` | 3 | 79 | 262 | 3 | 0.50 | - |
| `L_hotel_fremont_hat` | 2 | 37 | 716 | 1 | 0.29 | 2 "the pro makes the lettering larger" (7.8) |
| `L_mfab_hat` | 1 | 94 | 534 | 1 | 0.55 | - |
| `L_proseal_hat` | 1 | 92 | 209 | 1 | 0.58 | - |
| `L_toat_beanie` | 1 | 74 | 603 | 1 | 0.48 | - |
| `C_silhouette_logo` | 30 | 103 | 381 | 29 | 0.69 | 26 (3.2) |

Predicted pins: Gaulke 6 (S, 1.21 mm), ProSeal 2 (S, 1.38 mm), Gaulke 2 (E,
0.90 mm): all three hit, the two S's being pins the letter reader missed.

## Leave one item out (per note / per pin vs `chance_pick`, 3.0 mm)

| left out | per note diff, CI | per pin diff, CI |
|---|---|---|
| `L_bridge_hat` | +0.40 [+0.28, +0.49] | +0.31 [+0.28, +0.49] |
| `L_gaulke_roofing_hat` | +0.27 [+0.21, +0.44] | +0.28 [+0.22, +0.40] |
| `L_hotel_fremont_hat` | +0.33 [+0.22, +0.49] | +0.30 [+0.25, +0.49] |
| `L_mfab_hat` | +0.31 [+0.21, +0.47] | +0.29 [+0.23, +0.44] |
| `L_proseal_hat` | +0.31 [+0.21, +0.47] | +0.29 [+0.23, +0.45] |
| `L_toat_beanie` | +0.30 [+0.21, +0.46] | +0.29 [+0.22, +0.43] |
| `C_silhouette_logo` | +0.32 [+0.22, +0.49] | +0.32 [+0.22, +0.49] |

## Overlap with the letter reader (3.0 mm, same pins)

| | pins | notes (any pin hit) |
|---|---|---|
| both | 33 | 8 |
| **space only** | **7** | **4** |
| letter only | 2 | 2 |
| neither | 2 | 1 |

Space only: Gaulke 3 ("white spacing not very apparent"), Gaulke 6 and
ProSeal 2 (the S's), TOAT beanie 4 (the T into the border), silhouette 7, 10
and 30. Letter only: Bridge 12 (N and T merged: the letter reader's join;
nearest space flag 7.4 mm) and Fremont 2 (a size remark, not a place).
Neither: Bridge 2 (the B's holes) and silhouette 26. The misses were not
opened at the render. The two readers are complementary on these pins:
together they reach 14 of 15 notes.

## How to run

From a lane's `digitizer/`, with the letter reader's out dirs from its own
run (`docs/letter-fault-reader-2026-11-11.md`):

    E=<primary>/digitizer/eye_pairs_out
    python -m tools.space_fault_reader run --labels $E/defect-marks-1110/letter_reader --out $E/space_reader
    python -m tools.space_fault_reader run --labels $E/defect-marks-1111/letter_reader --out $E/space_reader
    python -m tools.space_fault_reader report \
        --marks ../docs/defect-marks-2026-11-10/marks.json --flags $E/space_reader --prefix L_ \
        --marks ../docs/defect-marks-2026-11-11/marks.json --flags $E/space_reader --prefix C_ \
        --letter-flags $E/defect-marks-1110/letter_reader --letter-flags $E/defect-marks-1111/letter_reader \
        --json ../docs/space-fault-reader-2026-11-12/score.json

Both `run`s take about 15 s on the laptop; no pipeline runs.

# Part 3: replication pre-registration (2026-11-12, before any 11-12 mark is read)

**Foreman's call 2026-11-12, not Kent's words:** score this reader, frozen,
on the `defect-marks-1112` sitting once the letter reader's hold-out there is
scored. Written and pushed before this session opened that sitting's
`marks.json` or its page. It does not say whether Kent has started sitting.

## What is frozen

- **The reader as at `837c105d`.** sha256 of its detection path
  (`to_mm`, `shapes`, `_hull_pts`, `hull_depth`, `enclosed`, `space_ridge`,
  `spread`, `read_class`, `_points`, `read_spaces`, `run` and the module
  constants, docstrings stripped, through `ast.unparse`): `aee7d26da21c71eaa2687e7e4bf7a1b2e6629a8482765b71ed6366b9a4f6d2b9`.
  (Corrected 2026-11-13: the first value, `6f29dace…`, hashed `ast.dump`,
  whose output changed in Python 3.13, so CI's 3.12 read a different number.
  The new one is the same on 3.12 and 3.14, at `837c105d` and on HEAD.)
  It is the same at `837c105d`, at `129131d2` (the result) and on main
  `8bd56ff7`. `test_detection_code_is_frozen_for_the_replication` pins it.
  The reader is not edited before this score.
- **The harness and the letter reader** (`fault_reader_harness.py`,
  `letter_fault_reader.py`) are byte-identical between `837c105d` and
  `8bd56ff7`. So the pin rule, the hit test and the nulls are the ones Part 1
  used.

## Items, pins, rasters

- **Kit:** `defect-marks-1112` (`kit_sha256` `f824c55c20f7…`), built by the
  letter-reader worker for ITS hold-out
  (`docs/letter-reader-replication-2026-11-12.md` on its branch). Nine
  Commons lettering logos `C_lt_*`, each at 80 mm on left_chest. Nobody has
  run this reader on any of them.
- **Target pins:** `select_space_pins(marks, "C_")` on that kit's
  `marks.json`. This is the letter reader's frozen pin rule plus `note_pin`,
  exactly as in Part 1. A **target item** is an item with at least one
  selected pin. No pin is added or dropped by hand, including letter notes the
  rule misses.
- **Rasters:** the letter reader's `labels.npz` from the letter worker's run
  on the kit, read and never written. If an item has none, it is made with
  the frozen letter reader into this reader's own out dir from the kit's
  stored job, with no digitize. If that is not possible, the item is refused.
  Outputs go to `eye_pairs_out/space_reader_1112/` only, never into the
  letter worker's files.

## Scoring and pass line (as Part 1, item floor raised)

At **3.0 mm**, against **`chance_pick`**. Per note is the verdict figure and
per pin has to clear too. Intervals are a 95% bootstrap over items, 5,000
draws, seed 20261110.

1. at least **5 target items** scored (not refused);
2. the per-note hit rate above `chance_pick`, lower bound above 0;
3. the per-pin pool's lower bound above 0.

- **Shown**: 1, 2 and 3 hold. "Shown, fragile" if leaving any one item out
  takes either lower bound to 0 or below.
- **No verdict**: fewer than 5 target items scored, or `chance_pick`
  undefined on a scored target item.
- **Not shown**: otherwise.

Why 5: it is the letter reader's own replication floor, so both readers face
the same line on the same pins. With nine items, 4 of 7 (Part 1's floor)
would be a lower bar.

**"No verdict" is a likely outcome, and an honest one.** The kit was chosen
for the letter reader. The first sitting gave a letter pin under the rule on
6 of 11 logos, so about 5 of 9 is expected, right at the floor. The
"S/E bay filled" fault this reader exists for may not be pinned at all. A
"not shown" at about 5 items is mostly a statement about power (the letter
worker's simulation puts a real half-size effect at P(shown) about 0.28 to
0.43).

## Also reported (not the verdict)

Per item and per note at 3 mm. Leave one item out. Overlap with the letter
reader on the same pins, using its flags from its own replication run, read
only. Precision against `precision_pick`. Flag counts on the kit's
non-target items. The result is appended here as Part 4 in its own PR.

# Part 4: replication result on `defect-marks-1112` (2026-11-13)

## Verdict: no verdict

Only **2 of the 9 items** carry a target pin under the registered rule, and
Part 3 needs 5. The reader is the one frozen at `837c105d` (the digest test
passes), and nothing was retuned. The 11-12 pins can neither support nor
contradict Part 2's "shown". Part 2 stays a result on the pins that shaped
the idea, with no replication.

- **Marks:** `digitizer/eye_pairs_out/defect-marks-1112/marks.json` in the
  primary checkout. Its sha256 is `12e74bff709304a6…`, the same as the letter
  worker's preserved copy. It was read, never written. Kent pinned 60 pins
  on 8 of the 9 items.
- **Target pins:** `select_space_pins(marks, "C_")` gives 2 pins, 2 notes, on
  `C_lt_bukit_asam` and `C_lt_n_sync`. These are the same two items the
  letter reader's own hold-out scored (also no verdict). The letter worker
  reads most of the other notes as edge, flatness, stitch-type and alignment
  faults.
- **Rasters:** the letter reader's `labels.npz` for those two items, taken
  from the letter worker's run and read only (tree `ea13a362`, the kit's). Its
  `flags.json` is identical to the one in its lane. Output went to
  `eye_pairs_out/space_reader_1112/`. The score is in
  `space-fault-reader-2026-11-12/score-1112.json`.

## For the record (not a verdict: 2 items, 2 pins)

| item | pin | Kent's note | flags / candidates | nearest flag | hit at 3 mm | `chance_pick` | letter reader |
|---|---|---|---|---|---|---|---|
| `C_lt_bukit_asam` | 2 | "No spacing between the rings" | 18 / 54 | 0.51 mm | yes | 0.65 | hit |
| `C_lt_n_sync` | 1 | thread angles that "shouldn't be adjacent or touching" on an "S" | 6 / 46 | 9.0 mm | no | 0.26 | miss |

Pooled at 3 mm against `chance_pick`, per note and per pin alike: hit 0.50
vs 0.45, +0.05, CI [-0.26, +0.35]. With one item in each leave-one-out arm,
the interval has zero width and means nothing. Precision is 0.125 vs 0.056.

The overlap with the letter reader is one pin hit by both and one hit by
neither. On these pins the two readers did not split the way they did in
Part 2.

**The S pin is a miss, and the write-up does not lean on it.** The note is
about two stitch directions meeting on the S, not about the S's bays filling
solid, so it is not the fault this reader looks for. The rule admits it
because "touch" is one of its closure words (`CLOSE_WORDS`). One pin is
below the registered floor either way.

## What this leaves

The kit was chosen for the letter reader and yielded two letter pins. A
replication of either reader needs a sitting whose art is likely to draw
closure and spacing notes: small lettering with bowls and bays (S, E, B, a,
e), sat at a size where they fill. That is a question for the foreman. This
page proposes nothing more.
