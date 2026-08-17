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

**START HERE if you are picking up the real-artwork parity work:**
[`docs/handoff-2026-08-16.md`](docs/handoff-2026-08-16.md) indexes the
2026-08-15/16 session — the honest baseline (**42.5**, not the older ~70), the
metric's own **75-84** pro-vs-pro ceiling, four defects real customer artwork
exposed, and the traps that cost that session time. Four of its findings are
standing rulings below. **The code and instruments it describes are ON `main`**
— PR #157 merged (`4967ed5`), so `digitizer/tools/pro_parity/` including
`selfconsistency.py` is in a plain checkout. This pointer said "in PR #157, not
on `main`" until 2026-08-17. *(confirmed 2026-08-17 — `git ls-tree origin/main`)*

**Last updated:** 2026-08-17. Dated history — every "we shipped X on date Y"
entry this file used to carry — now lives in
[`docs/scope-history.md`](docs/scope-history.md). **This file is current state
only.** See "How this document works" at the bottom for the rules that keep it
that way, including the line budget. The 2026-08-17 corrections arrived with the
file at 790 of 800 and so came with a compaction pass — the evaluation-corpus
entry gave up ~40 lines of build narrative that belongs in history, not in a
current-state dashboard. Do the same when you next find this file full.

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

2. **No width floor under satin — and the proposed fix is DISPROVED for flat
   art.** 19 of 162 corpus regions, all photo-class, sew sub-millimetre satin
   (Law 31). The proposed `2·p90 < ~1.0mm → run` reroute must NOT be applied
   design-wide: on 15 real customer logos, 61 of the 64 shapes classifying satin
   under 1.0 mm are ground the pro also sewed as satin — professionals satin
   hairline strokes on flat logo art routinely. The defect stands for the photo
   lane, where it was measured; the fix has to be gated there and measured
   there. *(measured 2026-08-11 — `docs/dt-first-verdict-2026-08-11.md`;
   disproved for flat 2026-08-16 — `docs/satin-gate-attribution-2026-08-16.md`
   §7)*

3. **14 jump-trims on an 80mm design,** in every fill variant measured.
   Not started. *(measured 2026-08-12 — scope-history)*

4. **Our output fragments into 129 runs where the professional uses 15** — on
   the same logo, at the same size. That is what drives **8.49 trims/1,000
   stitches against the pro's 1.27**, more than double the 4.1 ceiling this
   repo's own chaining test treats as the outer limit. Unambiguously a defect,
   unlike the stitch-count gap beside it. Cause not yet diagnosed.
   *(measured 2026-08-15 — `docs/becker-pro-parity-2026-08-15.md`)*
   **No longer blocked:** Kent delivered the artwork and five professionally
   digitized variants on 2026-08-15; they are committed under
   `digitizer/testdata/reference/`. Two things that comparison disproved, so
   nobody re-derives them: the 1-colour-vs-4 difference is **not** defect #1,
   and most of the 3,417-vs-8,694 stitch gap is a **design choice**, not a
   defect — the pro filled the banner and left the letters bare fabric, we
   filled the letters.
   **Correction 2026-08-17:** this entry blamed the colour difference on "richer
   artwork than we were given." Same file, actually — the missing piece is the
   **alpha channel**, 7,272 transparent pixels forming the letter counters, which
   the pro sewed as a second colour. The gap is enclosed-background being off by
   default, worth **+8.0 per Becker design**.
   *(corrected 2026-08-17 — `docs/handoff-2026-08-16.md` §0)*

5. **Satin-vs-fill routing sits at chance, and misroutes in BOTH directions.**
   The *mix* nearly matches the pro's, so the cap is not simply too high or too
   low, while per-place agreement is barely above chance — about a third of the
   pro's satin ground is filled and a third of its fill is satined, two designs
   below their own chance floor. Retuning `satin_max` cannot fix a
   wrong-shapes-picked failure; it only moves the mix that is already right.
   *(measured 2026-08-14 — confusion matrix over the pro-parity corpus;
   per-design detail in area 1)*
   **Partly closed 2026-08-16, and the remainder is NOT the classifier.** The DT
   regularity term accounts for 63.6% of the pro-satin ground we fill; loosening
   its limit is confirmed not to work (recovers 625 cells, leaks 439), while a
   promotion path reopening that term alone moves the corpus **45.8 → 48.1**
   (better on 8, worse on 1 — `bridge_lc`, unexplained — unchanged on 5). What
   is left is segmentation: an oracle knowing the pro's per-shape answer scores
   76.6% against our 55.4%, and 48% of graded cells sit in shapes under 75% one
   type, i.e. our regions straddle the pro's satin/fill boundaries.
   **RESOLVED 2026-08-17 — corrected kappa rose, gain is real.** The spec's
   actual bar, `parts["sttype"]`, moved 0.167 → 0.193 (+0.026) against a
   chance floor that itself rose (0.429 → 0.472) rather than dropped, so the
   rise isn't the floor-moving artifact §4 warned about — smaller than the
   raw `45.8 → 48.1` headline since sttype is one of six weighted components.
   *(measured 2026-08-17 — `kappacheck.py` vs `26ceaa3`/`2729ea5`; detail in
   `docs/satin-gate-attribution-2026-08-16.md` §9)*

---

## Latent — gated OFF, DO NOT FLIP without rebuilding its instrument

Safe today only because these ship off; each becomes a live defect the moment
someone flips a flag that reads like an optimisation. **A green suite is not
evidence for either** — on chaining, a green suite actively concealed it.

1. **`chain_links` — sews needle-down thread on bare fabric.** 16.15 mm exposed
   over 17 links on `full_back`/`fleece_sweatshirt`, stock preset, green suite,
   one point over a millimetre from any thread in the design. **Precondition to
   flip: rebuild the instrument** — the two shipped ones were structurally blind
   to this three ways over (one-point links skipped, first/last sewn segment
   never tested, cover measured as polygons not as where thread lands). Hold it
   to the contour lane's standard (`config.py:462-521`). *(confirmed OFF
   2026-08-17 — `config.py:1064`; measured 2026-08-02 —
   `docs/hardening-closeout-2026-08-02.md`)*
2. **`split_tonal_regions`** — the shading fix, merged but off; parked until the
   sew-out. Cost and ceiling under "Waiting on Kent". *(confirmed OFF
   2026-08-17 — `config.py:647`)*

*(section added 2026-08-17 — `docs/project-review-2026-08-16.md` §1.6: chaining
was absent from the live-defect list entirely, so a good-faith flip would have
shipped visible thread on bare fabric with no warning in this dashboard.)*

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

- **Six phase-numbering schemes exist; only ROADMAP.md's five engine phases
  are live.** Historical: the 4-phase pro-stitch roadmap, 11 digitizer steps,
  7 launch items, 8 Studio slices, 13 photo-plan rows.
  *(confirmed 2026-08-17 — docs review of ROADMAP/PRODUCT/READMEs/sdd ledger)*
- **The venv holds a STALE non-editable install of `digitizer_core`, and cwd
  decides which one you get.** `pytest` from `digitizer/` imports the working
  tree (verified), so tests are honest — but from any other cwd the same
  interpreter imports `.venv/Lib/site-packages/digitizer_core/`, whose files
  differ from both the working tree and `HEAD`. So a service or script launched
  from elsewhere can run code that is not in the repo. Reinstall (`pip install
  -e digitizer`) before trusting any out-of-tree run. *(confirmed 2026-08-17)*
- **Stage 0's `photo_subject` gate is bimodal** — textured subjects on smooth
  backdrops can't reach `photo_subject`. Pinned in the routing test's docstring.
  *(confirmed 2026-08-12 — scope-history)*
- **`stage0_classify._load` treats raw ndarrays as BGR** — A/B probes must
  convert first. *(confirmed 2026-08-12 — scope-history)*
- **A UI affordance that gates on service health fails indistinguishably from
  the service itself.** `.eladd-row` overflow hid "+ Auto-digitize" by 111px, so
  a clipped button read as a dead service and silently routed photo work through
  the browser engine, which emits no pipeline warnings — a full SAM2 on/off
  comparison was run and two result sets published that never touched SAM2.
  Closed for the upload path; remember the *class*.
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
- **Every pro-parity number before 2026-08-15 was measured on artwork
  RECONSTRUCTED from the pro's own stitches, and was flattered by 11.3 points.**
  Kent supplied 7 real customer artworks (15 designs) on 2026-08-15. Honest
  baseline: **42.5**. *(measured 2026-08-15 —
  `docs/pro-parity-real-art-2026-08-15.md`)*
- **The pro-parity 95 target is above the metric's own ceiling. Do not read
  `score/95` as an engine deficit** — and any plan quoting "we need to get to 95"
  is quoting an unreachable number. Two of the PRO's own files for one logo,
  scored against each other on the same scorecard, give **75-84**. The scorecard
  is not broken: on pairs that are one job saved twice it correctly returns
  96-100. But `direction` ceilings at **0.11 on one pair and 0.85 on another**
  from one digitizer on one logo, against a 20-point weight — it measures a
  choice, not a standard, and is the least defensible weight in the scorecard;
  `density`/`underlay`/`travel` ceiling at 0.89-1.00, so those are sound.
  **Deliberately NOT revised yet: n=2.** Growing n needs scale-normalised
  registration in `scorecard.py` (it registers by translation only, and every
  other same-logo PES pair is 4-17% apart in width).
  *(measured 2026-08-15 — `tools/pro_parity/selfconsistency.py`,
  `docs/pro-parity-real-art-2026-08-15.md` §11)*
- **The golden divergence is PER-FIXTURE, not per-platform.** This ruling used
  to say the goldens "fail on Windows and pass in CI, which is where they were
  captured." False for `logo_alpha`. Truth is three-way — rows are
  `flat_lane_byte_identical` and `stage2_photo_segment` unless named:

  | fixture | Windows | CI |
  |---|---|---|
  | `pushcomp[logo_whitebg.png-towel]` | fails | fails (deselected) |
  | both, `[logo_alpha.png]` | **passes** | fails (deselected) |
  | both, `[photo/enthusiast_logo.png]` | fails | passes |

  CI column is `.github/workflows/python-package-conda.yml:96-98`, which
  deselects three by name because they *"compare against goldens pinned on the
  original development machine"* — i.e. they fail there, so `ubuntu-latest` is
  NOT where every golden was captured. **Consequence:** an `enthusiast_logo`
  failure locally is expected; a `logo_alpha` failure locally is a genuine
  regression. Per-platform reasoning gets that backwards. **Still binding: never
  re-capture a golden from a Windows run.** Judge a change by "same failure set
  before and after", using the table as that set. Cause and the two permanent CI
  deselects nobody is assigned to: `docs/pro-parity-real-art-2026-08-15.md` §0b.
  *(corrected 2026-08-17 — Windows column re-run this date: `logo_alpha` ×2
  passed, `enthusiast_logo` ×2 failed; CI column read from the workflow)*
- **A SECOND expected local failure, nothing to do with goldens: the OCR test
  needs a binary Windows lacks.** `test_pipeline.py::test_full_pipeline_stamps_ocr_fields_on_the_benchmark_subline`
  demands one real character read. `pytesseract` is a declared dep and imports
  fine, but it only wraps the `tesseract` executable — CI apt-installs that
  (`python-package-conda.yml:75-76`), a Windows box usually has not, so
  `ocr_char` is `None` throughout and the assert fails. **Not a regression, and
  deselected nowhere**, so it reads as an unexplained local red. Install
  Tesseract on `PATH` to go green. *(confirmed 2026-08-17 —
  `shutil.which("tesseract")` is `None` here; passes on CI)*
- **Measure pro-parity in a git worktree, never in a shared checkout.** Three
  separate baselines were invalidated on 2026-08-15 by commits landing mid-run,
  including from a second Claude session on the same branch. The first symptom
  each time looked like engine non-determinism; the engine is deterministic —
  same art, same commit, four processes, byte-identical output. Verify module
  resolution hits the worktree's own `digitizer_core`, not the main checkout's
  editable install. *(measured 2026-08-15 —
  `docs/pro-parity-real-art-2026-08-15.md` §1)*
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
| 5. Stitch-out review & manual editing tools | Implemented — Kent's direct-manipulation request is **complete** (2026-08-13) | High. Every surviving requirement of the 2026-08-12 request ships: outlines+nodes on the canvas, the pulse cue, select-then-edit, node drag, line drag, add node, delete. Requirement 5 (whole-shape drag) was withdrawn by Kent. Geometry is unit-tested and every interaction was driven in a real browser against a live service |

---

## Waiting on Kent

The decision queue. Everything here is BLOCKED on a call only Kent can make, not
on engineering effort. Detail stays in its own section rather than duplicated
here, so this list can go stale about WHAT IS OPEN but never about the facts.

**The one Kent asked to have written down (2026-08-14) that is still open:**

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

The second of that pair — the Becker artwork and pro-digitized variants — closed
2026-08-15; its placeholder was deleted here 2026-08-17 as that entry instructed.

**Also open, same category — listed so this queue is not a half-truth. All of
these predate 2026-08-14 and are unchanged:**

2. **Schedule a physical sew-out.** Four hoopings specified in
   `docs/hardening-closeout-2026-08-02.md` settle nine geometric questions at
   once (DST axis, fabric presets, Law 19, PES/EXP on real hardware). Kent asked
   (2026-08-13) that this stop being the headline item every session; it stays
   because several confidence scores cannot move without it. See "No physical
   sew-out testing has occurred yet".
3. **The DST codec fix** — gated on the sew-out above, and Kent's call
   regardless: re-orienting the table changes every DST EMB-Bot has written. See
   "DST codec axis bug".
4. **Turn `split_tonal_regions` on?** Merged but default-OFF. Costs +74%
   stitches and pushes the palette to its `max_colors + PALETTE_OVERFLOW_K`
   ceiling. **Kent parked this until the sew-out** (2026-08-12). See the
   blend-tier entry and "Latent — gated OFF".
5. **Billing / backend.** Tabled since the pivot; Stripe + an entitlement
   check is the leaning, nothing committed. Needs its own session. See
   `PRODUCT.md`, "Open — not yet decided".
6. **Starter design pack (launch item 3).** The last unstarted item on the
   launch checklist, and it cannot start without a sourcing decision — the
   non-goals rule out a user-upload gallery on copyright grounds. See
   `PRODUCT.md`.
7. **The `scratch_corpus/` 37 files.** Gitignored; cloud checkouts are empty
   but all 37 are present on Kent's machine (confirmed 2026-08-17), so a local
   session can run the corpus legs today. Blocks cloud-side M2/M3 only.
8. **Font lawyer consult — optional.** Only gates RESTORING the 13 pulled
   ShareAlike fonts; the brief is written and ready to send. Nothing waits
   on it. See the font-licence entry.

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

**A nuance, reconciled 2026-08-17:** CLAUDE.md's "treat browser DST as
EMB-Bot-internal only" and `digitizer/README.md`'s "browser DST stays the
default because it is the one with sewn evidence" are not in conflict — the
first is about orientation in third-party software, the second about which of
EMB-Bot's own two encoders Studio picks. The code below settles it either way:
the choice is per-project and the user is told which one ran.

**CLOSED — a stale "unreachable from the real product" paragraph sat here until
2026-08-17.** That 2026-08-09 finding (no path-selection logic, `/export` with no
caller) was already false, and both halves ship: `digitizer.js:936` posts to
`/export` with `DownloadStep.svelte:173` passing `preferService:
isPurelyDigitized(project)`, so auto-digitized designs leave by pyembroidery
convention while lettering/manual stays on the browser codec deliberately, that
being the combination with sew evidence (`02cd97c`/`51746bd`, 2026-08-10). And
`DownloadStep.svelte:268-284` warns BEFORE a browser-DST download — naming the
symptom (quarter-turn rotation, colour stops possibly missing) and the way out
(PES/EXP or an image-only project) — then confirms after from the observed `via`,
not a prediction (`ad612c9`, 2026-08-12; test ids `dst-browser-encoder-note`,
`dst-browser-encoder-downloaded`). **So the 2026-08-11 audit's interim mitigation
is DONE, and `docs/project-review-2026-08-16.md` §1.1 plus its opportunity #5 are
wrong to list it as available-and-not-done — it shipped four days before that
review.** *(confirmed 2026-08-17 — code read, commits dated)*

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
ShareAlike. Upstream licence texts ship three ways (on disk, at
`/fonts/<key>.LICENSE.txt`, embedded in each `.embf`), attributions are complete
notices, guard tests pin all of it. **No longer launch-gating.** *(confirmed
2026-08-04 — PR #16, `docs/font-license-audit-2026-07-31.md`)*

**Still open, both Kent's:** the optional lawyer consult, which only gates
restoring the 13 pulled fonts (brief ready to send —
`docs/lawyer-brief-cc-by-sa-2026-08-04.md`), and the bluenesia permission
screenshots (audit §8).

### CI feedback speed

`-n auto` (pytest-xdist, pinned in `requirements.txt` with `execnet` and in
pyproject's `dev` extra) took the digitizer suite from **18m49s** serial to
**10m21s–13m12s** over four runs. **Do not re-tune hoping for the 2.5-3x seen
locally:** GitHub's standard runners are 2-core, so `-n auto` gets two workers
and OpenCV's own threading competes with them — more workers cannot help. The
remaining lever is `--durations`, not parallelism. Parallel-safety was verified
rather than assumed (identical pass/fail set both ways; fixtures read-only,
every writing test uses `tmp_path`).

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

**The gap: no repeatable automated quality signal**, so every serious quality
question queues behind either a corpus nobody has or a sew-out nobody has
scheduled. Not a reframing of the sew-out gap — a labelled corpus plus a scoring
harness would let a classifier change be judged against *something* before either
arrives. The DT-first classifier's M2/M3 has been blocked on it since 2026-08-01,
and the corpus-law recalibrations
(`docs/corpus-laws-round3-2026-08-01.md`) needed one-off hand validation for
exactly this reason.

**Harness half: BUILT — `digitizer/tools/corpus_scorecard.py`.** `capture` runs
all 14 committed `testdata/` fixtures (top-level and `photo/`) through
`digitize()` + the existing `digitizer_core.preflight.run_preflight` — which
already produced a 0-100 score, letter grade, typed findings and ~20 metrics, so
this aggregates existing signal rather than inventing a metric — at two configs
(80 mm width × `left_chest`/`hat_front`, two distinct fabric presets), writing
`testdata/corpus_scorecard_baseline.json`. `diff` re-runs that matrix and reports
score deltas, findings appeared/resolved, and metric drift past a 5% noise
threshold. **Deliberately a REPORTING tool, not a CI gate** — the docstring cites
this file's own corpus-laws-23/26 history (a "desk-safe" threshold picked without
validation, later reverted) as the reason not to invent pass/fail numbers yet.
Sole hard signal: a brand-new `block`-severity finding flips `diff`'s exit code.
**Verified, not just written:** a real baseline (14 × 2, grades A to F — the F/0
on `drone_render.png` and `summit_badge.png` are documented rough edges in those
photo-tier stress fixtures, not harness bugs) then an immediate re-`diff` with no
code changes reporting no drift at exit 0, so the pipeline is deterministic and
the harness does not false-positive on itself. **Scope limit:** that determinism
covers re-running the SAME code twice only — a recapture spanning real commits
can fold in genuine undiagnosed drift, as "Fix #6.1 landed" (area 1) found for
three fixtures. No dedicated test file, matching the convention that no
`tools/*.py` has one (including `capture_flat_lane_golden.py`); a full capture is
too slow for the regular suite. *(`repro_gradient_white_icon.png` is D/58 at both
configs — an earlier version of this entry said F/0; corrected 2026-08-11 —
`docs/photo-quality-root-cause-2026-08-11.md`)*

**Still open here:** `summit_badge.png` (#6.2) and
`repro_gradient_white_icon.png` (#6.3), same root-cause doc — `drone_render.png`'s
#6.1 fix landed and is algorithm-verified but does not move the grade (a
preflight pooled-metric measurement gap, traced in area 1). **Next step:** run the
tool by hand against a few real classifier changes to learn what a genuine
regression looks like before setting any hard threshold.

**The corpus half is no longer empty (2026-08-15).** Eight files of real
customer artwork now ship in `FIXTURES` — the first entries that are neither
synthetic nor hand-picked. They immediately contradicted the synthetic set:
**stage 0 routes six of the seven logos to the GRADIENT lane, not the flat
lane**, because real logo art carries JPEG ringing, anti-aliased edges and soft
shading that the synthetic flat fixtures do not. Any claim about "flat
spot-colour art" tuned only on synthetics is therefore untested against the
input this product actually receives. One (`logo_script_tires.png`, a clean
two-colour script wordmark on white) classifies as `photo_scene` outright — a
misroute, kept as a fixture so the bug has one.
*(measured 2026-08-15 — `tools/corpus_scorecard.py:FIXTURES`)*
This does **not** close `scratch_corpus/`: cloud sessions still can't reach
those 37 files (present locally — Waiting on Kent #7); M2/M3 still waits.

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
