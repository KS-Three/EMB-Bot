# `fillColumns` on the shape and image lanes (2026-10-08)

MASTER_SCOPE "Waiting on Kent" 22 asked whether the two lanes that did not
pass `fillColumns` after PR #662 (manual only) should. This is the evidence,
lane by lane, off beside on, made with `node tools/fill-columns-lanes.mjs`
(each design built the way `app/src/lib/generate.js` builds it: the Studio's
own preset and flatten/trace modules, the garment's fabric preset, underlay
on). **Nothing here has been sewn.** These are measurements of the stitch
stream the encoders are handed.

## Verdicts

| lane | floats off the fill | new floats off the fill | cuts | stitches (mean / worst) | verdict |
|---|---|---|---|---|---|
| basic shapes (63 designs) | 3,118 → 25 | none | 60 → 33 | +1.8% / +16.2% | **ON** (`generate.js` shape branch) |
| image, real logos (126 designs) | 188,952 → 484 | none | 3,714 → 3,208 | **+10.4%** / **+29.7%** | **ON**, Kent's call with this price in front of him |

- **Shapes: flipped.** The circle and both rectangles are byte-identical
  (no notch, no hole). The heart and every star lose their notch floats and
  their one center-out cut. The cost is +0.5% to +6% stitches on the default
  star and the heart; only the non-default 8-point star with 0.3 tips passes
  +10% (+12 to +16% at 50 and 100 mm). Of the 25 floats left, 23 are the 8-point
  star at 20 mm, which is a satin and is byte-identical on and off; the other
  two total 5 mm. Builds: 22 ms
  at most. Guard: `generate.spec.js`, "a star preset lays no float across its
  notches" (47 off-fill floats with the flag dropped from the shape branch,
  0 with it).
- **Image: ON, by Kent's call.** The floats go just as cleanly, and no
  design gains a float or a deeper one. But the stitch bill is past the ~10%
  bar this lane was measured against: +10.4% across the lane, over +10% on
  **76 of 126** designs, and +29.7% on `summit_badge` at full back. Thread
  laid over rows already sewn goes from 6.0 m to 52.1 m across the set (68 mm
  of it on the face of a fill, the rest on the rims), the worst millimetre of
  rim gains lines on 66 designs (becker 7 → 18, script tires 6 → 15, summit
  22 → 36), and one build takes 1.8 s (off: 88 ms). The lane was held OFF on
  that bar and put to Kent; he flipped it the same day, asking that **the next
  ten digitized images shown to him carry the off/on float picture** —
  `node tools/fill-columns-image-sheet.mjs <png> [out.svg]` draws it. Guard:
  `generate.spec.js`, "an image fill lays no float across its counter" (351
  off-fill floats with the flag dropped from the image branch, 0 with it).

## How each column is measured

See the head of `tools/fill-columns-lanes.mjs`. In short:

- **Floats off the fill**: moves with the thread attached that run more than
  0.8 mm outside the drawn shape they belong to (past terry's 0.6 mm pull
  compensation, a fill row and a stitch's rounding). Count, then total mm.
- **Rim lines**: on the worst millimetre of any drawn rim, the lines of
  thread within 0.5 mm of it and within 30° of its tangent, the fill's own
  rows not counted. The design's maximum, then the lane's maximum.
- **Travel**: fill thread that is neither a row nor a row turn (off the
  row direction, longer than 0.5 mm): all of it / the part over rows already
  sewn / the part of that more than 0.8 mm inside the fill (its face).
- **ms**: build time, the faster of two builds, one container core.

**The control** — two of `tools/fill-columns-sheet.mjs`'s manual-lane
shapes, whose answer is known. Its badge reproduces that sheet's stitch
counts to the stitch (3,149 → 3,253), so the instrument can see the defect:


| group | designs | changed | stitches off → on | worst Δ | cuts off → on | floats off the fill off → on (mm) | rim lines, worst mm (max) off → on | travel mm: all / over sewn rows / of that on the face, off → on | ms off → on (max) |
|---|---|---|---|---|---|---|---|---|---|
| badge, two cut-outs | 1 | 1 | 3,149 → 3,253 (+3.3%) | +3.3% | 1 → 0 | 70 (810) → 0 (0) | 5 → 6 | 0 / 0 / 0 → 14 / 2 / 0 | 5 → 12 |
| wide U (a notch) | 1 | 1 | 1,839 → 1,969 (+7.1%) | +7.1% | 1 → 0 | 107 (1526) → 0 (0) | 5 → 7 | 0 / 0 / 0 → 16 / 0 / 0 | 1 → 2 |
| **all** | 2 | 2 | 4,988 → 5,222 (+4.7%) | +7.1% | 2 → 0 | 177 (2336) → 0 (0) | 5 → 7 | 0 / 0 / 0 → 30 / 2 / 0 | 5 → 12 |

## Basic shapes — every preset, 20 / 50 / 100 mm, on left chest (pique), hat front (cap) and towel (terry)


| group | designs | changed | stitches off → on | worst Δ | cuts off → on | floats off the fill off → on (mm) | rim lines, worst mm (max) off → on | travel mm: all / over sewn rows / of that on the face, off → on | ms off → on (max) |
|---|---|---|---|---|---|---|---|---|---|
| circle @ 20 mm | 3 | 0 | 2,702 → 2,702 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 13 / 10 / 0 → 13 / 10 / 0 | 2 → 4 |
| circle @ 50 mm | 3 | 0 | 13,270 → 13,270 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 5 → 5 | 17 / 13 / 0 → 17 / 13 / 0 | 7 → 7 |
| circle @ 100 mm | 3 | 0 | 38,568 → 38,568 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 34 / 25 / 0 → 34 / 25 / 0 | 10 → 11 |
| rect @ 20 mm | 3 | 0 | 4,408 → 4,408 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 0 / 0 / 0 → 0 / 0 / 0 | 0 → 0 |
| rect @ 50 mm | 3 | 0 | 10,011 → 10,011 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 0 / 0 / 0 → 0 / 0 / 0 | 1 → 1 |
| rect @ 100 mm | 3 | 0 | 19,236 → 19,236 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 0 / 0 / 0 → 0 / 0 / 0 | 1 → 1 |
| rect {cornerRadiusMm:6} @ 20 mm | 3 | 0 | 4,191 → 4,191 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 4 / 3 / 0 → 4 / 3 / 0 | 1 → 1 |
| rect {cornerRadiusMm:6} @ 50 mm | 3 | 0 | 9,820 → 9,820 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 5 / 3 / 0 → 5 / 3 / 0 | 1 → 1 |
| rect {cornerRadiusMm:6} @ 100 mm | 3 | 0 | 18,876 → 18,876 (+0%) | +0% | 3 → 3 | 0 (0) → 0 (0) | 6 → 6 | 6 / 4 / 0 → 6 / 4 / 0 | 1 → 1 |
| heart @ 20 mm | 3 | 3 | 2,208 → 2,252 (+2%) | +2.4% | 3 → 0 | 4 (47) → 0 (0) | 7 → 6 | 7 / 5 / 0 → 9 / 5 / 0 | 3 → 8 |
| heart @ 50 mm | 3 | 3 | 10,130 → 10,229 (+1%) | +1.2% | 3 → 0 | 7 (161) → 0 (0) | 6 → 7 | 15 / 12 / 0 → 18 / 9 / 0 | 7 → 6 |
| heart @ 100 mm | 3 | 3 | 29,164 → 29,398 (+0.8%) | +1% | 3 → 0 | 9 (266) → 0 (0) | 6 → 9 | 25 / 13 / 0 → 143 / 126 / 0 | 6 → 14 |
| star @ 20 mm | 3 | 3 | 1,948 → 2,048 (+5.1%) | +6.2% | 3 → 0 | 56 (400) → 0 (0) | 5 → 8 | 4 / 3 / 0 → 71 / 33 / 0 | 0 → 3 |
| star @ 50 mm | 3 | 3 | 7,730 → 7,971 (+3.1%) | +3.6% | 3 → 0 | 169 (2416) → 0 (0) | 6 → 8 | 11 / 8 / 0 → 96 / 51 / 0 | 1 → 3 |
| star @ 100 mm | 3 | 3 | 20,734 → 21,229 (+2.4%) | +3.3% | 3 → 0 | 306 (8279) → 0 (0) | 6 → 8 | 42 / 32 / 0 → 218 / 126 / 0 | 2 → 8 |
| star {points:8,innerRatio:0.3} @ 20 mm | 3 | 0 | 1,842 → 1,842 (+0%) | +0% | 0 → 0 | 23 (189) → 23 (189) | 15 → 15 | 0 / 0 / 0 → 0 / 0 / 0 | 37 → 13 |
| star {points:8,innerRatio:0.3} @ 50 mm | 3 | 3 | 6,759 → 7,781 (+15.1%) | +16.2% | 3 → 1 | 771 (8410) → 0 (0) | 6 → 9 | 87 / 66 / 0 → 465 / 275 / 0 | 1 → 19 |
| star {points:8,innerRatio:0.3} @ 100 mm | 3 | 3 | 15,903 → 17,822 (+12.1%) | +14.8% | 3 → 0 | 1479 (26123) → 1 (2) | 8 → 13 | 133 / 104 / 0 → 799 / 525 / 0 | 2 → 21 |
| star {points:4,innerRatio:0.6} @ 20 mm | 3 | 3 | 1,912 → 1,921 (+0.5%) | +0.9% | 3 → 3 | 3 (41) → 1 (3) | 5 → 5 | 0 / 0 / 0 → 0 / 0 / 0 | 0 → 1 |
| star {points:4,innerRatio:0.6} @ 50 mm | 3 | 3 | 7,779 → 7,912 (+1.7%) | +2.1% | 3 → 1 | 104 (2232) → 0 (0) | 6 → 6 | 0 / 0 / 0 → 82 / 35 / 0 | 2 → 4 |
| star {points:4,innerRatio:0.6} @ 100 mm | 3 | 3 | 21,897 → 22,179 (+1.3%) | +2.3% | 3 → 1 | 187 (6719) → 0 (0) | 6 → 7 | 0 / 0 / 0 → 203 / 47 / 0 | 3 → 7 |
| **all** | 63 | 33 | 249,088 → 253,666 (+1.8%) | +16.2% | 60 → 33 | 3118 (55283) → 25 (194) | 15 → 15 | 406 / 299 / 0 → 2185 / 1289 / 0 | 37 → 21 |

## Image lane — 14 real logos under `digitizer/testdata`, 2 / 4 / 6 colours (background removed, the Studio default), on left chest, hat front and full back


| group | designs | changed | stitches off → on | worst Δ | cuts off → on | floats off the fill off → on (mm) | rim lines, worst mm (max) off → on | travel mm: all / over sewn rows / of that on the face, off → on | ms off → on (max) |
|---|---|---|---|---|---|---|---|---|---|
| logo_golke_roofing.png | 9 | 9 | 174,571 → 187,643 (+7.5%) | +8.3% | 455 → 393 | 6246 (84362) → 29 (152) | 29 → 29 | 1012 / 431 / 0 → 5429 / 2123 / 16 | 37 → 129 |
| logo_hotel_fremont_patch.png | 9 | 9 | 332,990 → 355,726 (+6.8%) | +7.4% | 435 → 346 | 12366 (662180) → 132 (3855) | 24 → 24 | 548 / 270 / 0 → 9226 / 4479 / 2 | 32 → 205 |
| logo_mfab_hat.png | 9 | 9 | 286,125 → 318,093 (+11.2%) | +13.7% | 449 → 386 | 18595 (688992) → 43 (630) | 17 → 18 | 738 / 492 / 0 → 10023 / 4803 / 2 | 29 → 266 |
| logo_mfab_lc.png | 9 | 9 | 286,096 → 318,034 (+11.2%) | +13.1% | 433 → 377 | 18651 (682103) → 45 (579) | 15 → 18 | 730 / 460 / 0 → 10260 / 4880 / 5 | 38 → 315 |
| logo_toat_beanie.png | 9 | 9 | 239,664 → 269,792 (+12.6%) | +15.4% | 258 → 227 | 18669 (1386236) → 22 (936) | 98 → 97 | 949 / 572 / 0 → 9911 / 4347 / 13 | 54 → 334 |
| logo_toat_machine.png | 9 | 9 | 225,420 → 255,499 (+13.3%) | +14.4% | 275 → 239 | 17824 (1468737) → 25 (476) | 60 → 60 | 1129 / 743 / 0 → 9999 / 3936 / 9 | 32 → 654 |
| becker_marine_logo.png | 9 | 9 | 227,688 → 262,740 (+15.4%) | +18.6% | 123 → 99 | 23529 (558666) → 0 (0) | 7 → 18 | 620 / 382 / 0 → 9114 / 4530 / 2 | 19 → 365 |
| logo_alpha.png | 9 | 9 | 172,473 → 175,986 (+2%) | +3.3% | 66 → 51 | 2115 (68837) → 0 (0) | 10 → 10 | 150 / 108 / 0 → 678 / 124 / 0 | 20 → 70 |
| logo_whitebg.png | 9 | 9 | 174,031 → 177,340 (+1.9%) | +3.1% | 66 → 60 | 2071 (67220) → 0 (0) | 10 → 10 | 238 / 185 / 0 → 725 / 195 / 0 | 16 → 62 |
| logo_script_tires.png | 9 | 9 | 117,771 → 133,383 (+13.3%) | +17.6% | 57 → 48 | 9777 (202698) → 0 (0) | 6 → 15 | 571 / 398 / 0 → 6096 / 2599 / 0 | 8 → 49 |
| enthusiast_logo.png | 9 | 9 | 87,688 → 93,125 (+6.2%) | +7.3% | 236 → 215 | 2846 (37795) → 89 (794) | 12 → 12 | 311 / 164 / 0 → 1698 / 743 / 4 | 28 → 53 |
| summit_badge.png | 9 | 9 | 563,673 → 636,933 (+13%) | +29.7% | 302 → 285 | 29913 (1288935) → 32 (243) | 22 → 36 | 1481 / 770 / 0 → 22805 / 10917 / 3 | 88 → 1846 |
| logo_drone_thermal_badge.png | 9 | 9 | 422,142 → 468,237 (+10.9%) | +15.8% | 515 → 441 | 22595 (604426) → 52 (529) | 38 → 39 | 1666 / 1013 / 0 → 17189 / 7643 / 8 | 47 → 465 |
| logo_gaulke_roofing.png | 9 | 9 | 53,142 → 59,098 (+11.2%) | +14.8% | 44 → 41 | 3755 (101944) → 15 (360) | 13 → 13 | 96 / 42 / 0 → 1655 / 780 / 3 | 4 → 39 |
| **all** | 126 | 126 | 3,363,474 → 3,711,629 (+10.4%) | +29.7% | 3714 → 3208 | 188952 (7903131) → 484 (8556) | 98 → 97 | 10239 / 6030 / 0 → 114810 / 52099 / 68 | 88 → 1846 |

*(measured 2026-10-08 — `node tools/fill-columns-lanes.mjs`, which prints these three tables)*
