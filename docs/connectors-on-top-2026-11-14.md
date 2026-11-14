# Connectors on top of finished satin (2026-11-14)

Kent pinned "Random Cross over stitch shouldn't be here" four times on Becker
hat large. Two of those pins (#0, #1) were the long needle-down joins fixed
by `inshape_piece_lift` (#1483). This page covers the other two (#14 @89.02,62.82
and #15 @95.43,50.74), and MFab hat #2 ("This random stitch in the middle
doesnt match the pros", @69.99,16.77).

## #14 and #15: the Column lane's connector, sewn after the satin it crosses

Both pins sit on MARINE's E. On each, a running connector of 6.2 and 9.3 mm
(travel, ~1.6-1.9 mm steps) goes from the end of one arm's satin to the start
of the next leg. It is sewn after that arm, across its finished satin: 5.9
and 5.8 mm of it lie on top.

The cause is in `columns.column_runs`:
- A satin leg's zigzag ends on its last cross's b rail.
- The hop to the next leg's first centre point starts there, and on these
  arms that rail is the far side of the stroke from the next leg. The hop
  runs back across the stroke just sewn.
- The link rule (step 4) accepts a hop "inside the letter" and calls it
  "under thread sewn later". It never checks that later thread does cover
  it. Its buried-path branch allows up to `allow` (max(trim_at, 2 stroke
  widths), several mm) not under later satin.

### How often, and what the pro does

Instrument: a stitch-list rule that reads ours and the pro's DST alike. A run
of two or more straight short stitches (0.3-3 mm, turning under 40 deg) is
"running". A stroke that reverses over 120 deg at both ends is "satin". The
measure is how much of each running run lies on satin sewn before it with
no thread sewn after it. Raster at 20 px/mm, thread 0.4 mm, stretches under
0.4 mm dropped. On Becker hat large it finds exactly #15 and #14 as the two
largest.

| | ours (default config) | the pro's file |
|---|---|---|
| Becker x5 | 5.5-8.7 mm, 2-4 runs each | 0 on four; 1.0 mm on LC large |
| MFab hat / LC | 12.3 / 4.2 mm | 0 / 0 |
| Bridge x2, Gaulke x3, Fremont x2, Golden Tee, To-a-T x3, Tires | 0-27 mm | 0 on all but Fremont hat (0.9 mm) |
| ProSeal hat / beanie | 18.9 / 2.4 mm | 26.3 / 18.1 mm |
| Drone | 6.0 mm | 230 mm |
| lettering logos (k_line, and_pizza, jakarta, ...) | 0-6.9 mm | (no pro file) |

On the pro's three exceptions, read by eye:
- **Drone:** outline detail, sewn as running stitch on purpose.
- **ProSeal:** a short run along the edge of a stroke, not across it.

At Becker's E (the one join compared by eye) the pro's running stitch is
each arm's centre run, sewn before its satin and covered by it
(`connectors/becker_hat_large_pro_join.png`).

A kind-aware count over our own runs agrees: travel left on the letter's own
finished thread, in lettering shapes, is 15.8-26.0 mm per Becker job and
268 mm over the 28 lettering designs.

## The fix: `cfg.lettering_columns_connectors_buried` (built OFF)

In `column_runs`, two steps:
1. **Which rail a leg ends on.** Each satin leg followed by another leg ends
   on the rail whose hop to the next leg lies less on satin already sewn
   and not under satin still to come. It changes only for a hop at least
   0.05 mm less on top, so a letter with nothing on top keeps its walk.
   This alone fixes the E, with no trim.
2. **What is still on top** (`_connectors_under`, after the link rule). A
   travel run, or the needle-down step into a run, that still lies more
   than `_ON_TOP_MAX_MM` (1.0 mm) on finished satin:
   - is walked along the centrelines over ground clear of finished satin
     or under satin still to come, if such a walk exists;
   - otherwise is cut: the next run starts with a jump and a trim. A jump
     alone would still lay the thread across.

1.0 mm is the most the pro leaves on Becker LC and the Fremont hat (0.97,
0.9 mm). OFF, the walk is byte-identical (the flag is read only inside
`column_runs`).

## OFF | ON, 28 lettering designs (full digitize, one at a time)

OFF = the d0b4981a captures of the apex-cut corpus. They are byte-identical
to this branch OFF (lt_k_line md5 checked); every PR between the two trees
is built OFF or render-only.

| design | letters' travel on finished thread, mm | trims | stitches |
|---|---|---|---|
| becker_hat_large | 15.8 -> 0 | 12 -> 14 | 16289 -> 16287 |
| becker_lc_large | 26.0 -> 2.9 | 13 -> 16 | 14951 -> 14957 |
| becker_hat_small | 21.4 -> 2.8 | 12 -> 15 | 10576 -> 10583 |
| becker_chest_small | 21.3 -> 2.8 | 12 -> 15 | 10339 -> 10346 |
| becker_beanie | 24.5 -> 3.1 | 16 -> 19 | 13902 -> 13908 |
| mfab_hat | 9.4 -> 0 | 17 -> 22 | 20849 -> 20846 |
| mfab_lc | 5.9 -> 1.4 | 20 -> 24 | 17897 -> 17915 |
| bridge_hat | 2.2 -> 1.7 | 12 -> 13 | 8569 -> 8574 |
| bridge_lc | 8.2 -> 1.2 | 13 -> 16 | 10998 -> 11010 |
| gaulke_roofing_hat | 11.8 -> 0 | 33 -> 35 | 7494 -> 7471 |
| gaulke_roofing_lc | 11.8 -> 1.5 | 24 -> 29 | 5852 -> 5870 |
| gaulke_roofing_beanie | 8.2 -> 1.7 | 26 -> 27 | 7679 -> 7655 |
| hotel_fremont_hat | 14.0 -> 0.9 | 28 -> 28 | 16106 -> 16107 |
| hotel_fremont_patch | 10.2 -> 7.0 | 23 -> 23 | 15061 -> 15060 |
| precision_drone | 8.6 -> 1.4 | 93 -> 93 | 14984 -> 14979 |
| proseal_hat | 10.6 -> 5.2 | 46 -> 48 | 6434 -> 6440 |
| proseal_beanie | 4.6 -> 2.9 | 39 -> 40 | 7785 -> 7790 |
| goldentee_hat | 1.6 -> 0.8 | 45 -> 45 | 13636 -> 13633 |
| lt_and_pizza | 11.0 -> 0 | 5 -> 7 | 2454 -> 2385 |
| lt_k_line | 9.7 -> 0 | 10 -> 14 | 3372 -> 3382 |
| lt_jakarta | 15.6 -> 4.2 | 22 -> 27 | 2966 -> 2990 |
| lt_bukit_asam | 6.6 -> 2.4 | 10 -> 11 | 2046 -> 2065 |
| lt_dot_music | 7.4 -> 0 | 5 -> 5 | 1529 -> 1526 |
| lt_n_sync | 1.7 -> 0.3 | 2 -> 2 | 2479 -> 2478 |
| lt_ahora, lt_but_seriously, lt_hed_p_e, toat_machine_hat | unchanged (md5 same) | | |

**Totals:**
- Letters' travel on finished thread: 268 -> 44 mm. The rest is hops under
  the 1.0 mm limit, adding up.
- Trims: **+50 over the 24 moved designs** (+1.8 each, at most +5).
- Exposed travel on bare fabric: 0 -> 0 everywhere (dot_music 0.4 -> 0,
  proseal_hat 0 -> 0.1).

Against the pro's own trims:
- Becker hat large: pro 10, ours 12 -> 14.
- Becker LC: pro 12, ours 13 -> 16.
- MFab hat: pro 19, ours 17 -> 22.
- MFab LC: pro 20, ours 20 -> 24.

By eye (sheets in the primary checkout, gitignored,
`digitizer/eye_pairs_out/jag-source-1113/connectors/sheets/`):
- **Pins #14 and #15** (`becker_hat_large_x14_offon.png`, `_x15_`): the
  diagonal thread across the E's arm is gone ON. Nothing else moves there.
- **Becker LC:** the long diagonal thread across the M's top and a short
  one across a stroke are gone.
- **k_line, Gaulke, Fremont, MFab:** read the same lit; the change is in
  sew order and where the needle travels.
- **Jakarta:** the 'a' gains a hairline notch at its counter (slight).

**md5.** OFF is byte-identical: `tests/test_column_connectors_buried.py` and
the Column lane's OFF pins (`OFF_LANE_MD5`) hold. Flipped ON:
- the flat-lane golden fixtures (`FLAT_GOLDEN_MD5`: logo_alpha, whitebg,
  ribbon_curve) do not move, in the golden's config or the default one;
- `becker_marine_logo.png` moves in both;
- the nightly tripwire's Becker and MFab rows would move.

## MFab #2: not a connector

At the pin is MFab's small white triangle, a `sew_enclosed_white` counter
("counter_in_field"):
- Ours sews it as a fill, then a closed 33.5 mm **bean** loop 0.85 mm
  inside the triangle's edge (half `machine.BORDER_WIDTH_MM`), on top. That
  loop is what reads as a random stitch in the middle.
- MFab classes `photo_scene`, so `border_style` is "significant" and the
  border tier rings the triangle. At 3.35 mm across it cannot host a 1.7 mm
  column, so the tier lightens the ring to bean (`stage6_border`).
- The pro sews the triangle as one fanned satin, with no ring.

Not fixed here. The next step would be to leave a ring off a shape too
narrow to host its column, rather than lighten it to a bean inside the fill.

## Not done

- Rerouting under satin still to come never fired on Becker's letters.
  Every hop the rail choice could not clear was cut. Walking along the
  finished stroke's edge, as the pro does on ProSeal, would save most of
  the +50 trims. Not built.
- Script words (`script_strokes`) call `column_runs` without the flag.
