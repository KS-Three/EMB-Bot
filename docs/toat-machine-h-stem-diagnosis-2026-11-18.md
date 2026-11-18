# Toat Machine hat, the "h" stem: diagnosis (2026-11-18)

Prime-grader fault (scorecard 2026-11-17, `L_toat_machine_hat`, pins near x 47.5, y 35.0 and x 48, y 39.5 mm):
the h's tall stem looks built from offset segments with steps and a split along its left edge.
**No fix is shipped.** This note names the stage and the dead ends, so the next session starts at the cause.
Pictures show our render and the original art only (no professional's file, per `tests/test_no_new_pro_renders`).

## Still there on current main

Yes. `docs/renders/toat-h-stem-2026-11-18/01_original_vs_ours_B2.png` (original | ours, 30 px/mm): the art's stem is one
smooth slanted brush stroke; ours has a left-edge step at about y 34.6 mm and a second at about y 38.8 mm, with a
white seam across the column at each.

## What `satin_thin_arm_stop` did to it: neither better nor worse

`02_thin_arm_stop_and_other_flags.png`, left to right: main (flag ON), `satin_thin_arm_stop` OFF, and three flags that
looked like candidates. The stem body and both steps are identical with the flag ON and OFF; the only difference is
the stem's top cap (OFF: 106 more stitches in the whole design, a flatter top). `satin_rails_follow_edge=False`,
`satin_patch_junctions="satin"` and `satin_junction_square` leave the stem unchanged.

## The stage

The stem is NOT sewn by `stage6_satin.satin_stroke`. That call runs only in stage 7's lane-OFF ordering pass. The plan's
stem comes from the Column lane: `column_runs` (columns.py) receives **one `curved` column of 61 stations** for it
(built in `outline_cut.py`), with rails cut on the artwork outline and then pushed by the pull.

Station widths of that column before pull, every third station, bottom to top: 0.26, 1.7, 2.36, 2.3, 2.5, **3.16, 3.18,
3.32**, **2.34**, 2.35, 2.45 ... 3.2, 2.72, 1.63, 0.3. For about 10 stations (3.7 mm of stem) the column is 0.7-0.9 mm
wider, with the width stepping within one to three stations at each end. That stretch is where the c's tail comes in from
the left and the arch's hairline leaves on the right: the **art's own ink widens there** (the merge), and the lane sews
the whole merge as part of the stem column. The picture `04_columns_over_art.png` shows the stem column (blue) over the art,
the c tail run (red) and the arch run (green) meeting it. `03_stem_run_alone.png` (left) is the stem column with
nothing else sewn: the steps are in this one column, not in a seam between separate pieces, and not from the
c-tail run crossing it.

The pro's stem (beanie file, viewed only) is a single constant-width column from top to foot, with the c's tail and the
arch's hairline as their own columns overlapping it.

## Dead ends (each measured, none is the cause)

- **Gap hold of the rail push (`satin_push_keeps_gaps` 0.5).** It does cut the push in one-station notches in the
  satin tier (width 2.09 among 2.6 neighbours), but those are in the ordering pass; the lane's stem never reads them.
- **Envelope reach (`satin_rails_follow_edge="envelope"`).** Rails are identical with it off (0.0 mm).
- **A width ramp, a lone-hold filter and a bulge cap in `stage6_satin._rail_points`** were built and measured. They
  change the lane-OFF pass only (the final stem was byte-identical, in a fresh process too) and were dropped.

## Where a fix belongs, and what it needs

A cap of the stem column's width where a sibling stroke meets it (the merge belongs to the meeting arms' columns, which
already overlap it), in the station cut of the `curved` column in `outline_cut.py`. A rule of that shape was
prototyped in `_rail_points` (opening the half-width profile over 5 mm, only beside a sibling spine, and keeping
the far-edge reach from widening it back); porting it needs the lane's own stations and then the full evidence
protocol (the 9 committed pro jobs and the 26 corpus fixtures, flag OFF against ON, stitches md5, a picture for
every mover). Not done here: 70 digitize runs do not fit the time given.
