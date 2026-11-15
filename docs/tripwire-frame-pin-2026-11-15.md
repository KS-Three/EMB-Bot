# Tripwire frame pin (ON since 2026-11-15)

*(built 2026-11-15 on Kent's ruling "Pin tripwire frame (Recommended)" (#1572, OFF); flipped ON the same day on his ruling "Flip ON now (Recommended)": the scheduled nightly passes `--pin-frame`, and the ledger's `frames` come from a five-pass CI capture with `pin_frame` ticked (see "Flipped" at the end). Laptop measurements here are for design and tests only.)*

## Why

`docs/corner-fold-kappa-2026-11-15.md` found the tripwire's kappa rows move by up to ±0.05 when an engine change shifts our outline by a sliver, with no stitch-type change.

- `scorecard.register` hill-climbs solid IoU, and the surface is flat: 0.896-0.902 across 0.75 mm on becker_hat_large.
- A 0.1 mm change lands the climb up to 0.55 mm elsewhere, and the 2 mm cell grid both kappas are read on moves with it.
- The five capture passes write one DST and so agree on the registration; every kappa row then carries tolerance 0.00.

Kent chose option B of four: pin the frame per job in the tripwire's ledger.

## What it does (OFF unless asked)

- **`scorecard.score_design(dirpath, explain=False, frame=None)`.**
  - `None` is the original code path, unchanged (`test_with_no_frame_the_score_is_the_original_path`).
  - `{}` registers as usual and reports the frame in `detail["frame"]`.
  - A pin `{dx, dy, x0, y0}` scores ours at that shift on that grid origin. `pinned_bounds` steps the origin out by whole 2 mm cells when the design now reaches past it, so the grid keeps the pin's phase and nothing is clipped.
  - It re-registers only when a fresh climb beats the IoU at the pin by more than `PIN_MARGIN`.
- **`tools/tripwire.py --pin-frame`.**
  - `measure` re-reads both kappas through `pin_kappas` and records each job's frame in the pass.
  - `capture` writes `frames` (pass 1's frame per job, plus `passes_agree`) into the ledger when every pass carries frames.
  - `check` scores at the ledger's pins and prints one line: how many jobs were pinned, re-registered or freshly registered.
  - A ledger without `frames` still loads, and a pinned check against it registers fresh and says so.
- **`nightly-tripwire.yml` gains a `pin_frame` dispatch input, default false.** The schedule never sets it, so the nightly's commands, outputs and ledger are unchanged until Kent flips it.

## The margin: `PIN_MARGIN = 0.01` IoU

| measured | IoU gap |
|---|---|
| becker_hat_large plateau, 0.75 mm of dy | ≤ 0.006 |
| the corner fold's 0.55 mm re-registration | 0.001 |
| a real 0.5 mm move, read at the old pin (Becker x3, Gaulke hat, MFab hat) | 0.014-0.044 (hat_small 0.015) |
| a real 1 mm move | 0.028-0.117 |
| a real 3 mm move | 0.082-0.282 |

So 0.01 keeps every re-pick on the plateau and re-registers any real move of about 0.5 mm or more. A move smaller than that is read at the pin, off by under half a millimetre, which is less than the plateau already spans.

## Tests

- **`tests/test_tripwire_frame_pin.py`** (real data, about 100 s: one build, one finish, two plans).
  - The pair is becker_hat_small with the corner fold OFF and ON, against the pro's DST in `testdata/reference/`. That file is byte-identical to the zip member, so the test reads nothing outside `digitizer/` and is not a wire test (still 79).
  - The default path is unchanged.
  - Pinned, the fold reads within 0.015 on both kappas; its one-frame figures are −0.008 and +0.008, against an own-registration swing of −0.054.
  - The grid keeps the pin's phase.
  - A design moved 3 mm re-registers and scores exactly as unpinned.
  - `pinned_bounds` never clips.
- **`tests/test_tripwire.py`** (fast).
  - With the pin OFF, a ledger and a check are what they were.
  - Pinned passes give the ledger one frame per job, with `passes_agree`.
  - A malformed frame is refused; a ledger without frames loads.
  - The check names re-registered jobs.
  - The workflow passes `--pin-frame` only on a dispatch that asks.
  - `--help` lists the flag.

## What ON reads on the 18 jobs (local, attribution only)

The two arms are #1533's two flags OFF (`all_off`) and ON (`main`), from the 11-15 triage. Each is scored the way today's tripwire reads it (fresh registration per arm) and the way the pin would (both in the OFF arm's frame). Chance-corrected stitch-type kappa, OFF -> ON:

| job | registration OFF -> ON | fresh | pinned | direction, fresh / pinned |
|---|---|---|---|---|
| becker_hat_large | (0.35, 0.15) -> (0.35, −0.40) | 0.340 -> 0.292 (−0.048) | 0.340 -> 0.358 (+0.018) | −0.036 / +0.005 |
| becker_hat_small | (0.15, 0.40) -> (0.25, 0.25) | 0.557 -> 0.514 (−0.043) | 0.557 -> 0.560 (+0.003) | +0.007 / +0.005 |
| becker_lc_large | (0.35, −0.05) -> (0.35, 0.15) | 0.306 -> 0.337 (+0.031) | 0.306 -> 0.301 (−0.005) | +0.012 / −0.001 |
| becker_chest_small | (0.15, 0.45) -> (0.15, 0.40) | +0.010 | +0.000 | −0.007 / +0.003 |
| becker_beanie | unchanged | +0.005 | +0.005 | 0 / 0 |
| precision_drone | unchanged | −0.001 | **−0.015** | −0.002 / 0.000 |
| gaulke x3, fremont x2, goldentee, mfab x2, toat x3, tires | unchanged | same as pinned (−0.008 to +0.011) | same as fresh | same |

- Every ON arm was read **pinned**: the largest IoU gap to a fresh climb was 0.003, under the 0.01 margin.
- The largest stitch-type move falls from 0.048 fresh to 0.018 pinned.
- **The pin does not make a single reading more accurate; it makes two readings comparable.** On precision_drone the shift did not move, but our extents moved the fresh grid's origin. Pinned, the edge-walk change is read at one grid phase: −0.015 where the fresh pair, cut on two phases, happened to read −0.001.
- With the pin ON, a kappa row still carries a single-phase reading, so the grid's aliasing (SD 0.02-0.04 over origins) remains in what a real change reads. What goes is the jump from a re-registration.

## What it does not do (Kent's accepted catch)

The pin stabilises **only the tripwire**. The corpus scorecard (`scorecard-capture.yml`), `tools.pro_pair`/`lane_census` kappas and every flip PR's ON-vs-OFF kappa still re-register per arm, so they can still swing ±0.05 for the same reason. Until something else changes, quote those deltas from one frame (memory `corner-fold-kappa-2026-11-15`).

A design that really moves less than ~0.5 mm is read at its old pin until the next capture.

## Flipping it (Kent's)

1. Dispatch `Nightly tripwire` in `capture` mode with `pin_frame` ticked. This takes five passes and gives a ledger with `frames`.
2. Commit that ledger.
3. Make the schedule pass the flag (`pin_frame` default true, or the expression replaced by `--pin-frame`).

## Flipped, 2026-11-15

Kent's ruling: **"Flip ON now (Recommended)"**.

- **Capture.** CI run 43772829964, `capture` mode with `pin_frame` ticked, five passes on `main` at `f095e1ab`.
  - The ledger artifact's sha256 is `ccac1b90…dc4007b070`, the same as printed in the capture log.
  - The committed ledger is those bytes plus `hand_edits`.
  - Frames for all 18 jobs, every one `passes_agree`.
- **Schedule.** The expression is `(github.event_name == 'schedule' || inputs.pin_frame) && '--pin-frame'`, and `pin_frame` defaults to true on a dispatch. Unticking it reads fresh again.
- **No baseline moved because of the pin.** The capture records each job's freshly registered frame, so each baseline is what the old reading gives on that tree.
  - The rows that did move are #1565's (Flip PR 2, Kent 2026-11-15), the only engine change since the last ledger besides #1571 (built OFF). They are listed in the flip PR.
- **The #1505 trap, again.** Five passes agreed on 12 rows that earlier five-pass captures measured moving between runners. Their tolerances are restored and recorded in the ledger's `hand_edits`, each with the run it was measured on (43754823644, or 43147117899 for three rows last seen moving there).
  - Evidence that 0 is false: check 43764055621, on an unchanged engine tree, read these rows 2-4 stitches and 0.004 stitch-type kappa off.
  - Left at 0: rows that moved only in the oldest 3-pass capture (42250031793) and never since.
- **Accepted catches, stated plainly.**
  - Baselines are now pinned readings, and each later engine PR is read in this frozen frame.
  - Single-phase grid aliasing (SD 0.02-0.04) remains in what a real change reads.
  - precision_drone showed a pinned read larger than the fresh one.
  - The corpus scorecard and flip-PR kappas still re-register per arm.
