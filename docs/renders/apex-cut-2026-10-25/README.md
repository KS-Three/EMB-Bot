# Apex cut: letters where two strokes meet at an acute tip (2026-10-25)

`cfg.lettering_columns_apex_cut`, built OFF (`digitizer/digitizer_core/outline_cut.py`,
`_apex_cuts`). Each sheet is ONE letter's stitches, OFF | ON | the professional's,
drawn by the Studio's previewer (`stitchviz.render_design`, the renderer
`tools/pro_pair.py` uses) at 40 px/mm, each file in its own frame. Ours are the
letter's runs from the plan; his are his needle-down runs inside the letter's box
(`tools/letter_pieces.py` letters). OFF = main with `lettering_columns_corner_fold`
on (as #1057 flips it); ON = that plus `lettering_columns_apex_cut`.

A whole-design `pro_pair --crop` is unreadable for MFab: the letters are black
satin on a black fill, so the per-letter render is the proof.

| sheet | what to look at |
|---|---|
| `marine76_M_off_on_pro.png` | OFF: two columns meet down the V's middle to its point. ON: the V is one block of level crosses from its crotch to its point, and the right diagonal's top sews with the stem's, as his do. His top-left is the font's sheared slab. |
| `marine80_M_off_on_pro.png` | the same at 79.8 mm (beanie) |
| `marine102_M_off_on_pro.png` | 101.9 mm: the junction rules already cut beside the crotch, so the tip's cross sits there. |
| `mfab105_W_off_on_pro.png` | OFF: each of the three tips fans (the dark knot at the left V's point). ON: each tip is one piece. Seven pieces, his seven. There is no house angle on this W, so the crosses are square to each apex's axis rather than level. |
| `mfab97_W_off_on_pro.png` | the LC's W. ON carries two straight travel runs on top of the satin: the walk leaving a dead-end tip. |
| `mfab105_N_off_on_pro.png` | both acute junctions of AND's N merged |
| `proseal86_A_off_on_pro.png` | ON: the A's top is one column, no mitre seam. A travel run lies on top from the top down to the crotch: the dead-end cost, which the walk (columns.py) has to fix. |

`table.md`: per letter, then per tip, pro / OFF / ON. It comes from the scratch
reader that the PR describes (one rule on both files). In the second table, the
"through" counts are the pieces whose crosses pass within 0.15 mm of points 30 /
60 / 85% of the way from crotch to tip.
