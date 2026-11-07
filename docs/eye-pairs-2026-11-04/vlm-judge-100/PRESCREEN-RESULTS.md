# The vision pre-screen: results, 2026-11-06

Computed once, exactly as `PRESCREEN-PRE-REGISTRATION.md` fixes it. Kent's
call, 2026-11-06, was "Compute pre-screen pre-reg (Recommended)".

- **Command:** `python -m tools.eye_pairs.vlm_prescreen`.
- **Output:** `prescreen.json`.
- **Rules:** no rule, threshold or data set was changed. The tool
  (`digitizer/tools/eye_pairs/vlm_prescreen.py`) is the pre-registration's
  arithmetic, and `tests/test_vlm_prescreen.py` pins its threshold to that
  file.
- **No new judging:** no render, no model call, no new verdict.
- **Gate 4:** kappa is chance-corrected throughout. Counts below are
  workload or tables, never an agreement share.

**This file judges nothing about the engine and flips nothing.**

## The rule (unchanged)

| class | rule on the verdict row | the screen's claim |
|---|---|---|
| nothing to choose | `choice == "tie"` | Kent ties the pair |
| plainly damaged | `choice` L or R, `confidence >= 4` | Kent picks the same side |
| Kent has to look | `choice` L or R, `confidence <= 3`, or no choice | no claim |

## The primary: the 11-04 judge's 54 recorded pairs

The data is the `claude-fable-5-1-session` verdicts on `pro-lettering-1102`,
excluding P001-P003, scored against Kent's picks. The verdicts were written on
11-04, before this rule existed.

| scope | n settled | of n | kappa, ties in | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|
| settled pairs (classes 1 + 2) | 39 | 54 | **+0.39** | [+0.15, +0.59] | [+0.23, +0.52] | **above chance** |

Kent (rows) against the screen (columns), settled pairs only, before / tie / after:

| | before | tie | after |
|---|---|---|---|
| **before** | 6 | 3 | 0 |
| **tie** | 1 | 19 | 0 |
| **after** | 0 | 10 | 0 |

## The replication: the 99 pairs of `vlm-judge-100`

**Contamination, declared as pre-registered.** The judge that wrote these 99
verdicts (`claude-opus-5-5-session`) had written this rule before judging. It
could, without meaning to, have pushed confidence on side picks up or down.

| scope | n settled | of n | kappa, ties in | CI pairs | CI designs (fixture) | reading |
|---|---|---|---|---|---|---|
| settled pairs (classes 1 + 2) | 67 | 99 | **+0.29** | [+0.07, +0.50] | [+0.11, +0.45] | **above chance** |

| | before | tie | after |
|---|---|---|---|
| **before** | 3 | 4 | 0 |
| **tie** | 0 | 43 | 0 |
| **after** | 1 | 14 | 2 |

The primary and the replication agree in reading. Under the stopping rule,
that is the condition for the proposal below.

## Secondaries (reported whatever the primary says, promoted to nothing)

### Tie class alone

This is a binary kappa: "screen says nothing to choose" against "Kent
tied", over all live pairs.

| set | n | kappa | CI pairs | CI designs | reading | Kent decided: screen not tie / tie | Kent tied: screen not tie / tie |
|---|---|---|---|---|---|---|---|
| 54 (primary) | 54 | +0.31 | [+0.05, +0.55] | [+0.09, +0.45] | above chance | 16 / 13 | 6 / 19 |
| 99 (replication) | 99 | +0.28 | [+0.09, +0.47] | [+0.14, +0.42] | above chance | 22 / 18 | 16 / 43 |

### Damaged class alone

The class is under 10 pairs in both sets, so as pre-registered it is listed
pair by pair, not scored.

**54 pairs (n 7).** Kent picked the same side on 6. Kent tied the 7th
(P042). Kent never picked the other side.

| pair | fixture | Kent | screen | conf | the judge's reason |
|---|---|---|---|---|---|
| P009 | proseal_beanie | before | before | 5 | RIGHT's PROSEAL letters are chewed and the SPRAY FOAM COATINGS line is shattered |
| P011 | and_pizza | before | before | 4 | RIGHT shows open seam lines across the p's bowl and both z's |
| P013 | jakarta | before | before | 5 | RIGHT's tagline is mush and the main letters have ragged edges |
| P025 | bukit_asam | before | before | 4 | RIGHT's BukitAsam letters are mottled with seams |
| P035 | k_line | before | before | 5 | LEFT's K LINE letters have a bumpy segmented fill; its small line is illegible |
| P042 | bukit_asam | tie | before | 4 | RIGHT's BukitAsam letters are mottled with seams through B, k, A and m |
| P057 | n_sync | before | before | 4 | LEFT's S, Y, N and C are chopped into segments with hard breaks |

**99 pairs (n 6).** Kent picked the same side on 5 and the other side on 1
(P037).

| pair | fixture | Kent | screen | conf | the judge's reason |
|---|---|---|---|---|---|
| P008 | bridge | after | after | 4 | right wraps every spoke and the ring in pale grey outlines not in the artwork |
| P010 | becker | before | before | 4 | Left's MARINE is broken up, with stray outline fragments around the letters |
| P028 | fremont | after | after | 5 | Right drops EST 1895 and EAT STAY PLAY entirely and breaks the rope border |
| P037 | drone | **after** | **before** | 4 | Left sews PRECISION and THERMAL as open zigzag skeletons that will not cover |
| P070 | drone | before | before | 4 | Left sews PRECISION and AND DRONE as hollow thin outlines that barely read |
| P084 | fremont | before | before | 4 | Right's HOTEL FREMONT and THE are sewn with jagged, spiky zigzag edges |

### What is left for Kent (workload counts, not agreement figures)

| set | live | nothing to choose | plainly damaged | Kent has to look | Kent's side picks | of them in "has to look" | in "nothing to choose" | in "plainly damaged" |
|---|---|---|---|---|---|---|---|---|
| 54 | 54 | 32 | 7 | 15 | 29 | 10 | **13** | 6 |
| 99 | 99 | 61 | 6 | 32 | 40 | 16 | **18** | 6 |

### Identical controls

All identical pairs landed in "nothing to choose": 3 of 3 on the 54 set and
4 of 4 on the 99 set.

## What this licenses, and the catch Kent should weigh

Both the primary and the replication read **above chance**. Under the
pre-registration that licenses exactly one thing: **a proposal to Kent for a
display-only row on the eye-pairs page** that shows the screen's class beside
each pair. Kent still sees and labels every pair. This PR does not build it,
and whether to build it is his call.

The proposal comes with the catch the workload table shows:

- **"Nothing to choose" is where the screen is weakest.** Of Kent's side
  picks, it labelled 13 of 29 and 18 of 40 "nothing to choose". A row reading
  "nothing to choose" beside a pair is therefore not a reason to look less
  closely. On a display-only row Kent would see that label beside pairs he
  will in fact decide.
- **"Plainly damaged" is the strong class, and it is small.** It covered 7 of
  54 and 6 of 99 pairs. Kent picked the same side on 11 of the 13, tied 1,
  and went the other way once (P037, the "open columns will not cover" call,
  which is a sew-out question).
- **Identical pairs are reliable.** The screen called every identical pair
  "nothing to choose".

**Never, from this file:** routing a design, choosing a lane, flipping or
holding a flag, gating a PR, a tripwire or a sew-out, or dropping a pair from
a sitting. Nor does it license pooling the screen with Kent's labels, any
engine-quality claim, or any API spend. A changed threshold or rule is a new
dated pre-registration, never pooled with this one.
