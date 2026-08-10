# EMB Bot — Cookbook for the next Claude agent

Handoff doc. Read this before touching code. Full blow-by-blow history lives in
Kent's memory file `emb-bot-digitizer.md` (in the operator's Claude memory
store, not this repo) — this file is the repo-local, self-contained version.

## What this is

Browser-based embroidery auto-digitizer + guided lettering studio, plus a
Python digitizing engine that runs as a localhost service. Three parts:

- **`EMB-Bot.html`** — original single-page tool (image-to-stitch +
  text-to-stitch, manual controls).
- **`app/`** — "EMB Bot Studio", a Svelte 5 + Vite guided wizard (garment →
  content → review → download) built on top of the same engine via
  `window.EMB` (loaded through `<script>` tags, engine untouched).
- **`digitizer/`** — Python 3.14 auto-digitizing pipeline (OpenCV, scikit-image,
  shapely) + an optional FastAPI service. See the digitizer section below.

**This claim used to read "zero server, zero Python/OpenCV — all stitch math is
hand-written JS."** That was true until 2026-07-29 and is now wrong in every
part: the browser engine still owns text and DST import, but the image path's
future is the Python pipeline. Check `digitizer/README.md` before assuming
where a piece of stitch math lives.

Read the top-level [README.md](README.md) first — it's accurate and
user-facing (outputs, fabric presets, honest limits, file map). This cookbook
covers what the README doesn't: current work-in-progress state, gotchas, and
where the bodies are buried.

## Binary font library (Slice 10 Stage A, 2026-07-27)

The Studio's fonts live in `src/fonts/manifest.json` + `src/fonts/bin/*.embf`
(**55 fonts** as of 2026-08-04, after the 4 license-audit pulls below and the
same-day removal of all 13 ShareAlike fonts (Kent's call — see the audit
doc's §9; removal made the paid launch independent of the CC-BY-SA legal
question, and the lawyer brief is now the optional restore path) —
previously drifted to 72 without this doc being updated; don't trust either
number without recounting `manifest.json`), lazily fetched per font by
`app/src/lib/fontLoader.js`. The
old eager `src/fonts/satin-fonts.js` is OUT of the Studio pipeline but still
used by legacy `EMB-Bot.html` — do not delete it. **Its audit ran 2026-08-04**
(`docs/font-license-audit-2026-07-31.md` §10): the 7 license-pulled fonts
(milli_marif_bold, tt_masters + the 5 ShareAlike: aventurina, emilio_20,
emilio_20_bold, geneva_simple, monicha) were removed, 21 → 14 entries, all
remaining OFL-1.1/CC0 and present in the shipping manifest. Do not re-add a
font there unless it is also in the shipping manifest. `EMB-Bot-standalone.html`
(the frozen artifact that inlined the pre-audit 21 fonts) was **deleted
2026-08-04, Kent's call** — no pre-audit font list ships anywhere anymore.

- **EMBF format** (`src/fontbin.js`): quantize coords ×4 → per-ring delta →
  Int16 stream; skeleton JSON carries everything else. Guard test
  `test/embf-guard.test.js` pins `decode(encode(font)) == quantizeFont(font)`
  for all 21 original fonts — it must stay green through any codec change.
  Acceptance evidence (0.00–1.07% stitch drift, visually cleared):
  `docs/superpowers/notes/2026-07-27-embf-acceptance.md`.
- **Rebuild**: `node tools/build-embf.mjs`. Requires `scratch_ink/`
  (gitignored): `_tiers.json` (tier classification) + `_out/*.json` (trial
  imports). Recreate `scratch_ink/` by copying from Kent's Desktop
  `Ink-Stitch Fonts` clone and re-running the classify/import steps; the
  committed `.embf` files are the artifacts of record either way.
- **Tier rule (Kent's decision): only `tier:"verified"` ships.** Unverified =
  internal work queue with a concrete reason per font in `_tiers.json`.
  License policy for NEW fonts: OFL-1.1 / CC-BY-4.0 / CC-BY-SA-4.0 / CC0
  only — `precious` is excluded (GPL-3.0). `ondulamarif_XL`
  was demoted by QC (letter glyphs runs-only → 0 stitches). `milli_marif_bold`,
  `tt_directors`, `tt_masters`, and `dejavufont` were PULLED from the build
  2026-08-04 per `docs/font-license-audit-2026-07-31.md` action items 1-3
  (ad-hoc/aggregator-only/mislabeled licenses — see `PULLED` in
  `tools/build-embf.mjs` for the per-font reasoning). ~~They still linger in
  the legacy `src/fonts/satin-fonts.js` / `EMB-Bot.html` pipeline~~ —
  resolved 2026-08-04 by the legacy-registry audit (audit doc §10):
  milli_marif_bold and tt_masters are removed from `satin-fonts.js` along
  with the 5 ShareAlike pulls, so `EMB-Bot.html` no longer ships any pulled
  font — and `EMB-Bot-standalone.html`, the only place that still embedded
  them, is deleted (see the paragraph above).
- **Engine-file lists live in THREE places** for the Studio: `app/scripts/
  copy-engine.mjs` (ENGINE_FILES), `app/src/lib/emb.js` (ENGINE_KEYS), and
  the `<script>` tags in **`app/index.html`** — the third one was missed once
  and broke fonts only in the live browser (tests preload differently and
  stayed green). Keep all three in sync; legacy `EMB-Bot.html` is a separate,
  fourth list that stays on the old registry.
- **Classifier gap**: tier classification counts satin columns per FILE, not
  per GLYPH. A font can classify as satin while its letters are runs-only
  (that's exactly what ondulamarif_XL was). If a font generates 0 stitches,
  check per-glyph `cols` first.
- ~~Known perf item for Stage B: opening the font dropdown lazily fetches ALL
  fonts for thumbnails (~30 MB).~~ **FIXED in Stage B:** the font browser
  grid uses committed preview PNGs (`src/fonts/previews/`, regenerate with
  `node tools/build-previews.mjs` after any library change — it orphan-cleans);
  `.embf` binaries are fetched ONLY on pick. THE RULE: nothing in browsing UI
  may call `ensureFont` except the picked font and the selected-font trigger
  preview. Live your-text tiles render only fonts already in
  `EMB.SATIN_FONTS`, memoized per (font, text).

## Stage B additions (2026-07-28)

- **Font browser** (`FontBrowser.svelte`): dialog (ProjectsDrawer mechanics),
  search + group chips, size-band subtitles from manifest `sizeMm`
  (0.75x–2.0x, spec-declared starting point — validate on real stitch-outs).
  Pure logic in `app/src/lib/fontFilter.js` (tested).
- **Credits** (`FontCredits.svelte` + `app/src/lib/credits.js`): generated
  from manifest `attribution`/`licenseId`/`source` fields — never
  hand-edited. Entry points: topbar "Font credits" + DownloadStep footer.
  Fonts are adapted from the Ink/Stitch open embroidery font collection
  (github.com/inkstitch/embroidery-fonts).
  `SEE-LICENSE-FILE` sentinel renders as "See license file".
  **As of 2026-08-04 (license-audit items 4–10/12,
  `docs/font-license-audit-2026-07-31.md` §8):** every font's binary embeds
  its FULL upstream license text (the 2026-07-28 summary-only compliance gap
  is closed); every font has a `src/fonts/<key>.LICENSE.txt` sidecar of
  record, shipped by `copy-engine.mjs` to `/fonts/<key>.LICENSE.txt` and
  linked per-row in the credits dialog; manifest attributions are complete
  notices (paragraph + upstream copyright + RFN declarations), generated by
  `tools/font-license.mjs` — shared by `build-embf.mjs` and
  `tools/patch-embf-licenses.mjs` (the in-place fixer for checkouts without
  `scratch_ink/`). Guard tests pin all of this (embedded license == sidecar,
  sidecar present per font, no truncation artifacts).
- **QC harness** (`tools/qc-font.mjs`, tested): the versioned tier gate.
  Per-GLYPH satin check (100% satinless letters = hard fail, >10% fail,
  ≤10% warn), advances incl. digits, finite geometry, coverage warnings.
  Run on any candidate font JSON before tiering it. The old gitignored
  scratch classifier is retired as the gate of record.
- **Attribution parsing gotcha:** upstream license blobs mostly use bare-CR
  (old-Mac) line endings — split on `/\r\n|\r|\n/` or "first line" becomes
  the whole blob.

## Font editing abilities Round 1 — merged 2026-07-27

Rotation, per-letter color, bold/thin weight, slant/italic for text elements.
Was previously sitting unmerged in a worktree (a memory note wrongly called
it "merged" — always verify with `git log`, don't trust prior claims at face
value). Fast-forward merged into `main`, worktree removed, branch deleted.
169/169 engine + 182/182 app tests green on `main` **at that merge
(2026-07-27)** — a historical record of that slice, not current counts; see
"Running things" for those.
Spec/plan: `docs/superpowers/specs/2026-07-27-font-editing-abilities-design.md`
and `docs/superpowers/plans/2026-07-27-font-editing-abilities.md`. Two
abilities were explicitly deferred (condensed/expanded width, mixed
per-letter size) — both risk distorting satin column width unevenly along
curves; prototype before committing.

**As of 2026-08-02, `feat/satin-rails` (56 commits: satin rewrite, chaining,
contour fill, push-comp, appliqué, the fill-axis geometry fix) is
fast-forward merged into `main`.** `feat/stitch-quality` no longer exists as
a branch — folded in along the way. `main` is still ahead of `origin/main`
locally; push is a user-confirm action, not automatic.

## The Python digitizer (`digitizer/`, added 2026-07-29, grown continuously since)

Separate Python engine + optional FastAPI service for auto-digitizing
photos/logos — built because the JS engine's auto-digitize path was retired
in favor of "feed it clean flat art" (see "the one rule" below); this
subsystem exists to do classical-CV auto-digitizing properly instead of
hand-rolling it in JS.

- **Env**: Python 3.14 venv at `digitizer/.venv` (gitignored). Run tests with
  `cd digitizer && .venv/Scripts/python -m pytest -q` — a bare
  `python probe.py` will NOT put cwd on `sys.path`, must use `python -m pytest`
  or set `PYTHONPATH=.`. 567 tests as of 2026-08-04 — see "Running things"
  below for the current pass/fail split, this count only grows.
- **Pipeline**: image → **classify** (`stage0_classify.py`) → prep
  (background mask, `stage1_prep.py`) → segment, one of two stages depending
  on class: `stage2_quantize.py` (global k-means + CIEDE2000 thread snapping,
  used for `flat`/`gradient`) or `stage2_photo_segment.py` (SLIC superpixels
  + region-adjacency-graph merge, used for `photo_subject`/`photo_scene`) →
  small-region absorb + enclosed-hole handling (`stage3_segment.py`) →
  contour vectorize (`stage4_vectorize.py`) → stitch planning: overlap
  resolution, fill/satin/border/contour/appliqué/**blend** tiers, sequencing
  (stages 5–7) → DST/PES/EXP/SVG export via pyembroidery.
- **The input classifier (`stage0_classify.py`, 2026-08-02)** is 4-way —
  `flat` / `gradient` / `photo_subject` / `photo_scene` — on three signals:
  `unique_color_mass`, `gradient_smoothness` (Sobel local variance,
  edge-excluded with a raw-variance fallback), `alpha_softness`. Tuned on
  real production art (`enthusiast_logo.png`, `drone_render.png`), not
  synthetic fixtures. **`unique_color_mass` is the real photo/non-photo
  gate, not `gradient_smoothness`** — `drone_render.png` reads rough on
  smoothness because of glow halos and an inset scene. The threshold order
  is documented in the module; read the why before "fixing" it.
- **`stage2_photo_segment.py`** is a drop-in alternative to
  `stage2_quantize.quantize()` with the same `Quant` output contract, so
  stages 3–4 run unchanged. It exists because global k-means clusters color
  independent of position, so a smooth gradient dithers into per-pixel
  speckle; SLIC groups by color *and* space (a superpixel never straddles a
  real edge), then the RAG merges perceptually close superpixels. Scope cuts
  vs. the source plan that have since landed: rembg background removal
  (`stage1_photo_prep.remove_background_seam`, wired 2026-08-04 via an
  isolated venv — see `digitizer/rembg_isolated/README.md` and
  `docs/photo-prep-deps-probe-2026-08-04.md`) and YuNet face priors
  (`detect_faces_seam`, plus the face-local threshold drop this module
  applies) are both real now, gated behind `photo_prep` (background removal
  behind its own extra flag on top of that — see `config.py`).
- **`stage6_blend.py`** is the gradient blend fill tier; its `detect_ramp`
  fitting logic is what the queued gradient-fragmentation fix wants to reuse
  one stage earlier (see Known bugs).
- **Run the service**: `.venv/Scripts/python -m digitizer_service` →
  `127.0.0.1:8721`. `GET /health`, `POST /digitize` (image+config → job),
  `GET /jobs/{id}`, `POST /export`. Binds loopback only, CORS localhost-only.
- **The load-bearing boundary decision**: `/digitize` returns an EMB-Bot
  `Design` object, never a DST — see [[dst-codec-axis-discrepancy]] / the
  "Known bugs" section below. Routing the disputed DST format off this
  boundary means a digitized design can't arrive pre-rotated while the axis
  bug is unresolved. `digitizer_core/adapter.py` owns the one y-flip.
- **Gitignored reference material that is NOT disposable**: `scratch_corpus/`
  (pro-digitized DST corpus the stitch-physics constants were derived from),
  `scratch_ink/` (Ink/Stitch font clone), `scratch_kent/` (Kent's
  commissioned files), `scratch_packs/`. Gitignored means "not in git
  history," not "safe to delete."
- **Read `digitizer/README.md` before touching stage 6.** It carries the
  physics constants, the sew-order reasoning, and a list of open questions
  that are Kent's calls rather than bugs.

### Hard-won lessons — do not relearn these

- **Measure on Kent's real art, not the fixtures.** `testdata/logo_whitebg.png`
  routes 1 of 5 regions to satin and reproduces almost nothing he complains
  about. The benchmark is `digitizer/testdata/photo/enthusiast_logo.png`
  (flat two-colour: hex shield + star, ENTHUSIAST wordmark, ENTERPRISES INC.
  subline — now committed to the repo, not just `Downloads/`). At 90 mm it
  makes 14 regions — the subline's letters included. **The subline no longer
  drops**: the run tier (`229efc6`, 2026-07-31, `digitizer_core/stage3_segment.py`'s
  `small_shape_rescue` path) rescues small shapes as run stitches instead of
  dropping them, and this is now verified against the real fixture, not just
  the synthetic one `tests/test_run_tier.py` already covered. The `warnings`
  list still carries `SMALL_SHAPES_AS_RUN` (count=14 on this fixture) — that's
  informational (rescued, not dropped), not the same defect this note used to
  describe.
- **Validate a quality metric on known-good geometry before you trust it.** A
  fan metric that assumed satin crosses sat at a fixed parity in the point list
  scored a CLEAN curved ribbon at 30.7% — identical to the logo that visibly
  sprays. Two code changes were evaluated against it, and one hypothesis was
  "refuted", before a clean fixture exposed it. Crosses are identified by
  LENGTH now (a cross spans the column, a rail step spans one spacing), and the
  clean fixtures read 0.0%. `tests/test_satin.py::_cross_rotations` is the
  version of record.
- **Green tests are not evidence of quality.** Step 4 shipped "done" on 68
  green tests that pinned determinism, no phantom loops and nothing outside the
  artwork — every one a mechanical property, none asking whether the output
  looks like embroidery. It stayed green while the engine produced starbursts.
- **Do not chase `trim_at_mm` to reduce trims.** Needle-lifts went 58 → 13 on
  the real logo purely from not fragmenting glyphs into many satin runs. The
  3.0 mm value is shared with `src/fabrics.js` and moving it moves the browser
  engine too.
- **Never edit a source file with a PowerShell `(Get-Content -Raw) -replace |
  Set-Content` round-trip.** It re-encodes the file: BOM added, every em-dash
  and ± mangled. Bit this repo twice. Use the Edit tool.

## Branches & worktrees

This repo uses git worktrees under `.claude/worktrees/` for parallel feature
lanes. **Don't trust any doc's snapshot of which worktrees/branches are
active — including this one.** Run `git worktree list` and `git branch -a`
yourself before assuming a lane is gone, merged, or still in flight. `main`
commonly sits behind the active feature branch (`git log main..<branch>
--oneline` to check) — merging/pushing is Kent's explicit call, never
automatic.

Never `git add -A` from the repo root without reviewing what it's about to
stage first — a worktree holding another lane's live uncommitted work is
exactly the kind of thing that gets swept in by accident.

**Snapshot as of 2026-08-04 (re-verify, don't trust it):** the 2026-08-03
snapshot's one worktree (`bg-guard` / `fix/bg-existence-guard`) no longer
exists — gone from both `git worktree list` and `git log --all` this pass,
so either merged under a different branch name or abandoned; not
independently confirmed either way. What's actually live now is a large
parallel-lanes fleet under `.claude/worktrees/` (dozens of `agent-*`
worktrees, one per feature slice — this is the normal way work happens
here, not an anomaly), most sitting on already-merged branch tips. Don't
assume any specific one is still in flight without checking; a couple were
observed `locked` (actively in use by another session) during this pass and
were left untouched, per the "never touch worktrees" rule.

## What's next (queue as of 2026-08-03)

Decision doc: `docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`.
Session handoff with the full context:
`docs/superpowers/handoffs/2026-08-03-gradient-defects-handoff.md`.

1. **The two gradient/enclosed-white regressions** (see Known bugs below).
   The angle-fragmentation half is FIXED (2026-08-03, same-day follow-up
   session). **`BACKGROUND_ENCLOSED` is now FIXED too, later 2026-08-04** —
   pipeline, service contract, and Studio Layers-panel restore UI all
   merged to `main`, and the one caveat that kept it from being real
   end-to-end (an opaque-alpha bug that defeated background detection on
   real Studio uploads) is fixed too, merged PR #22; see MASTER_SCOPE.md
   area 1 for the full breakdown, including the one thing still not
   verified (a live browser run of the fix, vs. the HTTP-level
   reproduction done so far). The `fix/bg-existence-guard` branch/worktree
   this bullet used to queue no longer exists anywhere in this checkout
   (confirmed 2026-08-04, see "Branches & worktrees" above) — its content
   appears superseded by PR #22's opaque-alpha fix (same problem class:
   background detection defeated on real uploads), but that wasn't traced
   commit-for-commit, so treat it as closed-by-inference, not
   confirmed-merged.
2. **M0 + M1 of the DT-first migration** — this is the sequencing call that
   is easy to miss: once the regressions close, do **not** go straight to
   photo-digitizing steps 5+. M0 instruments `digitizer/tools/shape_lens.py`
   with distance-transform stats (`max/μ/σ` at skeletal pixels) against the
   current `2·area/perimeter` satin-vs-fill call, on the fixture logo and all
   37 `scratch_corpus/` files — zero engine change, zero golden impact.
   **The instrument existed already (2026-08-02, `70a14e8`) but had never
   been run to completion — done 2026-08-04, unit-fixture + real-art +
   timing + taper legs measured and written up
   (`docs/superpowers/plans/2026-08-04-m0-shape-lens-measurement.md`). The
   37-file corpus leg is still blocked** — `scratch_corpus/` is gitignored
   and local-only, empty in this remote checkout; Kent needs to run
   `shape_lens.py corpus scratch_corpus/` locally and hand back the output
   before M0 fully closes per the architecture doc's original spec. Key
   finding so far: the shipped rule sews the SAME shape (`logo_alpha.png` vs
   `logo_whitebg.png`, same design, different file encoding) as satin on one
   file and fill on the other, purely from antialiasing noise landing
   `2*area/perimeter` on opposite sides of the 5.0mm cap — every DT arm
   agrees "fill" on both. **M1 is merged** (`bc1e59e`,
   `digitizer_core/shapefield.py` — `ShapeField`: mask, skeleton, exact EDT,
   scale, origin — hoisting one `medial_axis(rng=0)` so skeleton and DT are
   computed together, behind `cfg.extra["shapefield"]` defaulting to today's
   path). The byte-identical requirement is enforced, not just stated:
   `tests/test_shapefield_byte_identical.py` duplicates
   `stage6_satin._rasterize`'s rasterization number-for-number rather than
   reimplementing it, both on `origin/main` now. What's left of this slice is
   M0's corpus leg (above) and M2/M3 (below) — neither started. Rationale:
   `stage7_sequence.py:97` makes the satin/fill call
   from `2·area/perimeter` (a statistic the source patent warns against —
   it satins a 20mm disc under a 5mm cap once the edge is serrated) *before*
   the DT even exists in `stage6_satin.py`. Steps 5+ all lean harder on that
   classifier than anything shipped so far. Full
   architecture: `docs/dt-first-architecture-2026-08-01.md` §2 and
   `docs/masters-teardown-2026-08-01.md`.
3. **Photo-digitizing plan steps 5+** (`docs/photo-digitizing-plan-2026-07-31.md`)
   — **rows 6/8/9/10/13 are now built**: direction field (row 6),
   scan-line mono tonal (row 8), meander mono tonal (row 9), streamline
   thread-paint in both its mono and layered-multicolour slices (row 10),
   and chart-restricted weighted k-medoids palette selection (row 13 /
   build-order step 7, `digitizer_core/palette.py` — replaces the photo
   path's per-region nearest-thread snap; the eyes/skin/subject class
   multipliers are wired but run at 1.0 until step 3's face priors exist,
   see that module's THE CLASS-WEIGHT SEAM) — see MASTER_SCOPE.md area 1
   for the commit-level breakdown. Whatever the plan doc queues past these
   is still open; re-check the plan doc itself rather than trust this
   bullet's row count going forward.
4. **DT-first M2/M3 onward** — the classifier swap itself, the change a
   customer can see. Corpus-gated *and* sew-out-gated, and it needs the
   corpus disagreement table M0 produces before it can be judged.

A sew-out is still not scheduled — Kent's explicit call: more work first,
don't push for it.

## Known bugs (unresolved, not accepted — Kent's call on the fix)

- **DST axis transposition.** EMB-Bot's own DST codec (`src/dst.js` /
  `src/dstimport.js`) is transposed vs. the Tajima/pyembroidery standard —
  confirmed via 4 independent sources + a clean-room decode. Browser DST
  round-trips correctly against itself, so it's shipped this way undetected;
  every existing EMB-Bot DST is affected. Fixing it means a migration path
  for old files. See `dst-codec-axis-discrepancy` in Kent's memory and
  `docs/dst-axis-verdict-2026-07-31.md`.
- **Gradient-class designs fragment before blend treatment** — **FIXED
  2026-08-03**, same-day follow-up session. `gradient` class still segments
  via plain k-means (23 regions on the repro fixture, unchanged), but every
  fragment now sews its fill rows at one shared angle
  (`SourcePixels.design_row_angle_deg`, `stage6_blend.
  detect_design_ramp_angle`) instead of each independently computing its
  own — the "patchwork of differently angled wedges" is closed. Root cause
  was narrower than first suspected: all 23 fragments were hitting
  `blend_fill`'s plain-tatami FALLBACK (post-quantize color bands are
  already near-uniform, so per-fragment ramp detection rarely fires), and
  that fallback's hardcoded `angle_deg=None` was the actual bug. Also:
  fitting lightness alone (as `detect_ramp` does per-region) misses the
  repro fixture's ramp entirely (r2 0.003) because it's a hue rotation, not
  a lightness slope — the design-wide detector fits L/a/b independently and
  takes whichever channel carries it. Fragment count and radial-ramp angle
  sharing are explicit non-goals, left open. Full writeup: the plan doc's
  "Defect 1 update" section.
- **`BACKGROUND_ENCLOSED` drops enclosed white icon linework as a hole**
  even when it survives stage 1's background detection intact — root-caused
  2026-08-04 (same session as this bullet was first written). Corrected
  location: `stage1_prep.py::prep`'s no-alpha color-heuristic branch
  (`enclosed = close & ~border_bg`, folded into `bg` before `fg`), NOT
  `stage3_segment.py` as first suspected — enclosed pixels never reached
  stage 3, or vectorization, or ever got a `shape_id`, which made the
  warning's own "toggle it back on in review" claim false: there was no
  shape for a review edit to name. Repro fixture:
  `digitizer/testdata/photo/repro_gradient_white_icon.png`. Original
  diagnosis:
  `docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`.
  Design: `docs/superpowers/plans/2026-08-04-enclosed-background-restore-design.md`.

  **FIXED, later 2026-08-04 — the full cross-cutting slice landed:**
  `stage1_prep.py` now joins enclosed pixels to `fg`, `stage4_vectorize.
  tag_enclosed_background` tags them post-vectorization, `pipeline.py`
  resolves a `stitched` shape-override defaulting to "not enclosed" and
  excludes only at `plan_stitches`, the service (`digitizer_service/app.py`)
  accepts/validates/exposes the `stitched` key, and the Studio Layers panel
  gained a restore control for it. See MASTER_SCOPE.md area 1 for the
  commit-level breakdown. **The one caveat that kept this from working
  end-to-end through the actual UI is fixed too, merged PR #22:** Studio's
  real upload path manufactured an opaque alpha channel that defeated
  background detection entirely; a fully-opaque channel is now discarded
  as information-free. Verified post-merge at the HTTP level (opaque-RGBA
  twin of the repro fixture now matches its RGB original exactly); a live
  browser run of the full flow hasn't happened yet.

## Running things

All three counts below were re-run and verified 2026-08-04 (latest pass, on
`origin/main` at `354f075` — CI's own green run on this exact commit
confirms these numbers outside this environment too, not just locally) —
if one comes back lower, something regressed; don't assume the doc drifted.

**CI now exists.** `.github/workflows/python-package-conda.yml` (PR #37
rewrote Kent's initial stock conda template to run the three commands
below for real) runs on every push and pull request — three jobs, engine /
studio / digitizer, the digitizer job deselecting the same 3 known
container goldens called out below. Every PR now needs its Actions run
green in addition to a local pass before merging.

**Known ongoing issue, since 2026-08-09, unresolved as of this writing:**
CI checks across many PRs (#106 onward) fail in ~2-4 seconds with
`runner_id: 0` — no GitHub Actions runner is ever assigned, the job dies
before any step (not even checkout) runs. This is NOT a code problem —
confirmed repeatedly by diffing against the same workflow succeeding
normally (18s-15min per job) on a parent commit moments earlier, and by
every affected PR passing its full local test suite. Best diagnosis (not
confirmed, since this session can't see GitHub's billing UI): a GitHub
Actions minutes/spending-limit or concurrency-quota issue on the account —
check **Settings → Billing and plans → Plans and usage → Actions** on
whichever account/org owns this repo. This repo has no required-status-
check branch protection, so Kent has been merging past the red checks when
the failure matches this exact signature (verify via the GitHub API/UI:
near-instant failure + `runner_id: 0` on the job) — that's a reasonable
workaround given the pattern, not a reason to stop checking whether it's
actually cleared before assuming so.

```bash
node --test                 # engine tests (root) — 267/267
cd app && npm install && npm run dev     # Studio dev server
cd app && npm test          # Studio tests (vitest) — 348/348 (25 files)
node tools/build-embf.mjs   # rebuild the binary font library (see section above)

cd digitizer && .venv/Scripts/python -m pytest -q   # Python digitizer tests -- 654/658 (~7-11 min)
cd digitizer && .venv/Scripts/python -m digitizer_service   # service on 127.0.0.1:8721
```

**654/658, not 404/407.** The 3 failures are all **pre-existing,
container-environment** byte-identical/golden-hash mismatches this note has
flagged since 2026-08-03 (`test_flat_lane_byte_identical.py::…
[logo_alpha.png]`, `test_pushcomp.py::…[logo_whitebg.png-towel]`,
`test_stage2_photo_segment.py::…[logo_alpha.png]`) — still not investigated
further, still a guess (numpy/opencv/shapely point-version difference vs.
whatever machine the goldens were pinned on), still worth a look before
trusting either count as this environment's steady state. A 4th failure
briefly existed between two merges — `test_directionfield.py::
test_drone_render_smoke_and_debug_artifact`, because the direction-field
branch had merged without its `debugviz.direction_field` render function
(an agent lane's uncommitted worktree edit that never made it into the PR)
— and is now gone: PR #22 restored the function, confirmed by re-running
this suite against a fresh `origin/main` checkout after the merge. If this
specific failure resurfaces, that's a real regression, not this note being
stale.

`EMB-Bot-standalone.html` is **DELETED 2026-08-04, Kent's call** — do not
regenerate it. `tools/bundle.mjs` (its rebuild step) is now dead/orphaned
code — left in place, not wired to anything, not to be run.

Opening `EMB-Bot.html` needs internet (CDN: opentype.js@1.3.4 — **pinned,
v2 hangs** — jsPDF, ~137 Google Fonts). `file://` renders static-only; serve
over http to actually test Generate.

## The one rule that explains most "quality" bug reports

**Flat, spot-color art in → pro-quality stitches out. Photographic/gradient
art out of ANY auto-digitizer → mush**, no matter how good the engine gets.
Kent already chose "optimize for clean input art" over "make it magically
handle anything" — this is a settled decision, not an open question. If a
future report is "digitizing looks bad," check the input art's flatness
*first*, before touching engine code. The built-in **Flatten workflow**
(Image mode) exists precisely to make this collapse-to-N-colors step visible
and controllable to the user.

## Architecture map

- **`src/*.js`** — engine modules. Each is dual-mode: browser `<script>`
  (attaches to global `EMB`) and CommonJS (Node tests). Key ones:
  - `digitize.js` — the orchestrator. `buildQualityDesign` (image/logo path)
    and `buildLetteringDesign` (text path) both live here.
  - `satinplay.js` / `satinfont.js` / `satin.js` — satin column generation.
    `satinplay.js`'s `emitZigzag` + `satinFromRails` is the current quality
    lever for lettering (rails+rungs → clean zigzag, not auto-skeletonized).
  - `fabrics.js` — 7 fabric presets driving pull-comp/underlay/density/trim.
  - `flatten.js` — medianCut → modeFilter → absorbSmallRegions pipeline.
  - `fonts/` — pre-digitized satin font library (14 fonts, JSON + license
    files, parsed offline from Ink/Stitch's open-source font set).
  - `dst.js` / `exp.js` / `pes.js` — stitch file encoders. DST is
    byte-verified/primary; PES is best-effort.
- **`app/src/`** — Svelte 5 Studio. `App.svelte` + `ui/` (steps/components) +
  `lib/` (non-DOM logic, each paired with a `.spec.js`): `project.js` (data
  model, v2 = `{version,garmentId,selectedId,elements:[...]}`), `generate.js`
  (bridges to engine), `combine.js` (multi-element stitch merge), `preview.js`
  (2.5D canvas render), `projects.js` (localStorage save/load registry),
  `threads.js` (named thread-color catalog), `hints.js` (onboarding).
- **`digitizer/`** — Python auto-digitizing engine + optional FastAPI
  service (`digitizer_core/` importable lib, `digitizer_service/` wrapper).
  Own venv, own test suite, own docs. See "The Python digitizer" above.
- **`tools/`** — `bundle.mjs` (standalone builder — **run after any src/
  change**), `build-font.mjs` (Ink/Stitch font → JSON font library),
  `run-digitize.mjs` / `run-flatten.mjs` / `render-dst.mjs` (Node-side
  pipeline runners so you can test digitizing on a real image without a
  browser — useful since the browser tool here can't do file uploads).
- **`docs/superpowers/specs/` + `/plans/`** — every feature slice has a spec
  + plan written before building. Read the relevant one before extending that
  area; they contain the "why," not just the "what."
- **`.superpowers/sdd/progress.md`** — task-by-task ledger for the Studio
  slices (1–8). Doesn't cover the font-editing round (that used a plain
  worktree, not `subagent-driven-development`) — see the spec/plan above for
  that instead.

## Known limitations

**See [`MASTER_SCOPE.md`](MASTER_SCOPE.md) for current status, confidence,
and open issues per capability area** — that's the live dashboard now; this
section used to duplicate it and the two drifted, so it doesn't try to be
exhaustive here anymore. The one exception: the *design decision* that
photographic/gradient art can't reach pro quality via auto-digitizing is
architectural, not a status snapshot — see "the one rule" above, which stays
here since it explains *why*, not *what's currently true*.

## Working conventions this project has settled on (don't relitigate)

- **Process:** brainstorm → write spec → write plan → build (via
  `subagent-driven-development` in a git worktree, or ULTRACODE workflows for
  bigger slices) → review (multi-lens/adversarial before merge). This repo
  has done this ~10 times; deviating without reason will surprise Kent.
- **Additive, back-compat engine changes.** New `opts.*` fields default to
  exactly today's output when absent — no migration step, no behavior change
  for existing callers. Keep doing this.
- **Rebuild the standalone bundle** (`node tools/bundle.mjs`) any time
  `src/` or `EMB-Bot.html` changes — it's a committed 8MB+ artifact, not
  generated at load time.
- **Verify claims, don't trust prior summaries at face value** — this very
  cookbook exists because a memory note said work was "merged to main" when
  it was actually sitting unmerged in a worktree. `git log` is ground truth.
- When adding a font: must be an Ink/Stitch-style font with real
  `<path inkstitch:satin_column>` data (rails+rungs), not just an outline
  font — outline fonts only auto-trace, which Kent has already rejected as
  lower quality than hand-authored satin columns. Recipe is in the README's
  "Adding more fonts" section (via memory) / `tools/build-font.mjs` usage.

## Who's asking for what

Kent (`kent@sdwheel.com`) drives every product decision here via
AskUserQuestion-style brainstorming — he's picked the MVP scope, the font
list, the rejected fonts (too ornate / broken metrics / license-restricted),
and every "build vs. defer" call listed above. Don't assume a feature is
wanted just because it'd be a nice engine capability; check for an existing
spec/decision first, and if there isn't one, ask him rather than guessing.
