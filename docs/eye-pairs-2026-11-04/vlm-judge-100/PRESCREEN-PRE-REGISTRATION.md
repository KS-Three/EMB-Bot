# The vision pre-screen: pre-registration, 2026-11-06

**A proposal for Kent, through the foreman. Not a build.** Nothing here changes
the engine, a flag, a route or a sitting. This file fixes, before anyone
computes it, how to test the one shape of a vision judge that the 11-04 read
pointed at (`../vlm-judge/RESULTS.md`, "What this licenses"): a **pre-screen**
that sorts eye pairs into "nothing to choose", "one side plainly damaged" and
"Kent has to look". Kappa is chance-corrected throughout (ROADMAP gate 4).

## Why a pre-screen and not a judge

The 11-04 session judge cleared chance on the 54 live pairs of
`pro-lettering-1102` (3-way kappa +0.36, CI pairs [+0.16, +0.55], designs
[+0.20, +0.45]), but its sides-only kappa on the 16 pairs both decided was no
evidence either way, and of Kent's 14 picks for the arm it tied 10. The
agreement is shared ties and shared "the base is plainly worse" calls. A
pre-screen claims only that: it settles the pairs where nothing is to be chosen
or one side is plainly broken, and leaves every other pair to Kent.

## The three classes, defined from the verdicts already on file

No new prompt and no new model call. Each class is a function of one verdict
row (`choice`, `confidence`), exactly as `vlm_judge record` writes it under the
pinned prompt (sha256
`24acb29674ecca4b045c176cbb00ac971512ef510d4a7bea69233ce1c928095a`):

| class | rule on the verdict row | the screen's claim, in Kent's frame |
|---|---|---|
| **nothing to choose** | `choice == "tie"` (any confidence) | Kent ties the pair |
| **plainly damaged** | `choice` is `L` or `R` and `confidence >= 4` | Kent picks the same side |
| **Kent has to look** | `choice` is `L` or `R` and `confidence <= 3` | no claim |

The threshold is **4 and only 4**. No sweep, no second threshold, no
per-fixture rule. A row with no choice (refusal, parse failure) is "Kent has
to look". The prompt's confidence scale is 1-5, so 4 is "more sure than not";
it is fixed here without looking at any per-pair confidence against Kent's
label.

## The data, and what is already known about it

1. **The 54 recorded pairs (primary).** `../vlm-judge/verdicts-claude-fable-5-1-session.jsonl`,
   the live pairs of `pro-lettering-1102` minus `P001`-`P003` (Amendment 1 of
   that file), Kent's picks in `docs/eye-pairs-2026-11-02/pro-size-lettering/picks.jsonl`.
   Those verdicts were written on 11-04, before this rule existed, by a
   different session, so the judge could not shape its confidence to it.
   **Already public:** the 3x3 Kent-by-judge table and the mean confidence
   (3.48). The tie class is therefore partly known (19 of the judge's 32
   live ties were Kent ties). **Not yet computed by anyone:** how the 22
   side picks split at confidence 4 and how each half lines up with Kent.
   The writer of this file has not opened that jsonl.
2. **The 99 pairs of `vlm-judge-100` (replication).** The verdicts this
   session is about to give under `PRE-REGISTRATION.md` Amendment 1. The judge
   writing them knows this rule (declared contamination: it could, without
   meaning to, push confidence on side picks up or down). Kent's labels there
   are the committed pooled ones; `both_bad` maps to tie per
   `pooled.VOCABULARY`. Scored once, after `RESULTS.md` for that run is on
   file.

Kent's sittings have no "damaged" label of their own: on 1102 he answered
L / R / tie only. "Plainly damaged" is scored against the side he chose; a
`both_bad` (pooled sittings only) counts as his tie, so a screen that calls
one side damaged where he called both bad is scored as a miss.

## The primary, one number

On the 54 recorded pairs, keep the pairs the screen **settles** (classes 1
and 2), map the screen's claim to `before` / `tie` / `after` through the
sealed side map (`vlm_judge.to_label`), and compute
`vlm_judge._kappas(rows)` on `(kent_label, screen_label, design)` rows:
the 3-way linear-weighted kappa with both percentile intervals (10,000
resamples, seed 20261104; pairs, and design clusters as `load_sitting`
defines them), n settled, read by `pooled.reading` (both intervals must clear
zero; under 10 settled pairs nothing is read). Reported with n settled and
n of 54, never as a share of agreement.

## Secondaries, reported whatever the primary says, promoted to nothing

- **Tie class alone:** binary kappa of "screen says nothing to choose" against
  "Kent tied", over all 54, both intervals, n.
- **Damaged class alone:** n, and the sides kappa on it if n >= 10 (else
  listed pair by pair with the judge's reason).
- **What is left for Kent:** n in "Kent has to look", and how many of Kent's
  side picks fall in it versus in the settled classes. This is a count of
  workload, not an agreement figure.
- **Identical controls:** every identical pair must land in "nothing to
  choose". One that does not is reported by id.
- **The replication:** the same primary and secondaries on the 99 pairs of
  `vlm-judge-100`, design cluster = fixture, with the contamination above
  printed beside it.

## Stopping rule

One computation on the 54, one on the 99, each run once and committed as
written. No re-threshold, no re-prompt, no subset hunt afterwards. If the
primary is not `above chance`, the pre-screen is recorded as not shown and
this line stops; a changed rule is a new dated pre-registration, never pooled
with this one. If the 99-pair replication disagrees with the primary in
reading, both are reported and nothing is proposed.

## What it licenses, and what it must NOT be used for

- **If the primary and the replication are both `above chance`:** a
  proposal to Kent for a **display-only** row on the eye-pairs page that
  shows the screen's class beside each pair. Kent still sees and labels every
  pair. Whether to build it is his call.
- **Never:** routing a design, choosing a lane, flipping or holding a flag,
  gating a PR, a tripwire or a sew-out, dropping a pair from a sitting before
  Kent sees it, pooling the screen's classes with Kent's labels, or any claim
  about engine quality. Under ROADMAP gate 3 a flag stays where it is until
  its own instrument is rebuilt; this screen is not that instrument.
- No API spend is licensed by this file. The registered API arms of
  `../vlm-judge/PRE-REGISTRATION.md` stay as registered there.

## Cost

Docs and arithmetic only: one `_kappas` call per read over verdict and pick
files already committed (or about to be). No render, no model call.

## Amendments

None. Any amendment is dated here before the step it affects.
