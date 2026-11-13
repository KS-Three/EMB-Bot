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
