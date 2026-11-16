# Rule 7 measured: stack or knock out? (2026-11-13)

Research only. No repo file changed, no git write, no flag. Code on local main 19013abe (origin/main 35b789b1 differs by docs/memory/launch.json only, no code).
Scripts: reader.py (the reader), synth.py (synthetic check), run_ours.ps1 (pipeline runs), run_all.py, summarize.py, peek*.py. Our DSTs: ours/<job>/ours.dst from `python -m tools.pro_pair --job <slug>` (registry in scratch_kent/pro_intake), each 33-82 s.

## Answer in one paragraph

Kent's professional STACKS every piece up to about 5 mm wide (footprint, i.e. ~4.6 mm of penetration width): all 292 non-beanie pro pieces under 5.2 mm wide that lie inside an earlier ground read under-cover >= 0.92 (289 of them >= 0.99). From about 5.3 mm up he usually knocks out with a deep underlap: 8 of 12 non-beanie pieces 5.2 mm or wider (Plowing LC, Plowing JB, Fremont patch + hat's Wisconsin, MFab hat + LC panels; 40-1,549 mm2) have ground thread to 1 mm in, falling to 0.54-0.89 at 1-2 mm and 0.00-0.22 beyond 2 mm (Fremont hat 0.63); 4 stay solid (Becker large 5.4 mm and Machine 5.5 mm, each the same design in two files). On the same seven jobs ours ALSO stacks narrow pieces (126 pieces, 120 >= 0.99, lowest 0.78 on two MFab letters), and stacks wide ones too (Drone 6.7-8.2 mm, Machine 5.9, Fremont 5.0); the only knock-out is MFab's 9.2 mm panel, underlap ~1 mm (0.96 / 0.88 / 0.22 / 0.01 by depth). The code reading behind the study's rule 7 ("a hole under every later shape") is not what these files sew. A solid ground under the one knocked-out piece costs 1,570 stitches (420 mm2 x 3.74 st/mm2), 7.6% of that job; the other six jobs cost 0. Bare fabric in a 0.5 mm band each side of every piece on a ground: 0.00 median on both sides, every job, except the pro's Golden Tee (0.05).

## Method as run (and what I changed from the brief)

- Each side's DST (pystitch), own frame, 20 px/mm; needle-down STITCH->STITCH segments <= 6 mm drawn 0.4 mm wide; split into colour blocks at COLOR_CHANGE/STOP.
- Grounds: each block opened by 0.55 mm, connected components >= 25 mm2. A component is a GROUND when >= 50% of its segment length (segments >= 1 mm) lies within 15 deg of its dominant axis AND continues straight into a neighbouring segment (cos > 0.9): tatami rows run on, satin reverses every stitch. (Changed: per component, not per block, because one colour block often holds a fill and a satin border.)
- Pieces: later blocks opened by 0.55 mm, components >= 0.5 mm2, kept when >= 90% of the footprint lies inside an earlier ground's filled outer contour.
- Under-cover: CHANGED to "any earlier thread" (union of every earlier block's raster), not the ground's thread only. Reason, seen in the pro MFab render: the green letters sit on a red fill that sits in a hole in the grey field; the red component (fill + satin keyline joined) does not pass the ground test, so ground-only under-cover read the letters as knocked out (0.2-0.3) when they are stacked on the red. Ground-only under-cover is still in results.json (`under_cover`, `core_under_cover`).
- ADDED core under-cover (piece eroded 0.5 mm) and cover by depth (0-0.5, 0.5-1, 1-2, >2 mm from the piece edge). Reason, from the synthetic check: with 0.4 mm thread, a knocked-out 1 mm bar with a 0.25 mm tongue still reads footprint under-cover 0.92; its core reads 0.41. Knocked out = core under-cover (any earlier thread) < 0.5; footprint value when the piece has no core (under ~1.2 mm wide).
- Width = 2 x max distance transform of the opened footprint, so it includes the 0.4 mm thread.
- Cost of solid (ours): for each knocked-out piece, the hole = innermost containing ground's filled outline minus all earlier thread, components touching the piece, each pixel priced once, x that ground's own stitches/mm2 (all its penetrations / its thread area, underlay included).
- Band bare: 0.5 mm each side of the piece outline; fraction of pixels no thread of any colour covers. Also `band_bare_outside` (outer half only).
- Existing instruments: `tools/pro_parity/bare.py` measures bare inside pipeline region polygons (same 0.4 mm thread convention, 10 px/mm), and `flip_sheet_renders.bare_by_band` / `hairline_travel` measure bare TRAVEL thread. Neither reads bare fabric at a seam from a DST, so neither was reused; mine uses the same thread-width convention as bare.py.

## Synthetic check

20 x 20 mm tatami (0.2 mm rows, 3.5 mm stitches), then a second colour: four satin bars (1x4, 2x10, 4x8, 5x8 mm). Three cases: solid ground; hole with a 0.25 mm tongue; hole with a 0.3 mm GAP. All three read the square as one ground (tatami 1.00 / 0.86 / 0.80).
| case | piece area | footprint width | under-cover | core under-cover | core pen. ratio | band bare | knocked out | hole mm2 (case) | solid cost st (case) |
|---|---|---|---|---|---|---|---|---|---|
| solid | 5.218 mm2 | 1.239 | 1.0 | 1.0 | 4.246 | 0.0 | False | 0.0 | 0 |
| solid | 22.418 mm2 | 2.139 | 1.0 | 1.0 | 0.788 | 0.0 | False | 0.0 | 0 |
| solid | 41.732 mm2 | 5.139 | 1.0 | 1.0 | 0.87 | 0.0 | False | 0.0 | 0 |
| solid | 33.672 mm2 | 4.139 | 1.0 | 1.0 | 0.563 | 0.0 | False | 0.0 | 0 |
| knockout_tongue0.25 | 5.218 mm2 | 1.239 | 0.9238 | 0.4055 | 0.0 | 0.0 | True | 62.54 | 166 |
| knockout_tongue0.25 | 22.418 mm2 | 2.139 | 0.5406 | 0.0297 | 0.0 | 0.0 | True | 62.54 | 166 |
| knockout_tongue0.25 | 41.732 mm2 | 5.139 | 0.2932 | 0.0118 | 0.0 | 0.0 | True | 62.54 | 166 |
| knockout_tongue0.25 | 33.672 mm2 | 4.139 | 0.3363 | 0.0128 | 0.0 | 0.0 | True | 62.54 | 166 |
| knockout_gap0.3 | 5.218 mm2 | 1.239 | 0.0532 | 0.0 | 0.0 | 0.0353 | True | 107.28 | 325 |
| knockout_gap0.3 | 22.418 mm2 | 2.139 | 0.0055 | 0.0 | 0.0 | 0.0159 | True | 107.28 | 325 |
| knockout_gap0.3 | 41.732 mm2 | 5.139 | 0.0027 | 0.0 | 0.0 | 0.0655 | True | 107.28 | 325 |
| knockout_gap0.3 | 33.672 mm2 | 4.139 | 0.0031 | 0.0 | 0.0 | 0.0584 | True | 107.28 | 325 |
Read: solid reads 1.00 everywhere; knock-out with tongue reads core 0.01-0.41 (the 1 mm bar is the closest call); a 0.3 mm gap reads 0.00. Band bare is BLIND to narrow gaps: a real 0.3 mm gap reads only 0.02-0.07, because the 0.4 mm drawn thread on both sides covers most of it. So "0.00 band bare" means no gap wider than roughly 0.4 mm, not no gap at all. The penetration ratio (`core_pen_ratio`) is noisy on small cores (4.2 on the solid 1 mm bar) and is reported only, not used.
## Tables

## Table 1. Pro, every DST (under-cover, median [IQR], by piece width)

Width = 2 x max distance transform of the piece's footprint, thread drawn 0.4 mm wide (so it includes ~0.4 mm of thread). Cells: n pieces: footprint under-cover. Second row of each job: core under-cover (piece eroded 0.5 mm); pieces under ~1.2 mm wide have no core.

| job | beanie | blocks | grounds | pieces on a ground | <2 mm | 2-5 mm | >5 mm | core <2 | core 2-5 | core >5 | core pen. ratio median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c_gaulke_plowing_beanie | yes | 8 | 6 | 30 | n22: 1.00 [1.00-1.00] | n7: 1.00 [1.00-1.00] | n1: 0.98 [0.98-0.98] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.98 [0.98-0.98] | 0.73 [0.71-0.89] |
| gaulke_plowing_hat |  | 7 | 6 | 29 | n22: 1.00 [1.00-1.00] | n7: 1.00 [1.00-1.00] | n0: - | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | - | 0.70 [0.62-0.94] |
| gaulke_plowing_lc |  | 7 | 6 | 34 | n28: 1.00 [1.00-1.00] | n5: 1.00 [1.00-1.00] | n1: 0.82 [0.82-0.82] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.72 [0.72-0.72] | 0.72 [0.48-0.85] |
| c_gaulke_plowing_lc |  | 1 | 0 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| gaulke_jb |  | 21 | 11 | 13 | n10: 1.00 [1.00-1.00] | n2: 1.00 [1.00-1.00] | n1: 0.81 [0.81-0.81] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.73 [0.73-0.73] | 0.68 [0.49-0.72] |
| golf_hat |  | 7 | 2 | 4 | n2: 0.96 [0.96-0.96] | n2: 0.95 [0.94-0.96] | n0: - | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | - | 0.99 [0.93-1.06] |
| becker_hat_large |  | 5 | 2 | 3 | n0: - | n2: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | - | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.90 [0.84-0.90] |
| becker_lc_large |  | 4 | 2 | 3 | n0: - | n2: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | - | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.84 [0.80-0.86] |
| becker_chest_small |  | 4 | 2 | 3 | n0: - | n3: 1.00 [1.00-1.00] | n0: - | - | 1.00 [1.00-1.00] | - | 0.71 [0.70-0.77] |
| becker_hat_small |  | 5 | 2 | 3 | n0: - | n3: 1.00 [1.00-1.00] | n0: - | - | 1.00 [1.00-1.00] | - | 0.71 [0.70-0.77] |
| becker_marine_hat |  | 5 | 2 | 3 | n0: - | n2: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | - | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.90 [0.84-0.90] |
| gaulke_roofing_beanie | yes | 2 | 0 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| gaulke_roofing_hat |  | 1 | 0 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| gaulke_roofing_lc |  | 1 | 0 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| gaulke_roofing_c_golke_logo_hat_1 |  | 3 | 0 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| hotel_fremont_hat |  | 11 | 2 | 38 | n19: 1.00 [1.00-1.00] | n18: 1.00 [1.00-1.00] | n1: 0.88 [0.88-0.88] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.83 [0.83-0.83] | 0.93 [0.79-1.10] |
| hotel_fremont_patch |  | 9 | 2 | 32 | n15: 1.00 [1.00-1.00] | n16: 1.00 [1.00-1.00] | n1: 0.73 [0.73-0.73] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.61 [0.61-0.61] | 0.95 [0.83-1.01] |
| mfab_hat |  | 5 | 2 | 20 | n4: 1.00 [1.00-1.00] | n14: 1.00 [1.00-1.00] | n2: 0.66 [0.62-0.71] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.58 [0.53-0.63] | 0.06 [0.00-0.56] |
| mfab_lc |  | 5 | 2 | 19 | n7: 1.00 [1.00-1.00] | n10: 1.00 [1.00-1.00] | n2: 0.68 [0.64-0.73] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.59 [0.54-0.64] | 0.08 [0.02-0.46] |
| precision_drone |  | 23 | 10 | 48 | n46: 1.00 [1.00-1.00] | n2: 1.00 [1.00-1.00] | n0: - | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | - | 0.45 [0.00-0.61] |
| proseal_beanie | yes | 6 | 1 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| proseal_hat |  | 5 | 1 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| tires_hat_3d |  | 2 | 0 | 0 | n0: - | n0: - | n0: - | - | - | - | - |
| machine_beanie | yes | 3 | 2 | 24 | n18: 1.00 [1.00-1.00] | n5: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.91 [0.79-1.01] |
| machine_hat |  | 2 | 1 | 26 | n16: 1.00 [1.00-1.00] | n9: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.91 [0.70-0.97] |
| machine_lc |  | 2 | 1 | 26 | n16: 1.00 [1.00-1.00] | n9: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.91 [0.70-0.97] |
| becker_beanie | yes | 6 | 2 | 3 | n0: - | n3: 1.00 [1.00-1.00] | n0: - | - | 1.00 [1.00-1.00] | - | 0.70 [0.68-0.76] |
| toat_beanie | yes | 3 | 2 | 24 | n18: 1.00 [1.00-1.00] | n5: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | 0.91 [0.79-1.01] |

## Table 2. Paired jobs, pro vs ours, same reader

| job | side | stitches | grounds | pieces on a ground | <2 mm | 2-5 mm | >5 mm | knocked out (core uc < 0.5) | band bare 0.5 mm (median [IQR]) | outside-band bare |
|---|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | pro | 12356 | 2 | 3 | n0: - | n2: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| becker_hat_large | ours | 16262 | 6 | 3 | n0: - | n3: 1.00 [1.00-1.00] | n0: - | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| hotel_fremont_patch | pro | 15458 | 2 | 32 | n15: 1.00 [1.00-1.00] | n16: 1.00 [1.00-1.00] | n1: 0.73 [0.73-0.73] | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| hotel_fremont_patch | ours | 22376 | 5 | 40 | n38: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| golf_hat | pro | 5973 | 2 | 4 | n2: 0.96 [0.96-0.96] | n2: 0.95 [0.94-0.96] | n0: - | 0 | 0.05 [0.04-0.07] | 0.10 [0.07-0.13] |
| golf_hat | ours | 13515 | 2 | 3 | n3: 0.99 [0.98-0.99] | n0: - | n0: - | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| mfab_hat | pro | 17568 | 2 | 20 | n4: 1.00 [1.00-1.00] | n14: 1.00 [1.00-1.00] | n2: 0.66 [0.62-0.71] | 1 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| mfab_hat | ours | 20557 | 1 | 11 | n0: - | n10: 0.99 [0.98-1.00] | n1: 0.69 [0.69-0.69] | 1 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| machine_hat | pro | 13886 | 1 | 26 | n16: 1.00 [1.00-1.00] | n9: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| machine_hat | ours | 18917 | 1 | 25 | n15: 1.00 [1.00-1.00] | n9: 1.00 [1.00-1.00] | n1: 1.00 [1.00-1.00] | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| precision_drone | pro | 14552 | 10 | 48 | n46: 1.00 [1.00-1.00] | n2: 1.00 [1.00-1.00] | n0: - | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| precision_drone | ours | 14760 | 5 | 49 | n37: 1.00 [1.00-1.00] | n9: 1.00 [1.00-1.00] | n3: 1.00 [1.00-1.00] | 0 | 0.00 [0.00-0.00] | 0.00 [0.00-0.00] |
| gaulke_roofing_hat | pro | 6138 | 0 | 0 | n0: - | n0: - | n0: - | 0 | - | - |
| gaulke_roofing_hat | ours | 9506 | 0 | 0 | n0: - | n0: - | n0: - | 0 | - | - |

## Table 3. Ours: cost of a solid ground

| job | stitches | knocked-out pieces | hole area mm2 | stitches a solid ground adds | % of job |
|---|---|---|---|---|---|
| becker_hat_large | 16262 | 0 | 0.0 | 0 | 0.0 |
| hotel_fremont_patch | 22376 | 0 | 0.0 | 0 | 0.0 |
| golf_hat | 13515 | 0 | 0.0 | 0 | 0.0 |
| mfab_hat | 20557 | 1 | 419.98 | 1570 | 7.64 |
| machine_hat | 18917 | 0 | 0.0 | 0 | 0.0 |
| precision_drone | 14760 | 0 | 0.0 | 0 | 0.0 |
| gaulke_roofing_hat | 9506 | 0 | 0.0 | 0 | 0.0 |


## Wide pieces (>= 4 mm), cover by depth from the piece edge

```ours mfab_hat b 1 A 28.208 w 4.038 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': None}
ours machine_hat b 1 A 527.888 w 4.179 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours becker_hat_large b 1 A 30.682 w 4.258 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours mfab_hat b 2 A 115.535 w 4.379 core_any 0.9702 {'0-0.5': 0.996, '0.5-1': 0.964, '1-2': 1.0, '>2': 1.0}
ours becker_hat_large b 1 A 25.6 w 4.4 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours precision_drone b 6 A 88.815 w 4.439 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours becker_hat_large b 1 A 43.568 w 4.736 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours hotel_fremont_patch b 1 A 34.728 w 5.013 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours machine_hat b 1 A 379.135 w 5.918 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours precision_drone b 1 A 190.535 w 6.7 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours precision_drone b 2 A 148.182 w 7.51 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours precision_drone b 3 A 123.55 w 8.2 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
ours mfab_hat b 1 A 1312.812 w 9.22 core_any 0.4971 {'0-0.5': 0.958, '0.5-1': 0.875, '1-2': 0.222, '>2': 0.006}
pro mfab_lc b 1 A 26.035 w 4.0 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': None}
pro becker_lc_large b 1 A 21.428 w 4.079 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro machine_hat b 1 A 501.455 w 4.138 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro machine_lc b 1 A 501.822 w 4.138 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro c_gaulke_plowing_beanie (beanie) b 3 A 43.772 w 4.157 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro gaulke_plowing_hat b 2 A 43.772 w 4.157 core_any 1.0 {'0-0.5': 0.999, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_chest_small b 1 A 25.62 w 4.238 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_hat_small b 2 A 25.62 w 4.238 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_beanie (beanie) b 3 A 25.85 w 4.238 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_hat_large b 2 A 23.638 w 4.298 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_marine_hat b 2 A 23.638 w 4.298 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro machine_beanie (beanie) b 2 A 294.2 w 5.154 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro toat_beanie (beanie) b 2 A 294.2 w 5.154 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_lc_large b 1 A 38.065 w 5.159 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro gaulke_plowing_lc b 2 A 75.04 w 5.316 core_any 0.724 {'0-0.5': 0.959, '0.5-1': 0.916, '1-2': 0.574, '>2': 0.067}
pro becker_hat_large b 2 A 42.712 w 5.438 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro becker_marine_hat b 2 A 42.712 w 5.438 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro machine_hat b 1 A 346.255 w 5.514 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro machine_lc b 1 A 346.255 w 5.514 core_any 1.0 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 1.0, '>2': 1.0}
pro hotel_fremont_hat b 9 A 40.292 w 5.556 core_any 0.831 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 0.78, '>2': 0.631}
pro hotel_fremont_patch b 1 A 40.292 w 5.556 core_any 0.6076 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 0.538, '>2': 0.0}
pro gaulke_jb b 4 A 146.965 w 6.132 core_any 0.7338 {'0-0.5': 0.967, '0.5-1': 0.982, '1-2': 0.576, '>2': 0.11}
pro c_gaulke_plowing_beanie (beanie) b 3 A 105.315 w 6.339 core_any 0.9775 {'0-0.5': 0.997, '0.5-1': 0.994, '1-2': 0.973, '>2': 0.935}
pro mfab_lc b 3 A 168.542 w 9.859 core_any 0.4944 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 0.737, '>2': 0.043}
pro mfab_lc b 1 A 1330.858 w 10.459 core_any 0.6946 {'0-0.5': 1.0, '0.5-1': 0.999, '1-2': 0.855, '>2': 0.224}
pro mfab_hat b 3 A 194.508 w 10.539 core_any 0.4721 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 0.749, '>2': 0.054}
pro mfab_hat b 1 A 1549.08 w 11.198 core_any 0.6858 {'0-0.5': 1.0, '0.5-1': 1.0, '1-2': 0.887, '>2': 0.216}
```

## Not read

- Gaulke Roofing hat, LC, beanie (pro) and `c golke logo LC.DST` filed under Plowing: one colour block in the DST (no COLOR_CHANGE), so nothing is "later"; the multi-colour Roofing hat (3 blocks) and ours on Roofing have no tatami ground. Question 2 for Roofing: not read.
- Tires 3D: no ground (puff satin). Proseal hat/beanie: one small ground each (49-58 mm2), nothing inside it. Proseal has no repo art; not run on our side.
- Our side covers the seven jobs the brief listed; LC/small variants not run (the pro readings of those match their hat siblings).
- Beanies (Becker, Plowing, Machine E, To a T): read and flagged `beanie` in Table 1, left out of every count in the answer. Their knockdown is a separate low-density layer; they read the same way (stacked, core 1.00, Plowing beanie's 6.3 mm piece 0.98).

## Caveats that change how to read the numbers

1. Colour blocks only: a shape the same colour as its ground cannot be seen; nor can a piece that crosses the ground's edge (> 10% outside its outline), e.g. Becker's keyline letters.
2. Opening by 0.55 mm drops run-stitch details (hairlines, eyes sewn as runs) and narrow satin under ~0.55 mm; they are not in any count.
3. "Stacked" here = earlier thread exists under the piece. It does not say the ground runs at full density under it; the penetration check is too noisy on small cores to say.
4. Ours was one run per job at the pro's width with today's Studio request; MFab's ours knock-out sits at core 0.497, on the 0.5 line.
5. Pro piece counts are per file; Becker hat/marine-smaller and Machine hat/LC are the same design twice, so "pieces" over-count jobs. By job: knock-out of a >5.3 mm piece in 4 jobs (Plowing, Fremont, MFab; JB is Plowing's large logo), solid in 2 (Becker, Machine).
6. Band bare cannot see gaps under ~0.4 mm (synthetic). Cost uses the ground's own penetration density including underlay and row-end stitches; a hole's row ends inflate density a little (synthetic: 2.65 vs 1.85 st/mm2 solid), so 1,570 is an upper-side estimate.

## Follow-up A. Which code path sews the ground solid (2026-11-13)

Instrumented from `a_instrument.py` (wraps `pipeline.resolve_overlaps`, `silhouette_underfill.apply_cfg` and `pipeline.gate_underfill_for_photo`; no repo edit). Logs: `a_becker_on.log`, `a_fremont_on.log`.

| job | class | under-fill after gate | under-fill report | pairs (later shape inside an earlier shape's outer contour) | hole after stage 4 | hole entering stage 5 | under-fill outline covers it | ground polygon after stage 5 covers it |
|---|---|---|---|---|---|---|---|---|
| Becker hat large, 101.9 mm | flat | on (+ panels) | ring S92f2350b (black), host Sb7019eaf (white letter), outline 2,446 mm2, 4 shapes merged | 1 | yes | yes | yes | yes |
| Fremont patch, 92.5 mm | flat | on (+ panels) | ring = host Sba572771 (the ground), outline 2,769 mm2, 3 merged | 68 | 68 | 68 | 68 | 68 |

So stage 4 DOES leave the hole, and it is still there when the region enters stage 5. What closes it is `cfg.silhouette_underfill` (`config.py:2102`, True for every job since 2026-10-27, Kent's "Every job"):

1. `pipeline.py:2076-2081` calls `silhouette_underfill.apply_cfg`.
2. `silhouette_underfill.plan` (`silhouette_underfill.py:333-402`) reads a RING: a shape with holes that hold other shapes. Its outline with the holes closed goes into the host's meta as `UNDERFILL_KEY` (`apply`, lines 750-755).
3. `stage5_overlap.py:1009-1013` puts that outline into `ground_under`; `1095-1102` unions it into the host's grown polygon (`grown = grown.union(under)`); `1211` skips holding open any hole inside `under`. The `1202-1231` hole-holding block that the study read is real, but it never fires on these holes because `under` already covers them.

**When the hole is NOT closed (from the code):**
- **Photo classes.** `gate_underfill_for_photo` (`pipeline.py:133-163`, called at `1978`) switches the under-fill trio off on `photo_subject` / `photo_scene` (Kent 2026-11-05), unless the art reads as white-keyline art. MFab classes `photo_scene` but takes that exemption. On a photo-class job every later shape gets the knock-out the study described.
- **Not a ring** (`_ring_candidates`, `plan`, lines 305-386). The shape must be one Polygon with holes. Its area must be at least min(200 mm2, 4% of the design box), and never under 50 mm2. Its tier must be `auto`, and it must not be a letter. The shapes inside must fill at least 50% of the holes (`HOLES_HELD_MIN`). A ring under 200 mm2 needs 3 or more inner shapes. Any shape already used by a bigger ring is skipped, so a ground nested inside another ring's contents is never read as a ring of its own, and its holes stay knocked out.
- **Panels (MFab).** With `silhouette_underfill_panels` on (it needs `sew_enclosed_white` and `border_from_outline`), `_panels` builds a closed white panel under the text riders. `apply` then cuts that panel, shrunk by `overlap_mm`, back OUT of the black host's outline (`silhouette_underfill.py:739-753`: `outline.difference(cut)`). That is the one knock-out in the paired set. The measured underlap, ~1 mm, is that 0.25 plus the host's pull and the stage-5 tongue.
- Shapes left unsewn on purpose are cut back off the outline (`plan`, lines 358-361).

## Follow-up B. Cartoon and character art, ours only (2026-11-13)

`b_cartoons.py`: the Studio request through `tools.pro_pair.digitize`, the same entry `tools.photo_corpus` uses (80 mm left_chest is its default). `write_dst`, then the reader. One job at a time. The four fixtures:
- **Pooh**: `scratch_kent/pooh_hunny_266px.jpg`, Kent's own, read only, at his 54.6 mm left chest.
- **Owl**: `testdata/photo/owl_kent.jpg` at 127 mm (`OWL_WIDTH` in the hairline tools). It is a photograph, not a cartoon, but it was named in the brief.
- **Tux**: `photo/corpus/gradient_mascot.png`, a character with eyes and a belly on a body.
- **Bison**: `photo/corpus/flat_emoji_icon.png`, a flat cartoon icon.

Tux and bison ran at the corpus's own 80 mm, left chest. The repo has no leopard, panda or donkey fixture.
| fixture | width, garment | class (lane) | under-fill on | stitches | grounds | pieces on a ground | <2 mm | 2-5 mm | >5 mm | knocked out | hole mm2 | solid adds (st, %) | band bare median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bison_flat_emoji | 80.0 mm, left_chest | flat | True | 17054 | 7 | 1 | n0: - | n0: - | n1: 1.00 [1.00-1.00] | 0 | 0.0 | 0 (0.0%) | 0.00 [0.00-0.00] |
| owl_kent | 127.0 mm, hat_front | photo_scene | False | 80305 | 20 | 8 | n6: 1.00 [0.99-1.00] | n1: 0.54 [0.54-0.54] | n1: 0.59 [0.59-0.59] | 0 | 0.0 | 0 (0.0%) | 0.00 [0.00-0.03] |
| pooh | 54.6 mm, left_chest | gradient | True | 12081 | 6 | 5 | n4: 1.00 [0.79-1.00] | n1: 1.00 [1.00-1.00] | n0: - | 1 | 1.42 | 7 (0.06%) | 0.00 [0.00-0.00] |
| tux_gradient_mascot | 80.0 mm, left_chest | flat | True | 22591 | 5 | 4 | n0: - | n0: - | n4: 1.00 [1.00-1.00] | 0 | 0.0 | 0 (0.0%) | 0.00 [0.00-0.00] |

Knocked-out pieces:
```
pooh b6 A 0.548 w 0.579 core None depth {'0-0.5': 0.16, '0.5-1': None, '1-2': None, '>2': None} bare 0.0054
```

Read:
- Under-fill on (Pooh gradient, Tux and bison flat): every piece on a ground is stacked, except one 0.5 mm2 Pooh speck (cost 7 stitches).
- Owl: classed `photo_scene`, so the gate turned the under-fill off. Its two wider pieces (3.7 mm / 66 mm2 and 5.6 mm / 31 mm2) read as knock-outs with an underlap. Cover by depth is 0.61 / 0.65 / 0.25 for the first, and 0.95 / 0.99 / 0.47 / 0.00 for the second, which is the shape the study described. At core cover 0.54 and 0.59 they sit just above my 0.5 knock-out line, so the table reports 0 knocked out and 0 cost.
- Caveat on the owl: 45 of its candidate fill pieces failed the tatami test (most likely its curved fur rows; I did not check), so only 8 pieces were read there. The owl number is thin.
- Caveat on the counts: only Tux has many large pieces. Pooh has 5 pieces, and the bison has 1.