# Long needle-down steps between pieces of one shape (2026-11-07)

`docs/float-census-2026-11-06.md` found that on Becker most of the "uncut"
moves were not floats. They were **long-stitch encodings**: a needle-down
step longer than a DST record holds (`machine.MAX_STITCH_MM`, 12.1 mm),
13.8-16.7 mm into underlay and 34.4-37.5 mm into fill, inside shapes
S92f2350b, Sd86ce3cb and S118e45fc. The writer flies each one as jump
records with the thread uncut. The census put the cause in a stage 6 site
that never calls `stitches.split_long_moves`. This page traces the site,
builds the fix OFF, and measures it on the 18 pairs.
**No default moves and no constant is added.**

## The site: stage 7, not stage 6

Traced by wrapping `stage6_fill.stitch_shape` during a Becker hat plan
(101.9 mm). The long step sits BETWEEN two runs of S92f2350b, with
`jump` False on the second. The two runs come from two separate
`stitch_shape` calls, both made at one site:
`stage7_sequence.sequence -> stitch_one`, in `border_from_outline`'s
branch (default ON since 10-24). That branch sews the outline's own body
fill as one `stitch_shape` call per `keyline_rest` piece and joins the
calls with `o_runs += f_runs`. `stitch_shape` returns its first run
needle-down, because the step INTO a shape is the caller's job. Here the
caller never takes that step, so a step from one disjoint piece to the next
(15.0 mm into the second piece's underlay, 37.5 mm into the third piece's
fill) goes out as one unsplit stitch. `enclosed_white_keyline`'s branch
(`k_runs += f_runs`) has the same pattern.

Every stage 6 emitter splits its own paths. The gap is in the join.

## The fix: `cfg.extra["split_long_inshape_stitches"]` (built OFF)

`stage7_sequence.join_piece` runs before each concatenation in both
branches. A step longer than `machine.MAX_STITCH_MM` goes through
`stitches.split_long_moves(..., machine.MAX_STITCH_MM)`, and its inner
points become a TRAVEL run of the same shape, carrying the next piece's
`shade_thread_index`. That is the same shape `_chain` uses for a buried
link. The thread lies on the line the machine already flew, now tacked
down. No lift is added and no plan trim is added. A step that already fits,
a run the callee lifted, or an empty side leaves the runs untouched. OFF,
the flag is read once and nothing else runs.

Tests: `digitizer/tests/test_split_long_inshape.py` covers:

- `join_piece` on synthetic runs: equal steps at the ceiling, on the
  straight line, with each no-op case;
- `border_from_outline`, using `test_border_from_outline`'s face, with its
  rest strip cut into two pieces 24 mm apart (Becker's pieces are disjoint);
- `enclosed_white_keyline`, using `test_enclosed_white_keyline`'s
  two-tab band (pieces 37 mm apart, no patching).

In each case OFF has the long step and ON has none. ON equals OFF plus one
TRAVEL run per long step, with the same jumps and the same trims.
OFF-with-false equals the key left absent.

## Measured: 18 pairs, OFF vs ON, off the same stage 0-4 pickles

`tools.float_census gen` on this laptop (head `f0c59035`), one job at a
time. Stages 5-7 were planned three ways: main's `digitizer_core` (a
detached worktree of `f0c59035`), this branch OFF, and this branch ON.
"Long-stitch" is `float_census.dst_moves`' `uncut_long` count, read from
each DST. "Longest step" is the longest needle-down step in the plan,
including the step into a run that is not a jump.

| job | OFF = main (DST md5) | long-stitch OFF -> ON | DST cuts OFF / ON | uncut OFF -> ON | longest step mm OFF -> ON | stitches OFF -> ON | exposed mm OFF -> ON | bare mm @0.20 OFF -> ON |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | same `d9842ade` | 2 -> 0 | 11 / 11 | 2 -> 0 | 37.45 -> 10.38 | 16262 -> 16266 | 23.1 -> 35.9 | 0.1 -> 3.02 |
| becker_lc_large | same `86b3937d` | 2 -> 0 | 12 / 12 | 2 -> 0 | 34.44 -> 11.48 | 14922 -> 14925 | 31.1 -> 38.6 | 0.4 -> 2.82 |
| becker_hat_small | same `2bee93ac` | 1 -> 0 | 11 / 11 | 4 -> 3 | 13.77 -> 6.89 | 10546 -> 10547 | 21.7 -> 21.7 | 4.61 -> 4.61 |
| becker_chest_small | same `bcd45933` | 1 -> 0 | 11 / 11 | 4 -> 3 | 13.77 -> 6.89 | 10309 -> 10310 | 21.3 -> 21.3 | 4.82 -> 4.82 |
| becker_hat_smaller | same `d9842ade` | 2 -> 0 | 11 / 11 | 2 -> 0 | 37.45 -> 10.38 | 16262 -> 16266 | 23.1 -> 35.9 | 0.1 -> 3.02 |
| becker_beanie | same `4bff92b2` | 1 -> 0 | 14 / 14 | 3 -> 2 | 14.47 -> 7.24 | 13864 -> 13865 | 38.6 -> 38.6 | 3.72 -> 3.72 |
| mfab_hat | same `8c6ddc56` | 0 -> 0 | **27 / 25** | 13 -> 13 | 46.06 -> 11.52 | 21200 -> 21206 | 8.7 -> 14.7 | 0.0 -> 0.0 |
| mfab_lc | same `6777c8d2` | 1 -> 0 | **28 / 27** | 18 -> 17 | 58.13 -> 11.63 | 18562 -> 18567 | 13.3 -> 27.8 | 0.0 -> 0.1 |
| gaulke_roofing_hat | same `d5132aa0` | 0 -> 0 | 32 / 32 | 12 -> 12 | 4.89 -> 4.89 | 7413 -> 7413 | 15.6 -> 15.6 | 9.2 -> 9.2 |
| gaulke_roofing_lc | same `0b36038b` | 0 -> 0 | 23 / 23 | 23 -> 23 | 5.0 -> 5.0 | 5778 -> 5778 | 10.7 -> 10.7 | 7.22 -> 7.22 |
| hotel_fremont_hat | same `fc956855` | 0 -> 0 | 25 / 25 | 148 -> 148 | 4.22 -> 4.22 | 15866 -> 15866 | 9.1 -> 9.1 | 0.0 -> 0.0 |
| hotel_fremont_patch | same `fe4c59e6` | 0 -> 0 | 20 / 20 | 152 -> 152 | 4.22 -> 4.22 | 14858 -> 14858 | 12.4 -> 12.4 | 0.0 -> 0.0 |
| precision_drone | same `f906554d` | 0 -> 0 | 86 / 86 | 28 -> 28 | 4.55 -> 4.55 | 14769 -> 14769 | 22.0 -> 22.0 | 2.54 -> 2.54 |
| tires_hat_3d | same `caf8701a` | 0 -> 0 | 3 / 3 | 0 -> 0 | 4.34 -> 4.34 | 4544 -> 4544 | 13.2 -> 13.2 | 9.03 -> 9.03 |
| bridge_hat | same `1f3be834` | 0 -> 0 | 9 / 9 | 8 -> 8 | 4.91 -> 4.91 | 8517 -> 8517 | 8.4 -> 8.4 | 0.0 -> 0.0 |
| bridge_lc | same `42f77c4d` | 0 -> 0 | 9 / 9 | 7 -> 7 | 4.73 -> 4.73 | 10950 -> 10950 | 10.7 -> 10.7 | 0.0 -> 0.0 |
| proseal_hat | same `633955d6` | 0 -> 0 | 44 / 44 | 34 -> 34 | 4.76 -> 4.76 | 6304 -> 6304 | 16.7 -> 16.7 | 1.44 -> 1.44 |
| proseal_beanie | same `587eead4` | 0 -> 0 | 36 / 36 | 31 -> 31 | 3.98 -> 3.98 | 7671 -> 7671 | 143.2 -> 143.2 | 54.05 -> 54.05 |

Reading it:

- **OFF matches main byte for byte on 18 of 18** (DST md5). ON moves 8
  of the 18 cells and leaves the other 10 byte-identical. Those 10 have no
  step past the ceiling anywhere in the plan.
- **Long-stitch encodings fall 10 -> 0** across the 18 cells. Becker
  accounts for 9 of them (2 + 2 + 1 + 1 + 2 + beanie 1) and MFab LC for 1.
  The longest needle-down step anywhere in any of the 18 plans is
  11.63 mm with ON, against 58.13 OFF.
- **Becker's DST cuts are unchanged** (11 / 12 / 11 / 11 / 11 / 14). That
  is the done-test. Plan trims are unchanged on every job.
- **MFab's DST cuts fall by 2 (hat) and 1 (LC)** even though plan trims do
  not move (28 / 30 both arms). OFF, the 38.9-58.1 mm steps into
  underlay (shapes Sfbae5fe3 and S41ffffe3) were long enough that the DST writer's run of jump
  records reads as a TRIM (`dst_moves` counts it as a cut). With ON they
  are sewn travel instead. That travel lies 72-91% under thread sewn
  after it, and the rest lies on thread already sewn (100% of it is on
  thread). MFab moves toward the pro's count here (18 / 19 cuts).
- **Exposed travel and bare thread rise on the two large Becker jobs, and
  this is not new thread.** `travel_cover` and `bare_by_band` skip flights
  by design, so OFF's 37 mm flight never appears in either. ON turns the
  same line into needle-down travel, and the instruments see it for the
  first time. On Becker the line is 39-54% on its own shape's thread,
  92-100% on some thread, and 39-47% under thread sewn after it. Where a
  stretch of it lies on cloth, it lay there OFF too, as an untacked float.
- **Preflight's `STITCHES_TOO_LONG` reads 0 in both arms on all 18.** It
  counts steps inside a run only, so it never saw these steps in the
  first place. "Too-long to 0" was already true OFF, but only because the
  instrument has this blind spot. It is not a result of the fix.
  Widening it to the step into a run that is not a jump would raise a warn
  on 6 Becker cells and both MFab cells on today's default path. That
  changes a default, so it is not built here.

## `default_path_diff`

`python -m tools.default_path_diff --base-ref origin/main` was run on the
same laptop, once as plain OFF and once with
`--set split_long_inshape_stitches=true`. Results are in the PR body.
