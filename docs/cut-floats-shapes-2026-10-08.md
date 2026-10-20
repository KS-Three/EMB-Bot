# `cutFloats` on the basic-shape lane, after `fillColumns` (2026-10-08)

**Flipped ON for the basic-shape (preset) lane**, in
`app/src/lib/generate.js`'s `shape` branch, beside `fillColumns` (#673), as
PR #672 does for the manual lane. The engine default stays off and the image
lane passes nothing. "Waiting on Kent" 28 had this sequenced after
`fillColumns`. **Not sewn.**

What the flag does is in [`dst-float-cuts-2026-10-04.md`](dst-float-cuts-2026-10-04.md):
a float the DST writer lays as three or more jump records is a cut on a DST
machine, so the stream gets a `trim` there. No stitch moves.

## Per family

`node tools/cut-floats-shapes-sheet.mjs` (37 s). Every preset of
`file-cut-census.mjs --set shapes` — circle, heart, 9 rectangles (heights 10,
30, 50 × corner radii 0, 3, 8), 30 stars (3–12 points × five inner ratios) —
at 12, 20, 30, 40, 50, 65 and 80 mm under all ten garments, built the way the
shape branch calls the engine (`shapePresetPoints` → `shapesToRegions`, the
garment's fabric, `darkOnTop: false`, underlay, `fillColumns: true`). The
measures are #672's `tools/cut-floats-sheet.mjs`, unchanged.

| family | designs | stitches | trims off → on | DST cuts nobody asked for off → on (designs) | floats off → on | floats > 4 mm leaving the outline off → on |
|---|---|---|---|---|---|---|
| circle | 70 | 261,060 | 60 → 116 | 56 (37) → 0 (0) | 283 → 227 | 0 → 0 |
| heart | 70 | 202,284 | 0 → 25 | 25 (22) → 0 (0) | 125 → 100 | 0 → 0 |
| rectangle | 630 | 1,705,642 | 360 → 978 | 618 (364) → 0 (0) | 1,515 → 897 | 0 → 0 |
| 3-point star | 350 | 799,761 | 202 → 288 | 86 (64) → 0 (0) | 1,173 → 1,087 | 15 → 15 |
| 4-point star | 350 | 676,481 | 136 → 336 | 200 (94) → 0 (0) | 1,509 → 1,309 | 192 → 157 |
| 5-point star | 350 | 813,160 | 67 → 196 | 129 (108) → 0 (0) | 835 → 706 | 32 → 32 |
| 6-point star | 350 | 946,703 | 60 → 467 | 407 (139) → 0 (0) | 1,989 → 1,582 | 569 → 425 |
| 8-point star | 350 | 819,889 | 74 → 453 | 379 (121) → 0 (0) | 2,216 → 1,837 | 949 → 804 |
| 12-point star | 350 | 984,792 | 2 → 901 | 899 (117) → 0 (0) | 4,968 → 4,069 | 2,149 → 1,596 |
| **all** | 2,870 | 7,209,772 | 961 → 3,760 | 2,799 (1,066) → 0 (0) | 14,613 → 11,814 | 3,906 → 3,029 |

- **No stitch moved** in any of the 2,870 designs: the needle points are the
  same and in the same order.
- **No new thread.** Not one sewn or floated segment in the "on" stream is
  missing from the "off" one, and no design has more floats leaving its
  outline. A cut only takes thread away.
- **Circles, hearts and rectangles: 699 → 0.** Their unasked cuts are the
  move from the underlay to the fill across the face, which `fillColumns`
  cannot route round because there is no notch.
- **12-point stars carry a third of the new trims** (2 → 901, +2.6 a
  design): a satin arm's run ends and floats to another arm (defect 57).
  Those floats were already DST cuts; they are now `trim`s the counts and
  `ties` can see.
- The floats still leaving the outline (3,029) are left over from
  `fillColumns` on star tips, and are there with this flag off too.

## The file census

`node tools/file-cut-census.mjs --set shapes --on cutFloats` (772 s, four
jobs): each design written by all three writers and read back from its
format. Preset rows, `fillColumns` on:

| preset lane, 2,870 designs | `cutFloats` off | on |
|---|---|---|
| cuts nobody asked for (DST) | 2,799, in 1,066 designs | **0** |
| `trim` records in the stream | 961 | 3,760 |
| cuts in the DST, as its reader finds them | 4,850 | 4,850 |

Whole shapes set (presets and manual), `fillColumns` on: stitches 61,421,054
and needle holes 61,435,998 in each of DST, EXP and PES, both ways; with
`ties`, thread ends at a cut nobody asked for 14,126 → 0.

## The trade-off

- **DST: nothing changes on the machine.** The same 4,850 cuts happen; they
  are now in the stream, so the trim count, the run time and `ties` see them.
- **EXP and PES gain these cuts.** They have a cut of their own, so a float
  that was a float there becomes a cut — 2,799 more on the presets — and
  while `ties` (23) is off, each is an unlocked thread end. Same trade #672
  accepted for the manual lane.
