# Under-fill outer rim: the fill's outer edge as one closed satin loop (2026-10-25)

`cfg.silhouette_underfill_rim`, built OFF (`digitizer/digitizer_core/stage6_border.py`,
`underfill_rim_runs` / `underfill_rim_after`; one call in `stage7_sequence` after
`stitch_one`). Every sheet draws the needle paths in thread colour on grey, at
25 px/mm: OFF | ON | the professional's. OFF is arm d2 (`silhouette_underfill`,
`sew_enclosed_white`, `enclosed_white_keyline`); ON adds the rim.

Each window sits at the same fraction of each file's own box. The files are the
same design at the same width, so the windows land on the same stretch of edge
to within a millimetre or two, though not exactly.

| sheet | what to look at |
|---|---|
| `mfab_hat_whole_off_on_pro.png` | The whole design at 4 px/mm. OFF ends the black fill in a bean edge cap; ON and the pro both close the outer edge with a black satin rim. |
| `mfab_hat_edge_off_on_pro.png` | Five windows: the top bump over M, the top over A, the bay under AND, the G tail, and the end past LLC. OFF: the fill's rows end at the edge under the bean cap. ON: a satin rim 1.75 mm wide on the fill's sewn edge, crosses square to it, the corners pivoted (#1093). The pro's rim is 1.94 mm. |
| `fremont_hat_edge_off_on_pro.png` | Hotel Fremont hat: the top point, the left banner end, and the lower left. ON rims the white ground's edge in white, as his file does; his black frame sits inside it. |
