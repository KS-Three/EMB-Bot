# Ink read: ground from a ring round the cluster (`cfg.ink_ground_ring_mm`), 2026-10-14

Built OFF. Measured on Fremont's own artwork (`digitizer/testdata/photo/logo_hotel_fremont.webp`,
already in the repo) and the 17-design corpus of `tools/small_lettering_compare.py --corpus`.
Renders of EMB-Bot's own stitch output, not cloth. Nothing sewn (gate 1).

## Corpus: switch vs switch + ring 0.8 (`corpus/`)

All 17 designs byte-identical (stitch-stream md5): becker, tires, enthusiast, fremont,
bridge, golden_tee, gaulke, drone, screenshot, fremont_hat81, fremont_hat925, and the six
small-print fixtures (synthetic and Fremont tagline at 2.5 / 3 / 4 mm caps).
Fremont Hat 81 mm `1541421f`, 92.5 mm `e0d9323c`: the ring changes nothing there.

## Fremont Hat 65 / 72 mm (`hat_cells/`; OCR glyphs recovered, legibility)

| | main | switch | switch + ring |
|---|---|---|---|
| 65 mm 1895 | 0/4, 0.77 | 1/4, 0.77 | **2/4**, 0.64 (counters 2/3 -> 1/3) |
| 65 mm EST | 1/3, 0.92 | 1/3, 0.91 | 1/3, 0.90 |
| 65 mm THE | **3/3** | 1/3 | 1/3 |
| 65 mm tagline | **10/11** | 5/11 | 5/11 |
| 65 mm stitches / trims | 11,463 / 43 | 11,314 / 39 | 11,275 / 38 |
| 72 mm 1895 | 0/4, 0.53 | **2/4**, 0.79 | same as switch |
| 72 mm tagline | 9/11 | **10/11** | same as switch |
| 72 mm THE | 1/3 | 1/3 | same as switch |

The ring moves only the 65 mm date: it becomes bean letters and reads "1895" where main and
switch sew "1095" (`fremont65_1895_main_switch_ring.jpg`), at the cost of the 8's counters.
THE and the tagline at 65 mm are worse under the switch with or without the ring: a separate
cause.
