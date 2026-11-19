# `outline_strip_column`: a strip between two holes sewn once (2026-11-19) — built OFF, stays OFF

**Not a flip candidate.** The F's arm is better close up, but the whole word at print size is not clearly better
than OFF, and the hat costs +4 trims. Per the director's rule it stays OFF, and the 90-minute `flag_sweep` was not
run.

Follows the census `docs/mfab-junction-census-2026-11-19.md`. MFab's white top line is
`stage6_border.keyline_runs`: one 1.88 mm loop per black hole. Where two holes stand one to two loop widths apart,
both loops cover the strip between them. The professional sews such a strip once, as a full-width column: F arm
3.80 mm, B slots 2.83 mm.

## The build

`digitizer_core/outline_strip.py`, hooked in `stage7_sequence` just before the outline loops. It uses the typed field
`outline_strip_column` (default False). With it OFF the path is not entered, and MFab hat at 104.9 mm stays 20,564
stitches / 25 trims, as on main.

- **Strip.** The band's medial axis, keeping points whose feet are both on holes (not the outer edge) and whose
  half-width is between half and one loop width. The strip is the swept disks. It must be at least one loop width
  across, at least two of its own widths long, and fill at least 0.8 of its minimum rotated rectangle. A strip that
  fails as a whole is tested branch by branch of its axis. A hairline stem under one loop width is left to the loops.
- **Sewing.** The loops come first, every ring in one `keyline_runs` call, with each cross stopping `SPLIT_LAP_MM`
  (0.2) inside the strips. Then each strip, grown by the same 0.2 mm, is sewn as one satin column
  (`satin_shape`). The needle walks there through the band where `outline_band._hop` finds a route, else it lifts.
- No satin floor, pull, density or cover value is touched, and no outer loop is added (that is `outline_one_band`).

Two variants were tried and dropped:
- Cutting the loops at the gaps and walking them through the band (`_split_at_gaps`): jumps went 8 -> 33.
- One nearest-first walk over loops and columns together: trims +5, and the F arm's max went back to 15.

## Evidence

Junction layers on MFab hat at 104.9 mm (r 2.5 mm, mean / max). The professional's figures are from the census.

| junction | professional | OFF | ON |
|---|---|---|---|
| J1 M mark (16, 18.5) | 5.0 / 13 | 2.9 / 7 | 2.92 / 7 |
| J2 F upright / bar (35, 6) | 4.06 / 11 | 3.34 / 11 | 3.33 / 11 |
| J3 F arm (45, 12.5) | 3.49 / 8 | 4.18 / 15 | **3.22 / 13** |
| J4 dash (36, 17) | 4.23 / 12 | 5.19 / 15 | 5.07 / 13 |
| J5 B lower slot (89, 18.5) | 3.43 / 8 | 5.51 / 13 | 5.51 / 13 (no strip found) |

The director's bar was the max at J3-J5 coming down toward 8-9. It is not met: 13 / 13 / 13. The B slots are not
found, because they branch into the leg and are under one loop width at the slot's narrow end.

| run | OFF stitches / trims / jumps | ON | strips | preflight |
|---|---|---|---|---|
| mfab_hat 104.9 | 20,564 / 25 / 8 | 20,566 / **29** / 8 | 3: F arm, the M's right stem by the dash, one in WELDING | B 88 = |
| mfab_lc 96.7 | 17,570 / 20 / 9 | 17,626 / 22 / 8 | 2 | B 88 = |
| mfab_hat 30 | 2,996 / 12 / 2 | unchanged | 0 | B 76 = |
| becker_hat_large 101.9 | 15,820 / 20 | 15,833 / 19 | 1 (3.1 mm) | A 100 = |
| becker_lc_large 95.7 | 14,291 / 15 | 14,274 / 16 | 1 | A 100 = |
| becker_hat_small 76.5 | 10,165 / 11 | 10,139 / 12 | 2 | A 100 = |
| becker_chest_small 76.5 | 10,039 / 9 | 10,015 / 9 | 2 | A 100 = |
| becker_beanie 79.8 | 13,619 / 14 | 13,569 / 16 | 2 | B 88 = |

Results against the director's conditions:
- **Pictures** (`docs/renders/outline-strip-column-2026-11-19/`): the MFab F arm reads as one block where OFF shows
  the stepped double bar (fault 4). Elsewhere on the word the change is small; the M's right stem by the dash is
  somewhat heavier. BECKER moves at all five placements, with no visible change at whole-word size.
- **Becker:** it is not bounded out, which the director's rule (3) asks for in this case.
- **Trims:** +4 on the hat, which breaks the +1-2 condition. The rest are -1 to +2.
- **Coverage:** bare-cloth and coverage figures were not worse (coverage p50 3.29 -> 3.30, p95 5.72 -> 5.71 on
  the hat).

## If someone takes it further

- Find the B slots: branch-aware with a width bound read at the slot's middle, not its end.
- Bound Becker out.
- Sew each column next to the loop that borders it, without the nearest-first walk's extra lifts.
- The F arm is the one place where the gain is real: it matches his single 3.8 mm column.
