# Claude as the eye (`vlm-judge`): pre-registration, 2026-11-04

**Committed BEFORE any call to the model.** Its twin is
`digitizer/tools/eye_pairs/vlm_judge.py`; `digitizer/tests/test_vlm_judge.py`
fails if the prompt, effort, `max_tokens`, orders or models named here drift
from the module. **This file judges nothing about the engine and flips
nothing.** Kappa is chance-corrected throughout; no raw agreement figure is
computed anywhere in this experiment (ROADMAP gate 4).

## Why

Kent asked on 2026-11-04 whether EMB-Bot would benefit from Claude's vision
model and chose this test first. `docs/organic-review-2026-09-22.md` §3.4 had
already flagged a vision model for the judgment layer as "genuinely never
considered". ROADMAP Phase 1 exits when a metric's ranking agrees with Kent's
eye; the yardstick of 2026-11-01 found that only the trim counts clear chance
and nothing fidelity-shaped does. The instruments count stitches; Kent looks
at a render. A vision model looks at the render. The cheapest honest test is
whether its BLIND pick agrees with his, above chance, on pairs he has already
judged.

## What was run before this was written

No model call. Two images from the kit were opened to design the prompt and
to confirm the files are what the sitting's write-up says: `img/P001_L.jpg`
and `img/P001_art.png` (the ProSeal hat). No pick of Kent's was read beside a
render. `SITTING.md` and `analysis.txt` of the sitting were read; they hold
his controls (quoted below) and no per-pair pick beside a picture.

## The sitting

`pro-lettering-1102` (`docs/eye-pairs-2026-11-02/pro-size-lettering/`) is the
only labelled sitting whose renders survive: `digitizer/eye_pairs_out/pro-lettering-1102/`
on Kent's laptop (gitignored), 128 JPEG renders 1120-1530 px wide and 64 art
PNGs, exactly the files the picker page served him. Every older labelled
sitting's render directory is gone (`pro_pooled_build.py`, 2026-11-01). 64
pairs: 56 live, 4 identical, 4 repeat; Kent sat all 64 on 2026-11-03, 08:39
to 08:48. The judge is shown, per pair, the same three files he saw:
`P###_art.png`, `P###_L.jpg`, `P###_R.jpg`.

**Kent's own controls on it are the ceiling** (`SITTING.md`): identical pairs
called a tie 4 of 4; repeat pairs answered the same 1 of 4; 23 left and 7
right among the 30 pairs he chose a side on; 26 of 56 live pairs tied. A judge
cannot agree with him more reliably than he agrees with himself, so a null
here is a result about n and about this sitting as much as about the judge.

## The judge

- **Models:** `claude-opus-5-5` (primary) and `claude-haiku-5-5` (secondary,
  the cheap pre-screen candidate). Nothing else.
- **One user message:** the prompt below, then `ARTWORK:` and the art image,
  `LEFT:` and the left render, `RIGHT:` and the right render, as base64. No
  system prompt. No pair id, arm name, flag, or pick anywhere in the request.
- **Settings:** `output_config.effort` `medium`; `max_tokens` 1500; JSON-schema
  output `{"choice": "L" | "R" | "tie", "confidence": integer, "reason": string}`;
  thinking left at the model's adaptive default; no `temperature` (rejected on
  these models); **no `fallbacks`** (a fallback model would be a different
  instrument), so a refusal is recorded as a refusal and scored as unanswered.
- **Prompt, verbatim** (sha256
  `24acb29674ecca4b045c176cbb00ac971512ef510d4a7bea69233ce1c928095a`):

> You are standing in for an experienced embroidery digitizer at a blind sitting.
> Three images follow: the customer's ARTWORK, then two machine-embroidery stitch
> simulations of it, LEFT and RIGHT, made by two versions of the same digitizing
> engine. They may be identical.
> Judge them the way a digitizer judges a sew-out before it goes on the garment,
> and pick the one you would rather sew and hand to the customer. If you cannot
> tell them apart, or neither is better, answer tie.
> Answer as JSON only: {"choice": "L" | "R" | "tie", "confidence": 1-5,
> "reason": "at most 40 words"}.

- **Two orders per pair:** order A is the sitting as Kent saw it; order B has
  LEFT and RIGHT swapped (the two files exchanged, nothing else), so a screen-side
  habit shows up as disagreement with itself. 128 calls per model. Order B is
  mapped back into A's frame before anything is scored.
- **Record:** one JSON line per call in `verdicts-<model>.jsonl` beside this
  file (pair, order, choice, confidence, reason, stop reason, request id, served
  model, token usage, elapsed). The run is resumable; a key is never in the
  repository (`--key-file` or `ANTHROPIC_API_KEY`).

## Pre-registered reads

**Vocabulary.** His L / R / tie and the judge's L / R / tie are both mapped
through the sealed key (`arms.json`) to `before` (the base side) / `tie` /
`after` (the arm). Identical pairs have no before or after and are controls
only. **Code:** `tools.eye_pairs.pooled` (`kappa_from_table`, `_boot`,
`reading`), 10,000 resamples, seed 20261104: Cohen's kappa 3-way
linear-weighted with ties in, and 2 x 2 on the pairs both decided; 95%
percentile intervals over pairs and over designs (14 logos, 12 designs: `mfab`
and `proseal` each carry two logos). Reading rule, `pooled.reading` verbatim:
`above chance` only when BOTH intervals clear zero, `below chance` when both
sit under it, `n too small (<10)`, else `no evidence either way`.

- **Primary (one number, one reading):** `claude-opus-5-5`, order A, the 56
  live pairs, 3-way kappa with ties.
- **Secondary, reported whatever the primary says and promoted to nothing:**
  the sides-only kappa on the pairs both decided; order B; `claude-haiku-5-5`
  in both orders; the 29 pairs of the three arms that passed the manipulation
  check (`corner_fold_off`, `text_lean_off`, `inside_stagger_off`); the judge
  against the kit's own `expected_label` (what the 11-02 pre-registration
  predicted; Kent read +0.07 against it).
- **Controls:** identical pairs called a tie (of 4, per order); repeat pairs
  answered the same (of 4, per order); swap consistency: pairs with the same
  verdict in A and B (of 64) and pairs that picked the same SCREEN side both
  times; L / R share in each order's own frame; refusals and parse failures;
  mean stated confidence.
- **Listed, not scored:** every live pair where Kent chose a side and the judge
  (order A) chose the other, with the judge's reason. Renders for Kent to open,
  not a statistic.

## What each outcome licenses

- **Primary `above chance`:** on this sitting the model's blind pick tracks
  Kent's. It licenses ONE next step: re-render the 100 labelled pro pairs
  (`pro_pooled_build.py render`, about three hours) and repeat this protocol
  unchanged there. It does not license a flag flip, a routing change, or any
  claim about engine quality.
- **`no evidence either way`:** inconclusive at n 56 against a sitting whose
  own repeat agreement was 1 of 4. The judge's swap and repeat consistency say
  whether it is at least a stable instrument: a stable judge and a null is a
  reason to run the 100-pair set; an unstable judge is not.
- **`below chance`:** the judge weighs the opposite of Kent on these flips.
  Record it in DOCTRINE and stop.
- Haiku's reading decides nothing on its own; it stands beside Opus so the
  cost of a pre-screen is known if Opus earns one.

## Not read, by design

- No prompt tuning on the results. A second prompt is a second experiment
  with its own dated pre-registration; a run under a changed prompt is never
  pooled with this one.
- The sitting's own question (whether the trim family tracks Kent) is settled
  in its `SITTING.md`; nothing here reopens it.
- ROADMAP gate 1 (fabric), gate 2 (routing) and gate 3 (default-OFF tiers) are
  untouched; gate 4 is satisfied by construction.

## Cost

About 3,900 image tokens per call (three images at the API's 1,568-px cap)
plus roughly 130 output tokens, 128 calls per model: `claude-opus-5-5` about
$2.60 at $4 / $20 per MTok, `claude-haiku-5-5` about $0.07 at $0.10 / $0.50.
Measured usage is written per call and summed in `analysis.md`.

## Amendments

Any amendment is dated here before the run it affects.

**Amendment 1, 2026-11-04, before any pair was opened for judgment.** Kent:
"Don't create a key, just inject your own opinions into what's needed and feed
embot the results." The judge is therefore the Claude Code session itself
(`claude-fable-5-1`, recorded under the model name `claude-fable-5-1-session`),
reading each pair's three files with its Read tool and recording L / R / tie,
a confidence and a reason through `vlm_judge record`, eight pairs per batch,
each batch written to disk before the next pair is opened. What changes:

- **No API call.** `effort`, `max_tokens`, the JSON schema and `fallbacks` do
  not apply; the prompt above is the instruction the session holds itself to
  on every pair; the cost section is void. The two API arms
  (`claude-opus-5-5`, `claude-haiku-5-5`) stay registered, unchanged, for a
  later run with a key.
- **One order only (A, as Kent saw it).** A judge with memory cannot be swapped
  or repeated blind: order B and the repeat control would measure recall, not
  judgment. Both dropped; the swap row reads "not run".
- **Exclusions, named now.** While building the kit the session read the first
  three lines of `picks.jsonl` (`P001` L, `P002` tie, `P003` tie) and the first
  two entries of `arms.json` (`P001` base left, `lane_off` right; `P002`
  identical). `P001` and `P003` leave every scored read and every control;
  `P002` leaves the identical control (`analyse --exclude P001,P002,P003`).
  The session also knows the fixture list, the arm names, the repeat map
  (`P015` of `P020`, `P045` of `P026`, `P050` of `P044`, `P059` of `P022`) and
  the marginals (34 ties, 23 L, 7 R over 64; 16 before / 26 tie / 14 after on
  the live pairs), none of it per pair. Known marginals are one more reason the
  primary is the chance-corrected kappa and not a share. Verdicts are given on
  the pair's three files alone; `arms.json`, `picks.jsonl` and
  `sitting-inputs.json` are not opened again until all 64 verdicts are on disk.
- **Primary becomes:** the session, order A, the 54 live pairs left, 3-way
  kappa with ties. Secondary reads and the remaining controls as registered
  (the identical control on 3 pairs; the repeat control void).
- Also seen before judging: `img/P001_L.jpg` and `img/P001_art.png` (declared
  above; that pair is excluded anyway).
