# EMB-Bot architecture review and critical path — 2026-11-01

**What this is.** Kent asked for a review of EMB-Bot, the most critical path to
success, and an architecture outline that keeps the project pointed at the best
possible automatically digitized embroidery files. This is that document, written
against `main` at `f8e8b450` (PR #1208 merged). It is a review, not a plan: it
proposes, and every phase advance, flip, spend and scope call it names stays
Kent's.

**Method and limits.** ROADMAP, PRODUCT, MASTER_SCOPE (full), DOCTRINE (full,
9,321 lines), COOKBOOK's architecture and conventions, the two director handoffs
(10-23, 10-27), the K3 foreman handoff, the 10-27 pro baseline, the three
lettering boards, the machine-physics backlog and the memory index were read.
The pipeline was mapped from code (`pipeline.py`, `stage7_sequence.py`,
`config.py`, `digitizer_service/app.py`, `app/src/lib/*.js`, `src/*.js`). Three
sub-reads ran in parallel (pipeline map, quality audit, doctrine digest); every
load-bearing claim below was re-checked against the file it cites. **Nothing was
run**: no digitize, no suite, no sew-out. Every number is an instrument reading
with a pointer, none is sewn (gate 1), and every agreement figure is
chance-corrected (gate 4). The previous review of this kind is
[`project-review-2026-08-16.md`](project-review-2026-08-16.md); its §1.1 risk
(two codecs) is closed, its §4 opportunities are mostly built.

---

## 0. The verdict

1. **The engine is large, instrumented and converging on one professional's
   layout.** 77,812 lines in `digitizer_core` across 90 modules, 300 config
   fields, 462 test files, 266 measurement tools, 4,362 commits in 102 days
   (2,074 in October). On the 22 paired jobs, cuts are at parity (391 vs the
   pro's 409), lettering legibility is at or near his in three of four size
   bands, and in-letter trims on 10 mm+ text fell 66 → 21 across the three
   boards (pro 14). *(pro-baseline 10-27; `trim-defects-4-6-2026-10-29.md`;
   lettering boards 10-25/27/31)*

2. **The feedback loop is open at the one place that settles embroidery: cloth.**
   Two uncontrolled sew-outs exist (the Instagram icon 09-01, card v4 paused
   mid-way 10-20). **Eleven controlled cards are built under `docs/sewout/` and
   none is sewn.** 26 fabric-class flags, every fabric preset, and the Studio's
   Medium confidence wait on that. Gate 1 is the right rule and the project has
   honoured it so well that it is now the binding constraint on half the config
   surface. *(`tools.flag_ledger` 11-01: LAYOUT 30 / FABRIC 26 / HELD 5;
   MASTER_SCOPE "No CONTROLLED sew-out card has been sewn")*

3. **The yardstick does not agree with Kent's eye, and the project knows it.**
   Phase 1's exit is unmet: pooled over nine sittings and 49 of his picks, no
   fidelity instrument clears chance; only the trim count does (+0.28). The
   instruments that *do* drive flips he accepts are the pro-pair readings (one
   reader on both DSTs: cuts, needle-up, stitch-type kappa, word cc, columns).
   Those have never been tested against his picks. *(`yardstick-vs-kents-eye-2026-10-11.md`)*

4. **The single most customer-visible defect is ungated and cheap:** whole
   elements drop and preflight grades the file clean. `SHAPE_NOT_STITCHED`,
   `DROPPED_SMALL_SHAPES` and `THREAD_RESNAPPED_AFTER_DRIFT` have **zero
   consumers in `preflight.py`** (grep, 11-01). Kent graded `distressed_grunge`
   Terrible at A 100; 7 of his 14 designs on 08-27 lost an element.
   *(`logo-style-census-2026-10-27.md` items 3–4; MASTER_SCOPE area 1)*

5. **Two structural debts are growing faster than they are paid:** a flag
   surface that grew 64 bool fields in twelve days (49 born and flipped ON, 15
   born OFF), with the regression tripwire (`corpus_scorecard_baseline.json`)
   last captured 2026-10-05, about 55 flips ago; and plan CPU that each flip
   raises 4–31 % toward a 600 s service ceiling that 3 of 21 logo styles and
   7 of 18 photos already exceed.

6. **The reference corpus is one digitizer, ten artworks, logos only.** Every
   pro rule since 10-20 was derived and validated on the same designs. The
   project has started to practise held-out checks; it has not made them policy,
   and it has no second digitizer to tell house style from craft.

The critical path, in order: **sew the cards; adopt the yardstick that works;
make preflight see a dropped element; get a regression tripwire running again;
widen the corpus with held-out pairs; then keep building the lettering
construction gaps the board names.** Sections 3 and 4 say who owns each step
and what it unblocks.

---

## 1. Where it stands

All figures are ours / the pro's, one reader on both machine files, at the pro's
width and garment. The pro baseline is `main 2c6b656c` (10-27) and three
defaults have flipped since; re-run `tools.pro_baseline` before quoting a row as
live. *(`docs/pro-baseline-2026-10-27.md`)*

| job (worst per artwork) | stitches | trims | needle-up mm | stitch-type kappa (chance) |
|---|---|---|---|---|
| goldentee_hat | 11,629 / 5,973 (+95 %) | 26 / 10 | 550 / 289 | 0.58 (0.66) |
| bridge_lc | 15,278 / 8,535 (+79 %) | 32 / 20 | 730 / 214 | 0.04 (0.50) |
| toat_machine_hat | 23,427 / 13,886 (+69 %) | 58 / 31 | 872 / 528 | 0.40 (0.50) |
| precision_drone | 14,547 / 14,552 (0 %) | 92 / 59 | 1,858 / 901 | 0.20 (0.57) |
| becker_hat_large | 16,915 / 12,356 (+37 %) | 24 / 10 | 624 / 416 | 0.20 (0.50) |
| hotel_fremont_patch | 19,292 / 15,458 (+25 %) | 40 / 21 | 726 / 533 | 0.48 (0.44) |

Every job sews more stitches than the pro except Drone. Since 10-27: Becker hat
large trims 24 → 11 (10-30 flip sheet), corpus exposed travel 723 → 429 mm,
cuts 391 vs 409 but **breaks (needle-up moves) 879 vs 425** — 488 short floats
we leave uncut and he cuts. *(`trim-defects-4-6-2026-10-29.md`;
`seam-order-attribution-2026-10-30.md`)*

**Lettering board 10-31** (engine `a8758e96`, pooled, ours / pro):

| drawn height | word cc | columns | trims in letters | stitches | mean satin width mm |
|---|---|---|---|---|---|
| under 4 mm | +0.92 / +1.00 | 117 / 163 | 0 / 4 | 3,719 / 4,504 | 0.78 / 0.90 |
| 4–6 mm | +0.90 / +0.98 | 180 / 181 | 3 / 4 | 7,768 / 8,526 | 1.42 / 1.37 |
| 6–10 mm | +0.84 / +0.92 | 269 / 291 | 6 / 6 | 12,936 / 13,654 | 1.58 / 1.52 |
| 10 mm and up | +0.97 / +0.68 | 163 / 206 | 21 / 14 | 31,304 / 25,277 | 1.67 / 3.13 |

Read: small and mid text is at the pro's construction. **Big letters are the
open gap** — a quarter more stitches from fewer, narrower columns (his MARINE
4.51 mm wide, ours 2.60) and a Becker wordmark sewn at 2× his stitches
(4,815 / 2,301). The worst legibility rows are MFab "AND WELDING LLC" on the
hat (+0.07 / +0.92) and Drone "PRECISION" (+0.05 / +0.82); Drone's cause is
thread contrast and its cure is built OFF as of 11-01
(`lettering_stray_word_thread`, PR #1208). *(`scoreboards/lettering-board-2026-10-31.md`;
memory `lettering-thread-2026-11-01`, `big-letter-construction-2026-10-24`)*

**Satin-vs-fill routing** is no longer the gap: kappa 0.387 over 21 jobs, a
per-region oracle that gives each of our regions the pro's majority type scores
0.365 (below us), and the pro against himself 0.5 mm off is 0.650. The remaining
misroutes are construction and layering, not a threshold.
*(`satin-fill-remeasure-2026-10-29.md`)*

**Photo and gradient lanes** have no pro file and no fidelity instrument; the
judge is Kent's eye on the 39-row Commons corpus (photos 6 / 0 / 0 better /
same / worse after the cut-out guard; logos 1 / 15 / 5 before it). Confidence
stays Low beyond flat spot colour, and that is a settled architectural stance,
not a defect. *(`scoreboards/photo-corpus/README.md`; COOKBOOK "The one rule")*

---

## 2. The architecture as built

### 2.1 Two digitizers, one Design contract

There are two complete raster-to-stitch engines and they never call each other:

- **Python** (`digitizer/digitizer_core`, 77.8k lines) — the active target for an
  uploaded image. Reaches the Studio through `digitizer_service` (`/classify`,
  `/digitize` + `/jobs/{id}`, `/export`).
- **JavaScript** (`src/`, 13.0k lines) — `buildQualityDesign` (image), `buildLetteringDesign` (85
  pre-digitized fonts), the manual-shape lane, and the DST/PES/EXP writers.
  Documented as frozen and "retired in favour of feed it clean flat art", but it
  is the engine every typed name, every drawn shape and every mixed project sews
  with, and the one with **no pro datum at all** (area 2: trims saturate 7–9 per
  8 glyphs; 2,216 uncut floats over 143 designs, 1,993 on bare cloth).

They meet only at the **Design** contract (0.1 mm integers, +y up;
`adapter.plan_to_design` is the one y-flip). Fill, satin, underlay, pull comp,
ties, trims, jumps and colour order are implemented twice;
`test/engine-service-parity.test.js` records the drift; `fabrics.js` is a hand
port of `fabrics.py` held in step by `test_fabric_wire.py`.

**The one line that decides which engine a customer's upload gets is service
health at the moment the element is added**: `resolveArtworkType(health)`
(`app/src/lib/project.js:477`) returns `digitized` when the service answers and
`image` (the JS lane) when it does not. A service hiccup silently routes a logo
to the lesser engine, and nothing on the page says so afterwards. Cap sew order
is ON in JS and OFF in Python for the same garment; `cutEveryJump` and
`cut_every_jump` are two flags for one rule.

### 2.2 The Python pipeline

`pipeline.py` splits at the review-edit seam: `build_generation` (stages 0–4,
cached by `generation_key`) → `finish_generation` (edits, palette, white recipe,
layer order) → `plan_stitches` (stages 5–7) → `adapter` → pystitch.

| stage | owner | what it decides |
|---|---|---|
| 0 classify | `stage0_classify.classify` — a thresholded tree, not a model | lane: `flat`, `gradient`, `photo_subject`, `photo_scene` |
| 1 / 1.25 / 1.5 prep | `stage1_prep`, `photo_signals` (EXIF + YuNet), `stage1_photo_prep` (rembg subprocess) | background, px/mm, face → flat, cut-out |
| 2 region former | k-means (`stage2_quantize`) for flat; SLIC+RAG (`stage2_photo_segment`) for gradient and photo; SAM2 seam OFF | labels → threads |
| 3 segment | `stage3_segment` — **the lanes rejoin here** | masks |
| 4 vectorize + tagging | `stage4_vectorize`, then ~15 tagging passes: enclosed background, dark ink, revalidate, colour cap, **text clusters**, **small-text re-set**, letterform priors, OCR, house angle, strays, widths, design angle | `Region` polygons with `meta` tags |
| finish | white keyline recipe, enclosed white, lettering thread, bean letters, layer order | `PipelineResult` |
| pre-5 | fill-inside-border, keyline slivers, art outlines, **silhouette under-fill (ON)** | regions |
| 5 overlap | `stage5_overlap.resolve_overlaps` — pull comp, underlap, clip; `fragment_absorb` | `PlannedRegion` |
| 6 + 7 | `stage7_sequence.sequence` — one ~2,700-line function; **stage 6 has no pass of its own**: `stitch_one` picks a tier per shape in a fixed order (white field, bean letter, fine bars, hairline, skeleton, small solids, run, outline rings, script, **Column lane**, satin, compact solids, tonal tiers, tatami) then border / edge cap | `StitchBlock`s |
| post-7 | knockdown (beanie), `StitchPlan` | plan |

Two structural facts worth knowing before touching it:

- **Stage 7 runs twice per plan.** The Column lane needs the sew order, so
  `shape_memo.scope` runs `sequence` once with the lane OFF and again with it ON;
  memoized emitters answer the second pass (owl flat 137 → 113 s; it was
  2× before the memo). Every tier flag you add runs in both.
- **"Gradient" is the real logo lane.** 8 of the 14 pro artworks and 14 of the 21
  census logos route gradient at stage 0, and on every one the design-ramp fit
  refuses — so "gradient" means *SLIC+RAG former on anti-aliased flat art*. The
  flat lane's passes have been ported across one at a time (phantom-blend
  dissolve, `snap_region_edges`, dark thin strokes); the lane name no longer
  describes the input. Only Becker, at 1.46 px/mm, routes flat.
  *(`lane-census-2026-10-25.md`; MASTER_SCOPE defect 27)*

### 2.3 Service and Studio flow

Upload → `fitTargetWidthMm` into the garment's placement box (`PLACEMENTS`,
`proSized` ON: hat 113.5 × 64, LC 96 × 76.5, beanie 94.5 × 56 from the pro's
boxes) → debounced `POST /classify` shows the lane → `POST /digitize`, poll
every 500 ms, **wait up to 600 s + 30 s** → review edits re-plan from the cached
generation → `staleness.js` disables Download while stitches trail the config →
DST/PES through `/export` for purely digitized projects, browser codecs for
anything with lettering or shapes; JEF/XXX/VP3 service-only. `/classify`
re-implements stage 0 + 1.25 rather than sharing the function (pinned by a
service test). `/digitize-manual` has no caller.

The 600 s ceiling is now a product fact: a job past `JOB_TIMEOUT_S` stops at
its next stage seam (10-30), and the Studio tells the customer it stopped
waiting. Text-heavy art at jacket-back size finishes in neither arm (W6-01,
unstarted).

### 2.4 Configuration

`PipelineConfig` has **300 fields**: 196 bool-ish (118 default True, 70 default
False, 3 `bool | None`), the rest thresholds where `None` means OFF, plus a
`cfg.extra` dict that still wins over three fields that have since become real
(`absorb_fragments`, `small_text_bay_mouth`, `small_text_reset_grow_away`). The
ledger reads 61 flags built OFF (30 layout, 26 fabric, 5 held) and 12 stale
comments. Since 10-20, 64 bool fields were born and about 55 defaults flipped.

Pins: `FLAT_GOLDEN_MD5` (derived from `testdata/flat_lane_golden.json`),
`tests/engine_2026_10_27.json` via `frozen_cfg()`, `PRE_FLIP` (~50 entries, in
88 test files), `FLIP_2026_10_23/26/27/30`. **Most md5 pins now test a frozen
pre-flip engine, not the shipped one** — by design, so flips do not move them —
leaving three byte-identical tests and the `FLAT_GOLDEN_MD5` riders as the proof
of the shipped path. *(memory `flip-proof-pins-2026-10-27`)*

### 2.5 Instruments and the reference corpus

The method that has worked since 10-20 (director plan §1): pair every job with
the pro's DST, one reader on both files each in its own frame, state his rule
with thresholds, build it OFF, prove it as a picture and a number
(`tools/pro_pair.py`, `flip_sheet_renders.py`), and Kent flips by the number.
Instruments that carry it: `pro_baseline.py`, `lettering_board.py`,
`word_legibility.py`, `trim_census.py`, `satin_fill_census.py`, the kappa
readers in `pro_parity/`, the flip sheet, the eye-pairs blind picker, and the
photo corpus side-by-side.

The corpus those run on: **23 pro files, ~10 artworks, 8 clients, one
digitizer**; hats, left chests, beanies, one patch, one jacket back; 4 arts
route flat (all Becker), 8 gradient, 2 photo_scene; 6 of 11 art files are
vendor re-renders at 148–607 px. Not represented: any photograph with a pro
file, true tonal art with a pro file, a full back, a second digitizer (pro vs
pro, n = 2, scores 75–84 — the metric's ceiling). Free paired ground truth does
not exist; commissioning runs about $400 a design.
*(`paired-ground-truth-sourcing-2026-09-28.md`; memory `lane-census-2026-10-25`)*

Judges that do not work, per the project's own measurement: the pro-parity
scorecard ("changes that visibly improved a garment scored worse"), ARTFID (not
comparable across routes; Kent's 60 % vs its 83.7), the preflight grade
(clamped, no area floor on thread blocks, blind to dropped elements and
illegibility), `stitchviz` (draws a 3-pass bean as one thread). Judges that do:
trims and the pro-pair readings, Kent's eye on a render at viewing size, and his
verdicts on the photo corpus.

### 2.6 Knowledge and process

Four governing docs (155k words; DOCTRINE alone 97k), a 27,000-word live
dashboard under a tested budget, a memory index at its 24,986-character ceiling
with an archive, and a `(verb date — source)` discipline on every claim. The
build process since 10-07 is a foreman or director dispatching cloud workers,
one worktree and one PR each, flags built OFF and flipped in a separate re-pin
PR, auto-merge armed by default, four required CI jobs (the sharded digitizer
~25 min). The swarm is excellent at "state the pro's rule, build it OFF,
measure, flip" and has shipped about 55 such flips in twelve days. It is poor at
structural change, because no worker owns anything wider than one flag — which
is exactly the shape of the debts in §3.

---

## 3. The critical path

Ordered by what each step unblocks, with its owner. The first two are Kent's
and cost no code; nothing engineering can do substitutes for them.

### 1. Sew the cards (Kent; one sitting at the machine)

Kent's 08-21 ruling says the sew-out is accepted as-is and is not to be
re-raised as the highest-leverage next action. A review is the one place to say
it once, with the inventory, and then leave it: **eleven cards are built, zero
are sewn** (`docs/sewout/`: v2, v3/3.1/3.2, passes, lettering-arms,
bay-hold/edge-cap, cross-underlay, v5, v6, v7, hairline). Waiting on them:
`pull_comp_by_stroke` and `pro_measured_values` (fill 3.49 mm, satin 0.37/0.35,
bean 0.95 — the two flags the card v7 memo names as the only ones still on
fabric), `forbid_gap_mm`, `overlap_by_angle`'s knit factor, the hairline tier's
60/75 wt and 1.5 mm stitch, the bean holds already ON as candidates, every fabric
preset, and the Studio's confidence (held at Medium by this alone). Card v8
(`cut_every_jump` OFF beside ON, the 488 uncut floats of defect 4) is **not
built** — v7 is the latest tool — so defect 2 below cannot be released even by a
sew-out until a worker generates it from the v7 pattern.

What it buys: the only path from "candidate" to "constant" for 26 flags, and
the first cloth datum tying any instrument (bare-thread mm, exposed travel,
density) to what Kent sees on a garment.

### 2. Adopt the yardstick that works (one worker, then Kent's ruling)

Phase 1 exits when "the metric's ranking agrees with Kent's visual ranking and
nothing he judges better ever scores worse". The fidelity scorecard fails both
clauses on 115 labelled pairs. The pro-pair readings have never been tested
against his picks. Proposed: pool the nine sittings against `pro_baseline`
figures for the paired designs (cuts, breaks, needle-up mm, stitch-type kappa,
word cc, columns) with the same bootstrap the 10-11 doc used. If they clear
chance, declare them the Phase 1 yardstick and propose the exit; if they do not,
Phase 1 as written is chasing a fidelity metric the corpus cannot defend and
the exit condition needs rewriting — Kent's call either way. The blinded sitting
he ruled on 10-13 still needs 4+ flat lettering logos only he can supply
("Waiting on Kent" 42).

What it buys: a phase that has been open since July either closes or stops
pretending the scorecard is the judge. Every later flip sheet then quotes the
same figure the exit was judged on.

### 3. Make preflight see a dropped element (one PR, ungated)

The highest-leverage engineering item, and nothing gates it. Assemble one
area-weighted "element dropped" finding from the warnings the pipeline already
emits (`SHAPE_NOT_STITCHED` from stage 5, `DROPPED_SMALL_SHAPES` above a floor,
`THREAD_RESNAPPED_AFTER_DRIFT` past a dE threshold). Validate on the 21 census
logos against Kent's grades file: grunge, duotone, QR and Tux must fire; the
eleven Good/Great must not. Severity (block vs warn) is a consumer decision and
Kent's (DOCTRINE). The second half — stage 1 refusing a ground that reaches deep
inside a shape, which is how `distressed_grunge` lost its ring — needs its own
plan doc. *(`logo-style-census-2026-10-27.md` items 3–4; `preflight.py:3003`)*

### 4. Get a regression tripwire running (one worker)

Today a PR can move any job's stitches, trims or kappa in the wrong direction
and go green: the byte goldens pin frozen engines, the scorecard baseline is 26
days and ~55 flips stale, and `art-fidelity-baseline` is `continue-on-error`.
Two steps: recapture the scorecard baseline on cloud Linux and attribute the
movers; then stand up a **nightly** (not per-PR) `pro_baseline` run on the pairs
whose pro files are committed (`Embroidery Files.zip`), with a tolerance ledger
per job and figure, so a wrong-way move on cuts, breaks, needle-up or kappa is
a red the next morning. Per-PR is out: each digitize is 60–600 s and the pro
files for MFab, ProSeal and Bridge are gitignored or uncommitted (the lettering
board in CI already waits on a Kent permission for that art).

**Built 2026-11-02** (`digitizer/tools/tripwire.py`, workflow
`.github/workflows/nightly-tripwire.yml`, ledger
`digitizer/testdata/tripwire_ledger.json`). The population is the 18 pairs
whose art is under `testdata/` and whose pro DST is in the repo — the five
Becker files in `testdata/reference/` and the rest inside the committed
`Embroidery Files.zip` (Becker, Gaulke, Fremont, MFab, Drone, Tires, Golden
Tee, To a T); Bridge and ProSeal stay out, nothing gitignored was added. One
ledger row per job and figure (stitches, cuts, hops, needle-up mm: up is
worse; stitch-type kappa with its chance floor, direction kappa, word cc: down
is worse), the baseline measured on cloud Linux and the tolerance seeded from
the spread of three passes of the same tree on three runners — never a desk
guess. `check` runs nightly on `main` (schedule, never on a PR, never
required) and fails the job on a wrong-way change past tolerance, a figure the
run lost, or a pro-side figure that changed (the reader did). Re-seed after a
deliberate change by dispatching the workflow in `capture` mode and committing
its `tripwire-ledger-<run>` artifact. The first step above (recapture the
fidelity scorecard baseline and attribute its movers) is not done by this.

### 5. Widen the corpus, held out (Kent's money; one worker to intake)

Every pro rule since 10-20 was derived on the same ten artworks it was
validated on, and the project has already caught itself once (`border_by_size`'s
rule was wrong; the pro borders what the art outlines). Two moves:

- **Policy now, no cost:** hold three of the 22 jobs (To a T, Gaulke, Bridge)
  out of rule derivation; a flip PR must show its number on the held-out jobs
  moved the same way. The column-reach census already found "ratio rescues fail
  held-out" — make that the norm, not a finding.
- **Commission 5–8 pairs** in the classes the corpus lacks: a full back, a
  jacket-back text job, a second digitizer on two existing arts (the only way to
  separate house style from craft; pro-vs-pro is n = 2 today), and one photo.
  `tools/pro_intake.py` already registers a new pair. About $400 each.

### 6. Build the lettering gaps the board names (the standing priority)

In board order, all already in the handoff queues: MFab "AND WELDING LLC" on
the hat (+0.07 vs +0.92; the W never reaches the Column lane, L5); the 10 mm+
band's construction (fewer, narrower columns, 2× stitches on BECKER — Kent's
decision 5 from 10-23, copy the pro's cut construction or not, is still open);
flip the Drone thread-contrast cure once its OFF | ON | pro is on the sheet;
Tires script (we read 19.95 of 28.65 mm, 3 columns vs 8). Keep using the
method in §2.5; it is what moved the boards.

### 7. Hold the 600 s ceiling away (one structural lane)

Each flip since 10-20 added 4–31 % plan CPU; 3 of 21 logo styles and 7 of 18
photos exceed 600 s under load; text-heavy jacket-back art never finishes.
Known hot spots with no owner: the `travel_path` family, `_judged_overlong`
(59 of MFab's 102 s), `column_lean`, and the structural 2× of stage 7's second
pass. Target: median 80 mm job under 60 s on Kent's laptop. This is quality
work twice over — the customer's wait, and the CPU slot every census and flip
sheet needs.

### 8. Converge the engines; end the silent fallback (small, then structural)

Cheap first: when the service is down, say so and wait rather than routing the
upload to the JS lane unannounced (`resolveArtworkType`); surface `via` on the
result the way Download already does. Then one authority per responsibility:
Python owns raster → stitches; JS owns fonts, drawn shapes and the writers.
Where a rule exists twice (cap order, cut-every-jump, fabric tables), one flag
and one measurement. The typed-text lane has no pro datum and never will from
this corpus; its judge is the sew-out card (v8's `cutEveryJump` arm).

*Cheap half built 2026-11-02 (Studio only): a down service keeps the upload as a
"digitized" element that says "Digitizer service not reachable; retrying…" with
Retry and "Use browser engine instead"; the JS lane runs for an image only on
that choice, and results name their engine. See memory
`studio-no-silent-fallback-2026-11-02`.*

### 9. A consolidation discipline for flags

Proposed rules, Kent's to adopt: a flag ON for 30 days with no reopened question
loses its switch (the dated `engine_*.json` snapshot keeps the old engine for
tests); a measured wash (`satin_per_stroke`, kappa +0.002) is deleted, not kept
OFF; every new OFF flag names in its config comment the measurement that would
delete it; `cfg.extra` is retired; `test_off_flags_smoke` gains the flagged
pairs that have already interacted (seam order × cuts-first, white recipe ×
under-fill). Target: 300 fields trending down, not up.

### 10. Photo lane: hold

Settled architecture says photographic art out of any auto-digitizer is mush,
the lane has no pro file and no instrument, and Kent ruled 10-27 that its tools
must generalise across genres before more tuning. Keep the "don't make it
worse" census; spend nothing on photo fidelity ahead of items 1–6.

---

## 4. Target architecture

What to change, what to leave.

**Leave alone.** The stage split at the review-edit seam (cache is funded and
works). The Design contract and pystitch as the single format library on the
Python side. The derived satin angle, the 0.15 mm fill row, split-not-fill for
over-long satin, the white recipe as plain defaults, `proSized` placement boxes,
the "button starts every digitize" rule, the no-readouts rule, and every
measured negative in DOCTRINE §B. The pro-pair method and its tools.

**Change.**

1. **One judge.** The pro-pair readings (cuts, breaks, needle-up, kappa, word
   cc, columns), tested against Kent's picks, become the Phase 1 yardstick and
   the nightly regression gate. The fidelity scorecard and ARTFID are demoted to
   reporting; their baseline is recaptured only to attribute movers.
2. **Preflight reads the pipeline's own losses.** A dropped-element finding
   from stage 4/5/7 warnings; later, a legibility finding from the word reader.
   Grades stop being "preflight's own opinion of shapes it already sews".
3. **One engine per input.** Python for every uploaded raster, with the
   degrade path explicit; JS for fonts, drawn shapes, writers. Shared rules
   carry one flag and one test (`test_fabric_wire.py` is the pattern).
4. **Stage 6 becomes a dispatcher, not a region of stage 7.** When the Column
   lane's two-pass is next opened, lift `stitch_one`'s tier ladder into its own
   module with the order as data, so a tier is added once and stage 7 sequences
   once. This is the single largest CPU and comprehension win available and it
   belongs to a long-lived structural lane, not a flag worker.
5. **Config shrinks.** The §3.9 discipline; `cfg.extra` gone; `flag_ledger` as
   a CI check that every OFF flag has a kind, a PR and a deletion condition.
6. **Corpus as a registry with a held-out set.** `pro_intake` is the one door;
   `pro_baseline.py`'s JOBS carries a `held_out` column; the lettering board and
   flip sheet print held-out rows separately.
7. **Cloth closes the loop.** Card v8 generated; one sitting; the readback tools
   that already exist (`readback.json` per card) write the values into
   `fabrics.py`/`machine.py` behind a dated ruling, and gate 1 moves from "no
   constants" to "no constants without a card row".

---

## 5. Risks, ranked

1. **Overfitting one digitizer's house style.** He beans almost nothing, cuts at
   no single threshold, cuts MARINE into 163 columns, and never sews Golden
   Tee's extrusion. Several of those are already ruled "don't copy"; the risk is
   the ones not yet noticed. Mitigation: §3.5.
2. **A flip wave with no tripwire.** ~55 flips against a baseline from 10-05;
   interactions have bitten four times (seam order × cuts-first; seam order
   alone pushing Becker beanie 38.6 → 105.8 mm exposed; white recipe exposing
   D1–D3; lettering thread moving MFab a cone). Mitigation: §3.4, §3.9.
3. **The 600 s ceiling.** Already crossed on a sixth of logo styles under load.
   Mitigation: §3.7.
4. **Candidates sewing as if settled.** About twenty values flipped ON as
   "candidates" (bean holds, zigzag cap, square-end bounds, knockdown rows) have
   never met cloth; a sew-out is the one thing that reopens them. Mitigation:
   §3.1.
5. **Silent engine fallback.** A logo digitized by the frozen JS lane because the
   service blinked, with no trace. Mitigation: §3.8.
6. **Knowledge cost.** 155k words to onboard; the memory index at its ceiling;
   stale pointers (§7) that fail toward refusal. Mitigation: keep the budgets;
   let the archive grow; fix the pointers below.

---

## 6. Already ruled or disproved — do not re-propose

Short list; DOCTRINE has the numbers.

- Raising `SATIN_MAX_WIDTH_MM` or `SPLIT_SATIN_ABOVE_MM` (the pro's p90 column
  is 5.00 mm; the gap is segmentation).
- A per-region satin/fill router (oracle 0.365 < ours 0.387).
- Stage-0 recalibration on synthetics; "route by consequence" 6b; forced flat
  as a general cure (worse on 5 of 6).
- SAM2 as a logo region former (0–8 masks); font identification (IoU 0.9 is a
  wrong font); `chain_links` (bare-fabric thread; permanent).
- Copying MARINE's 163 columns before the construction study; Golden Tee's
  +95 %; the TM mark.
- Cap centre-out in Python (+225 % needle-up); `cut_every_jump` ON without the
  walk (trims 434 → 674).
- Smoothing region polygons, a design-wide fill-angle objective, blanket satin
  borders, thread-paint on faces.

---

## 7. Stale pointers found on the way

Not fixed here; each is one line in its file.

- `digitizer_core/adapter.py:15-25`, `export.py:17-20`, `app/src/lib/digitizer.js:21-28`
  still say `dst.js` is transposed and needs a sew-out; fixed 09-08.
- MASTER_SCOPE area 1 "Satin as SEWN 44.3 % vs 2.2 %, the biggest measured gap"
  predates the Column lane; the board reads columns 163 vs 206.
- MASTER_SCOPE "six of seven real logos route gradient" → lane census 8/14.
- MASTER_SCOPE "START HERE → 42.5 baseline" is ARTFID, which the file says never
  to quote.
- COOKBOOK flag list: `clip_keep_pieces`, `subpixel_corner_runs` listed OFF; ON
  since 10-20.
- `pipeline.py:2037` says `absorb_fragments` built OFF; `config.py:1858` defaults True.
- ROADMAP gate 3 names "contour", an opt-in nobody proposes flipping.
- `digitizer/README.md`: "127 tests", DST codec "has NOT been changed".
- MASTER_SCOPE's sew-out section does not record the 10-20 card v4 sitting.

---

## 8. What this review did not establish

Nothing was digitized or sewn, so no number here is newer than its pointer.
The CPU figures were measured on a loaded laptop and may be 2.6× high. The
typed-text lane was read, not measured against anything. Whether the pro-pair
figures agree with Kent's eye (§3.2) is the question this review poses, not one
it answers. And this is the fourth document to describe EMB-Bot's state from
the outside; the three before it were each partly wrong within a day — expect
the same here, and check a claim against its pointer before building on it.

---

## Decisions this review puts to Kent

1. A date for one card sitting (v7, plus v8 once generated).
2. Whether to test the pro-pair figures as the Phase 1 yardstick (and rewrite
   the exit if they fail too).
3. Severity for the dropped-element finding (block or warn).
4. Whether to commission held-out pairs, and which classes first.
5. Decision 5 from 10-23: copy the pro's cut construction on big letters, or not.
6. Whether to adopt the flag consolidation rules in §3.9.
