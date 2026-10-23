# Pull comp by stroke: the grown Fremont small text at 92.5 mm, Hat (2026-10-22)

One sheet per line (EST, 1895, THE, the tagline), four rows each at 40 px/mm,
`tools/small_text_columns.py` band crops in each file's own frame:

1. the pro's Hotel Fremont patch DST;
2. OFF: today's fixed 0.4 mm hat pull, with the #1024/#1025/#1029 flags
   (`small_text_cap_mm` 4.0, `small_text_cap_max_width_scale` 1.05,
   `small_text_cap_min_stroke_mm` 0.85, `small_text_cap_letter_gap_mm` 0.25,
   `small_text_cap_bold_scale` 1.45, `lettering_columns_small_bold` on);
3. ON: `pull_comp_by_stroke` added to row 2;
4. ON with `lettering_columns_small_bold` OFF: by-stroke pull alone.

Rows 2 and 3 are identical: at these letters' 0.85 mm stroke the pro's fit
returns the hat's own 0.4, and `small_bold`'s 0.15 share (0.13 mm) is the
smaller cap, so it wins. Row 4 is the blob: the fit alone is the fixed pull
here. Sewn column widths (median satin cross, mm), from
`small_text_columns` on the written DSTs:

| line | pro | OFF | ON | ON, small_bold off |
|---|---|---|---|---|
| EST | 0.90 | 0.89 | 0.89 | 1.40 |
| 1895 | 0.92 | 0.82 | 0.82 | 1.14 |
| THE | 0.90 | 0.80 | 0.80 | 1.40 |
| EAT STAY PLAY | 0.90 | 0.90 | 0.90 | 1.40 |
| HOTEL FREMONT (0.85 mm drawn, 7.7 mm letters) | 1.43 | 1.40 | 1.40 | 1.40 |

The flag's effect is on strokes wider than ~1 mm (none in this text): a
2.5 mm synthetic column sews 2.76 ON against 3.08 OFF
(`tests/test_pull_comp_by_stroke.py`).
