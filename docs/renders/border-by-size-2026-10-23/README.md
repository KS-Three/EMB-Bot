# border_by_size: OFF | ON | pro crops (2026-10-23)

Three shapes the flag changes, each at the pro's own width on the hat preset
through the Studio's request (`tools/border_census.py` digitize, OFF and ON).

`<slug>_<id>_off_on_pro.png`: `stitchviz` thread renders at 40 px/mm, 3 mm of
margin round the shape, our region polygon in yellow; the pro tile is his file
registered onto ours (`pairframe.register_pair`). The shapes are dark thread, so
the ring reads as the smoothed, slightly wider edge in ON; `runs_<id>.txt` under
`pro_pair_<slug>_<id>/` lists the border run itself (kind `border`, role
`border`, its extents), and `sheet_crop.png` there is `tools/pro_pair.py`'s own
art | ours | pro crop (each side in its own frame, unregistered).

| shape | min dim | OFF | ON | pro |
|---|---|---|---|---|
| `mfab_hat` `S127f7bff`, the 17 x 6.5 mm bar | 6.4 | fill, bare | fill + 2.1 mm ring (219 st) | fill + 2.4 mm ring |
| `gaulke_roofing_hat` `S4e044819`, the 31 x 16 mm arch | 10.2 | fill, bare | fill + 2.1 mm ring (447 st) | fill + satin ring (census reads it SATIN 2.55: an open ring) |
| `tires_hat_3d` `S396ab4ae`, "ires" script, 93 x 25 mm | 6.4 | fill, bare | fill + 2.1 mm ring (2046 st) | satin lettering (2.26) |

Sewn border width, median zigzag chord in the DST: 2.10 / 2.14 / 2.12 mm.
