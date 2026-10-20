### Per fixture: ARTWORK_UNCOVERED mm2 / bare-fabric mm2 / thread over bare fabric mm (travel links, `_thread_bare_mm`) / stitches

| fixture | off | on_cov | on_cov_gnd |
|---|---|---|---|
| logo_alpha.png | 0.0 / 0.25 / 0.0 / 5,854 | 0.0 / 0.25 / 0.0 / 5,854 | 0.0 / 0.25 / 0.0 / 5,854 |
| logo_whitebg.png | 0.0 / 0.12 / 0.0 / 5,824 | 0.0 / 0.12 / 0.0 / 5,824 | 0.0 / 0.12 / 0.0 / 5,824 |
| photo/drone_render.png | 0.0 / 2.94 / 0.0 / 19,015 | 0.0 / 4.44 / 0.0 / 18,382 | 0.0 / 4.44 / 0.0 / 18,331 |
| photo/enthusiast_logo.png | 0.0 / 2.62 / 0.0 / 2,292 | 0.0 / 3.88 / 0.0 / 2,097 | 0.0 / 3.88 / 0.0 / 2,097 |
| photo/logo_bridge_bar.jpg | 0.0 / 1.44 / 0.0 / 17,614 | 0.0 / 1.44 / 0.0 / 17,614 | 0.0 / 1.44 / 0.0 / 17,614 |
| photo/logo_gaulke_roofing.png | 0.0 / 3.19 / 0.0 / 4,892 | 0.0 / 7.06 / 0.0 / 4,636 | 0.0 / 7.06 / 0.0 / 4,636 |
| photo/logo_golden_tee.jpg | 0.0 / 4.06 / 0.0 / 8,345 | 0.0 / 6.12 / 0.0 / 6,884 | 0.0 / 6.12 / 0.0 / 6,884 |
| photo/logo_hotel_fremont.webp | 0.0 / 0.12 / 0.0 / 14,290 | 0.0 / 0.12 / 0.0 / 13,410 | 0.0 / 0.12 / 0.0 / 13,410 |
| photo/screenshot_phone_ui_golke.jpg | 0.0 / 5.62 / 0.0 / 8,254 | 0.0 / 6.94 / 0.0 / 7,907 | 0.0 / 6.94 / 0.0 / 7,907 |
| photo/summit_badge.png | 0.0 / 1.5 / 0.0 / 25,907 | 0.0 / 1.81 / 0.0 / 25,863 | 0.0 / 1.81 / 0.0 / 25,863 |

### `hairline_over_ground`: `on_cov` -> `on_cov_gnd` (drop + coverage guard on in both)
(bare / ARTWORK_UNCOVERED mm2, stitches, trims; ground = new bare cells outside the shape within 0.6 mm of a captured shape, of which rim = no stitched polygon under the cell; shapes = those carrying >= 0.1 mm2 of ground-gap cells in `on_cov`)

| fixture | bare | uncovered | stitches | trims | ground (rim) | ground-gap shapes |
|---|---|---|---|---|---|---|
| logo_alpha.png | 0.25 -> 0.25 | 0.0 -> 0.0 | 5,854 -> 5,854 | 15 -> 15 | 0 (0) -> 0 (0) | - |
| logo_whitebg.png | 0.12 -> 0.12 | 0.0 -> 0.0 | 5,824 -> 5,824 | 15 -> 15 | 0 (0) -> 0 (0) | - |
| photo/drone_render.png | 4.44 -> 4.44 | 0.0 -> 0.0 | 18,382 -> 18,331 | 147 -> 143 | 0.74 (0.68) -> 0.74 (0.68) | S181d280a 0.44, Sdad8ab8f 0.12, Se06679a1 0.12 |
| photo/enthusiast_logo.png | 3.88 -> 3.88 | 0.0 -> 0.0 | 2,097 -> 2,097 | 7 -> 7 | 0.3 (0.3) -> 0.3 (0.3) | Sacc60621 0.12, S0a7a203e 0.12 |
| photo/logo_bridge_bar.jpg | 1.44 -> 1.44 | 0.0 -> 0.0 | 17,614 -> 17,614 | 89 -> 89 | 0.0 (0.0) -> 0.0 (0.0) | - |
| photo/logo_gaulke_roofing.png | 7.06 -> 7.06 | 0.0 -> 0.0 | 4,636 -> 4,636 | 23 -> 23 | 3.81 (3.81) -> 3.81 (3.81) | Se9512992 3.81 |
| photo/logo_golden_tee.jpg | 6.12 -> 6.12 | 0.0 -> 0.0 | 6,884 -> 6,884 | 53 -> 53 | 0.81 (0.75) -> 0.81 (0.75) | S0bcd1e39 0.75 |
| photo/logo_hotel_fremont.webp | 0.12 -> 0.12 | 0.0 -> 0.0 | 13,410 -> 13,410 | 41 -> 41 | 0.0 (0.0) -> 0.0 (0.0) | - |
| photo/screenshot_phone_ui_golke.jpg | 6.94 -> 6.94 | 0.0 -> 0.0 | 7,907 -> 7,907 | 57 -> 57 | 0.44 (0.44) -> 0.44 (0.44) | S152a196e 0.19, Se693adc4 0.19 |
| photo/summit_badge.png | 1.81 -> 1.81 | 0.0 -> 0.0 | 25,863 -> 25,863 | 52 -> 52 | 0.31 (0.31) -> 0.31 (0.31) | S99d74eba 0.19, Sa37babb3 0.12 |

### Shapes that lose coverage under `on_nodrop`: new bare mm2 against OFF, by cause
(edge = run narrower than the stroke; erased = strand dropped; ground = gap in the colour beneath; est = `strand_bare_mm2`, the plan-time prediction)

| fixture | shape | ink mm2 | width mm (read / source) | strands / dropped | est mm2 | edge | erased | ground | new bare | in `on` | in `on_cov` |
|---|---|---|---|---|---|---|---|---|---|---|---|
