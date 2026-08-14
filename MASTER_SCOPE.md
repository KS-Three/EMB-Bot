# EMB-Bot — Master Scope

**What this is:** a live status dashboard, not a requirements doc. It exists so
Kent and any Claude session can answer "where do we actually stand?" without
re-deriving it from a dozen spec/plan docs each time. It tracks five product
capability areas on two independent axes — **Status** (is it built) and
**Confidence** (do we trust it) — plus cross-cutting issues that don't respect
area boundaries.

**How it's kept current:** updated proactively after PR-sized work lands, and
on demand via the `/update-master-scope` skill. See "How this document works"
at the bottom for the authority model behind the confidence ratings.

**Last updated:** 2026-08-14. Dated history — every "we shipped X on date Y"
entry this file used to carry — now lives in
[`docs/scope-history.md`](docs/scope-history.md). **This file is current state
only.** See "How this document works" at the bottom for the rules that keep it
that way, including the line budget.

**Every claim below carries a pointer** in the form
`(verb date — source)`: `confirmed` means checked against code or a passing
test, `measured` means a number was produced, `suspected` means neither. Treat
a claim with no pointer as unverified — and if you find one, either verify it
or move it.

---

## Live defects — believed true right now

1. **Every shade of every decomposed region sews in the same colour.**
   `stage6_blend` and `stage6_streamline` both compute a per-shade chart snap
   (`shade_thread_idx` / `shade_rgb`) and put it in their report; nothing reads
   it. A block's thread is `group[0].region.thread_index` — the region's ONE
   assigned thread. The blend tier has never produced multi-thread shading in
   the product. *(confirmed 2026-08-12 — `stage7_sequence.py:1347`; verified on
   `gradient_ramp_linear.png`, which accepts at r² 1.0 with 4 shades and still
   emits 2 blocks / 1 colour change)*

2. **No width floor under satin.** 19 of 162 corpus regions, all photo-class,
   sew sub-millimetre satin — Law 31 violations. A near-free
   `2·p90 < ~1.0mm → run` reroute is proposed, gated on a threshold sweep plus
   the sew-out. *(measured 2026-08-11 — `docs/dt-first-verdict-2026-08-11.md`)*

3. **14 jump-trims on an 80mm design,** in every fill variant measured.
   Not started. *(measured 2026-08-12 — scope-history)*

4. **Auto-digitized `becker logo.png` rates well below its professionally
   digitized version.** Forcing the flat lane on textured logo art makes it
   *worse* — k-means shatters texture, `summit_badge` 8,263 → 9,579 stitches.
   Closing this needs an edge-preserving flatten BEFORE region forming, plus a
   side-by-side against the pro file. Blocked on Kent supplying
   `becker logo.png` + the pro DST/PES. *(measured 2026-08-13 — scope-history)*

5. **Satin-vs-fill routing sits at chance, and misroutes in BOTH directions.**
   Against the 23 professional designs, the engine's satin/fill *mix* nearly
   matches the pro's — so the cap is not simply set too high or too low — while
   the per-place agreement is barely above chance: roughly a third of the ground
   the pro satins is sewn as fill, and roughly a third of what it fills is sewn
   as satin. Two designs score *below* their own chance floor. The failure is
   the classifier picking the wrong shapes, not a global threshold, so retuning
   `satin_max` alone cannot fix it — it would only move the mix that is already
   right. `is_satin_candidate` (`stage6_satin.py:185`) is three rejection gates
   with no path that promotes a shape back to satin, which is the shape of the
   hypothesis to test first. *(measured 2026-08-14 — confusion matrix over the
   pro-parity corpus; per-design detail in area 1)*

---

## Standing rulings — decided, do not re-litigate

- **The shading fix goes UPSTREAM.** Two options were on the table: teach
  stage 5/7 that one region can own several thread stops, or split
  tonally-diverse regions at segmentation so the existing one-thread-per-region
  model carries them. Kent picked the second — smaller blast radius, no new
  machinery downstream. Implemented as `split_tonal_regions`
  (`stage2_photo_segment`, **default OFF**). *(ruled 2026-08-12 — scope-history)*
- **Option A for the ramp-less path: tatami + shade bands.** Add a
  darkness-based fallback at `stage6_blend.blend_fill`'s `if model is None:`
  branch so a ramp-less region still decomposes into 3–5 shades. That branch is
  the norm, not an edge case — all 25 regions of `owl_kent.jpg` land there. The
  obstacle, and where the design effort goes: `_shade_layers` returns a
  *continuous* membership function, and tatami needs actual polygons per shade.
  `_band_clip` does not help — it slices by ramp position, which is exactly what
  doesn't exist here. **Write the design before the code.**
  *(ruled 2026-08-12 — scope-history)*
- **Engine quality is a parallel investment, NOT a launch gate.** SAM2 ships
  post-v1 as an opt-in download. *(ruled 2026-08-11 — PRODUCT.md,
  `docs/sam2-ship-path-brief-2026-08-11.md`)*
- **Real-photo provenance is not a concern**, so real photos are cleared to land
  as corpus fixtures. *(ruled 2026-08-12 — scope-history)*
- **Draw shapes stays a right-click canvas tool**, not an upload tile — Kent's
  amendment to "remove all of the unnecessary upload buttons".
  *(ruled 2026-08-13 — PR #138)*
- **Leave `MERGE_DELTAE00_THRESH` at 26.0.** No evidence for retuning it on a
  real photo, and its own tuning history says a global change costs more than it
  gains. *(measured 2026-08-12 — `stage2_photo_segment.py:452-496`)*
- **Do not spend time on `stage4_vectorize`'s re-snap code.** Current-thread
  error sits within ~1 dE00 of best-possible on nearly every shape; the re-snap
  is working and has almost nothing left to win. A shape whose own pixels differ
  from each other by more than the error being complained about cannot be
  matched by any single thread. *(measured 2026-08-12 — scope-history)*
- **`photo_segment_sam2_max_side_px` stays 1024.** *(measured 2026-08-11 —
  rejection recorded at the field in `config.py`)*
- **`feat/svg-import-shapes` is not resumed.** 277 commits behind, and the one
  task attempted past the tokenizer is genuinely broken against its own
  tolerance. If the need resurfaces, treat it as a fresh plan against current
  `main`, not a rebase. Branch left in place; deleting it is Kent's call.
  *(decided 2026-08-07 — scope-history)*

---

## Measured negatives — built or proposed, then rejected. Do not rebuild.

- **`blend_tonal_bands`** (banding inside the fill tier) — built, measured,
  **removed** in the same pass. It decomposed the geometry correctly and changed
  nothing visible, because the shades still shared one thread: 7,725 → 10,126
  stitches, trims 33 → 105, `color_changes` unchanged at 13.
  *(measured 2026-08-12 — scope-history)*
- **Subject-relative streamline `d_sep`** (the "cheap" alternative to option A)
  — retunes a tier with its own calibration history, against designs that
  currently work. Not cheaper than A, lower ceiling.
  *(measured 2026-08-12 — scope-history)*
- **DT-first classifier architecture swap** — the patented rule as printed sends
  62/83 clean satins to fill; corrected arms lose every disagreement they
  create. *(measured 2026-08-11 — `docs/dt-first-verdict-2026-08-11.md`)*
- **Swapping the SAM model** — in automatic-mask-generation mode SAM2's image
  encoder is only ~8% of per-image cost and the `points_per_side**2` prompt
  loop is ~92%, while every lightweight SAM variant optimizes the encoder.
  SAM 1 is *heavier* (375 MB smallest checkpoint).
  *(researched 2026-08-11 — `docs/sam-alternatives-research-2026-08-11.md`)*
- **FastSAM and EdgeSAM are license-disqualified** — FastSAM is AGPL-3.0 despite
  a README claiming Apache, EdgeSAM is non-commercial (NTU S-Lab 1.0).
  *(suspected 2026-08-11 — came from a research subagent, never independently
  re-verified; strong leads, not settled fact)*
- **Size-proportional `simplify_tol_mm`** — the fixed 0.2 mm constant is correct
  as-is; Ember's scaling equivalent is not a like-for-like comparison. No change
  made, and the investigation is closed rather than open.
  *(measured 2026-08-07 — `docs/scope/research-backlog.md`)*

---

## Corrections — suspicions this document itself raised, then disproved

Both entries are kept rather than deleted, because the failure mode they share
is the reason this file is now split: **a hedged observation loses its hedge as
it is copied forward.** Seeing the pattern is worth more than a tidy document.

- **`streamline_mode: "layered"` does NOT have the blend tier's row-pitch bug.**
  It was flagged as a likely twin on the strength of a note that layered
  "measured a negative (3,220 stitches, sparser than baseline)". That note
  compared layered against **tatami**, not against streamline-mono. Run directly,
  layered is consistently *denser*: `owl_kent.jpg` 1,902 → 3,215 (2.1×),
  `fur_ramp.png` 326 → 696 (1.7×), `gradient_ramp_linear.png` 614 → 1,918
  (3.1×). **No fix needed; do not go looking for one.**
  *(measured 2026-08-13 — scope-history)*
- **`_speckle_ratio` is not scale-broken.** The original note (0.35 max vs
  values of 39.93 / 49.45 / 78.72 on real regions) was hedged "confirm before
  trusting it" and hardened into a stated defect as it was copied. It computes
  an **unnormalised Laplacian-gain ratio**, so its scale is not comparable to a
  0–1 ratio by inspection, and it discriminates correctly at the shipped
  threshold. *(confirmed 2026-08-14 — `stage6_blend.py:295-299`)*
- **Not a defect, recorded so it isn't re-found:** the noise fixture in
  `test_blend_falls_back_to_ordinary_tatami_on_speckle` never reaches the speckle
  gate — r² is tested first and random noise fails it, so the branch that test is
  named for is not the one it exercises. Behaviour is correct; the test now says
  so. *(confirmed 2026-08-12 — scope-history)*

---

## Gotchas — cost someone a session once

- **Stage 0's `photo_subject` gate is bimodal** — textured subjects on smooth
  backdrops can't reach `photo_subject`. Pinned in the routing test's docstring.
  *(confirmed 2026-08-12 — scope-history)*
- **`stage0_classify._load` treats raw ndarrays as BGR** — A/B probes must
  convert first. *(confirmed 2026-08-12 — scope-history)*
- **A UI affordance that gates on service health fails indistinguishably from
  the service itself.** `.eladd-row` overflow hid "+ Auto-digitize" by 111px, so
  a clipped button read as a dead service — and silently routed photo work
  through the browser engine, which emits none of the pipeline warnings. A full
  SAM2 on/off comparison was run, and two result sets published, that never
  touched SAM2 at all. Structurally closed for the upload path by PR #138, but
  the *class* of bug is the thing to remember.
  *(confirmed 2026-08-13 — PR #122, PR #138)*
- **Pro-parity scores from before 2026-08-14 are on a different scale and do
  not compare.** `direction` and `sttype` were bounded agreement measures with
  a floor near 0.5, so ~21 of their combined 40 points were paid out for a
  wrong answer; both are now chance-corrected. Any score, table or doc quoting
  a pro-parity number from before that date is reading ~16 points high at the
  corpus level. `score_raw`/`parts_raw` in `score.json` carry the old scale
  when the two genuinely need lining up — reach for those rather than
  re-deriving. *(measured 2026-08-14 — PR #151,
  `tools/pro_parity/scorecard.py`)*
- **Three photo hypotheses are disproven** — palette collapse merging subject
  into background, `max_colors` as the binding constraint, and
  `MERGE_DELTAE00_THRESH` needing a retune. All three came from extrapolating
  the *synthetic* `photo_owl_pale.png`, which is a near-featureless blob (6
  regions, one at 98.1% of canvas) and behaves nothing like a real photograph.
  *(measured 2026-08-12 — scope-history)*

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art |
| 2. Font library & lettering | Implemented (library + license remediation) | High (tech) / High (compliance — resolved 2026-08-04 by removal, lawyer consult now an optional restore path) |
| 3. Studio app / guided wizard | Implemented | Medium (fabric-preset accuracy: **pending sew-out** — unchanged, no sew-out has happened). The photo-tier gap PR #123 closed stays fixed; the canvas gained a shape editor and auto-restitch 2026-08-13 |
| 4. Export formats | Implemented | Varies by format — see below |
| 5. Stitch-out review & manual editing tools | Implemented — Kent's direct-manipulation request is **complete** (2026-08-13) | High. Every surviving requirement of the 2026-08-12 request ships: outlines+nodes on the canvas, the pulse cue, select-then-edit, node drag, line drag, add node, delete. Requirement 5 (whole-shape drag) was withdrawn by Kent. Geometry is unit-tested (53 tests) and every interaction was driven in a real browser against a live service |

---

## Waiting on Kent

The decision queue. Everything here is BLOCKED on a call only Kent can make —
not on engineering effort. Each line says what is needed and where the
evidence lives; the detail stays in its own section rather than being
duplicated here, so this list can go stale about WHAT IS OPEN but never about
the facts.

**The two Kent asked to have written down (2026-08-14):**

1. **Fund the stage 0-4 cache?** A boundary edit currently costs a full
   stage 0-7 re-run — no cache helps, because `jobs.content_key` folds
   `shape_overrides` into the config, so every geometry edit is a guaranteed
   miss. Caching stages 0-4 and re-running only `plan_stitches` would take
   **logo art from ~7.3s to ~1.4s**, but a **photo only from ~14s to ~6.6s**
   (nearly half a photo's cost is stitch planning, which a boundary edit
   invalidates by definition). Worth building for logo work; not a route to
   "instant" on photos. Measured table + the caveat about the numbers being
   taken under load: **area 5**, under Kent's direct-manipulation request.
   Not started.

2. **`becker logo.png` + its professionally digitized DST/PES.** Kent rated
   EMB-Bot's auto-digitized version well below the pro file. Measured
   2026-08-13: forcing the flat lane on textured logo art makes it WORSE
   (k-means shatters texture — `summit_badge` 8,263 -> 9,579 stitches), so
   closing the gap needs an edge-preserving flatten BEFORE region forming,
   plus a side-by-side against the pro file to know what "good" looks like.
   **Blocked on Kent supplying both files.** Detail: the "Last updated"
   entry above and **area 1**.

**Also open, same category — listed so this queue is not a half-truth:**

3. **Schedule a physical sew-out.** Four hoopings specified in
   `docs/hardening-closeout-2026-08-02.md` would settle nine geometric
   questions at once (DST axis, fabric presets, Law 19, PES/EXP on real
   hardware). Kent asked (2026-08-13) that this stop being surfaced as the
   headline item every session; it stays here because several confidence
   scores below genuinely cannot move without it. See "No physical sew-out
   testing has occurred yet".
4. **The DST codec fix** — gated on the sew-out above, and Kent's call
   regardless: re-orienting the table changes every DST EMB-Bot has ever
   written. See "DST codec axis bug".
5. **Turn `split_tonal_regions` on?** Merged but default-OFF. Costs +74%
   stitches and pushes the palette to its `max_colors + PALETTE_OVERFLOW_K`
   ceiling. **Kent parked this until the sew-out** (2026-08-12). See the
   blend-tier entry.
6. **Billing / backend.** Tabled since the pivot; Stripe + an entitlement
   check is the leaning, nothing committed. Needs its own session. See
   `PRODUCT.md`, "Open — not yet decided".
7. **Starter design pack (launch item 3).** The last unstarted item on the
   launch checklist, and it cannot start without a sourcing decision — the
   non-goals rule out a user-upload gallery on copyright grounds. See
   `PRODUCT.md`.
8. **The `scratch_corpus/` 37 files.** Gitignored and empty in every
   checkout; no session has ever had them. Blocks the DT-first classifier's
   M2/M3. See the evaluation-corpus entry.
9. **Font lawyer consult — optional.** Only gates RESTORING the 13 pulled
   ShareAlike fonts; the brief is written and ready to send. Nothing waits
   on it. See the font-licence entry.

Items 3-9 predate 2026-08-14 and are unchanged; they are repeated here only
so a reader does not mistake items 1-2 for the whole queue.

---

## Cross-cutting issues

Things that don't respect one capability area's boundary. Referenced from the
area they drag down, documented once here.

### DST codec axis bug

EMB-Bot's own browser DST codec (`src/dst.js` / `src/dstimport.js`) is
transposed vs. the Tajima/pyembroidery standard — confirmed, unresolved.
It round-trips correctly against itself but reads a quarter-turn wrong in
third-party software. Full evidence trail: `dst-codec-axis-discrepancy` in
memory, `docs/dst-axis-verdict-2026-07-31.md`, `digitizer/README.md`'s "Open
finding" section.

**A nuance worth flagging, not a fix:** CLAUDE.md says "treat browser DST as
EMB-Bot-internal only," while `digitizer/README.md`/`digitizer_service/formats.py`
say browser DST stays the Studio's *default* encoder "because it is the one
with sewn evidence behind it." These aren't necessarily contradictory — the
first is about trusting browser DST as correct-orientation for arbitrary
third-party software; the second is about which of EMB-Bot's own two encoders
Studio picks internally — but they read differently enough side-by-side that
it's worth Kent confirming the intended reading rather than assuming.

**A concrete, code-verified gap in that same area, found 2026-08-09 by a
`digitizing-quality-auditor` pass, not yet acted on:** Studio's actual
Download button has no path-selection logic at all — `app/src/lib/
exporters.js` unconditionally calls the browser engine's own `EMB.encodeDST`/
`encodeEXP`/`encodePES` for every download, regardless of whether the
design came from the Python auto-digitizer. Grepping `app/src` for any call
to the Python service's `/export` route turns up none — `app/src/lib/
digitizer.js` only ever calls `/digitize` and `/jobs/{id}`. So the
pyembroidery-convention path this doc and CLAUDE.md both call "the
trustworthy path for anything leaving this app" is currently unreachable
from the real product for every design type, not just manual/lettering
ones. A proposed fix exists (route Python-digitized designs through
`/export` instead, leaving the manual/lettering path on the existing
browser codec since that's the specific combination with sew evidence) —
small and code-only, not sew-out-gated itself, but deliberately not done
yet: it changes what a downloaded file looks like for existing users, and
needs Kent's explicit sign-off first, same caution the "don't rotate
everyone's existing files" line above already establishes. Worth raising
with him as a concrete proposal in a future session rather than left to be
rediscovered.

**Resolution path:** a sew-out or third-party read of a browser-encoded DST
(the "third opinion" `digitizer/README.md` calls for). Fixing the codec itself
is explicitly Kent's call — every existing EMB-Bot DST is affected by any fix.

**Independent corroboration, merged 2026-08-04 (PR #18, `pes-crossval`):** a
browser-encode → pyembroidery-decode cross-validation harness
(`tools/crossval-stitch-formats.mjs` + `tools/crossval_decode.py`, pinned by
`test/crossval-stitch-formats.test.js`, part of the 267/267 engine count
above) with DST as the control case reproduces the transposition
independently (anti-transpose, rms 0.0) — the PR frames this as validating
the harness method itself, not as new information about the DST bug. The
harness's real news was about the other two encoders, previously unchecked
against an independent implementation, and is now **FIXED, not just
documented — merged 2026-08-05 (**PR #58**, `pes-exp-byte-framing-fix`):** the browser
**PES** encoder's 5-byte stitch-stream mis-framing (one extra header pad
byte plus two non-standard `0x9000` fields) is deleted and the
graphics-offset field re-derived against the standard's PEC-relative-512
baseline, its jump/trim PEC flags are no longer aliased to the same code,
and it now maps design RGB to the nearest Brother PEC chart index instead of
always falling back to sequential chart indices; the browser **EXP**
encoder's 2-byte `0x80 0x03` trim record (which aborted pyembroidery-
convention readers at the first trim) is replaced with the 4-byte Melco form
readers expect. Harness re-run: PES now decodes identity/rms 0/15 stitches
(was 354 phantom stitches, rms 234.6, transform "transpose"); EXP with a
trim now decodes the whole design incl. the second colour block (was
truncated at 11 of 15 stitches). DST is untouched and still reproduces its
documented transposition, confirming the fix didn't touch it. Full writeup
and before/after: `docs/pes-crossval-verdict-2026-08-04.md` (root-cause
memo) and this file's "Last updated" entry above (fix + re-run numbers). Both
encoders had no browser-side importer to create a migration trap, so — per
the memo's section 5 — this fix carried none of the DST codec's migration
risk and didn't need to wait on Kent's sign-off the way that fix would;
Export-formats confidence below is upgraded accordingly.

**Fifth independent corroboration, 2026-08-10 (Ink/Stitch's `pystitch`):**
Ink/Stitch's own DST reader/writer (`src/pystitch/DstReader.py` /
`DstWriter.py` — the format library backing a mature, actively-maintained
open-source tool with 20,000+ users) uses the identical low-nibble=X/
high-nibble=Y convention the four sources above already established,
verified directly against both files' source
(`docs/inkstitch-research-2026-08-10.md` §6). A fifth independent
confirmation EMB-Bot's own `src/dst.js`/`dstimport.js` table is the
transposed outlier, not a new source of doubt. **This does not change the
verdict or the recommended fix** — swap the movement bits to the consensus
table, still Kent's call, still gated on a sew-out per the section above —
it's a stronger citation to put in front of him if he wants more evidence
before authorizing it.

### Font license compliance — RESOLVED by removal

All 13 ShareAlike fonts were pulled rather than waiting on a legal opinion
(72 → 68 → 55). The surviving 55 are 52 OFL-1.1 + 1 CC-BY-4.0 + 2 CC0 — zero
ShareAlike. Full upstream license texts ship three ways (on disk, served at
`/fonts/<key>.LICENSE.txt`, and embedded in each `.embf` binary, which closes
the bare-download hole), attributions are complete notices, and guard tests pin
all of it. *(confirmed 2026-08-04 — PR #16, `docs/font-license-audit-2026-07-31.md`)*

**Not launch-gating any more.** The one-hour lawyer consult is now an optional
restore path, relevant only if Kent wants the 13 pulled fonts back — brief is
written and ready to send as-is (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`).
Still parked for Kent: the bluenesia permission screenshots (audit §8).

### CI feedback speed

The digitizer suite (~1,100 tests of real OpenCV/shapely work) ran **18m49s
serially** on every push — long enough that a red job stops being noticed
promptly. `-n auto` (pytest-xdist, pinned in `requirements.txt` alongside
`execnet`, and in pyproject's `dev` extra) brings that to **10m21s–13m12s**
across four measured runs, ~a third off.

Not the 2.5-3x seen locally, and the reason is worth writing down so nobody
re-tunes it hoping for more: GitHub's standard runners are **2-core**, so
`-n auto` gets two workers, and OpenCV's own threading competes with them.
Adding workers cannot help. The remaining lever is finding which handful of
tests dominate the runtime (`--durations`), not more parallelism.

Verified parallel-safe rather than assumed: the whole suite was run both
ways and the pass/fail set is identical. Nothing writes to a shared path —
fixtures are read-only and every writing test uses `tmp_path`.

### No physical sew-out testing has occurred yet

Zero sew-out testing has been done anywhere in this project — confirmed
independently across three separate research passes (auto-digitizing, Studio
fabric presets, export formats). `docs/hardening-closeout-2026-08-02.md`
states it plainly: "Nothing was sewn. Every number above... is geometry."
This is the single biggest confidence ceiling in the project: fabric-preset
accuracy, real stitch quality beyond test-suite geometry checks, and the DST
axis question all wait on this. Four hoopings are already specified in
`docs/hardening-closeout-2026-08-02.md` and would resolve nine currently-open
geometric questions at once — the highest-leverage next action across the
whole project, whenever Kent's ready to schedule it (his explicit call, not
something to push for).

### Evaluation corpus & harness — real gap, newly tracked here

**Newly named as its own cross-cutting item this pass, not a newly-discovered
problem** — every piece of it was already visible, scattered across area 1's
history as a recurring blocker with no single name: the DT-first satin/fill
classifier's M2/M3 has been blocked since 2026-08-01 on a 37-file
`scratch_corpus/` run that no session has ever had local access to
(gitignored, confirmed empty in every checkout); several corpus-law
recalibrations (`docs/corpus-laws-round3-2026-08-01.md`) needed careful,
one-off validation against golden fixtures specifically because there is no
standing, automated way to score "did this change make the output better or
worse" outside of manually re-running the digitizer suite and eyeballing a
handful of fixtures; and the fundamental confidence ceiling this doc has
always cited — zero physical sew-out testing — is the same root cause
wearing a different hat: no repeatable, automated quality signal, so every
serious quality question queues behind either a corpus nobody has, or a
sew-out that hasn't been scheduled. This is a real, distinct capability gap
— a labeled corpus plus a scoring harness — not merely a rhetorical
reframing of the sew-out gap above; landing it would let future classifier/
quality changes be judged against *something* before either the corpus or a
sew-out session is available, not instead of them.

**The harness half is now BUILT, same-day follow-up: `digitizer/tools/
corpus_scorecard.py`.** The corpus half is untouched — the 37-file
`scratch_corpus/` M2/M3 needs is still inaccessible, gitignored and empty in
every checkout, same as above. What this pass adds is the "remember and
diff" machinery that was missing: `capture` runs every one of the
digitizer's 14 committed `testdata/` fixtures (top-level and `photo/`)
through `digitize()` + the already-existing `digitizer_core.preflight.
run_preflight` — which already computed a 0-100 score, letter grade, typed
findings and ~20 metrics per design; this pass aggregates that existing
signal across the corpus rather than inventing a new metric — at two
configs (80mm width x `left_chest`/`hat_front`, two distinct fabric
presets) and writes `testdata/corpus_scorecard_baseline.json`. `diff`
re-runs the same matrix and reports score deltas, findings that appeared/
resolved by code, and metric drift past a 5% noise threshold against that
baseline. Shipped deliberately as a REPORTING tool, not a CI gate — the
script's own docstring cites this doc's corpus-laws-23/26 history (a
"desk-safe" threshold picked without real validation, later reverted) as
the reason not to invent pass/fail numbers yet; the one exception treated
as a hard signal is a brand-new "block"-severity finding, which does flip
the `diff` command's exit code, since that's the one low-noise, high-
confidence case. Verified working, not just written: a real captured
baseline (all 14 fixtures x 2 configs, grades spanning A to F — the F/0
scores on `drone_render.png` and `summit_badge.png` are real,
already-documented rough edges in those photo-tier stress fixtures, not a
harness bug, exactly the kind of honest signal this tool exists to surface
rather than hide), then an immediate re-`diff` with zero code changes
reporting "no drift against the baseline" at exit 0 — proving the
underlying pipeline is deterministic and the harness doesn't false-positive
on its own output. **Scope note:** that determinism claim only covers
re-running the SAME code twice — a recapture spanning real intervening
commits can still fold in genuine, previously-undiagnosed drift, as the
correction under "Fix #6.1 landed" (area 1) found for three fixtures in
the 2026-08-11 recapture. **Correction, 2026-08-11:** this paragraph originally
also listed `repro_gradient_white_icon.png` as F/0 — wrong, it's D/58 at
both configs; `docs/photo-quality-root-cause-2026-08-11.md` caught and
flagged this same error. No dedicated test file: matches this repo's own
convention that no `tools/*.py` script (including the same-pattern
`capture_flat_lane_golden.py`) has one, and a full capture run touches
several photo/SLIC fixtures, too slow for the regular suite.

**2026-08-11 update:** `drone_render.png`'s F/0 now has a landed,
algorithm-verified-correct fix (#6.1, `select_palette`'s `max_colors`
floor-aware overflow in `digitizer_core/palette.py`) that does NOT move
this grade — see area 1 above for the full trace and why (a preflight
pooled-metric measurement gap, not a fix defect). `summit_badge.png` (#6.2)
and `repro_gradient_white_icon.png` (#6.3) remain open, same root-cause doc.
**Next step for this gap:** use the tool by hand against a few real future
corpus-law/classifier changes to learn what a genuine regression looks like
here before deciding on hard CI thresholds; the labeled-corpus half stays
blocked on `scratch_corpus/` access, unchanged by this pass.

**A second, different harness also exists: `tools/pro_parity/`.** Where
`corpus_scorecard.py` asks "did our own preflight score move", this one asks
"how close is our output to the PROFESSIONAL digitization of the same
design" — 23 of Kent's customer designs, decoded from their PES/DST, scored
0–100 across six weighted components (coverage, direction, stitch type,
density, underlay, travel) after a registration search aligns the two.
**Its scale changed 2026-08-14:** `direction` and `sttype` are bounded
agreement measures whose floor was ~0.5, so both are now chance-corrected
against analytic floors (`sttype`'s being Cohen's kappa) and guessing scores
0. See the Gotcha above before comparing any number to a pre-2026-08-14 one.
*(confirmed 2026-08-14 — PR #151)*

**The corpus half of this harness is in the same position as
`scratch_corpus/`, and for the same reason:** it is built by `prep_all.py`
from Kent's local reference-art folder, which is not in the repo and is not
reachable from a fresh checkout — so the 23 prepped designs exist only for as
long as a session's scratch dir does. Nothing about the *scoring* code is
blocked on that; re-measuring after an engine change is. *(confirmed
2026-08-14 — `prep_all.py`'s `ROOT`)*

**Not promoted to a sixth top-level capability area.** This session
evaluated and explicitly rejected splitting area 1 ("auto-digitizing
quality") into separate "image analysis" (raster → regions/colors) and
"stitch planning" (regions → technique/stitches) areas, which an external
review of this doc proposed alongside naming this gap. Reasoning: those are
tightly-coupled pipeline STAGES of one system (`stage0_classify` →
`stage1_prep`/`stage1_photo_prep` → `stage2_quantize`/`stage2_photo_segment`
→ `stage3_segment` → `stage4_vectorize` → stages 5–7), not two separately
shippable products — nearly every feature this doc tracks under area 1
(this pass's own text-cluster detection included) touches both halves, so
splitting the tracking would recreate, at the doc level, the exact
"handoff nobody owns" problem that review raised as a reason to name this
gap in the first place. A future session should feel free to promote this
from a cross-cutting note to its own capability area once real work
actually lands against it (a labeled fixture set, a scoring script/metric),
per this doc's own convention of tracking status, not aspiration.

**Correcting the record on that same external review, so a future session
isn't misled by it:** it also claimed color quantization/palette reduction,
segmentation & vectorization, background removal, and small-detail/minimum-
feature culling had "no owner" in this project. Checked directly against
source this pass — all four already exist and are already documented above:
quantization is `stage2_quantize.py` (k-means + CIEDE2000 thread snapping)
and `palette.py` (weighted k-medoids chart selection); segmentation/
vectorization is `stage2_photo_segment.py` (SLIC+RAG)/`stage3_segment.py`/
`stage4_vectorize.py` — the literal subject of the `BACKGROUND_ENCLOSED` and
gradient-fragmentation sagas already detailed at length above; background
removal is `stage1_photo_prep.py`'s `remove_background_seam` (rembg,
isolated venv, PR #43); small-detail culling is `stage3_segment.py`'s
`small_shape_rescue` path (rescues a shape as a run stitch instead of
dropping it — the exact mechanism this pass's own text-cluster detection
builds on top of). The review's two accurate points — text detection in
logos being a real gap, and this evaluation-corpus/harness gap — are exactly
the two reflected in this update: the first is now closed by this pass's own
feature, the second is captured here.

### Research backlog — competitive and open-source leads

Two capability sweeps produced backlog items rather than status changes:
Ember Design (`emberdesign.net`, a browser-based competitor) and Ink/Stitch
(the open-source Inkscape extension). Both catalogues, plus the closed
`simplify_tol_mm` investigation they generated, now live in
[`docs/scope/research-backlog.md`](docs/scope/research-backlog.md).

Nothing in there is a commitment or a defect. Two things from it that DO bind:

- **Ink/Stitch is GPL-3.0** — concept-level clean-room reimplementation only,
  no literal copying or near-verbatim translation. The exception is
  `pystitch`, its MIT-licensed pyembroidery fork, which is usable as a real
  runtime dependency and has since been adopted.
  *(confirmed 2026-08-10 — `docs/inkstitch-research-2026-08-10.md` §0)*
- **A fifth independent source corroborates the DST axis bug.** No verdict
  change — see the DST section above. *(confirmed 2026-08-10 — same doc)*

---

## Capability areas

One verdict per area. **The supporting detail lives in
[`docs/scope/`](docs/scope/)** — one file per area, linked below. Status and
Confidence here must agree with the At-a-glance table above; if they ever
diverge, fix both rather than picking one.

### 1. Auto-digitizing quality (image → stitches) — [detail](docs/scope/1-auto-digitizing-quality.md)

**In progress · Low confidence beyond flat spot-color art.**
Covers both implementations as one capability: the browser JS engine (complete
but frozen — retired in favour of "feed it clean flat art", not because it is
broken) and the Python pipeline, which is the active target. Stages 1–7, fill +
satin, the service, preflight scoring and the review UI are all built. SAM2 is
merged and reachable from Studio via the `embstudio:sam2` dev seam, still
`photo_segment_sam2=False` by default.
**The binding constraint is the corpus, not the code.** The only
`photo_subject`/`photo_scene` fixtures are synthetic stubs, so the committed
corpus can neither defend nor refute SAM2's quality — a real-photo fixture is
the missing piece. *(confirmed 2026-08-11 — area 1 detail)*
**Next:** satin-vs-fill routing (live defect 5) — Kent's call 2026-08-14,
taken ahead of option A, which stays the standing ruling for the blend tier
whenever it is scheduled. The pro-parity scorecard was chance-corrected first
(PR #151) so the routing work is measured on a scale where guessing scores 0.
*(ruled 2026-08-14 — Kent, this session)*

### 2. Font library & lettering — [detail](docs/scope/2-font-library-lettering.md)

**Implemented · High (tech) / High (compliance).**
55 pre-digitized satin fonts, the EMBF binary codec, browser UI, and the
add-font QC/tier pipeline. License remediation was resolved by removal: all 13
ShareAlike fonts pulled, leaving 52 OFL-1.1 + 1 CC-BY-4.0 + 2 CC0, with full
license texts shipped three ways (sidecar, served, embedded) and guard tests
pinning it. *(confirmed 2026-08-04 — PR #16, PR #17)*
**Next:** expansion is unblocked. The lawyer consult is optional now — it only
matters if Kent wants the 13 pulled fonts restored.

### 3. Studio app / guided wizard — [detail](docs/scope/3-studio-app-wizard.md)

**Implemented · Medium.**
The Svelte guided flow (garment → content → review → download), saved projects,
the Layers panel, and fabric/garment presets. Logic coverage is broad —
nearly every `app/src/lib/*.js` module has a paired spec — with UI-behaviour
coverage riding on live-browser e2e specs across several garments, the image
content path, and four export formats.
**What holds it at Medium:** fabric-preset accuracy is sew-out-gated, and no
sew-out has happened. See Cross-cutting issues.

### 4. Export formats — [detail](docs/scope/4-export-formats.md)

**Implemented (all five) · Confidence varies by format, not one score.**
DST, EXP, PES, SVG and the PDF worksheet, via both the browser encoders and the
service's `/export` route. One reachability caveat: `/export` is only reachable
from the product for purely-digitized designs — anything containing lettering
or manual shapes downloads through the browser encoders.

- **DST — split by path.** Browser DST is Medium as Studio's sewn-and-shipping
  default, Low if treated as verified-correct-orientation in the abstract; that
  is the cross-cutting axis bug, same defect. Python `/export` DST is
  Medium-High by spec, not itself sew-verified.
- **EXP — Medium-High.** The 2-byte trim record (fatal to pyembroidery-convention
  readers at the first trim) and the phantom terminal end-stitch are both fixed.
  *(confirmed 2026-08-06 — PR #58)*
- **PES — Medium-High.** The 5-byte stitch-stream mis-framing, jump records
  flagged as trims, and never-set palette indices are all fixed.
  *(confirmed 2026-08-05 — PR #58)* Held below High because nearest-chart colour
  mapping is lossy by construction (PEC has 64 fixed colours) and this is
  pyembroidery cross-validation, not a verified Brother-machine load.

### 5. Stitch-out review & manual editing tools — [detail](docs/scope/5-review-manual-editing.md)

**Implemented · High. Kent's direct-manipulation request is complete.**
*(confirmed 2026-08-13)*
Every surviving requirement of the 2026-08-12 annotation ships: outlines with
nodes drawn over the result automatically, the pulse cue, select-then-edit, node
drag, line drag, add node, and delete. Requirement 5 (whole-shape drag) was
withdrawn by Kent. Geometry is unit-tested (53 cases in `shapeOverlay.spec.js`)
and every interaction was driven in a real browser against a live service.
**Do not compress the detail file's copy of Kent's request** — it is captured
verbatim there because the sub-requirements *are* the spec.

---

## How this document works

- **Two independent axes per area:** Status (is it built) and Confidence (do
  we trust it) — kept separate on purpose. Something can be fully
  Implemented and still Low confidence (the DST codec is the standing
  example), or In progress and High confidence (on track, just not done).
- **Confidence authority is hybrid.** Claude proposes a score with cited
  evidence (tests, docs, known defects); Kent has override authority.
  Anything whose real confidence depends on physical machine verification —
  fabric presets, real stitch quality, the DST orientation question — gets
  an explicit **pending sew-out** flag instead of a guessed score, because
  no sew-out testing has happened on this project yet.
- **This document is the source of truth for current status.**
  COOKBOOK.md's former "Known limitations" section pointed here instead of
  maintaining a parallel list, to avoid the two drifting out of sync.
- **Updates:** proactively after PR-sized work changes an area's status or
  confidence, plus on demand via `/update-master-scope` for a checkpoint
  whenever Kent wants a fresh read.

### The rules that keep this file current

Added 2026-08-14, after a fact-check found 30 of 56 sampled claims stale and
17 outright false. The root cause was not carelessness — it was that this file
interleaved live status with dated history in one stream, so every historical
measurement read as a current claim.

1. **Classify before you write.** Does this still govern a decision today, or
   was it true at a moment? *Still in force* — rulings, scope calls, known
   defects, invariants, open questions — goes here. *Was true then* — test
   counts, stitch counts, corpus grades, "landed PR #N", "as of today X" —
   goes to [`docs/scope-history.md`](docs/scope-history.md).
   **When in doubt, move it out.** History is recoverable; a stale claim
   presented as live is not.
2. **The cut is by force, not by date.** Kent's rulings are historical in
   origin and current in effect — they stay. An undated measurement is still a
   measurement — it goes.
3. **Every claim carries a pointer:** `(verb date — source)`. The verb is
   load-bearing and is not optional — `confirmed` means checked against code or
   a passing test, `measured` means a number was produced, `suspected` means
   neither. A claim with no pointer is unverified by definition. This exists
   because two suspicions in this document hardened into stated defects as they
   were copied forward, and both were later disproved by measurement; see
   "Corrections" above, which is kept precisely so that pattern stays visible.
4. **Budget: 800 lines.** Over it, compact before adding. The number has teeth
   on purpose — a skill already told agents to keep this file current, and it
   reached 5,400 lines anyway, one reasonable paragraph at a time.
   *(ruled 2026-08-14 — Kent, after the split measured 655 actual; the ~145
   lines of slack are deliberate, so a normal week of legitimate additions
   lands without forcing a compaction pass every time)*
5. **Overflow goes to [`docs/scope/`](docs/scope/), never to the bin.** One
   file per capability area, plus the research backlog. MASTER_SCOPE keeps the
   verdict and a link. Nobody should ever have to delete something load-bearing
   to satisfy rule 4.
6. **No test counts in prose.** They are stale within a day, nothing reads
   them, and every one the fact-check sampled was wrong.
