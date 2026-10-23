---
name: flip-sheet-2026-10-23
description: The first OFF | ON | pro flip sheet (2026-10-23) — ten layout flags on Fremont/Becker/MFab, rendered where each flag changes stitches; how the tool finds the crop, what each reader is, and the numbers Kent flips from. Read before pricing or rendering a parked layout flag.
metadata:
  type: project
---

Built 2026-10-23 after Kent's ruling that layout is judged in the preview
([[layout-judged-in-preview-2026-10-22]]). `digitizer/tools/flip_sheet_renders.py`
(`run` then `report`; a flag not on main runs with `--engine <checkout>` and
is diffed against THAT engine's own OFF) writes `docs/flip-sheet-2026-10-23.md`
and `docs/renders/flip-sheet-2026-10-23/index.html`. Note the name: the older
`tools/flip_sheet.py` is the corpus-grade pricing sheet from September and was
left alone.

**How the crop is found.** Needle points of OFF and ON on a 0.05 mm grid as a
MULTISET: a lock walks over the run's own stations, so `tie_in_off` removed 64
stitches on Becker and a plain set diff saw 12 points. An 18 x 11 mm window
slides over the differing points; the pro's crop is the same window as a
fraction of his extents (no registration, as `pro_pair`). Underlay flags get an
x-ray tile: the design drawn with its sewing order reversed per block, so
first-sewn thread lands on top. The renderer is untouched.

**Readers, one per number, all off the DST** (the pro's DST, never his PES:
trims differ 21 vs 52 on Fremont, 11 vs 40 on Becker; ours read 51 from the
file where the plan says 55). `pro_fill_underlay` verdicts, `trim_classes`
under_later, `small_text_columns` pieces, `pro_satin_underlay` (loaded from
PR #1044's branch when this checkout lacks it), a lock = first three stitches
after a cut/colour/jump all <= 1.0 mm with a reversal.

**What the sheet showed (OFF -> ON, pro):**
- `fill_turn_slant`: sub-0.5 mm stitches Fremont 2161 -> 989 (pro 295), MFab
  717 -> 625 (513), Becker 400 -> 376 (197).
- `cut_every_jump`: uncut jumps Fremont 172 -> 1 (pro 1) but TRIMS 51 -> 201
  against the pro's 21; MFab 33 -> 1, trims 65 -> 96 (pro 19). The pro cuts
  every jump and has few jumps; we have many. The jump COUNT is the lever.
- `tie_in_off`: run starts that lock Fremont 82 -> 38 (pro 3), Becker 16 -> 0,
  MFab 75 -> 23 (pro 0). Tie-offs stay, so the 38/23 are those.
- `satin_underlay_short_columns`: short columns bare Fremont 9.0% -> 0 (pro
  1.6), MFab 12.7 -> 4.9 (pro 0), Becker 10 points moved.
- `sew_enclosed_white`: Fremont byte-identical; Becker 5,928 -> 8,512 st (pro
  8,694); MFab 13,721 -> 25,512 st and 65 -> 108 trims (pro 17,568 / 19).
- `trim_bury_under_later`: Fremont trims 51 -> 37 (under-later hops 12 -> 0),
  MFab 65 -> 61; Becker byte-identical.
- `compact_solids_satin`: Fremont only (110 points); `small_solids_satin`:
  Fremont 1,527 points, MFab 190; neither touches Becker.
- `small_text_set`: Fremont only; small-letter height 2.15 -> 4.40 mm (pro
  4.25). Black thread renders as a silhouette in the previewer: stitches on
  THE are not visible in the tile, only its shape.
- `fill_underlay_cross`: the reader already calls Fremont's one fill CROSS
  OFF (the hat preset's double lattice reads as a crossing pass); the x-ray
  shows the lattice change. MFab reads RUNONLY both ways (pro CROSS 2).

PRs #1036 and #1035 were RED when rendered (one stale OFF md5 pin in
`tests/test_cut_every_jump.py`); their rows say so. Fremont ~270 s a cell,
Becker ~40, MFab ~95, three in parallel; the cache under
`digitizer/debug_out/flip_sheet/` is resumable.
