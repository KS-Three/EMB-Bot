# Gap audit — eight-domain census, nine investigations, 2026-09-12

A deep research sweep across the whole project: what is missing, what nobody has
measured, and where two sources disagree. Run as 38 agents in six phases (census →
triage → investigate → verify → critique → synthesise).

**Read the method limits first — they change how much weight each finding carries.**

## Method, and where it broke

- **8 domain teams** produced **91 raw gaps**. Every team was told to check against
  code rather than restate a doc, and to grep `DOCTRINE.md` before reporting so a
  settled ruling came back as a ruling, not a finding.
- **The triage input was truncated at 220 000 characters**, so only 6 of the 8
  domains reached the ranker. The doc-vs-code discrepancy audit and the
  product/market team were censused but never ranked. Their findings are in §3 and
  §5 below, pulled from the journal by hand.
- **26 of the 38 agents failed on usage limits** (session limit at 21:10 UTC, then
  the weekly limit). All 9 investigations completed. **Only 1 of 18 adversarial
  verifications ran**, and the critique and synthesis stages never ran at all —
  this document is written from the journal instead.
- **That one verification matters more than its count suggests.** It returned
  *stands-with-corrections* and caught a real re-discovery: investigation 1's
  "13 of 249 designs, 1 832 stitches, worst 23.6 mm" is the same population already
  published in `docs/superpowers/plans/2026-09-11-wide-columns-in-lettering.md` §5,
  re-counted per design instead of per font. **The prior for the eight unverified
  investigations is therefore that some of them also re-derive known numbers.**
  Treat every §2 entry as single-source until re-checked.
- Main moved four times during the run (#465, #467, #469, #470) and twice more
  before this was written (#472, #474). Findings were re-confirmed against
  `origin/main` where the investigation says so.

---

## 1. The verdict

EMB-Bot's engine is in better shape than its *ability to know that* is. The four
patterns below crossed three or more domains each, and every one of them is a
failure of measurement or of bookkeeping rather than of geometry. Nothing found in
this sweep says the stitches are wrong; a great deal of it says the project cannot
currently tell when they become wrong, which copy of a fix is the one that ships,
or which of its own written blockers is real. The single highest-leverage finding
is that **ten of thirteen load-bearing blocker claims are false against HEAD**, and
the errors run toward *false refusal* — sessions declining work that is not
actually blocked. That is precisely the failure mode that cost six weeks on the DST
axis bug.

## 2. The four cross-cutting patterns

**1. A fix lands on one copy of N, and nothing compares the copies.** *(measured
2026-09-12 — investigation 1)* The DST axis fix reached `src/dst.js` and
`src/dstimport.js` but **not `tools/render-dst.mjs`**, whose `decodeDelta` still
reads X from the high nibble. Rebuilt with both decoders, **85 of 85 committed font
previews are exact dimension transposes** and 0 of 85 of today's renders match the
corrected decoder. `tools/sewout_bridge.mjs` prints two contradictory sizes for one
file in a single JSON output — `[96,66]` from the renderer and `[66,96]` from the
round-trip — and nothing compares them, so **the preview a human checks before
committing thread to the gate-1 sew-out is a quarter turn from the card it would
sew.** Lock stitches and `MAX_STITCH_MM` exist in Python and nowhere in `src/`.
`test_fabric_wire.py` was the lesson from law 26's month of silent underlay drift;
it was applied to the fabric table and stopped.

**CORRECTED 2026-09-13, by censusing it instead of restating it.** This entry said
"eleven physical constants are hand-mirrored JS↔Python with two guarded", and both
halves were wrong. *(measured 2026-09-13 — `digitizer/tests/test_machine_wire.py`)*

- **19 constant names carry more than one declaration, not eleven. 17 agree.**
- **The duplication is not only across the language boundary.** `FILL_ROW_MM` has
  **three** copies (`src/digitize.js`, `src/satinfont.js`, `machine.py`);
  `UNITS_PER_MM` has four; `THREAD_WIDTH_MM`, `MM_PER_INCH`, `DST_UNITS_PER_MM` and
  `TRANSPARENT_INDEX` are JS↔JS pairs with no Python side at all.
- **Both disagreements are deliberate and documented on both sides**, not drift:
  `SATIN_MAX_WIDTH_MM` (3.0 browser / 5.0 Python, the merge owned by a sew-out) and
  `MAX_DELTA` (121 in `dst.js` / 127 in `exp.js` — two formats' real per-axis record
  limits, a name collision rather than a copy).
- **Three wire tests already existed, not two** — `test_fabric_wire.py`,
  `test_code_wires.py` (warning codes) and `test_charts.py` (thread charts).

So the constants were in better shape than this document claimed. What was missing
was anything *checking* them: the agreement was held by hand and by comment.
`test_machine_wire.py` now asserts all 19, pins the two divergences with their
reasons, and fails when a pinned one silently comes true.

**The first cut of that test was itself the bug it was written for.** It took
"first declaration wins", so drifting `satinfont.js`'s copy of `FILL_ROW_MM`
changed nothing it could see — a mutation test walked straight through it. That is
why it now counts every copy.

### The logic half of the same census *(measured 2026-09-13)*

Constants were the easy half. The three duplicated *behaviours* this entry named:

- **The long-stitch split across the three browser encoders — one already fixed,
  one still open.** PES was closed by #465 on 2026-09-12 (`PEC_MAX_SEWN_DELTA =
  121`), on the same day the census ran and against the checkout it ran on, so that
  recommendation is spent. **EXP is the last one out of line.** It uses a single
  `MAX_DELTA = 127` for both its record limit and its sewability split, where
  `machine.MAX_STITCH_MM` is 12.1 and both other encoders split at 121. Measured on
  one design — a 6-step sewn chain of 12.5 mm axis moves, encoded by all three and
  decoded with `pystitch`: **DST 12 sewn / worst axis 12.1 mm; PES 12 / 12.1; EXP
  6 / 12.5.** One design, three sew-outs, and only EXP's carries a move past the
  ceiling — which is the sentence `pes.js`'s own comment records about PES *before*
  it was fixed, and that comment even names the outlier: *"121 rather than EXP's 127
  so that a PES file never carries a sewn move DST would have split."*
  **Deliberately not fixed here:** Kent ruled the PES split; this is the same kind of
  call and changes every `.exp` a customer exports. Pinned in
  `test_machine_wire.py`'s `SEWN_SPLIT_DIVERGENCE` with the measurement, so the
  flip is a one-line deletion plus the `crossval` pin — exactly the shape the PES
  flip took.
- **Lock stitches and `MAX_STITCH_MM` are ABSENT from the browser lane, not
  divergent.** Confirmed: zero hits for `MAX_STITCH_MM` in `src/`, and the only
  `lock`/`tie` match anywhere in `src/` or `app/src/lib/` is the brand name "Baby
  Lock" in a `garments.js` comment. Python has `stitches.apply_ties` used from
  `stage7_sequence` and `stage6_applique`. That is a feature gap rather than a
  drift, so a wire test is the wrong instrument for it; the dossier already priced
  the port at **+2.93% stitches and zero added trims**.
- **`REG_IOU_FLOOR` guards 1 of 8 call sites.** Confirmed: it is declared and used
  only in `pro_parity/pairframe.py`, while `scorecard.register(...)` is called from
  `blockcensus.py` (×2), `gateprobe.py`, `pairframe.py`, `regsweep.py` (×2),
  `scorecard.py` itself and `splitprobe.py`. Seven of the eight take an alignment
  with no floor check — the failure mode #463/#466/#467 spent three PRs on. This is
  research tooling rather than product, which is why it is recorded and not fixed
  in the same pass.

**2. A number measured at one operating point becomes a standing claim.** Stage 0's
lane census at one k-means seed, one resolution, one pre-denoise decode. The edge
cap's cost at one width, which #469 showed reaches +58.7% eight millimetres away.
`design_angle` priced at 95.7 mm, where the design has already collapsed to tatami.
The cheap countermeasure, proposed independently in three investigations: **every
instrument should print the perturbation it is stable under, beside its verdict.**

**3. The counter and the sentence measure different quantities.** Stage 3 counts
regions and tells the customer "5" when 1 170 left. `QualityReport` counts cones per
element on a screen whose recap counts per design. `corpus_scorecard`'s 52 rows are
26 designs twice. In each case the fix is to measure the quantity the sentence is
about — usually area, or per-design — rather than the one that was easy to count.

**4. The document that gates the decision is behind the tree, and the error runs
toward false refusal.** `MASTER_SCOPE.md` went untouched across four merges while
three of them touched `DOCTRINE.md`, so the "live dashboard" is the stalest
read-first file. See §3 — this is the one with money attached.

## 3. Corrections — claims that are false against HEAD

*(all measured 2026-09-12 — investigation 4 unless noted; re-confirmed against
`git show origin/main:<path>` rather than the working tree)*

| Claim | Where | What is actually true |
|---|---|---|
| `src/dst.js` "uses the transposed table"; the two encoders are "a quarter turn apart"; "unresolved by design — it needs a sew-out on the shop's Tajima" | `digitizer_service/formats.py:9-15` | All 26 stitch+jump records are byte-identical to `pystitch.DstWriter.encode_record`. A rendered "FRITSCH" export draws upright and unreversed. **False for five days, across 50+ merges, and it invokes gate 1 for a question settled 2026-09-08.** |
| The same claim, in **present tense**, as the stated justification for the `preferService` gate | `app/src/lib/exporters.js:21-27` | Same refutation. Not in DOCTRINE, not in the assignment's list — found by sweep. |
| The 20 stripped glyphs "need the Ink/Stitch SVG sources in `scratch_ink/`, which exist on Kent's machine" | `test/font-dead-glyphs.test.js:58`, `tools/build-font.mjs:257` | 6 of 6 fetched over plain HTTPS, 862 KB–1.17 MB, no auth. **20 of 20 roaring glyphs carry an authored run length.** The question that "needed a local session" is answered. |
| "U01 loses the colour change entirely" | `MASTER_SCOPE.md:340` and `:681` | U01 preserves every colour block: N colours → N `NEEDLE_SET` records, for N = 1, 2, 3, 5, all 60 coordinates round-tripping at max delta 0. #465 already recorded this correction on 2026-09-12; the status doc still carries the old claim. |
| `split_satin` wiring "has not landed" | `digitizer_core/config.py` | Wired at two call sites — `stage7_sequence.py:1464` and `stage6_applique.py:1117` — verbatim as the comment describes. |
| Appliqué is an explicit non-goal | `PRODUCT.md:67` | `stage6_applique.py` is 1 373 lines with 66 tests and eight config fields. *(confirmed by me, 2026-09-13)* |
| `digitizer` CI job runs "10 to 42 minutes" | `CLAUDE.md`, `MASTER_SCOPE.md`, `DOCTRINE.md` | Re-measured twice: agent n=114 → p50 37.1 / max 72.1; my own n=88 → **min 22.4, p50 40.8, p90 53.8, max 72.1, and 48% of runs exceed the documented ceiling.** "Budget half an hour, read a 35-minute job as normal" now inverts. *(measured 2026-09-13 — public Actions API)* |
| `MASTER_SCOPE.md` says both "**FIRST PHYSICAL STITCH-OUT 2026-09-01 — thread has met cloth**" (line 35) and "**No physical sew-out testing has occurred yet / Zero sew-out testing**" (lines 408-410), with line 254 repeating the false half | `MASTER_SCOPE.md` | One 800-line current-state file, contradicting itself about the event ROADMAP phase 5 exits on. *(confirmed by me, 2026-09-13)* |
| PRODUCT.md: 85 sidecars "ship beside" the binaries in `app/public/fonts/bin/` | `PRODUCT.md` row 7 | `bin/` holds 85 `.embf` and **zero** sidecars; the 85 sidecars are one directory up. The invariant holds, the path does not. Same row's "55-font manifest" is now 85. *(confirmed by me, 2026-09-13)* |

**Three threads were being refused on paper and are not actually blocked:** the
`formats.py` sew-out demand, the `exporters.js` routing justification, and the
`scratch_ink/` glyph question.

## 4. What the sweep found that the project did not already know

Ranked by leverage. Every entry is **single-source and unverified** except where noted.

**1. No automated guard fails when the shipped engine gets worse — and the
regression was already written into a CI artifact nobody reads.** *(measured — inv. 2)*
40 `artfid-baseline-<sha>` artifacts were fetched **unauthenticated** and ordered
along main. On the 2026-09-11 edge-cap flip (`59085f7`, PR #455): corpus thread
**+9.10%**, 11 of 14 fixtures moved, and the CSV's `preflight_grade` for
`logo_script_tires` went **A 100 → B 88**. ARTFID itself did not see it. CI was
green. The art-fidelity job is `continue-on-error` and fetches no prior artifact.
The flat-lane byte-identity golden — the strongest regression guard in the repo —
**covers 79% of the shipped stitch stream and 0% of the block the flip added**: its
4 550 coords are an exact prefix of the shipped 5 745. All six `conftest.PRE_FLIP`
flags ship ON, so the goldens pin a configuration that does not ship.
*Cheapest fix, no new instrument and no invented threshold:* widen
`corpus_scorecard`'s exit code from "a new block finding" to "a grade band fell" —
the committed pre-flip baseline already holds that row at A 100 and the diff already
prints `grade: A -> B`. Causally proved at HEAD with a two-arm A/B.

**2. The satin/fill cliff is a sub-pixel raster artefact, and no measurement-only
fix stabilises it.** *(measured — inv. 3)* Nine 1 mm steps between 60 and 108 mm
swing Becker's sewn-satin share by ≥ 17 points; 87 → 88 mm crosses 42.5% → 12.8%
and **+73% stitches**. At 85 mm the banner reads `explained` = 0.799796 — **0.79 of
one skeleton pixel** below the promote threshold, deciding **+4 923 needle
penetrations**. Two causes: `rasterize_polygon`'s 6 px/mm floor stops adapting above
~1.333 mm wall, and a real −0.14 drift in the polygon itself from a fixed 0.2 mm
simplification against 146×91 px source art. **Five reparameterisations were tried
and all nine-crossing or worse — a measured negative.** Only **area-weighting**
survives, and finding 8 sizes it. Claim (b) confirmed on four independent measures:
the flipped satin state is *the professional's* state, not merely the cheaper one.

**3. Stage 0's lane verdict is a property of the decode, not the artwork.**
*(measured — inv. 7)* **7 of 29 fixtures (24%) change lane** under at least one
perturbation that is not a change to the artwork: the k-means seed moves
`logo_script_tires` across gradient/photo_scene/flat; a one-pixel resize flips
`enthusiast_logo`; and **applying the bilateral filter stage 1 runs one call later
moves 6 of 29, every one leaving photo territory.** `UCM_PHOTO_MIN = 0.28` was
sited on `photo_scene_stub`, whose signal reads 0.4256 today and **0.0346 after one
pass of stage 1's own default denoise** — the calibration fixture's margin is
deleted by the next stage. Separately: `logo_golden_tee.jpg` is **enrolled in
`color_diversity.CORPUS` as flat/real and is tonal artwork** (rendered), which
matters because that corpus is the one gate 2 would re-site stage 0 on.

**4. The Studio's worst customer-facing defect is silent data loss.** *(confirmed —
inv. 6)* Three of four `.embproj` inputs **open as an accepted blank design carrying
the customer's own file name, with no error**: `migrateProject` matches
`version === 2` strictly and otherwise falls through to `defaultProject()`. Also
measured: `INPUT_LOW_RESOLUTION` has a false-positive window on **7 of 26 fixtures**
because it tests the clamped raster rather than the file (exact fix available — the
app already holds the naturals); and no `BACKGROUND_UNCERTAIN` deep-intrusion firing
survives a colour-precision gate — rendered, it is pointing at **the white inside
letterforms**, the code's own admitted false-positive class.

**5. Artwork loss is counted in regions and never in area — and the headline number
was misattributed.** *(measured — inv. 9)* Stage 3 removes **5 090 regions /
400.8 mm² by absorb** and 819 / 25.8 mm² by drop across ten real logos. The
`phone_ui` "count=5, cleaned_total=1170" is **two stages**, not one: stage 3 drops
513 regions / 14.06 mm², stage 4 `vectorize` drops a further 657 / 42.7 mm², and
`pipeline.merge_warnings` silently discards stage 4's `largest_mm2`. Absorb is
**recolouring, not deletion, and almost none of it merges into the shape the sliver
belongs to**: on Fremont 131.2 of 133.6 mm² lands at ΔE ≥ 25 and 0.0 mm² under
ΔE 10. Rendered, the absorbed set on Fremont is the entire "EAT | STAY | PLAY"
wordmark, the rope border twist, "EST 1895" and the star.

**6. The browser lettering lane ships files the Python lane's own rules reject.**
*(measured — inv. 5)* Zero tie/lock records exist in `src/` — the only hit for
lock/tie is the brand name "Baby Lock" in a comment. Porting `stitches.tie_run`
costs **zero added trims** and +2.93% stitches across the 75 satin fonts. The
per-axis DST rule says the corpus is clean (worst 11.0 mm), but **16 designs break
the Euclidean-length rule the Python lane's own preflight uses**, and a per-axis
split cannot fix them: DST and EXP split per axis, so the longest emittable segment
is a **17.1 mm / 18.0 mm diagonal**, 41% past the ceiling. Porting `exp.js`'s split
loop into `pes.js` is **byte-identical on all 2 550 quick-start designs** and moves
exactly 23 files, all of which already carried an over-record stitch.

## 5. Refuted, and already-known

- **ARTFID cannot answer phase 1's exit condition, and fixing its ink rule does not
  change that.** *(measured — inv. 8, `refuted-the-premise`)* 15 of 26 fixtures
  refuse on artwork alone. A border-ground-relative Lab rule is a genuine
  improvement — it fixes the letterbox defect and raises n from 7 to 13 — but
  **both n=9 and n=13 remain null**, and the fix makes the metric's
  most-documented row *worse*: `logo_gaulke_roofing` moves 32.2 → 83.0 on
  byte-identical engine output. Otsu is **worse than the current rule** on white
  grounds (IoU 0.731 vs 0.868) and collapses on dark (0.067). Ship the ink rule as
  a correctness change with the sample-size claim removed; do not ship it as a way
  to enlarge the study.
- **The long-stitch defect does not exist on the digitizer lane at all.**
  *(measured — inv. 1)* 26 fixtures × 8 formats, written twice and sha256-compared:
  **208 byte-identical, 0 differ** — the longest sewn segment anywhere in the
  corpus is 5.10 mm. The defect is real only on the **lettering** lane, where the
  service is the only JEF encoder.
- **The photo lane omits the enclosed-counter guard, and it costs nothing today.**
  *(measured — inv. 9, the investigator's own hypothesis, refuted)*
- **The service's 8-format orientation sweep is mirror-blind** — a mirroring writer
  passes every assertion on all 8 formats with the bounding box agreeing to 0.00 mm.
  *(measured — inv. 1)* This is the 2026-09-08 lesson re-armed: a bbox fits a turn
  and a mirror equally.

## 6. Blocked on data — the shopping list

- **The stage-0 re-siting (gate 2).** Blocked on real tonal artwork, of which the
  repo has one (`drone_render`). The candidate signal's margin is **zero if a
  photograph counts as tonal**. What would unblock it: real tonal customer artwork
  in the committed corpus, plus a correction to `logo_golden_tee`'s flat/real label.
- **`satin_ceiling` vs the split threshold (3.0 vs 5.0)** — 7.61% of sewn segments
  across 79 of 85 fonts. The census called this **the best-specified sew-out card
  brief it produced**; it should ride the next card.
- **`splitSatin` default-ON rests on unsewn constants.**
- **No file this project has produced has ever been loaded by a real machine.**

## 7. Kent's decision queue

1. **`MASTER_SCOPE.md` is at exactly 800 lines** and its own rule is compact-before-adding.
   Nothing from this audit can be filed there until that call is made.
2. **Appliqué — in scope or parked?** `PRODUCT.md` says non-goal; 1 373 lines ship.
3. **Area-weighting for `classify_ribbon`** — the only one of PR #469's three
   candidates that survived measurement.
4. **FLIP as a second yardstick column** (see the sourcing dossier) — needs one
   blind ranking session from Kent to be worth anything.

## 8. What this sweep could not see

- **The verify stage.** 1 of 18 ran. It found a re-discovery on the first thing it
  looked at.
- **The completeness critique never ran**, so nothing audited what the eight domains
  collectively missed.
- **Two domains never reached triage** (§3 is their salvage).
- **No browser was driven.** The Studio findings are read from source and from
  Node-side runs against `app/src/lib/*`, not from a real browser — and this
  project's own standing lesson is that a Studio change is not verified until it has
  been *looked at*.
- **No sew-out, no machine, and no access** to `scratch_corpus/`, `scratch_ink/` or
  the tonal acceptance set.
