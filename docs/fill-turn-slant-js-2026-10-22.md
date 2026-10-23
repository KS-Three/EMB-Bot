# The browser fill's rows turn on a slant (`fillTurnSlant`, built OFF) — 2026-10-22

The JS twin of PR #1036 (`cfg.fill_turn_slant`,
[`docs/fill-turn-slant-2026-10-21.md`](fill-turn-slant-2026-10-21.md)), which
Kent chose on 2026-10-22: port the rule to the browser stitch engine, built OFF.
The Python flag stays OFF too until a sew-out; its doc has what the pro does and
why this is construction rather than a fabric constant (gate 1 does not apply:
the row spacing does not move, and 0.7 came off his files, not off cloth).

## What was there

`src/fill.js` `sewColumns` walked each column as `[lo, hi]` per row and stepped
`sewTo(hi_k, lo_{k+1})`: one row spacing straight across, 0.15 mm at the
builder's row, the needle beside its own hole. Its own comment said so ("A
fill's own turns are one pitch long"). The plain walk did the same between
consecutive row groups. On the test fixture 842 of 842 row turns were under
0.5 mm; on a 30 mm square every turn was 0.15 mm.

## The port

- `src/fill.js` `slantSpans` / `slantTurns` (exported): the Python rule, line for
  line. Of the two boundary points a turn joins, the outer stays on the boundary
  and the inner is pulled in until the turn runs `along` along the row.
  Narrowing or square edge: the next row's entry. Widening edge: this row's exit.
  A column's last near-square turn: the exit, so the last row keeps its corner.
  Preferred row too short to keep `minStitch` after the pull: the other end.
  Left alone: a turn already that far along, and one neither row can afford.
- `tatamiFill({ turnAlong, minStitch })`: `turnAlong` in the fill's own units,
  0 or absent is off and byte-identical. The column walk slants each variant's
  rows; the plain walk slants each sweep (centre-out's two sweeps are two
  columns; the float back between them is not a turn). A row of several spans
  under the plain walk begins on its first span and ends on its last; a turn
  across a hole is already further along than the rule asks, so it is left.
  The plain-or-columns decision is taken on the turns as cut, the same decision
  with the option off.
- `src/digitize.js` `FILL_TURN_ALONG_MM = 0.7` (the wire test will hold it
  against `machine.py` once #1036 lands) and `buildQualityDesign({ fillTurnSlant })`,
  which passes `turnAlong` and `minStitch` to every COVER pass of a shape, never
  to the underlay — the Python reach.

## Before / after

`node tools/fill-turn-slant.mjs`, on the test fixture (three fill shapes, one
with a hole, `ties`/`dedupeHoles` OFF as its pins were taken) and six shapes
built as the Studio builds a `shape` set to fill on left chest. Stitch stream
read at the file's 0.1 mm; row turns read from the cover passes in the fill's
frame. Nothing sewn.

| design | stitches off → on | under 0.5 mm off → on | row turns under 0.5 off → on | turn p50 mm off → on | trims |
|---|---|---|---|---|---|
| test fixture, three fill shapes | 13,451 → 13,379 (−0.5%) | 842 (6.3%) → 0 | 842 of 842 → 0 | 0.15 → 0.72 | 5 = 5 |
| test fixture, `fillColumns` | 13,596 → 13,360 (−1.7%) | 955 (7.0%) → 2 | 955 of 960 → 2 | 0.15 → 0.72 | 4 = 4 |
| 30 mm square | 2,064 → 2,063 | 202 (9.8%) → 0 | 202 of 202 → 0 | 0.15 → 0.72 | 1 = 1 |
| 30 mm disc | 1,682 → 1,646 (−2.1%) | 192 (11.4%) → 0 | 197 of 202 → 0 | 0.17 → 0.72 | 1 = 1 |
| 40 × 8 mm bar, round ends | 732 → 724 (−1.1%) | 53 (7.2%) → 0 | 53 of 57 → 0 | 0.18 → 0.72 | 0 = 0 |
| 5-point star, 40 mm | 1,701 → 1,656 (−2.6%) | 274 (16.1%) → 40 (2.4%) | 260 of 270 → 26 | 0.16 → 0.72 | 1 = 1 |
| 30 mm heart | 1,349 → 1,319 (−2.2%) | 197 (14.6%) → 2 | 197 of 203 → 0 | 0.20 → 0.72 | 1 = 1 |
| 30 × 3 mm strip | 275 → 274 | 23 (8.4%) → 0 | 23 of 23 → 0 | 0.15 → 0.72 | 0 = 0 |

- The turn lands at 0.716 mm (sqrt(0.7² + 0.15²)), the Python lane's number;
  the pro's p50 is 0.71–0.83. Like the Python's, ours is uniform where his varies.
- **What remains under 0.5 mm** is at tips: the star's 26 short turns are rows
  at an arm's point too short to afford the pull, left alone by the rule. The
  stream count (40) is read at the file's 0.1 mm rounding and the two measures
  do not pair one to one.
- Trims never move; the design's size, colours, cuts and runs are the same
  (`test/fill-turn-slant.test.js`).

**Coverage.** At the builder's 0.15 mm row, under a 0.4 mm thread, the bare
corner a pull leaves is a right triangle 0.7 along by 0.15 across whose far
corner is 0.147 mm from the slanted thread — under the thread's 0.2 half-width.
Measured on a box, a disc, 20° and 60° parallelograms and a 2.5 mm strip: the
cover within 0.002 of OFF. (At a 0.4 mm row the far corner is 0.35 mm out and a
box drops 0.75%: thread width decides it, which is why the flip is a sew-out's,
exactly as the Python doc says.)

**Default OFF is byte-identical.** Eight md5 pins in
`test/fill-turn-slant.test.js`: the builder fixture in four arms
(`fillColumns` × `fillStagger`) and four fills asked of the module directly,
all taken on `main` at `03ccab4e` before the option existed.

## Not in this change

- The flip: Kent's, after the OFF/ON fill swatch on the next sew-out card.
- Only `buildQualityDesign` reads it (every Studio lane that builds a shape
  goes through it; the lettering builder sews no fill), as `fillStagger` did
  when it was built.
- The Studio has no control for it; nothing in `app/` reads it.
