# Satin flat ends: the pro's construction, and the house lean's tilted end (2026-11-14)

The Director's queue item: Kent's 14 end/corner pins from #1481. The corner
turn (#1518) cures none of them. Their designs are byte-identical under it,
Becker #10/#11 included: those pins are end faces and acute joints, not L
corners.

## The pro's ends, needle by needle

I drew the pro's DSTs and ours stitch by stitch at five of the pins, every
stitch that touches the window, sew order coloured, needle points dotted.
The pro was aligned by phase correlation. Ours is today's main with
edge-walk and the corner turn on. Sheets (gitignored, primary checkout):
`digitizer/eye_pairs_out/jag-source-1113/flat-ends-pro/`.

| pin | the pro | ours |
|---|---|---|
| Becker #10, MARINE N's flat top ("The letters should be flat") | steep parallel crosses; every needle end on ONE straight top line | crosses about 10-15 deg off horizontal; the top drawn by a tilted cross's body |
| Becker #11, the N's foot ("The letters should be flat") | crosses parallel to the baseline, the last one lying ON it | crosses 10-12 deg off the baseline |
| ProSeal hat #2, a slanted end ("no crisp edge cut-off") | parallel crosses, each clipped on the slanted face, ends on the face line | the end fans and one cross sticks past the face |
| Gaulke hat #2, an edge along the gap ("edges are very jagged") | parallel crosses, ends on the gap edge | ends staggered along the edge |
| Fremont hat #3 | matches ours (as #1481 found) | |

**His rule, every pin:** the edge is drawn by cross ENDS on the straight
line, or by the last cross lying along a flat face. Never by a cross body at
an angle to it.

## Why ours tilts at Becker #10/#11

The cut already mitres a column's end onto a flat face 8-45 deg off square
(`outline_cut._mitre_ends`). The house lean (`lettering_columns_text_lean`,
ON since 10-24, `column_lean.lean_columns`) then re-stations each straight
column with the word's house cross. On the N's diagonal that cross is
clamped by the lean cap to 10-12 deg off horizontal. The re-stationing
throws away the mitred end: the foot and top end in leaned crosses across
the flat face.

## The build: `cfg.extra["lettering_columns_lean_flat_ends"]` (built OFF)

After a column is re-stationed under the house cross, the cut's own mitre
runs again on the leaned stations. Its axis is the normal of the house
cross, so a face 8-45 deg off the CROSS (not off the column's own normal)
gets its last crosses turned onto it, the final one on the face.
- A face that lies on another piece of the letter is a cut, never an end.
- The flag is set plan-wide (`lean_flat_ends_scope` in
  `pipeline.plan_stitches`) and registered in `shape_memo._AMBIENT`.

**On Becker hat large's N** (lane input, `testdata/becker_hat_large_lane_N.json`):
- **The foot:** the mean gap from the baseline to the lowest needle, per
  0.5 mm, is 0.534 -> 0.428 mm (worst 1.24 -> 0.99).
- **The top:** unchanged by that measure (0.47 -> 0.48, worst 1.09 -> 1.48).
- **By eye** (`sheets/becker_hat_large_p10_off_on_pro.png`, `_p11_`):
  - #11's foot ends flat on the baseline, as the pro's does.
  - #10's top now ends in one cross lying along the top line, so the edge
    reads flat. The pro gets his flat top differently: steep crosses whose
    ends line the edge.

## The 28 designs

28 designs at main's defaults, the flag alone OFF -> ON, one digitize at a
time. **21 move**; unchanged: ahora, but_seriously, dot_music, hed_p_e,
bridge_hat, bridge_lc, toat_machine_hat. Exposed thread 0.5 -> 0.5 mm.

| design | stitches OFF -> ON | trims | letters' travel on thread, mm |
|---|---|---|---|
| becker_hat_large | 16090 -> 16112 | 19 -> 19 | 16.2 -> 17.4 |
| mfab_hat | 20954 -> 20958 | 26 -> 26 | 2.3 -> 2.3 |
| lt_and_pizza | 2454 -> 2466 | 5 -> 5 | 11.0 -> 10.3 |
| lt_bukit_asam | 2027 -> 2048 | 9 -> 9 | 5.8 -> 6.6 |
| lt_jakarta | 3166 -> 3181 | 22 -> 22 | 17.7 -> 17.7 |
| lt_k_line | 3442 -> 3437 | 12 -> 12 | 9.7 -> 11.9 |
| lt_n_sync | 2479 -> 2567 | 2 -> 3 | 1.7 -> 1.7 |
| becker_lc_large | 14579 -> 14586 | 17 -> 17 | 25.7 -> 26.6 |
| becker_hat_small | 10293 -> 10299 | 12 -> 12 | 17.3 -> 18.1 |
| becker_chest_small | 10110 -> 10112 | 11 -> 11 | 18.6 -> 19.3 |
| becker_beanie | 13647 -> 13653 | 15 -> 15 | 20.5 -> 21.2 |
| mfab_lc | 17905 -> 17918 | 23 -> 24 | 8.7 -> 7.0 |
| gaulke_roofing_hat | 7494 -> 7551 | 33 -> 34 | 11.8 -> 9.3 |
| gaulke_roofing_lc | 5852 -> 5865 | 24 -> 23 | 11.8 -> 11.8 |
| gaulke_roofing_beanie | 7679 -> 7728 | 26 -> 26 | 8.2 -> 7.9 |
| hotel_fremont_hat | 16106 -> 16108 | 28 -> 28 | 14.0 -> 14.0 |
| hotel_fremont_patch | 15061 -> 15065 | 23 -> 23 | 10.2 -> 10.2 |
| precision_drone | 14984 -> 15025 | 93 -> 93 | 8.6 -> 9.1 |
| proseal_hat | 5707 -> 5738 | 36 -> 36 | 15.0 -> 10.7 |
| proseal_beanie | 7372 -> 7404 | 31 -> 31 | 9.8 -> 9.0 |
| goldentee_hat | 13636 -> 13669 | 45 -> 45 | 1.6 -> 1.7 |
| **all 28** | 266005 -> 266458 | 592 -> 594 | 263.8 -> 261.4 |

**Read it plainly:** the flag reaches further than the pins it was built
for, though each change is small.
- **Trims:** 592 -> 594. N Sync gains one trim and 88 stitches, MFab lc and
  Gaulke hat one trim each, Gaulke lc loses one.
- **Letters' travel on finished thread:** 263.8 -> 261.4 mm in total, but
  mixed. It rises on 9 designs (all five Becker jobs by 0.7-1.2 mm, k_line
  9.7 -> 11.9) and falls on 6 (ProSeal hat 15.0 -> 10.7, Gaulke hat
  11.8 -> 9.3).
- **The other pin sheets** (`sheets/<pin>_off_on_pro.png`): and_pizza #1 and
  ProSeal #2 do not change at the pin. k_line #4 ("The I should be
  completely flat on top") is still topped by tilted crosses ON, so that pin
  is not cured either.

## Not built

- **ProSeal #2:** the pro clips parallel crosses on a slanted face; ours
  fans (`_fan_ends`).
- **Gaulke #2:** staggered ends along an oblique edge.

Both are construction changes in `outline_cut` with their own risks, not
done here.
