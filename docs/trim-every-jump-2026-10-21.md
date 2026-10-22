# No uncut jumps: `cfg.trim_every_jump` (built OFF, 2026-10-21)

Follows the settings audit (`docs/settings-vs-pro-2026-10-21.md`, row 25):
the professional leaves **no** needle-up move uncut in any of his 28 DSTs,
and we left 0-171 per job. Kent picked this build on 2026-10-21.

## What an uncut jump is, and where ours came from

A jump moves the needle without a penetration. With no trim, the thread
still runs from the last stitch to the next one, lying on top of the
fabric, and it can pull into a loop. Kent's 2026-10-20 test card showed
loops at the start and end of the tagline copies. These jumps may be the
cause, but no sew-out has tied the two together.

Stage 6 and stage 7 decide jump vs trim at about thirty sites, all with
the same rule: a hop longer than `fabric.trim_at_mm` (3.0 mm on hat, LC and
beanie) is cut, and a shorter one is left as a bare jump. On Fremont at
81 mm, 141 of the 166 uncut jumps are run-to-run hops under 2 mm between
small-text strokes. Of the rest, 13 are fill-to-fill lifts inside one
shape, 8 leave a satin and 1 is a run-to-travel hop. (3 run-to-run hops are 2 mm or longer.)

## The rule

With the flag on, `stitches.cut_every_jump` runs once, after everything
else in stage 7 (and on the knockdown block, which is built later). It
handles every run that is still a jump with no trim inside a colour block:

- **Hop no longer than one run stitch (`RUN_STITCH_MM`, 2.0 mm): sewn
  needle-down, as that one stitch.** It lays the same thread, along the same
  straight line, as the uncut jump already did. The difference is that the
  thread is tight. This adds no visible thread that the default does not
  already lay.
- **Longer: cut**, and locked on both sides by `apply_ties`' own rule (the
  run before is tied off and the run is tied in).

Needle-down travel (travel under cover, `trim_bury_under_later`, chaining,
links inside a shape) is not a jump, so it is not touched. A block's first
run is a colour stop, and it is not touched either.

**Why not cut them all.** That was the first build. It took Fremont 81 from
38 trims to **204**, while the pro uses 20. The pro does not cut hops this
short: his shortest cut is 1.99-4.7 mm on these jobs and 1.4-4.6 mm across
all 28 files. Cutting a 0.7 mm hop costs a cutter cycle and two locks to
remove thread that is shorter than one stitch. No new constant was needed,
because a hop up to one run stitch is just a stitch.

## Measured

`digitizer/tools/uncut_jumps.py` (new) reads the **raw DST records** on both
sides. A move with three or more jump records is a cut (the Tajima
convention, and the one pystitch's writer follows). One or two records is an
uncut jump. Note that `pystitch.read` folds a run of jump records into a
single JUMP, so reading through it makes every move look uncut. Ours was
digitized the way the Studio sends it (`tools/pro_pair.digitize`) at the
pro's width, on a hat.

| job | mm | uncut off → on | trims off → on | pro trims | stitches off → on | uncut off by bin (0.5-1 / 1-2 / 2-3 / 3-6) |
|---|---|---|---|---|---|---|
| Fremont hat | 81 | 166 → **0** | 38 → 48 | 20 | 15,281 → 15,361 | 117 / 39 / 10 / 0 |
| Fremont hat | 92.5 | 171 → **0** | 51 → 68 | 20 | 18,611 → 18,747 | 29 / 124 / 17 / 1 |
| Drone | 62.6 | 55 → **0** | 112 → 134 | 58 | 14,802 → 14,978 | 7 / 25 / 22 / 1 |
| Becker large | 101.9 | 0 → 0 | 27 → 27 | 9 | 9,411 → 9,411 | — |
| Becker small | 76.5 | 1 → **0** | 15 → 15 | 10 | 5,928 → 5,928 | 0 / 1 / 0 / 0 |
| Golden Tee | 74.9 | 10 → **0** | 30 → 36 | 9 | 8,339 → 8,387 | 1 / 3 / 6 / 0 |

The pro has 0 uncut jumps in all five of his files (`HOTEL FREMONT HAT`,
`PRECISION DRON HAT 2`, `beckers logo hat`, `beckers logo hat 2 A`,
`GOLF HAT`). Our shortest cut with the flag on is 2.06-3.81 mm, against his
1.99-4.70.

The two hops in the "3-6" bin measure 3.002 mm (Fremont 92.5) and
3.041 mm (Drone) in the file. Both are on `trim_at`'s 3.0 edge, after
rounding to the DST's 0.1 mm grid. The flag cuts them like any other hop
over 2 mm.

**Cost.** Each extra trim is a cutter cycle on the machine (thread cut,
pull, re-start), plus two locks of 4 points each. The machine time per trim
is not measured here. Fremont 92.5 gains 17 trims and Drone gains 22.
Becker gains none. The stitch counts above include the locks. Our trim
count was already above the pro's before the flag (the trim-economy study,
`docs/trim-economy-2026-10-21.md`, covers why). This flag does not close
that gap. It removes the uncut jumps and adds the fewest cuts that doing so
requires.

**OFF is byte-identical.** The `ours.dst` md5 is the same before and after
on all six jobs, against an extract of the base commit `03ccab4e`. Three
fixture md5s are pinned in `tests/test_trim_every_jump.py`.

## Open, and Kent's

- **Flip.** The sewn-down hops lay no thread the default does not already
  lay. But they are needle-down thread on what may be bare fabric, and
  gate 3 in ROADMAP exists because a green suite once hid exactly that. The
  cut half is plain trimming.
- **The browser engine has the same rule** (`src/digitize.js:1143-1146`,
  `:2033`): it trims past `trimAtMm` and jumps otherwise. Its DST writer
  already writes a trim as three or more jump records. It is not changed
  here.
- Whether these jumps were the loops on the 2026-10-20 test card is a
  sew-out question.
