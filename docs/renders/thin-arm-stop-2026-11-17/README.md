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

## The 26 corpus fixtures (director's request)

`tools.corpus_scorecard.FIXTURES` (TESTDATA), Studio request at 80 mm,
`left_chest`, flag OFF vs ON, compared by md5 of `design["stitches"]`:
**10 of 26 moved, 16 byte-identical. 8 are pictured** (`fx_<name>.png` =
ORIGINAL | BEFORE | AFTER, `fx_<name>_closeup.png` = the three largest changed
spots); the other 2 moved by 4 and 32 stitches, too small to show at any
render scale (no close-up is produced), and have the full picture only.

By eye, worse first:

| fixture | stitches / trims OFF -> ON | by eye |
|---|---|---|
| scene_stub | 23327/75 -> 22780/78 | **slightly worse at one spot**: the top-right patch gains a small cluster of crossing blocks; the other two spots re-lay, no clear change; -547 stitches |
| phone_ui_golke | 10864/125 -> 10803/123 | **trivially worse**: a small pale sliver patch appears inside black; the rest unchanged |
| golden_tee | 14360/54 -> 13940/54 | better: cleaner outer ring, a stray crossing patch gone |
| repro_gradient_white_icon | 22911/12 -> 22672/12 | better: the fanned block at the top-left becomes one short tuck |
| photo_owl_pale | 24873/9 -> 24840/9 | slightly better: the eye ring has fewer wedge fans |
| drone_render | 18337/114 -> 18273/114 | no visible change |
| logo_bridge_bar | 10827/17 -> 10811/17 | no visible change |
| photo_grass_macro | 3952/13 -> 3924/13 | no visible change |
| photo_chrome_specular | 36052/85 -> 36048/85 | no visible change |
| photo_dof_meadow | 20873/66 -> 20841/66 | no visible change |
