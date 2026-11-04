# Claude as the eye (`vlm-judge`): results, 2026-11-04

The session judge of Amendment 1 (`PRE-REGISTRATION.md`) gave all 64 verdicts
on 2026-11-04 in eight batches of eight, each batch written to
`verdicts-claude-fable-5-1-session.jsonl` before the next pair was opened;
`analyse --exclude P001,P002,P003` ran once and wrote `analysis.md` /
`analysis.json`. **This file judges nothing about the engine and flips
nothing.** Kappa is chance-corrected throughout; no raw agreement figure exists
here (ROADMAP gate 4).

## The pre-registered primary

| scope | n scored | n Kent decided | kappa, ties in | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|
| live pairs, order A | 54 | 29 | **+0.36** | [+0.16, +0.55] | [+0.20, +0.45] | **above chance** |

Both intervals clear zero. On this sitting the session's blind L / R / tie
tracks Kent's above chance.

## What the agreement is made of

Kent (rows) against the judge (columns), the 54 live pairs:

| | before | tie | after |
|---|---|---|---|
| **before** (base side) | 11 | 3 | 1 |
| **tie** | 6 | 19 | 0 |
| **after** (the arm, flag OFF) | 2 | 10 | 2 |

- The judge chose a side on 22 live pairs: 19 for the base, 3 for the arm.
  Kent chose a side on 29: 15 base, 14 arm.
- Of Kent's 14 arm picks the judge tied 10, agreed 2, went the other way 2.
  Of his 15 base picks it agreed 11, tied 3, went the other way 1.
- **Sides only** (both chose a side): 16 pairs, kappa +0.45, CI pairs
  [-0.14, +1.00], designs [-0.12, +0.74]: no evidence either way.
- Pairs where both chose a side and disagreed: 3 (`P022` toat_machine_hat
  `inside_stagger_off`, `P030` k_line `text_lean_off`, `P061` proseal_beanie
  `exit_next_off`), two of them at the judge's confidence 2.

So the agreement is shared ties and shared "the base is better" calls: a
shattered small line (ProSeal's SPRAY FOAM COATINGS, K LINE's KAWASAKI line,
Jakarta's tagline), a mottled fill with seams through the letters (BukitAsam,
MFab's white keyline fragments), a split column in a big letter (TOAT's M,
NSYNC's N). Where Kent preferred the arm, the judge mostly saw nothing to
choose. That half is the half the Phase 1 question lives in.

## Secondary reads (registered, promoted to nothing)

| scope | n | n Kent decided | kappa, ties in | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|
| the three arms that passed the manipulation check | 28 | 15 | +0.18 | [-0.08, +0.43] | [-0.15, +0.34] | no evidence either way |
| against the kit's own `expected_label` | 54 | 54 | +0.16 | [+0.01, +0.30] | [-0.00, +0.28] | no evidence either way |

The `claude-opus-5-5` and `claude-haiku-5-5` arms were not run (no key);
they stay registered.

## Controls

- Identical pairs called a tie: **3 of 3** (`P002` excluded, seen as identical
  before judging).
- Refusals 0, unparsed 0; mean stated confidence 3.48; 32 of 54 live pairs
  tied (Kent 25).
- Sides in the judge's own frame: 16 left, 7 right. The kit put the base on
  the left in half the live pairs and the judge chose the base on 19 of its
  22 decided live pairs, so the lean follows the base, not the screen. Order
  B was not run, so a screen habit is not ruled out by measurement.
- Repeats answered the same: 4 of 4, **void** (Amendment 1: a judge with
  memory). Three of the four were tie / tie, which a judge tying 32 of 54
  reaches without memory; `P059` / `P022` were L / L.

## Against the ceiling

Kent's own repeat agreement on this sitting was 1 of 4 and 26 of 56 live
pairs were ties (`SITTING.md`). A kappa against a rater who disagrees with
himself three times in four cannot sit far above where this one landed; the
+0.36 is read as "tracks his eye on this sitting", not as a measure of how far
a vision model can go.

## What did not go as pre-registered

Amendment 1, in full and before any pair was opened: the session judged, not
the API; one order; `P001` and `P003` out of every read, `P002` out of the
identical control. The confidence field is the session's own 1-5, not a
model's sampled integer.

## What this licenses

Per the pre-registration, an above-chance primary licenses **one** next step:
re-render the 100 labelled pro pairs on their sitting trees
(`python -m tools.eye_pairs.pro_pooled_build render`, about three hours under
the `%TEMP%\embwt\cpu.lock` slot) and repeat this protocol unchanged there,
with the session as judge under the same amendment or the API arms with a
key. It does not license a flag flip, a routing change, or any claim about
engine quality. The sides-only null says the useful shape of a vision judge
today is a pre-screen: it separates "identical or plainly damaged" from
"Kent has to look", and the second pile is where his labels disagree with
every instrument so far.

## Cost

No API spend. 192 image reads in one Claude Code session, 64 verdicts.
