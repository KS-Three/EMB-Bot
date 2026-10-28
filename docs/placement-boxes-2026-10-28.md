# Placement boxes: measured vs seeded (2026-10-28)

Every garment x placement pair the Studio offers, with the largest box a design
is auto-fitted to there. Generated from `src/garments.js` (the `PLACEMENTS` and
`GARMENT_PLACEMENTS` tables PR #1159 added, 2026-10-27); the numbers here ARE
the code's numbers, not a copy of them.

- **MEASURED** (3 boxes, on 5 rows): read from a commercial digitizer's stitch
  files by `digitizer/tools/garment_size_census.py` (`PRO_PLACEMENT_MM`). Not up for review here.
- **SEEDED** (23 rows): the inch table or an industry decorator chart,
  not a measurement. **These are the rows Kent should check against real jobs**
  and correct in `PLACEMENTS` when a machine or a customer disagrees.
- **Area cap**: the left chest (and its mirror) also caps the auto-fit at the
  artwork's bounding-box area, so a square logo fits 76.2 mm, not 96.
- **Hoop**: the smallest preset whose field takes the box either way round.
- **Auto-fit W x H**: the box after the largest-hoop cap (8×8 in, 200 mm less
  1 mm a side). A box bigger than the hoop is "hoop-capped": the
  design is still clamped to the full box when typed or dragged, only the AUTO size caps.

Regenerate after any change to `src/garments.js`:

```bash
node tools/placement-table.mjs > docs/placement-boxes-2026-10-28.md
```

`test/placement-table.test.js` checks the row count against the code and the
three measured rows against their census numbers.

| Garment | Placement | Box W x H | Area cap | Source | Hoop | Auto-fit W x H |
|---|---|---|---|---|---|---|
| Hat Front | Hat front, centered (default) `hat_front` | 113.5 x 64.0 mm (4.5 x 2.5 in) | none | MEASURED | 5×7 in | 113.5 x 64.0 mm (4.5 x 2.5 in) |
| Hat Front | Hat front left `hat_front_left` | 57.2 x 50.8 mm (2.3 x 2.0 in) | none | SEEDED | 4×4 in | 57.2 x 50.8 mm (2.3 x 2.0 in) |
| Hat Front | Hat front right `hat_front_right` | 57.2 x 50.8 mm (2.3 x 2.0 in) | none | SEEDED | 4×4 in | 57.2 x 50.8 mm (2.3 x 2.0 in) |
| Hat Front | Hat side left `hat_side_left` | 63.5 x 38.1 mm (2.5 x 1.5 in) | none | SEEDED | 4×4 in | 63.5 x 38.1 mm (2.5 x 1.5 in) |
| Hat Front | Hat side right `hat_side_right` | 63.5 x 38.1 mm (2.5 x 1.5 in) | none | SEEDED | 4×4 in | 63.5 x 38.1 mm (2.5 x 1.5 in) |
| Hat Front | Hat rear `hat_rear` | 88.9 x 38.1 mm (3.5 x 1.5 in) | none | SEEDED | 4×4 in | 88.9 x 38.1 mm (3.5 x 1.5 in) |
| Left Chest | Left chest (default) `left_chest` | 96.0 x 76.5 mm (3.8 x 3.0 in) | 5,800 mm2 | MEASURED | 4×4 in | 96.0 x 76.5 mm (3.8 x 3.0 in) |
| Left Chest | Right chest `right_chest` | 96.0 x 76.5 mm (3.8 x 3.0 in) | 5,800 mm2 | SEEDED (measured left chest, mirrored) | 4×4 in | 96.0 x 76.5 mm (3.8 x 3.0 in) |
| Left Chest | Full back `full_back` | 304.8 x 304.8 mm (12.0 x 12.0 in) | none | SEEDED | 8×8 in | 198.0 x 198.0 mm (7.8 x 7.8 in) (hoop-capped) |
| Left Chest | Upper back `upper_back` | 254.0 x 76.2 mm (10.0 x 3.0 in) | none | SEEDED | 8×8 in | 198.0 x 76.2 mm (7.8 x 3.0 in) (hoop-capped) |
| Left Chest | Sleeve `sleeve` | 76.2 x 76.2 mm (3.0 x 3.0 in) | none | SEEDED | 4×4 in | 76.2 x 76.2 mm (3.0 x 3.0 in) |
| Full Back | Full back (default) `full_back` | 304.8 x 304.8 mm (12.0 x 12.0 in) | none | SEEDED | 8×8 in | 198.0 x 198.0 mm (7.8 x 7.8 in) (hoop-capped) |
| Full Back | Left chest `left_chest` | 96.0 x 76.5 mm (3.8 x 3.0 in) | 5,800 mm2 | MEASURED | 4×4 in | 96.0 x 76.5 mm (3.8 x 3.0 in) |
| Full Back | Right chest `right_chest` | 96.0 x 76.5 mm (3.8 x 3.0 in) | 5,800 mm2 | SEEDED (measured left chest, mirrored) | 4×4 in | 96.0 x 76.5 mm (3.8 x 3.0 in) |
| Full Back | Upper back `upper_back` | 254.0 x 76.2 mm (10.0 x 3.0 in) | none | SEEDED | 8×8 in | 198.0 x 76.2 mm (7.8 x 3.0 in) (hoop-capped) |
| Full Back | Sleeve `sleeve` | 76.2 x 76.2 mm (3.0 x 3.0 in) | none | SEEDED | 4×4 in | 76.2 x 76.2 mm (3.0 x 3.0 in) |
| Beanie | Beanie front (default) `beanie` | 94.5 x 56.0 mm (3.7 x 2.2 in) | none | MEASURED | 4×4 in | 94.5 x 56.0 mm (3.7 x 2.2 in) |
| Beanie | Beanie cuff `beanie_cuff` | 101.6 x 44.5 mm (4.0 x 1.8 in) | none | SEEDED | 5×7 in | 101.6 x 44.5 mm (4.0 x 1.8 in) |
| Sleeve | Sleeve (default) `sleeve` | 76.2 x 76.2 mm (3.0 x 3.0 in) | none | SEEDED | 4×4 in | 76.2 x 76.2 mm (3.0 x 3.0 in) |
| Tote | Tote (default) `tote` | 203.2 x 203.2 mm (8.0 x 8.0 in) | none | SEEDED | 8×8 in | 198.0 x 198.0 mm (7.8 x 7.8 in) (hoop-capped) |
| Jacket Back | Jacket back (default) `jacket_back` | 304.8 x 254.0 mm (12.0 x 10.0 in) | none | SEEDED | 8×8 in | 198.0 x 198.0 mm (7.8 x 7.8 in) (hoop-capped) |
| Jacket Back | Left chest `left_chest` | 96.0 x 76.5 mm (3.8 x 3.0 in) | 5,800 mm2 | MEASURED | 4×4 in | 96.0 x 76.5 mm (3.8 x 3.0 in) |
| Jacket Back | Right chest `right_chest` | 96.0 x 76.5 mm (3.8 x 3.0 in) | 5,800 mm2 | SEEDED (measured left chest, mirrored) | 4×4 in | 96.0 x 76.5 mm (3.8 x 3.0 in) |
| Jacket Back | Upper back `upper_back` | 254.0 x 76.2 mm (10.0 x 3.0 in) | none | SEEDED | 8×8 in | 198.0 x 76.2 mm (7.8 x 3.0 in) (hoop-capped) |
| Jacket Back | Sleeve `sleeve` | 76.2 x 76.2 mm (3.0 x 3.0 in) | none | SEEDED | 4×4 in | 76.2 x 76.2 mm (3.0 x 3.0 in) |
| Patch | Patch (default) `patch` | 88.9 x 88.9 mm (3.5 x 3.5 in) | none | SEEDED | 4×4 in | 88.9 x 88.9 mm (3.5 x 3.5 in) |
| Towel | Towel (default) `towel` | 152.4 x 152.4 mm (6.0 x 6.0 in) | none | SEEDED | 6×10 in | 152.4 x 152.4 mm (6.0 x 6.0 in) |
| Blanket | Blanket (default) `blanket` | 254.0 x 203.2 mm (10.0 x 8.0 in) | none | SEEDED | 8×8 in | 198.0 x 198.0 mm (7.8 x 7.8 in) (hoop-capped) |

