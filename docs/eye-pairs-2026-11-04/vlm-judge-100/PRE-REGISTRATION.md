# Claude as the eye, the 100-pair repeat (`vlm-judge-100`): pre-registration, 2026-11-04

**Committed before any pair was paired or opened.** The sibling experiment
`../vlm-judge/PRE-REGISTRATION.md` (one sitting, 54 pairs) read its primary
above chance and licensed exactly one next step: the same protocol on the 100
labelled pro pairs, re-rendered. This file is that step. Its twin is
`digitizer/tools/eye_pairs/vlm_judge.py` (`kit`, `record`, `analyse --pro100`);
`digitizer/tests/test_vlm_judge.py` fails if the prompt, seed, size rule or
exclusion named here drift from the module. **This file judges nothing about
the engine and flips nothing.** Kappa is chance-corrected throughout; no raw
agreement figure is computed (ROADMAP gate 4).

## What was run before this was written

`pro_pooled_build render --sitting-size` was started minutes before this
commit (deterministic engine work, two to three hours under the laptop's CPU
slot); no design, picture or log line of it beyond "started" was looked at.
`labelled_pairs()` was called for counts only (pairs by sitting, fixture and
arm; designs by tree). No label was read beside a pair except the one named
under Exclusions.

## The pairs

- **Source:** the 100 labelled pairs with a pro file in
  `docs/eye-pairs-2026-11-01/pro-pair-inputs.json`
  (`pro_pooled_build.labelled_pairs`): nine sittings 2026-09-18 to 10-08, six
  fixtures (becker 18, bridge 19, drone 18, fremont 13, golden_tee 17,
  tires 15), 21 arms, 143 distinct designs over eleven trees, two of them
  ref-engine trees (`ref_0827`, `ref_0930am`: the pair's `before` is an older
  engine's base). Kent's label vocabulary `after` / `before` / `same` /
  `both_bad` maps to `after` / `before` / `tie` / `tie` as `pooled.VOCABULARY`
  already does.
- **Excluded, named now:** `off-flags-1003:cap_recentre:becker`. Its label was
  printed while the file format was being inspected on 2026-11-04. **99 live
  pairs.**
- **Re-drawn at the sitting's own request, not the pro's.** The 11-04
  pre-registration said "re-render the 100 labelled pro pairs
  (`pro_pooled_build.py render`)"; that tool draws each design at the pro
  job's width and garment because its purpose was the pro's DST. This test
  has no pro file in it, and Kent's labels were given on the sittings' own
  pictures, so the faithful repeat is the sitting's request: `--sitting-size`
  (added for this), `thin_strokes.REAL_ART`: becker 100 mm `left_chest`,
  fremont 92.5 mm `patch`, bridge / drone / golden_tee / tires 80 mm
  `left_chest`; the Studio's six colours; the sitting's base flags
  (`SITTINGS[...]["base"]`); each design on ITS sitting's tree in a detached
  worktree outside the repository with the primary checkout's venv and rembg
  venv, as the 11-01 build did.
- **Pictures:** today's `digitizer_core.stitchviz.render_design` at 14 px/mm,
  JPEG quality 92 (the sittings' own scale and format), one picture per
  design, cached beside it; the artwork through `artfid_eye_rank._normalise_art`
  on white from today's `testdata/` (byte-identical to the trees' for these six
  files). Both sides of every pair are drawn by the same renderer.
- **Not reproduced, from the 11-01 build's own caveats:** the 77-pair flags
  sitting (`flags-0918-0928`, 49 of these pairs) was judged on a cloud render
  this laptop never held, and the `density-1007` tree broke ties from OS
  entropy, so its arm is a sample of that engine. Both are read as a split
  below, not hidden in the pool.
- **Pairing:** `vlm_judge kit`, seed **20261104**: live pairs shuffled, the
  base on the LEFT in exactly half of them, plus **4 identical pairs** (one
  design on both sides, drawn from the live designs), the whole order
  shuffled, ids `P001` onward. `pairs.json` is what the judge reads;
  `arms.json` (the sealed side map) and Kent's labels are not opened until
  every verdict is on file.

## The judge: unchanged

The session itself, under the 11-04 Amendment 1 terms: the Read tool on
`P###_art.png`, `P###_L.jpg`, `P###_R.jpg`; the same prompt held to on every
pair (sha256 `24acb29674ecca4b045c176cbb00ac971512ef510d4a7bea69233ce1c928095a`);
L / R / tie with a 1-5 confidence and a reason; one screen order; batches of
eight written to `verdicts-claude-fable-5-1-session.jsonl` before the next
pair is opened; no API call, no key. Repeat and swap controls are void for a
judge with memory and are not run.

**What the judge knows, declared:** the arm-level rulings in the project's
memory index (which flags later shipped ON or stayed OFF), the yardstick note
that Kent picked the 09-18 engine over the 08-27 one on four logos (the
`ref_0827` arm, logos unnamed), and the label marginals of the 100 (41 decided:
29 `after`, 12 `before`; 59 ties). None of it is per pair; the judge is not
shown an arm name, a sitting or a flag, and a ref-engine pair is not marked.
The six logos are recognisable. Known marginals are one more reason the
primary is a chance-corrected kappa and not a share.

## Pre-registered reads

Code and vocabulary as in the 11-04 file: `pooled.kappa_from_table`,
`pooled._boot` (10,000 resamples, seed 20261104), `pooled.reading` (both
intervals must clear zero; under 10 pairs nothing is read). The design
cluster for the second interval is the FIXTURE (six clusters), so that
interval will be wide; it is reported, never dropped.

- **Primary, one number, one reading:** the 99 live pairs, 3-way kappa with
  ties in.
- **Secondary, reported whatever the primary says, promoted to nothing:** the
  sides-only kappa on the pairs both decided; `flags-0918-0928` (the cloud
  render) against the other eight sittings; the two ref-engine arms against
  the flag arms.
- **Controls:** the 4 identical pairs called a tie; refusals and parse
  failures; L / R share in the judge's own frame against the kit's
  half-and-half; ties on live pairs; mean stated confidence.
- **Listed, not scored:** every live pair where Kent chose a side and the
  judge chose the other, with the judge's reason.

## What each outcome licenses

- **Primary `above chance`:** with the one-sitting read of 11-04 this is two
  independent sets (and five sittings' worth of pictures) on which the
  session's blind pick tracks Kent's. It licenses a proposal to Kent, not a
  build: a vision pre-screen row on the eye-pairs page ("the judge calls this
  identical / damaged / look"), and spending the registered API arms' few
  dollars once a key exists. No flag flip, routing change or engine-quality
  claim.
- **`no evidence either way`:** the 11-04 result stands as one sitting's and
  is recorded as such; stop.
- **`below chance`:** DOCTRINE entry; stop.
- The sides-only and split reads qualify the primary's reading (where the
  agreement lives); they do not overturn it.

## Not read, by design

No prompt change. No per-arm kappa (n per arm is 1 to 9). No comparison
against the pro's DST (that was the 11-01 question). No claim about the
engine from any of this.

## Cost

Two to three hours of laptop CPU under the shared slot for 143 designs;
about 310 image reads in one Claude Code session. No API spend.

## Amendments

None. Any amendment is dated here before the step it affects.
