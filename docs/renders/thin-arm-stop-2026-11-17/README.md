# `satin_thin_arm_stop` OFF vs ON — 2026-11-17

Prime-grader fault: Toat Machine's script **M** (`toat_machine_hat`, pins near
10.5/23.5, 20.5/24.0 mm). A hairline joins each thick stem near its top; the
satin tier ran the hairline INTO the stem (`satin_junction_stack`, part B) and
capped it (`_is_tip_end` → `_extend_to_cap`), so a fan of crossing stitches
lay over the stem's own crosses. The flag makes a thin arm (node at least 2x
its own width, read 1.5-4 mm back from the end) stop at the blob's edge: no
reach-in, no tip cap. Default OFF; OFF is byte-identical.

The nine committed pro jobs (`tools.prime_grader.population()`), flag OFF vs ON:
**6 moved, 3 byte-identical** (becker_hat_large, hotel_fremont_hat, tires_hat_3d).
**All 6 are pictured** (`<slug>.png` = ORIGINAL | BEFORE | AFTER;
`<slug>_closeup.png` = the three largest changed spots, BEFORE left, AFTER right).

| design | stitches / trims OFF -> ON | by eye |
|---|---|---|
| toat_machine_hat | 17430/21 -> 17353/22 | **better**: both M stem tops lose the fan; hairline ends at the stem with one short tuck |
| toat_beanie | 17357/24 -> 17241/23 | **better**: the stacked block at the second stem is gone, one small tuck remains |
| goldentee_hat | 13613/50 -> 13184/47 | no visible change at print size; the F's orange body is a little less lumpy in close-up |
| precision_drone | 14182/100 -> 14083/101 | no visible change (the R of THERMAL knots slightly differently) |
| mfab_hat | 20846/27 -> 20840/27 | no visible change |
| gaulke_roofing_hat | 7392/34 -> 7336/34 | no visible change (one hairline stitch moves a few mm inside black) |

None got worse. Not fixed by this flag: the lumpy "head" of the M's first stem
(the stacked blocks above the joint) is a separate cause and stays.

Also found: the existing OFF flags `satin_tip_corner_gate` ON +
`satin_junction_stack` OFF clean the same M tops (stem-top picture in the PR),
but `satin_junction_stack` is the ON default Kent flipped 2026-09-19 for
MARINE's junctions, so turning it off moves every logo; the new flag is the
narrow version.
