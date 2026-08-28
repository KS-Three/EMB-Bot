# Does the yardstick agree with Kent's eye? — 2026-08-28

ROADMAP phase 1's exit condition is *"a yardstick that agrees with Kent's eyes"*.
This is the first attempt to measure that, and the headline is that **it cannot
be settled with the evidence that exists** — but two useful things fell out on
the way, and one proposed method had to be abandoned before it was run.

## The method that was proposed, and why it was dropped

The plan was a chance-corrected agreement between the instrument stack and
Kent's ranking. **There is no such ranking.** `docs/kent-review-2026-08-27.md`
records verdicts *on the instrument's own ordering* — eight rows, of which six
carry a verdict (four "rank looks right", two "OUT OF PLACE") — not an
independent ordering of his own. There is nothing to correlate against, and at
n = 6 a chance-corrected figure would not survive its own interval anyway.

Replaced with a test the evidence does support, and one that does not require
guessing which direction "out of place" meant: **does any column place BOTH
flagged designs below ALL FOUR endorsed ones?** That predicts *where* the
ranking changes rather than how, and it is falsifiable.

## Result

| pos | fixture | artfid | lost | lost_frac | worst mm² | Kent |
|---|---|---|---|---|---|---|
| 1 | `bg_uncertain` | 95.6 | 4 | 0.026 | 40.7 | rank looks right |
| 2 | `logo_alpha` | 92.6 | 9 | 0.063 | 18.4 | rank looks right |
| 3 | `logo_whitebg` | 91.8 | 18 | 0.065 | 15.5 | — |
| 4 | `ribbon_curve` | 88.4 | 8 | 0.104 | 11.9 | rank looks right |
| 5 | `becker_marine_logo` | 85.0 | 39 | 0.096 | 18.1 | **OUT OF PLACE** |
| 6 | `logo_script_tires` | 86.6 | 32 | 0.164 | 13.8 | rank looks right |
| 7 | `enthusiast_logo` | 79.7 | 34 | 0.246 | 6.9 | **OUT OF PLACE** |
| 8 | `region_blobs` | 47.2 | 120 | 0.160 | 20.9 | — |

| column | endorsed | flagged | separates? |
|---|---|---|---|
| `artfid` | 86.6 – 95.6 | 79.7, 85.0 | **yes** |
| `lost` (count) | 4, 8, 9, 32 | 34, 39 | **yes** |
| `lost_frac` (area) | 0.026 – 0.164 | 0.096, 0.246 | no |
| `worst_mm2` | 11.9 – 40.7 | 6.9, 18.1 | no |

**Two findings, and one confound that stops either being a validation.**

### 1. Element COUNT matches his judgement; element AREA does not

`lost` separates cleanly. `lost_frac` and `worst_mm2` both fail, and they fail in
the specific way that matters: `ribbon_curve`, which Kent endorsed, loses a
*larger area fraction* (0.104) than `becker_marine`, which he flagged (0.096),
and `bg_uncertain`, also endorsed, has the largest single lost element in the set
(40.7 mm²).

That is consistent with how he actually writes: he names **elements** — *"the red
'arm' … was lost"*, *"the C infill was completely lost"*, *"EAT | STAY | PLAY was
completely lost"* — never areas. **So weight the count, not the area.** This
holds independently of the ranking question below, and is the more portable of
the two findings.

### 2. `artfid` alone already separates — and that is the confound

On today's engine, ARTFID puts both flagged designs below all four endorsed ones
with no element-loss term at all. The specific inversion Kent objected to has
**resolved itself**: `becker_marine` (85.0) now sits below `logo_script_tires`
(86.6), where his table had them the other way round.

**This is not a validation, and must not be quoted as one.** His verdicts were
given on stitch-outs from the engine as it stood on 2026-08-27; PRs #282/#283
(the lettering house angle) and others have landed since. Comparing today's
ARTFID against his old verdicts mixes an instrument question with an engine
question, and this data cannot separate them. The mean ARTFID over these eight
is 83.4 today against the 83.7 recorded at review time, so the scores barely
moved overall — but the becker/script_tires gap is 1.6 points, comfortably
inside that drift.

## Why this cannot settle phase 1

Beyond the confound: **n = 6.** Two flagged designs landing as the bottom two of
six by chance alone is 1 / C(6,2) = **1/15 ≈ 0.067**. Suggestive, not
significant, and it is one threshold fitted on six points. ROADMAP gate 4 bars
quoting a raw agreement figure precisely because numbers like this move when the
mix moves.

**What would settle it: fresh per-design verdicts on CURRENT output.** Kent's
fourteen notes describe stitch-outs that no longer exist. A re-run of the same
fourteen designs through today's engine, re-reviewed, would give verdicts and
output from the same moment — and would also say whether his 60% has moved.
Until then this stays open, and no phase advance rests on it.

*(measured 2026-08-28 — `tools/artfidelity_self.py`, `tools/dropped_elements.py`
against `docs/kent-review-2026-08-27.md`)*
