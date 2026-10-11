# coverage_edges under the Column lane — Becker, 2026-10-11

PR #818 built `coverage_edges` OFF with two open follow-ups: (a) read it at
the stitch level before any flip, and (c) MARINE reads messier under it,
blamed on the skeleton satin tier having been tuned on stair-stepped
polygons. This is that read: Becker (`becker_marine_logo.png`, the one
fixture the flag touches) at 50 and 80 mm, left chest, six colours, across
`coverage_edges` {off, on} × the Column lane (`lettering_columns` +
`lettering_words`) {off, on}. **All three flags stay OFF. Nothing was sewn.**

No new instrument. One digitize per cell; every number is an existing tool's
(`tools.eye_pairs.features`: `dropped_elements` + `edge_smoothness` on one
registration; `tools.fan_census`: cross lengths and bare satin area per
text-tagged letter). Script, JSON and log:
`docs/renders/coverage-edges-columns-2026-10-11/`. Re-ran twice, identical.

## Verdict

**The MARINE mess comes from the skeleton decomposition, not from the
polygon.** On the same coverage outline (which is clean; #818's
`becker-flag-outlines.png`), the skeleton tier triples MARINE's over-long
crosses at 80 mm (9 → 28: M 13, N 4, E 11), and the needle map fills with
short scattered stitches. The Column lane sews the same outline with **zero**
long crosses and zero fans, and it gives the cleanest of the four crops.
**Under outline rails the cleaner outline does help.** Against the Column
lane alone it cuts bare MARINE satin 3.97 → 1.06 mm² and uncovered ink 4.85 →
3.71% at 80 mm, and halves `lost_frac` at 50 mm (0.0395 → 0.0196, nearly all
overshoot). It also takes a few trims and stitches off at both sizes. It
costs a higher Hausdorff (3.1 → 3.5 mm at 80; that follows the flag in both
lanes, so it is the flag's). At 50 mm the A's counter shrinks and the notch
between its legs closes: the sub-pixel feature loss #818 predicted. So if
`coverage_edges` ever ships, it should ship **with** the Column lane, not on
its own under the skeleton tier. That flip is Kent's call, and both are
still unsewn.

## The table

`lost` = `lost_frac` = `unsewn` + `overshoot` (the two halves; their
magnitudes are not quotable, only their deltas; see
`.claude/memory/lost-frac-is-two-metrics-2026-09-20.md`). `uncov` =
colour-free uncovered ink fraction. MARINE columns are its six text-tagged
letters: over-long crosses (left to right M A R I N E), fan crosses, and satin
area that carries no thread of any kind.

### 50 mm

| arm | stitches | trims | lost | unsewn | overshoot | uncov | ragged mm | hausdorff mm | MARINE long (M A R I N E) | fans | MARINE bare mm² |
|---|---|---|---|---|---|---|---|---|---|---|---|
| shipped | 3157 | 24 | 0.0325 | 0.0031 | 0.0294 | 3.40% | 0.165 | 2.09 | 9 (0 0 0 0 0 9) | 0 | 8.54 |
| coverage_edges | 3197 | 18 | 0.0176 | 0.0043 | 0.0133 | 3.03% | 0.151 | 2.53 | 4 (0 0 0 0 0 4) | 4 | 7.50 |
| columns_words | 2922 | 16 | 0.0395 | 0.0031 | 0.0363 | 2.77% | 0.165 | 2.92 | 0 | 0 | 0.34 |
| **coverage + columns** | 2869 | 15 | 0.0196 | 0.0043 | 0.0153 | 2.43% | 0.151 | 2.80 | 0 | 0 | 0.80 |

### 80 mm

| arm | stitches | trims | lost | unsewn | overshoot | uncov | ragged mm | hausdorff mm | MARINE long (M A R I N E) | fans | MARINE bare mm² |
|---|---|---|---|---|---|---|---|---|---|---|---|
| shipped | 6842 | 40 | 0.0221 | 0.0076 | 0.0144 | 4.82% | 0.165 | 3.10 | 9 (9 0 0 0 0 0) | 0 | 14.12 |
| coverage_edges | 7051 | 36 | 0.0238 | 0.0112 | 0.0126 | 4.50% | 0.172 | 3.50 | **28** (13 0 0 0 4 11) | 0 | 14.31 |
| columns_words | 6161 | 24 | 0.0288 | 0.0134 | 0.0154 | 4.85% | 0.169 | 3.10 | 0 | 0 | 3.97 |
| **coverage + columns** | 6029 | 21 | 0.0234 | 0.0101 | 0.0133 | 3.71% | 0.167 | 3.50 | 0 | 0 | 1.06 |

Pipeline warnings (`result.warnings`) are the same four codes in all eight
cells. #818's `HOLE_NEARLY_CLOSED` did not appear, but this read uses the
Studio's six colours and does not read plan-level warnings.

## The pictures

`docs/renders/coverage-edges-columns-2026-10-11/`:

- `marine-80mm-thread.jpg`, `marine-50mm-thread.jpg`: thread render of
  MARINE, a 2×2 sheet. Top row is the skeleton tier, bottom row the Column lane;
  left is the shipped outline, right is `coverage_edges`.
- `marine-80mm-needle.jpg`, `marine-50mm-needle.jpg`: the same crops with
  every needle penetration dotted. The top-right cell (coverage outline,
  skeleton tier) is where the scatter of short stitches shows.

## What could be wrong

- One fixture, one run per cell, Becker only. It is the only file the flag
  touches.
- The fan census reads text-tagged letters. BECKER's five tagged letters carry no
  satin crosses in any cell, so MARINE is the whole lettering read.
- Hausdorff is a design-wide maximum and was not localised here.
- Becker's A-counter loss at 50 mm and the narrower lower slot of the E (at
  both sizes) under `coverage_edges` come from looking at the pictures. They
  are not measured.

## Eye pairs

Two arms were added so this can be sat blind: `coverage_edges`
(`coverage_edges=True`) and `coverage_columns` (all three flags). Both are
paired against shipped, which is the same pattern as `columns_words` (#815).
`python -m tools.eye_pairs --render --fixtures becker --arms coverage_edges,coverage_columns,columns_words`.
