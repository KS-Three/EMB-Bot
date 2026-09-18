# Eye pairs — a paired-comparison yardstick built on Kent's picks — design — 2026-09-17

**Status:** design approved section by section by Kent, 2026-09-17, in the
session that produced `docs/pipeline-flow-and-foundation-review-2026-09-17.md`
(concern F4). No code exists yet. Nothing here changes a stitch.

## 0. What already governs this — read before changing the design

- **ROADMAP phase 1's exit condition** is the thing being built toward: *"on
  real customer designs, the metric's ranking agrees with Kent's visual
  ranking, and nothing he judges better ever scores worse."* This tool
  measures the SECOND clause directly. **Only Kent advances a phase**; the
  tool's output never claims an advance.
- **ROADMAP gate 4** — no quality claim on a raw agreement number. Every
  agreement figure here is reported chance-corrected (`2a − 1`, 0 = chance)
  with its interval and its n. No bare "% agreement" is printed anywhere.
- **Gate 1 does not apply** — no physical constant is read or set.
- **Kent's eye has never been in an instrument.** `docs/kent-review-2026-08-27.md`
  is fourteen free-text notes on the instrument's own ordering;
  `docs/yardstick-vs-kents-eye-2026-08-28.md` found n = 6 verdicts cannot
  settle anything and named the cure — *fresh verdicts on CURRENT output*;
  `tools/artfid_eye_rank.py` (2026-09-11) is a blind RANK harness whose one
  run used **Claude's** eye and came back null at n = 7
  (`docs/artfid-eye-agreement-2026-09-11.md`).
- **ARTFID is not comparable ACROSS routes** (DOCTRINE 2026-09-11), and
  `score_image` refuses six of fourteen fixtures. A same-design pair sidesteps
  both: both arms are one artwork, and a refusal applies to both sides alike.
- **The preflight score saturates at 0** on floored designs (memory
  `instruments-that-underreport-2026-09-06`); `raw_score` is the unclamped
  value and is the one read here.
- **The 08-27 validation artifact self-republishes — never republish it.**
  This tool does not use an Artifact at all (Kent's call, §2).
- **Existing pieces reused, not rebuilt:** `artfid_eye_rank.py`'s two-command
  commitment device, its `_normalise_art` and `VIEW_PX_PER_MM`;
  `thin_strokes.corpus_cases()` for the fixture table and Studio configs;
  `stitchviz.render_design` (the lit-filament model the Studio also uses).

## 1. The gap, in one sentence

Every flag flip in this repo is steered by instruments that correlate with
each other at ρ 0.405 and with Kent's "60%" not at all, and there is no
record of which of two outputs Kent actually prefers — so the instruments
cannot be checked, and the flags cannot be ruled, except one render at a time.

## 2. Decisions — Kent's, 2026-09-17

| # | question | ruling |
|---|---|---|
| 1 | what is a pair | **the same design digitized two ways** (shipped vs one alternative arm) |
| 2 | which arms | **the pending default-OFF flags, each vs shipped, plus today vs the engine at his 08-27 review** |
| 3 | where he clicks | **a local page served by the tool**, picks appended to disk |
| 4 | how picks become a verdict | **sign agreement primary (pre-registered); a small fitted composite exploratory only** |
| — | design sections 1/3, 2/3, 3/3 | each approved as presented |

Not chosen, so nobody rebuilds them unasked: cross-design pairs (a second
sitting, once the picker exists); an Artifact/phone picker; a fitted composite
as the headline.

## 3. Design

### 3.1 Fixtures

`thin_strokes.corpus_cases()` — the ten `REAL_ART` names, nine after its
byte-duplicate check (`thermal` is `drone`). Each at the config a customer
gets: `target_width_mm` and `garment_id` from `REAL_ART` (becker 100 /
left_chest, fremont 92.5 / patch, the rest 80 / left_chest) and
`max_colors = STUDIO_MAX_COLORS` (6). Kent's own icon is not in the repo
(public) and is not used.

### 3.2 Arms

The BASE arm is the shipped config above. Every other arm is the base plus
exactly one change:

| arm id | change |
|---|---|
| `per_stroke` | `satin_per_stroke=True` |
| `patch_junctions` | `satin_patch_junctions="satin"` |
| `polygon_axis` | `satin_polygon_axis="artwork"` |
| `area_weighted` | `classify_area_weighted=True` |
| `design_angle` | `design_angle=True` |
| `rail_comp` | `satin_rail_comp=True` |
| `wide_columns` | `wide_columns=True` |
| `lettering_column` | `lettering_min_column_mm=1.0` |
| `phantom_dissolve` | `dissolve_phantom_blends=True` |
| `directional_comp` | `directional_comp=True` |
| `ref_0827` | the engine at `25da2fe` (main on 2026-08-27), base config |

One digitize per (fixture, arm). An arm whose Design `stitches` hash equals
the base's is **skipped and logged** (`identical_to_base`) — there is nothing
to judge. An arm that raises is recorded as an error row and dropped; one bad
arm never takes the run down (`artfid_eye_rank`'s rule).

`ARMS` is a module-level table, so a later sitting adds a row, not a feature.

### 3.3 Pairs, blinding, controls

- **Live pair** = base vs one non-identical arm of the same fixture.
- **Identical control** = base vs base, same image both sides — up to 8, one
  per fixture. Measures the tie rate (attention) and the left-share (side
  bias).
- **Repeat control** = 8 live pairs sampled by the seeded RNG, shown a second
  time with sides swapped. Measures Kent's own consistency — the ceiling no
  instrument can be asked to beat.
- Order shuffled and left/right assigned by `random.Random(SHUFFLE_SEED)`;
  a repeat is never adjacent to its original.
- Pair ids are opaque (`P001`…). The public `pairs.json` carries ids and image
  names only. The artwork copy is per pair and opaquely named, so no filename
  carries a fixture or arm name.
- **Known and recorded, not excluded:** some arms are self-identifying (the
  08-27 engine sews 0.40 mm rows), and Kent has already seen renders for
  several flags under `docs/renders/`. Results are printed per arm so a reader
  can see what either effect is doing.

### 3.4 The tool — `digitizer/tools/eye_pairs.py`, four verbs

| verb | does |
|---|---|
| `--render` | digitize base + arms per fixture; render; extract features. Resume-safe: a checkpoint is written after every (fixture, arm), and a finished one is skipped on rerun — a row is reused only when its `source_sha256` and `schema` match. `--fixtures a,b` / `--arms x,y` limit the run (smoke tests, a second sitting) and **never touch the sitting**. Prints the arm-run COUNT only. |
| `--pair` | build the sitting from every rendered arm (**split out of `--render` 2026-09-17, review findings 2–3**: a scoped render used to reshuffle the whole sitting). Writes `sitting.json` with a hash of the SEALED map; once picks exist it refuses any other map, and refuses when `sitting.json` is missing. Prints pair COUNT only. |
| `--serve` | the picker, §3.5 |
| `--reveal` | refuses unless every pair id has a pick and no pick names an unknown pair; then runs §4 and writes `results.json` + the results tables to stdout |
| `--verify` | drift control: on one fixture, the features this tool computes from a held plan equal what each instrument's own `analyse()` returns after digitizing for itself. Unlike `artfid_eye_rank --verify` it contaminates nothing — Kent never ranks by score here, and the features stay sealed from the picker either way |

Files, all under `digitizer/eye_pairs_out/` (gitignored, new `.gitignore` line):

```
pairs.json      PUBLIC  [{"pair","left","right","art"}]
sitting.json    PUBLIC  {"sealed_sha256","n_pairs","built_ts"}   (a hash names nothing)
img/            PUBLIC  P###_L.jpg  P###_R.jpg  P###_art.png
arms.json       SEALED  pair -> {fixture, left_arm, right_arm, kind, repeat_of}
features.json   SEALED  fixture -> arm -> {metric: value|null, "refusals": {...}}
designs/        SEALED  fixture__arm.json   (the Design dict; what was rendered)
picks.jsonl     append-only, one line per click:
                {"pair","choice":"L"|"R"|"tie","ms","ts","undo_of":null|"P###"}
                The LAST line for a pair wins; nothing is ever rewritten.
```

After the sitting, `picks.jsonl`, `pairs.json` and `arms.json` are copied to
`docs/eye-pairs-<date>/` and committed — the audit trail, same role as
`docs/artfid-eye-ranking-2026-09-11.json`.

Renders: `render_design(design, px_per_mm=14.0, lit=True)`, JPEG q92. Artwork
through `_normalise_art` (alpha onto white; `.webp` to PNG).

### 3.5 The picker

`http.server.ThreadingHTTPServer` bound to **127.0.0.1:8731** (the service
owns 8721). No framework, no new dependency.

- `GET /` the page; `GET /pairs` → `pairs.json` plus the set of pair ids
  already picked; `GET /img/<name>` only for names listed in `pairs.json`;
  `POST /pick` appends one line to `picks.jsonl` and flushes before replying.
  Anything else — `arms.json`, `features.json`, `designs/` — is **404 by
  whitelist**, and a test asserts it.
- One pair per screen: left render, artwork (small, centre), right render.
  Keys `←` left, `→` right, `space` can't tell, `u` undo (appends a line with
  `undo_of`; the pair returns to the queue). A progress counter `n / N`.
  Click-to-zoom pans both renders together, so the same patch of both
  designs is on screen.
- Nothing else is on the page: no names, no counts, no flags, no timers shown.
- Closing the tab loses nothing; reopening resumes at the first unpicked pair.

### 3.6 The 08-27 arm

The old engine cannot be imported beside today's, so it runs out of process:

1. `git worktree add --detach <scratch>/eye-pairs-ref-25da2fe 25da2fe`, where
   `<scratch>` is resolved and **asserted non-empty and outside the repo**
   before the command runs (memory `worktree-add-empty-var-wipes-cwd`). The
   tool never reads or writes `.claude/worktrees/`.
2. A subprocess runs the MAIN checkout's venv python with
   `cwd=<worktree>/digitizer` and a ten-line driver: `digitize(image,
   PipelineConfig(target_width_mm, garment_id, max_colors))` →
   `plan_to_design` → JSON on stdout. All three kwargs exist at `25da2fe`
   (checked), and `requirements.txt` has not changed between the two refs.
3. Today's `render_design` draws that Design JSON (`stitches` / `colors` /
   `widthMM` — the contract is the same at both refs), so the two sides of the
   pair differ in stitches only, never in how they are drawn.
4. The worktree is removed (`git worktree remove --force`) when `--render`
   finishes or fails.

Because only a Design dict crosses the process boundary, the ref arm gets the
Design-only metrics of §3.7 and is excluded, by name, from the rest.

### 3.7 Features — one digitize, every instrument

The harness holds `gen`, `result`, `plan` and `design` for each arm and feeds
the instruments' INNER functions; nothing re-digitizes.

| metric | better | source | ref arm |
|---|---|---|---|
| `stitches`, `cones`, `stops` | none — descriptive only | `plan.stats`, Design records | yes |
| `trims_per_1000` | lower | preflight metrics / Design records | yes |
| `preflight_raw_score` | higher | `run_preflight(...)["metrics"]["raw_score"]` | no |
| `preflight_blocks` | lower | count of `severity == "block"` | no |
| `uncovered_total_mm2` | lower | preflight metrics — NOT `uncovered_wanted_mm2`, which is that check's DENOMINATOR (the area the design wants covered: 476.8 mm² on a tiny design graded A 100, measured 2026-09-17) and says nothing about a defect | no |
| `thread_worst_delta_e` | lower | preflight metrics | no |
| `artfid`, `artfid_coverage`, `artfid_structure` | higher | `artfidelity_self` `stitch_coverage_field` / `art_ink_field` / `register` / `ms_ssim` | yes |
| `artfid_colour` | higher | `artfidelity_self.colour_score(image, result, plan, cfg)` | no |
| `lost_elements`, `lost_frac` | lower | `dropped_elements.analyse_design` (§3.8) | yes |
| `ragged_mm`, `hausdorff_mm` | lower | `edge_smoothness.analyse_design` (§3.8) | yes |
| `roughness_deg` | lower | `curve_fidelity.measure(traces(plan))` | no |
| `thin_recall` | higher | `thin_strokes.measure(gen.p, cfg, plan)` | no |
| `legibility` | higher | `legibility.measure(gen.p, result, plan)` | no |

**An instrument's own refusal is carried as a FLAG, and the value is kept**
(`features.json`: `"refusals": {metric: reason}`). The ink-based refusals
(saturated or ambiguous ink mask) are properties of the ARTWORK, so they hit
both arms of a pair alike — but an unreliable mask can still turn a delta's
sign, so they are not simply ignored either: §4 headlines the non-refused
pairs and prints the all-pairs figure beside it, the same primary/secondary
split `artfid_eye_rank` pre-registered. (An earlier draft of this section
nulled refused metrics outright, which contradicted §0 and would have removed
the ink-based instruments from about six of the nine logos.) A metric an
instrument could not compute at all (NaN, or an exception) reads `null`.
`legibility` reads `null` wherever tesseract is
absent — which includes Kent's Windows box — and simply has a smaller n.
`artfid` on the ref arm is computed without the colour term and is therefore
NOT pooled with the flag arms' `artfid`; it is reported as `artfid_no_colour`.

### 3.8 The instrument splits

`dropped_elements.analyse` and `edge_smoothness.analyse` each become
`digitize` + `analyse_design(image_path, design, route=None)`; `analyse`
keeps its signature and calls the new function, so every CLI reads
byte-identical output. `dropped_elements` is guarded by
`test_dropped_elements.py`. **`edge_smoothness` has no test file of its own**
(only `test_curve_fidelity.py` mentions it, checked 2026-09-17), so the plan's
first task proves the split rather than assuming it: on one in-test synthetic
image, `analyse(path, cfg)` must equal `analyse_design(path, design, route)`
fed the SAME digitize, key for key. **Not a literal pin of the numbers** —
that would be a platform-bound golden, and this repo's goldens already
diverge between Kent's Windows box and CI (memory
`windows-goldens-fail-locally`). Equality of the two paths is
platform-independent and is the property the split actually has to keep.
`curve_fidelity`
already exposes `traces` + `measure`; `legibility` and `thin_strokes` already
expose `measure`. Nothing else in those tools moves.

## 4. The analysis — fixed before any pick is seen

Stated here, not at reveal time, because choosing the subset after seeing the
numbers is how a null becomes a positive (`artfid_eye_rank`'s own rule).

**Unit.** A *decided live pair*: a live pair whose final pick is `L` or `R`.

**PRIMARY — per-metric sign agreement, FLAG arms only.** For each metric with
a stated direction, over decided live flag pairs where the metric is non-null
on both arms and differs — compared at the rounding each instrument already
applies to its own output, with no extra tolerance (both arms are
deterministic, so an exact inequality is a real difference): `a` = the share
where the arm the metric prefers is the arm Kent picked. Reported as **`2a − 1`** (0 = chance, 1 = always agrees,
−1 = always disagrees) with n and the Wilson 95% interval on `a`.

**Corrected 2026-09-17, before any pick existed (code review of PR #506,
finding 1).** `2a − 1` puts chance at 0.5, which holds only when Kent's
picks and the metric's preferences are each split 50/50 between arm and
base. Nothing balances that (§3.3 balances LEFT/RIGHT), and the arms are
default-OFF flags with measured costs, so a shared lean to shipped is the
realistic case — under one, an independent metric agrees above 0.5 by
arithmetic (both at 75% base: `a` = 0.625, Wilson's lower bound clears 0.5
at n = 60, verified with the module's own `wilson()`). So the chance floor
is the observed-marginal one this repo's other corrections use
(`scorecard.type_chance`): `pe = p_pick·p_metric + (1 − p_pick)(1 −
p_metric)`, and the corrected figure is **`kappa_marginal = (a − pe)/(1 −
pe)`**. `2a − 1` stays in the output because it was pre-registered; the
report prints both marginals and flags `skewed` when `pe` is more than 0.05
from 0.5. A constant metric (`p_metric` 0 or 1) has `pe = a` and earns
nothing, which is right. Verdict:
*agrees* if the Wilson interval's lower bound is above `pe`, *anti-agrees*
if its upper bound is below `pe`, otherwise *no evidence* — identical to the
pre-registered rule on a balanced sitting; **n < 10 prints "n too
small" and no verdict.** The HEADLINE row for a metric uses only pairs where
neither arm carries a refusal for it; the same statistic over ALL pairs is
printed directly beneath, so dropping refused rows can never be mistaken for
the result. `stitches`, `cones`, `stops` have no direction and
are printed descriptively (which way Kent's picks lean), never as agreement.

**CEILING.** Over repeat controls: the share where the same ARM was chosen
both times (`tie`/`tie` counts as consistent). No metric is expected to beat
it, and the table prints it on its first line.

**CONTROLS.** Identical pairs: tie rate, and left-share among non-ties. All
decided pairs: left-share. A left-share far from 0.5 is printed as a warning
above every other table.

**THE EXIT-CLAUSE TABLE.** For each metric: every decided live pair where
Kent picked the arm that metric scores strictly WORSE — pair id, fixture, arm,
both values. This is phase 1's second clause read literally, and it is the
list of renders worth opening.

**CLUSTERING, stated.** Pairs from one fixture are not independent and there
are nine fixtures. Beside each metric's pooled figure: per-fixture agreement,
and the count of fixtures on which the metric agrees with the majority of
that fixture's decided pairs (a sign test at n ≤ 9).

**SECONDARY — exploratory, and only if decided live flag pairs ≥ 40.** A
logistic model of the pick on four standardized deltas named NOW —
`artfid`, `lost_elements`, `ragged_mm`, `roughness_deg` (fidelity plus Kent's
two themes) — fitted by Newton's method in numpy (no new dependency),
scored leave-one-FIXTURE-out against the best single metric. Labelled
exploratory in the output; its weights are written to `results.json` and
shipped nowhere.

**BY-PRODUCTS.**
- *Flag table:* per arm, wins / losses / ties of the arm against shipped,
  per fixture and pooled, with the arm's skipped-as-identical count. This is
  evidence for Kent's flag rulings; **the tool flips nothing.**
- *08-27 table:* today vs `ref_0827`, wins / losses / ties per fixture — the
  only datum the repo will have on whether his "60%" has moved.

**What a result licenses.** A metric that *agrees* is one whose direction can
be trusted on a same-design A/B — nothing more. It is not a quality
percentage, it says nothing across designs or across routes, it settles no
physical constant, and it is one sitting by one viewer on nine logos. A metric
that *anti-agrees* is a defect in the metric and gets its own entry.

## 5. Testing — TDD, `digitizer/tests/test_eye_pairs.py`

No real-logo digitize in CI (the `digitizer` job already runs ~50 minutes).

- **Pair building:** same seed → same order and sides; sides balanced;
  an identical arm is skipped and logged; control counts honoured; a repeat is
  never adjacent to its original; **`pairs.json` as TEXT contains no fixture
  name, arm id or flag name.**
- **Picks:** append-only; undo returns the pair to the queue; the last line
  wins; resume yields exactly the unpicked ids.
- **Reveal:** refuses on a missing pick and on an unknown pair id.
- **Analysis on synthetic picks with known answers:** direction handling
  (lower-better and higher-better), null handling, ties excluded from `a`,
  Wilson bounds against hand-computed values, the n < 10 rule, the ceiling,
  left-share, the exit-clause rows, the per-fixture sign count, and the ≥ 40
  gate on the exploratory fit (a separable synthetic set must be recovered;
  39 pairs must not run it).
- **Server:** a real `ThreadingHTTPServer` on an ephemeral port — `POST /pick`
  lands one flushed line; `/arms.json`, `/features.json`, `/designs/x` and a
  path-traversal name are 404.
- **Ref arm:** the scratch-path guard raises on an empty or in-repo path; the
  subprocess contract is exercised against a stub driver, not a real worktree.
- **Instrument splits:** `analyse()` output is identical before and after on
  the tools' existing fixtures (their current tests stay green unedited).
- **End to end:** one tiny synthetic image, base + one flag arm, `--render`
  then a scripted pick then `--reveal`.

## 6. Runtime and failure

99 digitizes plus 9 on the old ref. Per-design clocks at customer defaults
have never been recorded (`docs/flag-runtime-bills-2026-09-12.md` measured
the parity config only), so the budget is an estimate — one to three hours,
run in the background, resumable. `--render` records wall-clock per
(fixture, arm) into `features.json`; that table is itself a first
customer-default runtime record.

## 7. Out of scope

Cross-design pairs and any corpus-wide quality scale; a phone/Artifact
picker; any engine change; any default flip; un-clamping the preflight grade;
recalibrating any instrument from the result (a follow-up, with its own
plan, once there is a result to read).
