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

## The 26 corpus fixtures (director's request), with the judge

`tools.corpus_scorecard.FIXTURES` (TESTDATA), Studio request at 80 mm,
`left_chest`, flag OFF vs ON (the build with the judge below), compared by md5
of `design["stitches"]`: **9 of 26 moved, 17 byte-identical** (the first build
moved 10; `photo_dof_meadow` is now identical). 7 are pictured with close-ups
(`fx_<name>.png` = ORIGINAL | BEFORE | AFTER, `fx_<name>_closeup.png` = the
three largest changed spots); `photo_chrome_specular`, moved by 4 stitches, has
the full picture only.

By eye, worse first:

| fixture | stitches / trims OFF -> ON | by eye |
|---|---|---|
| scene_stub | 23327/75 -> 23216/75 | **slightly worse**: one small cream gap appears between patches (bottom spot); the others re-lay, no clear change (the judge reverted part of the first build's -547) |
| phone_ui_golke | 10864/125 -> 10803/123 | **trivially worse**: a small pale sliver patch appears inside black |
| golden_tee | 14360/54 -> 13940/54 | better: cleaner outer ring, a stray crossing patch gone |
| repro_gradient_white_icon | 22911/12 -> 22672/12 | better: the fanned block at the top-left becomes one short tuck |
| photo_owl_pale | 24873/9 -> 24840/9 | slightly better: the eye ring has fewer wedge fans |
| drone_render | 18337/114 -> 18273/114 | no visible change |
| logo_bridge_bar | 10827/17 -> 10811/17 | no visible change |
| photo_grass_macro | 3952/13 -> 3924/13 | no visible change |
| photo_chrome_specular | 36052/85 -> 36048/85 | no visible change |

## The MARINE finding and the judge (flip PR, 2026-11-17)

Kent's "Flip ON" was given without this: with the flag ON, Becker MARINE at
80 mm (the junction-stack test's own config) reads **2.8 -> 6.8 mm2** of bare
artwork (`ARTWORK_UNCOVERED`, test ceiling 5.0; ROADMAP gate 3's failure mode).
`marine80_bare_zoom.png`: ORIGINAL | BEFORE (flag OFF) | AFTER, first build |
AFTER, judged build, at the two new bare patches, (-7.9, 1.3) 2.4 mm2 and
(-35.7, 5.1) 1.6 mm2 in plan mm. **What it is:** two thin arms that meet a
wider node at a leg's foot / a slab. Stopped at the blob edge, their last
stitches no longer reach the artwork's end; in the first build the stroke tails
that fill the leg's bottom (row 2) and the slab's lower corner (row 1) are gone.

Why no simple guard worked (all measured on MARINE's 9 and Toat's 11 firing
ends): arm/node width ratio, arm width, angle to the stem, and the ribbon
cover of the lost zone each overlap between the Toat M's ends and MARINE's
offenders (ratio 3.2 / 4.3 against 2.5 / 3.8; ribbon margin 0.01-0.02 mm in
both). Neither half of the rule alone works either (no reach-in alone: 4.4
mm2; no tip cap alone: 5.2).

**The judge** (`satin_shape_judged`): a shape sewn with the flag keeps it only
where it leaves at most 0.3 mm2 more bare artwork than the same shape sewn
without (the crown cover's patch finder and floors, `_uncovered_patches`).
Results with the judge: MARINE 80 **2.8 mm2 ON, same as OFF, unmodified test
green** (2,404 stitches against 2,476 OFF, 2,305 first build); the six pro
movers are byte-identical to the first build (Toat hat 17,353, beanie 17,241:
the M gain is whole); fixtures as above. Cost: a flagged shape is sewn twice
(the OFF arm is memoized), only when the ON run differs.
