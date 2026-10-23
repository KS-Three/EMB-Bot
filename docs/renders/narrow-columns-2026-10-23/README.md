# Narrow columns: Fremont's ~4 mm letters built like the pro's (2026-10-23)

One sheet per word: **before | after | pro**. Before and after are the
Column lane (`lettering_columns_shape`) on the 21 grown letters stage 7
handed it at 92.5 mm Hat with the small-text flags ON (`small_text_cap_mm`
4.0, `small_text_cap_letter_gap_mm` 0.25, `small_text_cap_bold_scale` 1.45,
`small_text_cap_min_stroke_mm` 0.85, `lettering_columns_small_bold`);
satin crosses dark, travel red, the artwork outline grey, 40 px/mm. The
pro panel is the same word cut from his Hotel Fremont Patch DST
(`Embroidery Files.zip`, pystitch), needle-down stitches drawn 0.4 mm wide.

Made by `python -m tools.column_harness --out . --before before_runs.json
--save-runs after_runs.json`; `before_runs.json` is the construction of the
engine before this change (main at d02405bf), `after_runs.json` this one.
`table.md` / `letters.json` carry the per-letter numbers.

What changed (all under `lettering_columns_small_bold`; OFF byte-identical):

- a serif block is sewn as part of its stroke's column, the stem's zigzag
  widening through it (`outline_cut._absorb_serifs`);
- a junction corner's edge is read as a chord over half a stroke, so the
  grown outline's corner chamfers no longer hide a T's through cut
  (`_chord_dir`);
- a mitre face must span most of the column: a chamfer no longer fans the
  last crosses at every corner (`SMALL_BOLD_MITRE_SPAN`).

Totals over the 21 letters: columns 74 -> 55, crossed zigzag legs 13 -> 7,
trims 3 -> 1, travel 83.8 -> 59.2 mm, unsewn pieces 0 -> 0, station fans
past 45 deg 0 -> 0 (the 8's and the 9's ring and the S's curl pivot as the
pro's do). Crosses over 1.5 stroke widths 15 -> 55: the widened serif
crosses, which is the pro's foot.
