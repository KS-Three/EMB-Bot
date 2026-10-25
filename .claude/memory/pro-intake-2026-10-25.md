---
name: pro-intake-2026-10-25
description: tools/pro_intake.py makes a new pro job measurable in one command; registry is gitignored beside the jobs; preview vs art by content AND name; lettering lines confirmed by tesseract
metadata:
  type: project
---

`digitizer/tools/pro_intake.py` (2026-10-25). Kent drops a job into
`scratch_kent/Embroidery Files/<Job>/`; `python -m tools.pro_intake` (from `digitizer/`)
reads only folders not yet registered and prints a census: size, colours, stitches, trims
(DST), smallest lettering cap per colour. After it, `tools.pro_pair --job SLUG`,
`tools.flip_sheet_renders --fixtures SLUG` and `tools.word_legibility --digitize SLUG` take
the job by slug.

**The registry is a gitignored FILE, on purpose** (`scratch_kent/pro_intake/registry.json`).
The committed pairs are a registry IN CODE (`prep_all.DESIGNS`, `blockcensus.FIXTURES`,
`preview_split.MANIFEST`, `border_census.PAIRS`); a script cannot add a new job there
because the repo is public and a folder name is a client's name. The intake reuses those
tables' slugs and committed art for every file they know and mints only the rest. Commit
numbers from it, never names of new clients.

**Traps found building it:**
- Vendor JPGs are TWO-PANEL previews (art + his simulation, or two sims on every Becker),
  not "a render of his stitches". A preview is two panels of equal aspect (0.96-1.00 on
  all 17); real art has no gutter or splits at <= 0.70. But art that repeats a motif
  ("AB  AB") splits the same way, so content AND name must agree; disagreement is
  `preview?` / `art?`, flagged, never used. Which panel is art stays the hand MANIFEST.
- The geometric line finder alone puts graphics in the MINIMUM (a truck wheel 3.0 mm, a
  strip inside GOLF 2.0). Tesseract confirms a line (3+ letters at conf 70+; real lines
  read 73-96). ProSeal's honeycomb read "ODE" at 95, so a convexity gate (median
  solidity <= 0.93) runs first.
- Names drift: "beckers beanie.DST" is "beckers logo hat 2 A a.PES" (matched by stitch
  count and extents); "Machine beanie E.JPG" vs "E (1).DST" needs copy marks stripped.
- Gaulke Plowing's `c golke logo LC.DST` is byte-identical to Gaulke Roofing's: flagged
  `same_as`, count it once in an aggregate.
- `small_text_columns.pieces` draws every block on the whole canvas: 29 s on a 40-colour
  design; `block_pieces` crops per block.

**How to apply:** after Kent drops files, run the one command; a job flagged NO SOURCE ART
needs the art file or a MANIFEST entry before `--job` can digitize it. Related:
[[pro-rules-across-jobs-2026-10-21]], [[word-legibility-instrument-2026-10-24]].
