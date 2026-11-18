# The apex_pro family is OFF again (Kent, 2026-11-17)

`lettering_columns_apex_pro`, `lettering_columns_apex_pro_joints` and
`lettering_columns_corner_fold_cap_flared` were flipped ON on 2026-11-15
(#1583, Kent's "Flip all three ON"). On 2026-11-17 Kent, looking at Becker:
"the letters in MARINE regressed from what i've previously seen. make sure
something isn't effed up here." Shown the whole word before and after, he
picked **"Revert all three (Recommended)"**. `lettering_columns_ring_floor`,
the fourth flag of #1583, stays ON: it is byte-identical on this design.

## What changed, by eye

Pictures in `docs/renders/apex-family-revert-2026-11-17/`, Becker hat
101.9 mm, the MARINE band:

- `marine_five_dates.jpg`: renders of 11-14, 11-15 and 11-16 have no cap. Main
  on 11-17 (`796123f2`) sews a separate slab of near-vertical stitches across
  the top of M, A, R, N and E, with a visible seam; the A's and the R's slab
  overhang the letter. The flag ends/seam trio (#1641, flipped the same day)
  is the fifth row and changes nothing here.
- `marine_one_flag_off_each.jpg`: each flag turned off alone on main
  `796123f2`. `apex_pro_joints` OFF removes the caps on A, R and N.
  `corner_fold_cap_flared` OFF removes the E's. `apex_pro` OFF changes the M's
  top-left. `ring_floor`, `stroke_floor` and `ribbon_handback` OFF are
  byte-identical to main on this design.
- `marine_today_vs_reverted.jpg`: main with the three OFF sews MARINE as the
  11-16 render did (16,212 stitches against 16,239 with them ON).

## Why it looked new to him

The renders he had seen through 11-16 came from lanes cut before #1583 merged
(2026-11-15 21:47). And the sheets he ruled the flip from were single-letter
close-ups (art | main | four ON | pro, `eye_pairs_out/flips-1115/`). In
close-up the cap matches the professional's. Nobody showed him the word.

## What the revert moves

Rendered on 36 designs (Kent's flag, 10 pro jobs, 21 Commons logos, the four
other Becker jobs), main `796123f2`, 2026-11-17: 7 move, 29 are identical.

| design | stitches with the three ON | OFF |
|---|---|---|
| Becker hat large, 101.9 mm | 16,239 | 16,212 |
| Becker hat small, 76.5 mm | 10,172 | 10,324 |
| Becker LC large, 95.7 mm | 14,536 | 14,635 |
| Becker chest small, 76.5 mm | 10,085 | 10,160 |
| Becker beanie, 79.8 mm | 10,862 | 10,949 |
| comic halftone, 80 mm | 24,526 | 24,566 |
| vintage engraved badge, 80 mm | 22,702 | 22,702 |

## What comes back, and how

The professional does sew a slab cap on these letters
(`docs/renders/big-letter-construction-2026-10-24/marine_102_art_off_pro.png`):
a narrow sheared band that stays inside the letter. Ours was the same
construction executed worse. Before the family is offered again:

1. The cap stays inside the letter's outline (no overhang on the A and the R).
2. Its depth matches his.
3. **The flip question shows whole words**, beside the letter close-ups.

## Correction to `docs/becker-marine-caps-limit-2026-11-17.md`

That note (#1628) answered a prime-grader pin on these caps with "not a fault
to fix; the professional sews the same cap". Two things it missed: the cap
was new on main since 2026-11-15, and ours overhangs where his does not.

## For tests

A number pinned on main between 2026-11-15 and 2026-11-17 was read with the
three ON: spread `APEX_FAMILY_2026_11_15_ON` (`tests/conftest.py`).
