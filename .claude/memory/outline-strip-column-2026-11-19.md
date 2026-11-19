---
name: outline-strip-column-2026-11-19
description: MFab white top line is keyline_runs hole loops (NOT stage6_satin); pro sews each strip between two holes as ONE full-width column + one outer loop; `outline_strip_column` built OFF, stays OFF (F arm one block; whole word not clearly better, hat +4 trims, Becker moves)
metadata:
  type: project
---

2026-11-19, follows #1694 (MFab top-line faults).

- **Census.** `tools/satin_census.py` (#1701) segments stitch files into satin pieces by throws. On our hat
  with run boundaries dropped it reads 7 of 11 loops exactly. Doc: `docs/mfab-junction-census-2026-11-19.md`.
- **The white is not the satin ladder.** MFab's white M-F-A-B is `stage6_border.keyline_runs` via
  border_from_outline: one 1.88 mm loop per black hole.
- **The pro's construction:** per letter group, a full-width column on every strip between two holes (F arm 3.8,
  B slots 2.83), then ONE outer loop, and no fill.
- **What makes our 15-layer peaks:** ONE loop pivoting at a hole corner (12 consecutive crosses through one
  point), not two bars stacking.
- **`cfg.outline_strip_column` (built OFF, `outline_strip.py`).**
  - How a strip is found: medial axis with both feet on holes, half-width 0.5-1 loop width, at least one loop
    width across, straight (0.8 rect fill), branch-wise when it fails whole.
  - How it sews: loops first, cut 0.2 inside the strips; then the column, grown 0.2 mm.
  - Results: F arm max 15 -> 13 (mean 4.18 -> 3.22) and it reads as one block. J4 15 -> 13; B slots not found;
    hat trims +4. All 5 Becker placements move, invisibly. Whole word not clearly better: OFF, no sweep.
  - Pictures: `docs/renders/outline-strip-column-2026-11-19/`.
- **Traps.**
  - Cutting the loops at gaps (`_split_at_gaps`) gave jumps 8 -> 33.
  - A nearest-first walk over loops and columns together gave +5 trims and lost the F gain.
  - A strip cut from the loops but not sewn leaves bare lines: cut only what is sewn.

Related: [[outline-one-band-2026-11-18]], [[outline-loop-split-shared-2026-11-18]], [[mfab-top-line-2026-11-19]].
