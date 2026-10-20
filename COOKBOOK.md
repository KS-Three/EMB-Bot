# EMB Bot — Cookbook for the next Claude agent

Handoff doc. Read this before touching code. Full blow-by-blow history lives in
`.claude/memory/emb-bot-digitizer.md` (moved into the repo 2026-08-14, indexed
by `.claude/memory/MEMORY.md`) — this file is the self-contained handoff.

**Last refreshed 2026-10-20** over `5a4c019..0eb5e02` on `main` (2026-10-11 →
10-19, 172 PRs merged; PR #990, merged during the refresh, is folded in). `.claude/hooks/nudge-cookbook-stale.js` nags once 20
source commits have piled up past the last touch; the foreman then assigns
ONE named session per refresh (the K3 standing rule under "Branches &
worktrees"), and every other session puts status in its PR body, not here.

## What this is

Browser-based embroidery auto-digitizer + guided lettering studio, plus a
Python digitizing engine that runs as a localhost service. Two parts:

- **`app/`** — "EMB Bot Studio", a Svelte 5 + Vite configurator — one panel
  (`ui/Configurator.svelte`: design, garment), a sticky `SummaryBar`,
  and a `DownloadSheet` that wraps `DownloadStep`; e2e specs reach the sheet
  through `e2e/helpers.js` `openDownload` — built on top of the JS stitch engine via
  `window.EMB` (the `src/*.js` modules, copied into `app/public/engine/` by
  `app/scripts/copy-engine.mjs`).
- **`digitizer/`** — Python auto-digitizing pipeline (OpenCV, scikit-image,
  shapely) + an optional FastAPI service. See the digitizer section below.

(The original single-page `EMB-Bot.html` was deleted 2026-08-08, commit
cd9dfcb — the Studio is the only front end now.)

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
(**85 fonts** as of 2026-08-22; was 55 after the 2026-08-04 licence-audit pulls
and the same-day removal of all 13 ShareAlike fonts (Kent's call — audit §9;
removal made the paid launch independent of the CC-BY-SA question, and the
lawyer brief is the optional restore path), then grew through the 2026-08-21/22
upstream sweeps — this number has drifted twice without the doc being updated,
so don't trust it without recounting `manifest.json`), lazily fetched per font by
`app/src/lib/fontLoader.js`. The
old eager `src/fonts/satin-fonts.js` is OUT of the Studio pipeline and — since
`EMB-Bot.html`'s deletion (2026-08-08) — has no consumer left at all (this line
said "still used by legacy `EMB-Bot.html`, do not delete it" long after that
page was gone); it survives as the audited legacy registry of record, and
removing it is Kent's call, not cleanup. **Its audit ran 2026-08-04**
(`docs/font-license-audit-2026-07-31.md` §10): the 7 license-pulled fonts
(milli_marif_bold, tt_masters + the 5 ShareAlike: aventurina, emilio_20,
emilio_20_bold, geneva_simple, monicha) were removed, 21 → 14 entries, all
remaining OFL-1.1/CC0 and present in the shipping manifest. Do not re-add a
font there unless it is also in the shipping manifest. `EMB-Bot-standalone.html`
(the frozen artifact that inlined the pre-audit 21 fonts) was **deleted
2026-08-04, Kent's call** — no pre-audit font list ships anywhere anymore.

- **EMBF format** (`src/fontbin.js`): quantize coords ×4 → per-ring delta →
  Int16 stream; skeleton JSON carries everything else. Guard test
  `test/embf-guard.test.js` pins `decodeFontBin(<committed .embf>) ==
  quantizeFont(font)` for every static `src/fonts/*.json` source (17 now — the
  2026-08-04 license pulls shrank the original 21; the test's floor assert is
  >= 14) — it must stay green through any codec change.
  Acceptance evidence (0.00–1.07% stitch drift, visually cleared):
  `docs/superpowers/notes/2026-07-27-embf-acceptance.md`.
- **Two builds from one tree.** `node tools/build-embf.mjs` writes the
  **sellable** library (85 fonts, everything inside `ALLOWED_LICENSES`).
  `node tools/build-embf.mjs --personal` writes Kent's private library — the
  sellable set plus the ShareAlike / NC / GPL / pulled trial imports (38
  personal-only faces as of 2026-08-22, per the builder's own sidecar pass;
  this count drifts with the sweeps, trust the build output) — to
  `bin-personal/` + `manifest-personal.json`, both gitignored, so a fresh
  clone or CI cannot produce a build containing them. The split is at BUILD
  time on purpose: a runtime toggle is not a distribution boundary. `copy-engine.mjs` serves the
  personal build when it exists and says so loudly. `--personal` also writes
  `previews-personal/` and `licenses-personal/` (both gitignored, and they must
  stay that way — a preview is a RENDER of the font, so publishing one for a
  ShareAlike/NC face is the distribution the split exists to prevent);
  `copy-engine` OVERLAYS them on the committed ones. Run
  `node tools/build-previews.mjs --personal` after a personal rebuild.
- **Rebuild**: `node tools/build-embf.mjs`. Requires `scratch_ink/`
  (gitignored): `_tiers.json` (tier classification) + `_out/*.json` (trial
  imports). Recreate `scratch_ink/` by copying from the master
  `Ink-Stitch Fonts` clone at `G:\My Drive\EMB-Bot\Ink-Stitch Fonts\`
  (see BACKUPS.md) and re-running the classify/import steps; the
  committed `.embf` files are the artifacts of record either way.
- **Tier rule (Kent's decision): only `tier:"verified"` ships.** Unverified =
  internal work queue with a concrete reason per font in `_tiers.json`.
  License policy for NEW fonts: **OFL-1.1 / CC-BY-4.0 / CC0 only** — this line
  read "OFL-1.1 / CC-BY-4.0 / CC-BY-SA-4.0 / CC0" until 2026-08-21 and was
  wrong from 2026-08-04 onward; `ALLOWED_LICENSES` in `build-embf.mjs` is the
  authority, not this doc. **ShareAlike is permanently closed** (Kent,
  2026-08-21: SA may propagate through the compiled `.embf` onto customer
  stitch files — an unbounded liability on the product's core output). Do not
  re-propose it; the `docs/lawyer-brief-cc-by-sa-2026-08-04.md` restore path is
  retired. **NonCommercial and NoDerivatives can never ship** in a paid product
  — `licenseId()` labelled both as plain `CC-BY-4.0` until 2026-08-21
  (`docs/font-expansion-research-2026-08-21.md` §5). `precious` is excluded
  (GPL-3.0). `ondulamarif_XL`
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
  stayed green). Keep all three in sync. (There used to be a fourth list in
  legacy `EMB-Bot.html`; it died with that page, 2026-08-08.)
- **Classifier gap — FIXED, and then found to have a second half.**
  `qc-font.mjs` now counts stitchability per LETTER GLYPH, not per file, so a
  font whose letters are runs-only no longer classifies as satin (that was
  ondulamarif_XL). The second half, found 2026-08-22: the check asks "does this
  letter produce stitches", which a glyph can pass while rendering as a STUB.
  Four shipped fonts did, and the cause was `build-font` dropping SVG transforms
  (next bullet). `qc-font.mjs` warns on letters under 0.45x their case-median
  height and `test/font-stunted.test.js` guards it; the library is currently
  clean. **If a font looks wrong, render it — do not trust the QC line.**
- **`build-embf` RUNS the tier gate** (since 2026-08-22). A `qcFont` hard fail
  excludes a font from the sellable build; `--personal` warns and keeps. Before
  this the gate was enforced only by a test over the 17 static `src/fonts/*.json`
  sources, so the 68 fonts arriving via `scratch_ink/_out` were QC'd by nothing.
- **Unsupported characters are REPORTED, not swallowed.** The lettering path
  skips a character the font has no glyph for; `buildLetteringDesign` returns
  `unsupported` (source order, deduplicated) and `generateAll` carries it per
  element, so the field can say "This font can't stitch …" instead of sitting
  empty. Since 2026-08-22 the same report covers a glyph that EXISTS but sews
  nothing (satin-less, no authored run length, no cross grid — `e56ff13`): it
  keeps its own advance (a hole of the right width) and lands in `unsupported`
  instead of vanishing quietly. If you add a code path that builds lettering,
  pass it through.
- **Watch for Latin assumptions when touching font tooling.** Adding Hebrew
  found three, all silent: `build-previews`' sample-text fallback, the personal
  build's `sewsAnything()` gate, and the lettering path's character skipping.
  A helper that filters on `[A-Za-z0-9]` is the smell.
- **Text direction.** A font imported from `rtl.svg` carries `dir: "rtl"`, and
  `satinfont.layoutText` walks that line's characters in reverse so the FIRST
  logical character lands rightmost. `charIdx` deliberately stays logical, since
  it exists to map a `<textarea>` selection onto glyphs. Hebrew needs nothing
  more (no contextual forms). **Arabic is NOT supported** and must not be added
  by simply importing it: its letters need initial/medial/final/isolated forms
  and must join, so unjoined output is wrong text, not plain text.
- **SVG transforms are applied for BOTH layouts** (`pathsTf`, since 2026-08-22).
  There used to be a second walk that ignored them, used for every
  single-`ltr.svg` font. A glyph that places repeated geometry by transform —
  `mimosa_large`'s "D" is one dot with 38 transforms — collapsed onto a point
  and sewed 6,193 stitches into 0 mm of height. Do not reintroduce a
  non-transform-aware fast path.
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
  Per-GLYPH stitchability check — satin columns, a run with an authored
  stitch length, or a cross-stitch region with a measured grid all count,
  since bean/run and cross-stitch lettering became sewable (2026-08-21);
  it was satin-only when this bullet was written. 100% unstitchable letters
  = hard fail, >10% fail, ≤10% warn; plus advances incl. digits, finite
  geometry, coverage warnings, and the stunted-height warn (see the
  classifier-gap bullet above). Run on any candidate font JSON before
  tiering it. The old gitignored scratch classifier is retired as the gate
  of record.
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

- **Env**: Python venv at `digitizer/.venv` (gitignored) — 3.14 on Kent's
  box; the floor is `requires-python = ">=3.12"` (`pyproject.toml`), CI pins
  3.12, and cloud sessions must build with `python3.12` explicitly (CLAUDE.md
  owns that trap — this line used to state 3.14 flatly, which misled cloud
  sessions whose venv is 3.12). Run tests with
  `cd digitizer && .venv/Scripts/python -m pytest -q` — a bare
  `python probe.py` will NOT put cwd on `sys.path`, must use `python -m pytest`
  or set `PYTHONPATH=.`. **`.venv/Scripts/` is Kent's Windows box; on Linux —
  every cloud session — the same interpreter is `.venv/bin/python`, and that
  substitution is the only difference. It applies to every `.venv/Scripts/`
  path in this file.** No test count is quoted here on purpose — see
  "Running things" below for the expected *failure classes*, which are what
  actually tells you whether a red run is a regression. *(a count lived here
  until 2026-08-21 and had drifted several hundred tests out of date;
  MASTER_SCOPE rule 6 bans counts in prose for exactly this reason)*
  **A fresh cloud container has NO venv built and its bare `python3` is not
  3.12** — "What a cloud worker session has" under "Running things" lists
  what else is missing there (measured 2026-10-20).
- **Pipeline**: image → **classify** (`stage0_classify.py`) → prep
  (background mask, `stage1_prep.py`) → segment, one of three stages
  depending on class/config: `stage2_quantize.py` (global k-means +
  CIEDE2000 thread snapping, used for `flat`/`gradient`),
  `stage2_photo_segment.py` (SLIC superpixels + region-adjacency-graph
  merge, used for `photo_subject`/`photo_scene`), or
  `stage2_sam2_segment.py` (SAM2 mask-based segmentation for
  photo-classified designs, opt-in via `cfg.photo_segment_sam2`) →
  small-region absorb + enclosed-hole handling (`stage3_segment.py`) →
  contour vectorize (`stage4_vectorize.py`) → stitch planning: overlap
  resolution, fill/satin/border/contour/appliqué/**blend** tiers plus the
  photo tonal tiers (scan-line, meander, streamline, sketch —
  `stage6_scanline/meander/streamline/sketch.py`), sequencing
  (stages 5–7) → DST/PES/EXP/SVG export via **pystitch** (pyembroidery's
  actively maintained Ink/Stitch fork, same API and coordinate convention —
  swapped 2026-08-11, `docs/pystitch-evaluation-2026-08-11.md`; this bullet
  said "pyembroidery" long after the swap). The pipeline is also split at
  the review-edit seam — `pipeline.build_generation` (stages 0-4) +
  `finish_generation` (edits applied, palette, plan) — for the service's
  generation cache below; `run_stages` composes the two.
- **The input classifier (`stage0_classify.py`, 2026-08-02)** is 4-way —
  `flat` / `gradient` / `photo_subject` / `photo_scene` — on three signals:
  `unique_color_mass`, `gradient_smoothness` (Sobel local variance,
  edge-excluded with a raw-variance fallback), `alpha_softness`. Tuned on
  real production art (`enthusiast_logo.png`, `drone_render.png`), not
  synthetic fixtures. **`unique_color_mass` is the real photo/non-photo
  gate, not `gradient_smoothness`** — `drone_render.png` reads rough on
  smoothness because of glow halos and an inset scene. The threshold order
  is documented in the module; read the why before "fixing" it.
- **Stage 1.25 — "is this a PHOTOGRAPH?" (`photo_signals.py`, 2026-09-11)** is
  a separate question from the classifier above and answered by separate
  signals, because the colour ones cannot: a real photograph reads LESS
  photographic than two gradient logos on `unique_color_mass`. EXIF camera
  Make/Model, then the YuNet detector, behind `cfg.detect_photographic`
  (DEFAULT OFF). It answers **True or None, never False**, so it can only ADD
  photographs and an explicit `is_photographic` still wins. Detection runs in
  `build_generation`, but `finish_generation`, `plan_stitches` and preflight
  each arrive holding the CALLER's config — the verdict therefore rides the
  `Generation` and the `PipelineResult` (like `design_class`), and the first
  two fold it back in with one line, `photo_signals.apply_detection`. Preflight
  instead re-reads the `PHOTO_DETECTED` warning — the pattern it already uses
  for the classifier's verdict, and the one that still works when it is handed
  a bare plan with no result. **If you add another entry point that reads
  `is_photographic`, add the fold to it**, or a detected photograph silently
  loses the machinery there. Nothing
  committed here trips either signal, so the corpus cannot show you it works —
  see DOCTRINE before concluding it is broken.
- **The design-silhouette cap (`cfg.edge_cap`, DEFAULT `"bean"` since
  2026-09-11)** closes the design/fabric boundary where every tatami row ends
  in open air — the union of several shapes' edges, which no per-shape border
  can reach. Two consequences to know before reading a plan: **every design now
  ends with one extra BLOCK**, and that block sews in a cone the job already
  ran, so the operator re-loads it (Kent ruled that stop acceptable rather than
  cap the edge in a badly matched colour — DOCTRINE carries the numbers). It is
  gated: `silhouette_cap(omit=…)` skips whatever linear stitching already
  covers the outline, which is what took the bill from +8.6-100.4% down to
  +5.9-26.3%. Turning it off is `edge_cap="none"`, and most tests whose subject
  is artwork sequencing say exactly that.
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
- **SAM2 runs in its own isolated venv** (`digitizer/sam2_isolated/`, same
  subprocess pattern and reasoning as `rembg_isolated/` — torch must never
  touch the shared venv's exact pins). `stage2_sam2_segment.sam2_segment_seam`
  shells out to `digitizer_core/sam2_worker.py` under that venv's
  interpreter; without it built, `photo_segment_sam2` degrades to the
  classical SLIC+RAG path with an honest warning. The checkpoint cache MUST
  be pre-warmed (`sam2_worker.py --prewarm tiny`) — job mode refuses to
  download, by design. The prewarm now enforces the server's Content-Length:
  a real cloud-container truncation (2026-08-22) had two runs cache 136.9
  then 140.8 MB of a 156.0 MB checkpoint, print "checkpoint cached", and
  kill every later job far from the cause — the `.part`-rename discipline
  can't help when "success" is the lie. The whole lane is proven buildable
  and runnable in a cloud container, not just on Kent's box; build steps and
  disk budget in `sam2_isolated/README.md`.
- **`stage6_blend.py`** is the gradient blend fill tier; its `detect_ramp`
  fitting logic is what the queued gradient-fragmentation fix wants to reuse
  one stage earlier (see Known bugs).
- **The photo-lane satin width floor** (`stage6_satin`, 2026-08-22): a shape
  that EARNED satin but whose doubled p90 medial width sits under
  `PHOTO_MIN_SATIN_WIDTH_MM` (Law 31's 1.0 mm, adopted verbatim — gate 1
  owns the value, never tune it without cloth) is rerouted to the outline
  run, with verdict reason `photo_width_floor`. **Photo classes only**, and
  that gate is the finding, not a hedge: the defect population
  (drone/summit) and the disproof population (61/64 sub-mm satins on real
  customer logos are ground the pro also satined) BOTH classify `gradient`,
  so classification can't separate them — the photo lane (stage 0's own
  photo classes, or stage 1.25's EXIF-or-face detection, which the Studio
  asks for on every job since 2026-09-30; the user's own "It's a photo"
  correction before that) is the only honest gate. Flat/gradient stay
  byte-identical.
- **Run the service**: `.venv/Scripts/python -m digitizer_service` →
  `127.0.0.1:8721`. **Building the venv from scratch takes TWO installs, not
  one.** CLAUDE.md sends you to `pip install -e .` (correctly — it enforces the
  3.12 floor that `requirements.txt` does not), but the web stack is an
  optional extra in `pyproject.toml`, so that command alone gives you a venv
  that imports `digitizer_core` fine and dies on `ModuleNotFoundError: No
  module named 'fastapi'` the moment you start the service. Use
  `pip install -e ".[service]"`. Cost a cycle on 2026-08-25.
  *(confirmed — `digitizer/pyproject.toml` `[project.optional-dependencies]`)* `GET /health`, `POST /digitize` (image+config → job),
  `POST /digitize-manual` (hand-authored shapes, no image — stages 1-4
  skipped; same job/response contract), `GET /jobs/{id}`, `POST /export`,
  and since 2026-09-30 the calibration trio — `GET /calibration/info`,
  `GET /calibration/card?format=` (card v2 in any machine format; built on
  first use, ~15 s, cached for the process) and `POST /calibration/read`
  (a photo of the sewn card → readings + a draft fabric profile, synchronous,
  10-20 s; 422 when the card is not found). `digitizer_core/calibration/`.
  Binds loopback only, CORS localhost-only.
- **The stage 0-4 generation cache** (2026-08-22): `/digitize` caches
  `build_generation`'s output per artwork + every config field EXCEPT the
  four review-edit keys (`digitizer_service/jobs.py` — `GenerationCache`,
  LRU of 4, `EDIT_KEYS` pinned by `tests/test_generation_cache.py`), so an
  edited re-digitize re-runs only `finish_generation` + `plan_stitches`
  (stages 0-4 measured at 53-81% of a job). Every consumer finishes from
  `Generation.fork()`; responses carry `generation_cache: "hit"|"miss"`.
  Separate gotcha: the JOB cache replays a finished job for an identical
  request, so after changing machine state a cached job embedded (repairing
  the SAM2 venv, say) restart the service or you get the pre-repair result
  back at 0.0s and believe it.
- **Stitch-geometry instruments, one per quality claim (2026-09-03).** A number
  in a PR body or MASTER_SCOPE is not evidence unless a committed script
  re-produces it: `digitizer/tools/fill_exposure.py` (fill travel laid over
  columns already sewn, `--off` for the before), `digitizer/tools/satin_lean.py`
  (how far satin crosses lean off their own perpendicular and off the house
  angle, and the thread pitch across the column; `--stock` for the instrument's
  own floor on unhoused columns; `--anchor` for the house anchored to the
  line of text, lettering plan step 1), `digitizer/tools/fill_dust.py` (fill steps
  halved by float dust at the stitch-length threshold), `digitizer/tools/rail_edge.py`
  (where satin rails sit against the artwork edge, rail jitter and same-rail
  holes; `--ladders` for the containment-miss census, `--bare` for coverage as
  bare satin area, `--follow-edge` for the rail flag), `digitizer/tools/curve_tiers.py`
  (per-shape tier diff for `curve_turn_deg` off vs on, shapes paired by
  centroid — the flip evidence a stitch total cannot give), `digitizer/tools/ribbon_stability.py`
  (how many satin/fill verdicts flip when only the polygon's boundary detail
  changes, and what each candidate cure does to the shipped verdicts;
  `--variant` for the cures), `digitizer/tools/recapture_flat_lane_key.py`
  (the only sanctioned way to move a golden: pre-change tree + control fixture),
  `digitizer/tools/halo_spools.py` (cones a design spends on JPEG/anti-alias
  ringing rather than on artwork — thin bands, grouped into the stacks stage 4
  shatters them from, whose thread is a Lab interpolation of the two things
  they lie between; `--detail` per region),
  `digitizer/tools/stroke_verdicts.py` (per-stroke satin verdicts against TWO
  denominators — all regions and the ones the plan actually SEWS — and it calls
  `classify_ribbon` both ways rather than restating the rung's rule),
  `digitizer/tools/satin_columns.py` (satin passes rebuilt from the plan, where
  a run of another kind BREAKS the pass), `digitizer/tools/width_tail.py`
  (per satin shape: gate p90, MAX, over-cap fraction and the bare mm2 preflight
  attributes — the p90 gate is blind to a 3% over-cap tail),
  `digitizer/tools/bare_patch_render.py` (preflight's OWN bare cells drawn over
  the artwork, `--patch-junctions` for the fix),
  `digitizer/tools/revalidate_floor.py` (which shapes `revalidate_threads`
  REFUSES on its pixel floor and whether the answer would have changed — it
  wraps the real function and lets the real pass run, so it measures the
  shipped design), `digitizer/tools/region_colour.py` (every SLIC-lane
  region of every fixture: its mean, its median and its modal mean in Lab,
  their distance from the mean, and the chart spool each would pick —
  the census that chose the statistic behind `cfg.robust_region_colour`),
  `digitizer/tools/enclosed_census.py` (every scorecard
  fixture's enclosed regions — count, area, share of the design, the colour
  they would sew in or "unknown" on an alpha hole — and the garment rule's
  verdict against each Studio swatch at both thresholds; item 9's
  instrument), `digitizer/tools/thread_color_render.py` (a design drawn in
  the cones it will actually sew, each changed shape tiled OFF beside ON at
  90 px/mm — a 0.9 mm2 shard is four pixels at whole-design scale),
  `tools/preview-vs-dst.mjs` (the only thing comparing a PICTURE to a FILE:
  the previewer's own `designToStrands` against pystitch's read of the
  encoded bytes, three fixtures x DST/EXP/PES, reporting orientation, how far
  the file's thread strays from the drawn line, and sewn thread either side —
  its fixtures must REACH the split path, which its test asserts, because the
  crossval harness's axis-aligned `long` fixture is exactly how the 2026-09-20
  dogleg survived),
  `tools/long-stitch-census.mjs` (the BROWSER lettering lane: every sewn
  segment of the 85 shipped fonts at three texts, counted past one DST
  record **per axis** — `--doctrine` reproduces DOCTRINE 2026-09-07's own
  Full Back row to the stitch, which is what makes the rest of its output
  quotable, `--big` sweeps the regime the defect lives in, and `--arm
  off|split|fill|both` prices item 10's two answers side by side),
  `digitizer/tools/junction_nodes.py` (every node-to-node edge of the satin
  skeleton per shape with its length, the DT at both ends and the shape's
  half-width — the histogram `_cluster_junctions`' threshold was read from;
  `--clustered` for what is left after the pass), `digitizer/tools/wide_columns.py`
  (the band above the satin width cap per fixture and size — which regions a
  ceiling of X admits — and `--compare` for OFF/ON stitches, trims, sewn
  tiers, satin self-crossing pairs, coverage and uncovered),
  `digitizer/tools/letterforms.py` (every column END of every satin shape —
  a plain stroke or one Goldman member, as `_satin_joined` sews them — with
  its kind, reach to the cap, cap obliquity, flare along the cap face and
  the crossing pairs seated there, split WITHIN one column vs BETWEEN two;
  plus the bare artwork at each junction node. It is what showed the wide
  band's "251 self-crossings" to be seams at two joins and the pro's file
  to carry 2,593 of them; `--flag` repeatable, `--widths`, `--json`),
  `digitizer/tools/junction_blobs.py` (every junction cluster as a BLOB — the
  node's radius against its arms' halves, what the merge did at each arm,
  coverage layers / bare / seam pairs inside it, the arms-only DT p90 per
  shape; `--render`; it is what showed a 17 mm bold letter to be 45–90%
  junction) and `digitizer/tools/pro_layers.py` (a reference DST/PES in our
  frame by the whole design's stitch box: coverage layers and thread inside
  our own letters and blobs, ours beside the pro's — the calibration that
  showed our junctions under-stacked, not over),
  `digitizer/tools/design_direction.py` (where a design's stitch directions
  point: per fill shape the row angle it sewed, its aspect and where the
  angle came from; per design the spread over the half-circle; `--pro FILE`
  registers a professional's stitch file into our frame the scorecard's way
  and reports its spread, ours, the chance-corrected `direction` agreement
  and the pro's direction inside each of our shapes — the item 7 instrument
  that found the pro holding one fill angle at every size),
  `digitizer/tools/rail_comp.py` (what stage 5's pull growth does to every
  satin-tier shape — the corner-arc vertices, the exterior slots it seals,
  the stroke graph on the artwork against the grown polygon — and the
  thread's IoU against the compensated target and the artwork; `--compare`
  digitizes OFF/ON `cfg.satin_rail_comp` with stitches, trims and
  preflight's coverage/uncovered — the item 6 instrument),
  `digitizer/tools/travel_cover.py` (every travel leg read against the thread
  sewn AFTER it, by preflight's own ribbon rule — exposed length per leg and
  per design, `--order nearest|euler`, `--width`; the lettering plan's step 2
  instrument, which found the 245 mm exposed at 80 mm to be the nearest
  order's own legs, not the Euler walk's — and not the satin tier's at all:
  see the next one; its 1 mm grid under-reads fill exposure by a third),
  `digitizer/tools/travel_legs.py` (WHOSE each travel leg is and what it lies
  on: the emitter off the construction call stack, the runs either side, the
  grid reading beside an exact one, and `own-fill` / `top` / `other` /
  `underlay` / `own-bare` / `art-bare` / `FABRIC` under every exposed
  sample; `--set KEY=VALUE` puts any config field on, so it is how
  `fill_bridge_cut` is read — 97.7% of that 245 mm is the FILL tier's column
  bridges on their own finished fill, defect 21's residual, none on fabric),
  `digitizer/tools/pushcomp_pins.py` (`test_pushcomp.GOLDEN_FLAG_OFF`'s tuples
  as THIS tree computes them, for a re-pin with the same pre-change proof),
  `digitizer/tools/resnap_escape.py` (cones `revalidate_threads` ADDS, and how
  many of them the selected palette never chose — the count behind
  `cfg.bind_resnap_all_classes`), `digitizer/tools/tonal_split_ab.py` (what
  photo tonal splitting BUYS, run against its own absence via an explicit
  `split_tonal_regions=False` — cost and quality printed together, because the
  question is the trade). Run each from `digitizer/` with `.venv/bin/python`.

  Two more added 2026-09-06, both born of a finding that would not say what
  it knew: `digitizer/tools/spool_remedy.py` (per blocking
  `THREAD_MATCH_POOR`, whether a spool the design ALREADY LOADS is
  meaningfully closer — 5 of the F-wall's 24 blocks name one) and
  `digitizer/tools/floor_depth.py` (how far BELOW zero the floored designs
  sit, since the score clamps at 0 and hides a 234-point spread behind it),
  and, 2026-09-10, `digitizer/tools/thread_match_floor.py` (every
  `THREAD_MATCH_POOR` finding over the scorecard matrix with the graded
  patch that judged it, then the same designs under a 0 / 2 / 5 / 10 mm²
  patch floor — `run` caches per pair, `report` prints the movers, the floor
  depth and the totals; the sweep behind `_THREAD_MATCH_MIN_PATCH_MM2`), and,
  2026-09-11, `digitizer/tools/color_diversity.py` (the 08-15 spec's
  candidate stage-0 signal — 3-bit colours needed to cover 90% of foreground
  — swept over resolution on a corpus labelled real/synthetic, the margin
  read at NATIVE resolution, and a refusal below four real tonal artworks.
  `--foreground bbox` is the definition that reproduces the spec's own table;
  `engine` is the pixels stage 1 digitizes. They disagree by an order of
  magnitude on a JPEG, so a number from this tool always names its mode).

  And, same day, `digitizer/tools/stage0_signal_origin.py` — the one that
  answers WHERE a stage-0 verdict came from rather than what it was: the share
  of `unique_color_mass` contributed by the background interior, the ink
  interior and the anti-aliased band; which k-means centres landed in each and
  how far apart they are in CIEDE2000; the spread of the verdict across seeds
  (`classify`'s own confidence is one draw, so it cannot show this); and
  `--ablations` / `--sweep` for the one-variable arms and the export-resolution
  sweep. It is what showed `logo_script_tires.png`'s photo-lane misroute to be
  97% the white ground's ±1 grey-level grain and not the lettering at all
  (`docs/stage0-tires-photo-scene-2026-09-11.md`). **Hand it a file, not an
  array you rebuilt** — its own arms had to learn that: four real fixtures
  carry alpha, `_fg_mask` calls alpha ≤ 127 background, and a three-channel
  rebuild silently promotes every transparent pixel to foreground
  (`enthusiast_logo` read `flat` through the file and `gradient` through the
  same pixels without alpha).

  Three more added 2026-09-08 for the quality review and the plans it opened
  (`docs/quality-review-2026-09-08.md`): `digitizer/tools/sewn_tiers.py` (the
  tier each shape actually SEWS, read off the emitted plan's run kinds, flag
  off and on — `stroke_verdicts.py` prints what the classifier says, this
  prints what the plan did), `digitizer/tools/thin_strokes.py` (the strokes
  the ARTWORK carries under the detail floor, read with the flat lane's
  quantizer whichever lane the design took, and how much of each the plan
  sews in the right colour — recall per width band, because a design total
  is dominated by whatever thin structure is longest; `--corpus` for the
  real-art fixtures, nine distinct files, `--forced-class flat` for the lane
  A/B), and
  `digitizer/tools/legibility.py` (OCR on the RENDER against the artwork, per
  text cluster, masked to the cluster's own members, best over three page
  modes and three preprocessing variants on each side; a LOWER bound on
  lettering loss, because tesseract's word model reads Fremont's sewn
  "T H C" as THE at confidence 95 — a per-cluster 1.00 certifies the word,
  not the glyphs, and the missing arm is `thin_strokes.py`'s to see; needs
  the tesseract binary, which CI has — and since 2026-09-10 the measurement
  itself lives in `digitizer_core/legibility.py`, the tool being a CLI over
  it, because preflight's `LETTERING_ILLEGIBLE` check (`cfg.legibility_check`)
  reads the same code). The first two run anywhere; the third
  skips without tesseract the way the OCR tests do. A fourth, the same day,
  for the sub-pixel edges plan: `digitizer/tools/edge_truth_ladder.py` (stage
  4's polygons against the synthetic fixtures' VECTOR truth at 200–3200 px —
  the first edge instrument here that measures against the curve and not a
  raster; `--flag NAME[=VALUE]` runs it with any `PipelineConfig` field on,
  `--tiers` prints the per-shape tier diff DOCTRINE asks of every stage-4
  change). Its baseline found the floor above ~15 px/mm is the 0.2 mm
  simplification tolerance, not the pixel.

  **`digitizer/tools/doc_claims.py` is the odd one out** — it reads no artwork
  and runs in seconds. It checks the two kinds of doc claim a script can
  settle, documented `cfg.<flag>` defaults and `NAME = <number>` constants,
  against the code. It prints what it CHECKED as well as what it found (a
  clean run that examined nothing otherwise reads like a clean run that
  examined everything), and exits 1 only when a CURRENT-STATE doc disagrees,
  so the legitimate dated snapshots in `docs/scope/` stay advisory instead of
  making it permanently red. `tests/test_doc_claims.py` covers it.

  **Three traps these instruments have already sprung, all costly:**
  `StitchRun.jump` means the needle was lifted to REACH the run — the run is
  still needle-down, so filtering on it does NOT exclude travel, it excludes
  genuinely sewn work (a `sewn` count built that way reported 11 of 25
  `THREAD_MATCH_POOR` blocks on unsewn shapes when the real number was 0). And
  a finding labels a shade row `"<shape_id> shade <number>"` for its message —
  that string is not a shape id, and looking it up directly reports every
  gradient band as 0.00 mm2 and unsewn.

  **And `dropped_elements`' `lost_frac` is a SUM of two opposite defects**
  (2026-09-20): artwork never covered, plus thread standing on bare cloth.
  Read `unsewn_frac` / `overshoot_frac`, never the total — a wordmark is
  typically 100% overshoot and a photo lane 100% unsewn (`bridge`). **But
  never quote `unsewn_frac`'s zero as evidence** — its per-region vote
  (`mean > 0.5`) cannot fire where the largest region ink fraction is 0.33,
  as on `enthusiast`; read `uncovered_elements` / `uncovered_ink_frac`, which
  are colour-free and unopened (0.90% of ink, no component over 1 mm²).
  **Nor quote `overshoot_frac` as an area:** `HALO_OPEN_PX` is 0.50 mm and
  `pull_comp_mm` + thread half-width is 0.30 + 0.20 = 0.50 mm, so the opening
  sits exactly on the pedestal and the figure swings 182.7 → 0.0 mm² across
  kernels 3→13 px. It is a same-instrument drift tripwire, nothing more. The two move in OPPOSITE
  directions under one engine change, so the total cannot say which one a
  change bought, and a session read a wordmark's total as lost coverage and
  set out to recover artwork that was never uncovered. Neither half polices
  the other on its own: `unsewn_frac` only counts regions ≥ 1 mm² after a
  0.5 mm opening, so coverage lost as a thin rind along every column is
  invisible to it (a candidate that added 1.7 points of bare satin read
  0.0028 there) — that shape of loss belongs to `rail_edge.bare_area`. See
  DOCTRINE 2026-09-20 and `tests/test_lettering_coverage_regression.py`.

  **Which of the four to reach for, after 2026-09-30.** `preflight`'s
  `ARTWORK_UNCOVERED` is now the one that names a HOLE: it measures every
  thread kind on a 0.25 mm grid with no erosion, behind a thickness and a
  compactness test, and reports `uncovered_hole_mm2` (adjudicated) beside
  the threshold-free `uncovered_worst_mm2`. `tools/uncovered_floor.py`
  sweeps its floor over the corpus, and **any threshold here that has not
  been swept against the current corpus should be assumed stale** — the
  5.0 mm² floor it replaced had drifted above the largest patch the check
  could resolve anywhere.

  **And `tools/bare_anatomy.py` counts SATIN CROSSES AND NOTHING ELSE**, so
  every figure it prints is an upper bound on cloth — by 1.07x to 38.9x
  fixture-dependent, which cannot be divided out. Pass `--all-thread` when
  the claim is about what a customer sees; the default is the right reading
  only for *"did the COLUMN cover its own artwork"*. DOCTRINE 2026-09-30.
- **Acceptance A/B contact sheet** (`digitizer/tools/acceptance_ab.py`, pure
  logic in `digitizer_core/tools_acceptance.py`): the phase-4 eyeball loop.
  Runs every image in the gitignored `digitizer/testdata/photo/acceptance/`
  dir through the LIVE service (`/digitize` → `/jobs` → `/export`, Studio's
  own wire) across five arms — classical, relaxed-speckle
  (`blend_speckle_r2_override`, Kent-funded 2026-08-23), the default-route
  stock/relaxed pair (real photos route `gradient`, where the blend tier and
  therefore the speckle question actually live — the forced-photo arms never
  consult it), and SAM2 when its venv is runnable. Output is a side-by-side
  contact sheet Kent judges by eye; deliberately NO score number on it.
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

- **`make_valid` does not return one type, and the polygons can be nested a
  level deeper than you expect.** Repairing a self-intersecting ring gives a
  bare `MultiPolygon` in the easy case and a `GeometryCollection` holding a
  `MultiPolygon` **plus** a `LineString` when the repair also sheds a dangling
  edge. A flat `[g for g in fixed.geoms if g.geom_type == "Polygon"]` finds
  ZERO polygons in the second case — and stage 4 then dropped the whole
  region. That cost 1,662 mm² on `owl_kent.jpg` and a single 2,787 mm² drop on
  `summit_badge.png` (the entire badge body), for three days, invisibly.
  Always flatten shapely results RECURSIVELY (`_polygon_parts` in
  `stage4_vectorize.py`). Related: a repair also SPLITS a shape into parts, so
  "keep the largest" silently discards real area — take every part that clears
  your sewable floor.

- **An iterative cleanup pass must not re-judge the mess it made itself.**
  `stage6_satin._prune_spurs` erases short dead-end skeleton twigs and repeats
  up to 4 times so a twig behind a twig still goes. But erasing a spur leaves
  its branch node standing, and a node left holding one arm turns that arm into
  a dead end — through no thinning of its own. Pass 2 then measured that stem
  against the same bar and deleted a real limb. On `enthusiast_logo.png` that
  was the emblem bracket's 3.3 mm tab: stem 19.000 px against a 19.4770 px bar,
  while its MIRROR TWIN's stem was 20.000 px against 19.1152 px and lived. One
  raster pixel (0.167 mm at 6 px/mm) decided it, between two shapes whose areas
  differ by 0.06% — so this reads as a traversal-order or symmetry bug and is
  neither. **The general trap: when a decision margin is smaller than the noise
  in its own input, no threshold value is correct** — every candidate just
  moves which shape sits on the knife edge, which is why the retune was
  measured and rejected (it fixed two fixtures and broke two others). Fixed by
  exempting a dead end the function itself created. Also: `_prune_spurs` is
  shared with `textcluster.py`, so its constant is not private to satin.

- **The raster skeleton renders one junction as several pixels, and a fork
  on a symmetric peak as a loop (2026-09-09).** `extract_strokes` now runs
  two passes between `medial_axis` and `_merge_through_junctions` that
  `textcluster.py`'s composition deliberately does NOT: `_collapse_pinholes`
  (the 4-px diamond `medial_axis` leaves around a distance-transform peak,
  which made a cap a junction — 13.6 mm² bare on enthusiast's "N"; a
  Zhang-Suen `thin()` is a no-op on it, tried) and `_cluster_junctions`
  (branch nodes joined by a stub under 0.5 half-widths are ONE junction,
  rooted at the deepest-DT pixel, and a loop returning to its own cluster
  within twice that goes too — the PLUS at 1.25× was two 3-way nodes a
  pixel apart and three strokes). Threshold read off
  `tools/junction_nodes.py`'s corpus histogram (bump 0.2–0.4, trough
  0.4–0.5). Junction noise comes in two shapes, and removing the stubs
  without the loops bared 7 mm² at a tab's tip. Both passes hand back the
  same list when they find nothing, which is why the three flat-lane goldens
  (single strokes, no branch node) did not move.

- **The satin width ceiling is ONE number in four places, and the overlap
  guard is about the bend, not the width (2026-09-09).** `machine.satin_
  ceiling_mm(cfg)` — 5.0, or 6.5 under `cfg.wide_columns` (OFF), or an
  explicit `satin_max_width_mm` — is what stages 5 and 7 classify at AND
  what stage 7 threads into `satin_shape → satin_stroke → _rail_points` and
  `_stroke_underlay`, so the emitter can never refuse what the classifier
  admitted (the 2026-09-02 split route). Under the flag `_fold_caps` caps a
  station at 0.7 × the spine's local radius of curvature; measured, that is
  load-bearing on Becker's bends at 80 mm (coverage_max 7.07 → 5.08) and
  nowhere else, and logo_alpha's apex no longer crosses itself at any
  ceiling to 8.0 — the 2026-09-02 entry's premise has moved. What keeps
  the flag OFF is the render: MARINE goes satin at −13% stitches and comes
  out fanning and crossing at its feet and junctions, +18 trims. Width was
  never the blocker; decomposition is (`docs/renders/wide-columns-2026-09-09/`).

- **A warning that makes a large loss sound routine is itself the defect.**
  The above was reported on every run as "N details were too small or thin to
  hold a stitch and were removed" — while N included a 2,787 mm² region.
  Nobody chases a lost detail. When a warning reports something being
  discarded, report HOW MUCH; the number is what makes it investigable.

- **The Playwright e2e suite goes dark silently when nothing runs it — run it
  yourself after touching `ContentStep`/`ManualPanel` markup.** Since
  2026-08-17 the `studio-e2e` CI job runs it (single worker, and a guard step
  fails the job if any spec skips — the digitize specs skip, not fail, when
  the service venv is missing); the lesson below is from the era when nothing
  on GitHub executed them, and it still applies locally. On
  2026-08-13 all 9 service-backed specs turned out to be failing, and had
  been since **2026-08-10** — commit `301393e` replaced the literal `+` in
  the element tiles with an `aria-hidden` `<Icon name="plus">`, so every
  tile's accessible name lost its `+` and every
  `getByRole("button", { name: "+ Auto-digitize" })` stopped matching. Three
  days of no coverage on the shape-edit contract, invisible from CI. Run
  `npx playwright test` from `app/` after any change to those tiles — and
  note the failure signature is a 300s TIMEOUT on a locator, not an
  assertion, so a red run looks like a slow machine unless you read the
  error context.

  Repairing the locators took the suite from 4 passed / 9 failed in 20
  minutes to **9 passed / 4 failed in 46 seconds**. The 4 then still red
  were PRE-EXISTING and unrelated (verified by running them at `1ab138d`,
  where they failed identically) — and **all four have since been resolved**;
  they were only visible at all because the suite ran. How each closed is
  worth keeping, because two were the suite catching real premise drift:
  - `digitize-background-enclosed` (×2): the 2026-08-11 background-existence
    guards had deliberately reclassified the old repro fixture as
    `BACKGROUND_ABSENT` — no background, nothing to tag enclosed, banner can
    never fire. The Python tests took a guards-off config; a real-browser
    spec cannot (it sends only real Studio configs), so it moved to fixtures
    whose white ground survives the guards (`logo_whitebg`,
    `enthusiast_logo`) — see the spec's own FIXTURE CHANGE banner. Passes
    2/2, driving the banner + "Sew all N" bulk restore end to end.
  - `digitize-boundary-edit`: the old panel vertex drag genuinely changed
    nothing; the spec was rebuilt around the real boundary editor
    (shape-layers contract v1.4 — drag a vertex, Save boundary, Apply, the
    design measurably reshapes and resews).
  - `manual-trace-import`: rewritten around the trace-import flow (real file
    upload through a real `createImageBitmap` decode, traced shapes landing
    on ManualPanel's canvas, `Edit points` vertex drag included —
    `ManualPanel.svelte:846` still renders that button).
  All seven specs now run green in the `studio-e2e` job, whose no-skip guard
  means a merge-able PR proves them, not just runs them.

- **An auto-traced outline has ~1 node per 1.3 mm, so "move one node" is not
  an edit the stitches can express.** `owl_kent.jpg`'s body region is 346
  vertices around a 458 mm perimeter. Dragging one of them moves 2.6 mm of
  boundary and adds a needle: measured 2026-08-13, a 6 mm single-vertex pull
  grew the polygon by exactly the 7 mm² asked for and put **0 stitches** in
  the area it added. Nothing was broken in the fill, the service or the
  restitch — the geometry handed to them was simply too thin to sew, and the
  overlay drew a big visible spike over it, so it read as "the fill isn't
  working". Canvas drags now pull the neighbouring boundary along
  (`shapeOverlay.js`'s `pullRing`, raised-cosine falloff over an arc-length
  radius of 2× the drag). **The general lesson: before believing a shape-edit
  path is broken, check the AREA the edit actually adds or removes against
  what a fill row can occupy** — on line art (4-vertex squares, 25 mm apart)
  the same one-vertex code was always fine, which is exactly why this hid.

- **The field's right-click menu is context-sensitive since 2026-09-09.** On
  a recognised shape (outline or interior — `shapeOverlay.hitShapeInterior`,
  smallest containing ring) it grows a shape section with the border items
  (`borderMenu.js`: Add border → `auto`, Remove → `off`, Use design setting →
  clears) above the drawing tools, and writes `shapeOverrides[sid].border`
  through `elupdate` like a boundary drag. Its `aria-label` is then "Shape
  and canvas tools", not "Canvas tools" — an e2e that right-clicks ON a
  digitized shape and expects the plain name will not find it.

- **Nothing in `DigitizePanel` starts a run except `.dgp-run` ("Auto Digitize
  Image") and "Apply layer changes" (Kent 2026-10-05).** The four watchers
  that used to run on their own are gone: new artwork, params, the crop box,
  and shape edits behind a 2 s pause (with a 0 ms fast path for borders,
  `editKind`, which is still exported and no longer called by the panel).
  What replaced them is one comparison: `configKey(buildDigitizeConfig(el,
  project))` against `element.appliedConfig`, written from the SUBMITTED
  config when a result lands. Unequal means the stitches are behind the
  settings, and the button goes transparent (`dgp-run-stale`). **Two things
  to keep if you touch it:** the key lives on the element, not in the
  component, because `ContentStep` remounts the panel per selection; and a
  project saved before the field existed has a result and no key, which the
  panel takes as current as it loads. **Artwork is added file-first:**
  `App.onAddElement("artwork")` clicks one hidden input
  (`[data-testid="art-file"]`) and only adds the element once a file comes
  back, handing it to the new panel as `pendingFile`.

- **`pollJob` survives a transient poll failure (PR #981, 2026-10-15).**
  `app/src/lib/digitizer.js` used to throw out of its loop on the FIRST poll
  that could not reach the service. A photo at 80 mm is about four minutes
  polled every 500 ms, so one connection reset or 5xx (a box under load, a
  service just restarted) abandoned a job the service then finished and
  cached: `DigitizePanel.runDigitize` landed in its `catch`, cleared the
  status and the resume mark, and the element kept the PREVIOUS run's
  stitches and "Since last run" delta — no console error, only an
  `OFFLINE_DIGITIZE` banner in the DOM. The tell is a re-digitize whose
  status clears long before the job could have finished (84 s into a 295 s
  job, in the report) and then shows the old count. Now a fetch rejection,
  a truncated body or a 5xx retries on the next tick up to
  `maxTransientFailures` (20, about 10 s), the streak resetting on any clean
  read; a real job error, any 4xx (a 404 is "no such job") and the overall
  timeout still surface at once. `digitizer.spec.js` and
  `DigitizePanel.spec.js` pin it fail-to-pass. The run-emb-bot smoke driver
  had the same class of bug the next day (PR #982, "Running things"): a
  poller that accepts a stale result reads as green.

- **`digitizer/` cites its own docs relative to the package root**, i.e.
  bare `docs/dt-classifier-spike-2026-08-02.md` meaning
  `digitizer/docs/...` (8 such references vs 2 spelled-out ones, mostly in
  READMEs). A dangling-link scan resolved from the repo root will report
  these as missing files and they are not — `digitizer/docs/` holds the
  playbook, the DT-classifier spike and the SAM2 live-acceptance doc.
  Cost one detour on 2026-08-12; don't pay it twice.

- **Parallel lanes each test against their own base, so cross-lane
  breakage only appears in the merged full suite.** On 2026-08-11 six tests
  broke that way at once: the new background-existence guards correctly
  stopped flooding the repro/stub fixtures that other tests' scenarios were
  built on. The fix pattern is an explicit guards-off config
  (`bg_border_agreement_min=0.0, bg_border_rival_min=0.0`) with a comment
  saying which orthogonal mechanism the test is really pinning — see
  `test_enclosed_background.py`, `test_thread_revalidate.py`,
  `test_stage6_blend.py`, `test_preflight.py`, `test_service.py`. Run the
  FULL suite after merging parallel lanes; per-lane green means nothing
  about their interaction.

- **Never pipe ANY test suite to `tail`** — you get tail's exit code, so a
  red suite reports success. Redirect to a file (or background the run and
  read its file) and check `$?` directly. Cost a false "suite green" claim
  on pytest 2026-08-11, then bit again on **vitest** 2026-08-22 — the trap
  is universal, not a pytest quirk.

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
- **Keep `.ps1` files ASCII-only.** The reading side of the same trap: Windows
  PowerShell 5.1 decodes a BOM-less script as ANSI, so a UTF-8 em-dash becomes
  three chars ending in U+201D, which PowerShell honours as a string delimiter.
  `tools/start-emb-bot.ps1` and `digitizer/tools/pro_parity/ladder.ps1` both
  failed to parse on 5.1 for this reason (fixed 2026-08-26) while working fine
  under `pwsh` 7, which reads UTF-8 -- so a PS7 author never sees it.
- **Run the pro-parity corpus with `digitizer/tools/pro_parity/parity_run.ps1`,
  not by hand from `prep_both.py`'s docstring.** That docstring is bash, and
  both halves fail SILENTLY under PowerShell. `PRO_PARITY_OUT=<dir> python ...`
  is bash's per-command env syntax; PowerShell either errors on it or, worse,
  reuses a `$env:PRO_PARITY_OUT` left over from an earlier run and writes to
  the wrong directory. And `scorecard.py <OUT>/real/*` needs the SHELL to
  expand the glob — PowerShell does not, so `scorecard.py` gets the literal
  string, finds no `pro_stitches.csv`, skips every entry without complaining
  and prints a clean empty report. **Zero designs scored looks exactly like a
  successful run.** The wrapper enumerates the design dirs explicitly and fails
  loudly on an empty lane. `-SkipPrep` re-scores an existing output directory,
  which is what you want when only the SCORER changed.

## Per-shape stitch width (2026-09-29)

Kent, on small shapes, text and letters coming out rough: *"only being able to
choose a single stitch width across the entire photo or logo"* — and the one
control called "Stitch width" was the DESIGN's width. Now
`digitizer_core/stitchwidth.py` (its module docstring is the design doc):

- **Measure.** Every column-shaped region (`2*area/perimeter` under two satin
  ceilings, or small, or in a text cluster) gets `meta["stitch_width_measured_mm"]`
  — twice the mean skeleton half-width, via `textcluster._stats_of_polygon`, so
  it is memoized with the text doors. Cold cost 0.6 s on the 31-shape
  enthusiast logo, 1.2 s on the 50-shape drone render.
- **Group.** A text cluster is split into WEIGHT MODES (`split_weight_modes`,
  ratio `(1+0.15)/(1-0.15)` — the regularizer's tolerance, not a new number;
  a run wider than the ratio is cut at its largest step, recursively); each
  mode of two or more records its median as `stitch_width_auto_mm`, named by
  `stitch_width_group` (`<cluster>` or `<cluster>:<k>`). **The median is NOT
  a safe default, and this is measured, not assumed:** Gaulke's line is ONE
  cluster of 35 letters whose widths run 0.77 → 1.33 mm as a smooth chain
  with no step (an I, an M and an O of one font measure differently at the
  skeleton), so no split finds "two words" and the first cut moved 21 letters
  to a 0.95 that nobody has. Evening out is therefore `cfg.stitch_width_auto`,
  **default False**, the Studio's "Even out lettering widths" box.
- **Apply** (`apply_stitch_widths`, in `finish_generation` after the edits and
  the `stitched` resolution): target = override (always), else — only under
  `stitch_width_auto` — the group median past the 15% tolerance, else
  `lettering_min_column_mm` on small shapes and lettering (None by default —
  ROADMAP gate 1; on its own the flag keeps its exact 2026-09-09 door-1
  meaning). The polygon is OFFSET by half the difference (`offset_polygon`):
  a hole that would close is held at its original size (stage 5's own rule),
  a gap between strokes is read off a mitre closing of the shell and never
  bridged, a stroke thinner than a narrowing step is read off the mirror
  opening and never erased (an E's arms), all bisected to the largest passing
  step; `stitch_width_limited` says a guard clamped it; an override under
  twice the fabric's pull is `below_fabric_pull`, unchanged. A sized shape is
  `column_sized`, which `stage5_overlap.widened_lettering` now includes, so it
  gets the regularizer's four rules (no sub-floor run routing, classified and
  sewn on the compensated polygon, growth kept over the ground, pull on the
  polygon not the rails).
- **Wire** (contract v1.8): `shape_overrides[sid].stitch_width_mm`, SEWN mm in
  `[SATIN_MIN_CROSS_MM, SATIN_WIDE_COLUMN_MAX_MM]` = [0.5, 6.5], validated in
  `stitchwidth.validate_override_mm` from both `app.py` (400) and
  `regions.apply_shape_edits` (ValueError). Not carried across a merge or
  split — those run BEFORE the edits, so the key never exists on a source;
  a merged shape is measured late in `apply_stitch_widths` instead, so the
  panel offers it the control. The review payload's per-shape `stitch_width`
  block reports `art_mm` (the artwork stroke, no pull) and `measured_mm /
  auto_mm / sewn_mm / override_mm` (sewn mm, artwork + 2 × pull;
  `stitch_width_pull_mm` is stamped so the payload needs no fabric) plus
  `source / group / limited / skip_reason`. Sewn = art + 2·pull holds for a
  SATIN column on both compensation paths (stage 5 grows a sized polygon
  isotropically; the rails carry the pull on everything else) and NOT for a
  shape the plan sews as a run — a sub-floor bean on the artwork outline, no
  pull — which is why the Studio shows `art_mm` on a run-tier row.
- **Studio.** `canonicalShapeEdits` carries the key (rounded to 0.01 mm,
  range-checked so it never 400s); `reviewFromJob` maps `stitchWidth`;
  `stitchWidthGroupRows` is the word. The row control in `DigitizePanel.svelte`
  writes the whole weight group in ONE patch (one undo step, one restitch;
  `editKind` reads it as "other", so it keeps the drag debounce) unless
  "whole word" is unticked. **"Stitch width" on the params list was renamed
  "Design width"** — both e2e specs that read that label were repointed.

Measured (on-vs-off plan md5): with the box OFF every corpus fixture is
byte-identical, pinned on the two art fixtures that would move
(`tests/test_stitch_width.py`, Fremont and Golke). With it ON, over the 24
`testdata` fixtures: 22 unchanged; `drone_render` / `thermal_badge` bring two
letters of one word from 0.79/0.82 mm to the word's 0.65 mm; Gaulke moves
21 letters and is the reason the box is off. The flat-lane goldens are
unmoved (`enthusiast_logo` is the platform red, identical on the pristine
tree).

## Manual digitize: copy/paste and per-shape dim (merged 2026-08-26, PR #255)

Studio Mode 2 (`app/src/ui/ManualPanel.svelte` + `app/src/lib/manualShapes.js`).
Two of the three Ember gaps Kent picked.

**Copy / paste / duplicate.** `Ctrl+C` / `Ctrl+V` / `Ctrl+D`, plus a Duplicate
button so it is discoverable without knowing the shortcut. `duplicateShape()`
is pure and tested. Two things it has to get right, both of which read as a
different shape if you get them wrong:

- **Curve control points move WITH their anchors.** A quadratic control is an
  absolute canvas point, not a delta — a copy that kept the original's
  controls bows toward the original.
- **The paste offset is clamped to the canvas** (`PASTE_OFFSET_PX`, against
  `CANVAS_W`/`CANVAS_H`). A shape near an edge would otherwise paste partly
  off-canvas where it cannot be selected or dragged; the copy shifts back by
  the overflow instead.

The clipboard holds a **snapshot, not an id**, so pasting still works after
the original was edited or deleted. Duplicate deliberately does NOT route
through the clipboard — the one-gesture case must not clobber what the user
actually copied. Both are ephemeral and stay out of the saved `.embproj`.

**Per-shape dim (`shapeAlpha`).** A view control for seeing what a shape
covers. Held as ephemeral component state, **not** as a field on the shape.
`shapesToRegions` only reads `points`/`curves`/`stitchType`/`colorRgb`/
`angleDeg`, so a field on the shape would not reach the stitch plan *today* —
keeping it off the shape entirely means it cannot start reaching it by
accident later. Verified end-to-end in the browser, not just by unit test: the
main stitch canvas is byte-identical at `shapeAlpha` 1.0 vs 0.15, checked
non-vacuously against a canvas rendering 1764 stitches over 580 distinct
colours.

**Watch the return type.** `shapesToRegions()` returns `{regions, pxPerMm}`,
not an array. Destructure it; `.toHaveLength()` on the return value is a
mistake this repo has already made.

## Manual digitize: editing on the hoop, cut-outs, columns and lines (2026-09-29 → 2026-10-11, PRs #562, #570, the cut-outs PR, #831, #840)

Three things landed in a week and none of them was written down here. Detail
and measurements: `docs/scope/5-review-manual-editing.md`.

**Where a hand-drawn shape is edited.** The side canvas (`ManualPanel`) only
DRAWS. Clicking a shape on the hoop canvas opens `ShapePopover`
(`lib/shapePopover.js` is its pure decision table); the selected shape's
anchors and curve handles are dragged on the hoop (`lib/fieldNodeEdit.js`).
The engine exports `design.shapeOutlines` (field mm) and `design.fit` so the
field maps authored px ↔ field mm with the engine's own numbers — never a
second transform.

**The re-fit rule.** The engine fits the bbox of all an element's shapes, so
any edit that changes that bbox would rescale everything else.
`refitShapesPatch` (and `editedElementPatch` on top of it) patches
`shapes + sizeMm + offsets` together so nothing unedited moves. It covers
edits made ON THE HOOP — node drag, insert/remove point, the Cut out switch.
Adding or deleting a shape in the side panel, and Delete on the hoop, still
re-fit.

**Two more things a hand can draw since 2026-10-11 — a column and a line.**
The side canvas's mode row reads Shape | Hole | Column | Line
(`ManualPanel.svelte`). **Column mode** (PR #831) draws an open SPINE and gets
a satin column: in `manualShapes.js` a column is an open spine plus a width
in mm, `shapeRing` says what ring any shape presents, and a new column is born
4.0 mm wide in the design it lands in, not at a fit it is about to change. The
engine sews a region with authored rails as satin between them and its centre
run along them (2026-10-01). **Line mode** (PR #840) draws an open path and
sews a RUN along it: `runAlongPath` in `src/digitize.js` sews a region with an
authored path as that run and nothing else of it. The popover converts a line
into a column and back (run ↔ column swaps fields, never the spine), shows a
column's width in mm and what it sews at, warns past 6.5 mm, and shows a
line's passes and stitch length; `fieldNodeEdit` edits an open spine like a
shape and converts through the re-fit rule above. Both are proven end to end
in `app/e2e` (a drawn line sews thin, and run → column → run gives the same
line back). Detail and measurements: `docs/scope/5-review-manual-editing.md`.

**A hole is a shape marked `cutOut: true`** (spec
`docs/superpowers/specs/2026-09-30-manual-digitizing-gaps-design.md` §5). It
sews nothing and cuts the smallest shape that contains it.

- **`resolveCutOuts(shapes)` in `manualShapes.js` is the only judge** of which
  shape a cut-out cuts. Nothing is stored; every consumer calls it. Do not
  re-derive containment anywhere else.
- A cut-out emits **no region**, so the engine never sees it except as its
  parent's `holes`. Two consequences that will bite if forgotten: the field
  builds a cut-out's outline itself (`cutOutOutlinesInFieldMm`), and
  `fieldNodeEdit`'s bbox skips cut-outs so it keeps agreeing with the engine's.
- Never store `cutOut: false` — `withCutOut(shape, false)` removes the key, so
  an untouched record equals a pre-feature record. No file-version bump.
- The engine's hole floor is **3 points** at both readers in `digitize.js`
  (it was 4, which silently dropped a triangular hole).
- On the side canvas, **Hole mode's click always draws**; Shape mode's click
  inside a finished shape selects it. That asymmetry is deliberate — a hole
  starts inside a shape.
- **A cut-out is clear of the needle (2026-10-03), and of thread in the manual
  lane since 2026-10-07 (shapes and image since 2026-10-08).** Without `fillColumns` the
  JS fill goes from one span of a split row straight to the next, so every
  row lays a float (or, under 4 mm, a stitch) across the hole. The Studio's
  field shows it only with its **Jumps** toggle on, which is off by default.
  The cure, OFF by engine default: `buildQualityDesign({ fillColumns: true })` sews a forked FILL
  shape column by column (`fill.js` `opts.columns`, a port of the Python
  `_columns`) and goes ROUND a hole instead of crossing it. A satin shape is
  untouched by it, and so is a fill with no hole and no inside corner. Of
  `generate.js`'s three callers all pass it: MANUAL since 2026-10-07
  (`generate.spec.js` pins it with a cut-out), basic shapes and the image
  lane since 2026-10-08 (pinned with a star's notches and a traced counter;
  the image lane pays +10.4% stitches on real logos, Kent's call with that
  price measured — `tools/fill-columns-lanes.mjs`). It has not been sewn. Eight things to know before touching it:
  - Every move is asked what ground it runs over (`groundUnder`): on the
    ground it may float, on the rim it is sewn, deeper than `openTol` into
    open ground it must go round or be cut.
  - The ground is what the FILL covers. `openTol` is the fill's row pitch for
    every pass, and an underlay is handed the fill's rings as `ground`: never
    a pass's own pitch, never "the outline plus the pull compensation".
  - Moves are between a column's four corners. A column that cannot make one
    of its own turns is cut in two first (`splitAtOpenTurns`), so every hard
    move is one `moveTo` handles: a stitch, a run along the row, round the
    ring, or the way through the corners (`webRoute`).
  - Change a rule, then run the seeded shapes ("shapes nobody chose" in
    `test/fill.test.js`) with more of them than the suite carries, and mutate
    the rule to see a test die. Two rules here were wrong and green.
  - Random shapes never run a move along a line of their own corners, and a
    drawn badge or U does it all the time. Ask the ground test both ways
    round on whole-number shapes ("whole-number shapes" in the same file),
    and sweep every preset in `FABRICS.FABRICS`: terry sews its fill upward,
    and that was the direction a third audit found wrong. Draw notches
    exactly twice a preset's pull compensation wide as well (4 to 12 px at
    10 px per mm): the outline the fill is sewn to closes one to a slit, and
    no sweep had one until an audit drew it (2026-10-03, "a move of no
    length").
  - A pass has two ends and is told both: where the thread is (`from`) and,
    when the run after it begins at a point of its own, where it goes next
    (`to`). A pass the plain walk sews is that kind, and the builder asks
    where it begins with a function of its own, `fill.plainStart`. Do NOT
    ask a question through `tatamiFill`. It was first an option that made
    `tatamiFill` answer null and had the pass built before its turn, and
    three tools wrap `tatamiFill` to watch the passes: each took the null
    for a pass, or the order of the calls for the order of the sewing. Two
    were patched; a review found the third throwing
    (`tools/sub-unit-stitch-census.mjs`, 2026-10-05). Before changing what
    `tatamiFill` returns or when it is called, grep `tatamiFill = ` in
    `tools/` and `test/`, and run all of `node --test`, not the two files
    you are in.
  - A walk that comes out cut is walked again from the other first columns
    (`sewFrom`, eight at most) and the better walk is kept: fewer cuts, and
    no more threads of fewer than four penetrations between two of them. So
    before touching the walk, count the cuts by WHERE they are: inside a
    pass, on the float into it, on the float out of it, and what kind of run
    is on either side. The most of any kind left is not the walk's at all:
    the float from an EDGE RUN into a plain walk (2026-10-04, "where a pass
    ends").
  - Count more than cuts, and sweep shapes the last sweep did not have. By
    cuts alone a walk saved a cut by stranding a row, one stitch cut to and
    cut from, and 56,120 designs of combs, badges and letters showed none:
    the re-measure's mazes did. The same re-measure found a comb of 100
    teeth with 615 cuts where no option has 1, its passes walked nine times
    for nothing (5.0 s → 18.5 s). Mazes, spirals and combs of 24 teeth and
    more belong in the sweep, and so do a pass's short threads, the thread
    it sews, and the time it takes.

  To SEE thread rather than penetrations, run
  `node tools/fill-columns-sheet.mjs`: it draws four manual-lane shapes off
  beside on, floats in red, and prints the cost table. In the Studio, the
  field's Jumps toggle draws every needle-up move as a dashed line.
- **Lock stitches are built OFF in both JS builders (2026-10-03).**
  `ties: true` on `buildQualityDesign` or `buildLetteringDesign` locks every
  thread where it starts and where it is cut. It is ONE function,
  `applyTies` in `src/digitize.js`, run on the finished record stream, which
  is in DST units. Do not compute a lock in px: the lettering port of 09-14
  did, and its 0.8 mm leg came out 0.1 to 0.5 mm. No Studio caller passes
  the flag; the flip is Kent's ("Waiting on Kent" 23).
  `node tools/lock-stitch-census.mjs` prints what a lock costs and how long
  its legs really are, on every shipped font and eleven shapes.
- **Cutting long floats is built OFF by default for the shape builder (2026-10-04).**
  A DST has no cut. `dst.js` lays three jump records for a `trim`, and also
  for any float over 24.2 mm, so a machine cuts where the stream has only a
  jump, and `ties` lays no lock there. `cutFloats: true` on
  `buildQualityDesign` puts the `trim` in the stream: one pass,
  `cutLongFloats` in `src/digitize.js`, over the finished stream and before
  `applyTies`. How many records a move takes is asked of the writer
  (`dst.jumpRecords`); do not work it out from a length. The move to the
  stitch AFTER a float counts, since the writer lays it as jumps up to its
  last record. A float with no thread on it is left: after a cut, after a
  colour change, at the start. To check any change to what is written, read
  the FILE: `node tools/file-cut-census.mjs` writes every design with the
  three writers, reads each back with its own readers and says what every
  run of three jumps was; `--against <src>` says whether two engines differ
  by cuts put in and nothing else. The MANUAL and basic-shape branches of
  `generate.js` pass it (2026-10-08, after `fillColumns`; `generate.spec.js`
  pins it on a plain manual square, the default circle and a 12-point star;
  `node tools/cut-floats-shapes-sheet.mjs` prints the per-family preset
  table); the image lane does not ("Waiting on Kent" 28,
  `docs/cut-floats-manual-2026-10-08.md`, `docs/cut-floats-shapes-2026-10-08.md`).
- **Row stagger is built OFF for the shape builder (2026-10-03).**
  `fillStagger: true` on `buildQualityDesign` puts the cover fill's needle
  holes on one grid shifted row by row (`tatamiFill`'s `stagger`, `minStitch`
  and `splitTol`): the Python fill's rule, row for row. `stagger` is a NUMBER
  of rows; `true` is no stagger. It moves only the holes BETWEEN a row's two
  ends. To check a change to it, take those out and compare with the flag
  off ("the same walk" in `test/fill-stagger.test.js`). Count holes in line
  across THREE rows, not two: a halved step sits near the next row's grid
  point by the rule itself, which along a straight edge is a line of dashes
  and is stated for the flip. To check it against Python, compare rows in
  the order the thread runs and aim rows a hair either side of a stitch: a
  sorted comparison of random rows passed while two things were wrong.
  `node tools/fill-stagger-census.mjs` prints the numbers and, with
  `--sheet out.svg`, draws every hole. No Studio caller passes the flag; the
  flip is Kent's ("Waiting on Kent" 24).
  The lettering builder's own fill (`satinplay.fillFromGeom`) is NOT
  staggered and does not ship: it runs only under `wideColumnFill`, off
  since 2026-09-11. Whatever flips that passes `stagger`, `minStitch` and
  `splitTol` there, the two lengths in the layout's units: final mm,
  divided by the fit scale, times `pxPerMm`, as `fillStitchMm` beside them
  already is.
- **The browser's satin tracer can no longer walk for ever (2026-10-03), and
  that is all that changed in it.** `skeletonEdges` in `src/satin.js` walks
  skeleton pixels from a node to the next node, under a guard of one step
  per grid cell. Three pixels that all touch are no node; a walk went round
  them until the guard ran out, and the satin emitter sewed what came back
  (a 20 mm star off the shape tool: 48,645 stitches). A rule ended such a
  walk and left every other one alone; it was replaced on 10-04 by one pixel
  to one edge (next bullet), under which no walk can go round. Three things
  to know before touching it:
  - It reached every lane that calls `medialSatin`, not stars: thin
    round-ended bars and 273 of 612 image-lane designs moved too. Sweep
    every caller before saying which designs a change moves.
  - The walks then still stepped onto pixels another edge had: a median 72
    layings too many for every 100 skeleton pixels on the shape tool's
    stars, and "rings" were found in shapes with no hole. Cured 10-04
    (next bullet). A stitch as long as the star is still MASTER_SCOPE
    defect 57.
    The knot had also been COVERING small round shapes: a 2 mm one sewed
    four stitches after it went.
  - `node tools/satin-walk-census.mjs` builds what the shape tool builds and
    says which designs sew out of line with their neighbours in size;
    `--against <tree>` says which designs differ from another engine's,
    `--walks` counts the walks that only the guard stopped, `--kind rect`
    does bars, `--render` draws one from its DST bytes. A counter it cannot
    insert is an error: the first version read "0 walks at the guard" on a
    file whose loop it had not found.
- **No second stitch in one hole is built OFF for the shape builder
  (2026-10-03).** The builder rounds to 0.1 mm, so a row at a tip, a move
  across the mouth of a notch, or a scanline through a corner can put two
  `stitch` records on one point: the needle twice in one hole, in what
  ships. `dedupeHoles: true` on `buildQualityDesign` lays the first and not
  the second. It is ONE place, `pushRun` in `src/digitize.js`, and it is
  narrow on purpose: only a stitch whose record comes straight after a
  stitch on its point is left out. After a jump or a cut the stitch is laid,
  whatever point it is on. Do not widen it to look through jumps. A cut is
  written as three jump records (`dst.js`), so a stitch taken out from
  between two jumps can leave a reader a cut nobody made; the first build
  did look through them, and an independent audit's remark caught it.
  `node tools/sub-unit-stitch-census.mjs [srcDir]` counts the pairs on two
  sets of designs and says what made each; `--on dedupeHoles=true --off
  dedupeHoles=true` runs it with the flag, and `--against <other src>` says
  whether two engines' streams differ only by such stitches. No Studio
  caller passes the flag; the flip is Kent's ("Waiting on Kent" 25). Since
  PR #990 (2026-10-20) `buildLetteringDesign` takes `dedupeHoles` and
  `underlayDirection` too, both built OFF there (MASTER_SCOPE 25 + 40;
  `test/text-lane-flags.test.js`, `tools/text-lane-flags-sheet.mjs`).
  `docs/sub-unit-stitches-2026-10-03.md`.
- **A ring may arrive CLOSED, and three readers still take its points
  (2026-10-03).** `[p0, ..., pn, p0]`: the first point said again at the end.
  `offsetRing` moves the corners said ONCE (`distinctCorners`) and
  `isConvexRing` reads them, so the fill's pull compensation and the
  `fillColumns` edge run are the open ring's. Three things are still read off
  the POINTS, and a point said twice is one more of them: the auto stitch
  angle and a satin shape's centre run (`pcaAngleDeg`), and the edge run that
  is drawn toward the centroid and the order of a colour's shapes
  (`insetRing`, `orderShapes`). That edge run is every shape's without
  `fillColumns`, and with it a shape's with no hole and no inside corner. No
  Studio lane sends an exact repeat: the tracer and the basic shapes never say
  a point twice, and a hand-drawn shape that does is refused as crossing
  itself. `parseSVG` (every circle, ellipse and rounded rect) and `src/fonts.js`
  `pathToPolygons` DO; nothing in the Studio calls them, and a lane that will
  should take the repeat off before the builder. "Twice" is to within rounding
  (1e-9 px). A point merely NEAR the next is a corner, and the open bug at the
  top of "Known bugs" is what one does. `node tools/closed-ring-census.mjs`
  prints the wedge, closed against open, what each lane hands over, and the
  near repeat; `--hash` and `--compare` are the before and after of an engine
  change on rings that say no point twice.
- **The browser satin's skeleton, its walk and its ends were put right
  together (built 2026-10-04, on `main` from the 2026-10-11 port), and they
  depend on each other.** `7bb83e9b` (2026-10-08) had put the first of the
  three on `main` alone, with its own run-out (`extendToOutline`); the port
  replaced that with this lane's. Three things in
  `src/satin.js`:
  - `thin` never deletes a pixel on the edge of its grid, and `ringToSpines`
    laid shapes against the grid's top and left, so a shape's top row and
    left column were its skeleton (a bar's was an L, and its last cross ran
    the length of the bar). It leaves one cell there now. Rasterize nothing
    for `thin` without an empty cell on every side.
  - `skeletonEdges` is one pixel to one edge, a port of the Python tracer's
    walk (`_skeleton_edges`). The wrong skeleton had been HIDING the old
    walk's faults: with a true one, a C drawn by hand and set to satin came
    out with its mouth sewn solid (447 stitches to 6,047) until the walk
    was ported. Do not change one without the other's census.
  - A free end of a spine is run on to the outline (`runOut` in
    `railSatinFromSpine`), because a centre line stops half the stroke's
    width short of its end; and the station that lands ON the outline
    takes the widths of the one before it, because a ray cast from there
    can leave through the stroke's end and cross a concavity.
  It moves every satin shape of the browser lanes (the shape tool, drawn
  shapes, the image lane's thin shapes) and no fill. `spineToRails` shares
  the grid and the walk and has no run-out. What it leaves is MASTER_SCOPE
  defect 57: a square or a dot up to 6 mm has no stroke and takes
  `satinColumn`, which starts 12% in from each end; a bar's centre-run
  underlay ends at the far end from where its column starts; a star's
  centre. To measure a satin change, `tools/satin-walk-census.mjs`:
  `--kind arc --satin` (hand-drawn curved strokes on the user's satin, the
  census that caught the C), `--cover` (the share of each drawn shape under
  thread, how far outside it a needle lands, thread over open ground),
  `--images` (eight corpus logos shape by shape, a shape's OWN thread apart
  from any thread: a ground fill runs under small shapes and hides what the
  satin lost), `--dst` (the files' bytes), `--sheet` (designs before and
  after at one scale).

## `coverage()` is measured BY RENDERING — restyle the render, move every number (2026-08-25)

`digitizer_core/stitchviz.coverage()` renders the design twice, on black and on
white, and reads the difference. There is no separate geometric path. So **any
change to how thread is DRAWN silently rewrites every coverage figure ever
recorded** — and those figures are what the fill-tier, border and shade-bind
rulings were decided on.

Adding the lit-cylinder shading hit this twice before it was split correctly:

| attempt | coverage drift |
|---|--:|
| off-centre bands (their anti-aliased fringe runs fractionally wider) | **8e-4** |
| collapse the measurement to ONE opaque band at the nominal width | **1.2e-3** |

The second is the instructive one and the trap a tidier will fall into. Three
concentric anti-aliased lines are **not** equivalent to one line of the widest
width: each pass re-blends the fringe pixels of the pass before, so the
footprint's soft edge depends on **how many passes** there were, not only how
wide they were.

**The split that fixes it:** `render_design(..., lit=False)` reproduces the
pre-shading draw EXACTLY — three centred bands, in that order, at those widths
— and `coverage()` is the only caller that passes it. Shading is display; the
measurement is frozen. `test_shading_cannot_move_coverage` pins it by setting
the shading bands to something absurd and requiring the number not to twitch.

Verified 2026-08-26 by loading the pre-change module alongside the current one:
coverage is **bit-identical on four stitch angles**. If you touch the draw,
re-run that comparison before you believe anything.

## The `preview.js` renderer collision — three broken `main`s in one night (2026-08-25)

Worth reading before touching `app/src/lib/preview.js`, and as the clearest
worked example of the parallel-lane hazard.

#249 and #251 both rewrote the thread draw. They merged with no textual
conflict into a file containing BOTH draw paths and two `const lw` in one
scope — a `SyntaxError`, so the module did not load and the Studio canvas was
dead. Then **two sessions fixed that in opposite directions twenty minutes
apart** (77333cf kept `drawFilament`; 872d950 kept `drawThreads`), both fixes
merged, and git applied **both deletions and neither implementation**. The
union of two self-consistent fixes was worse than the original bug. A third
lane (#254) then proposed a fourth resolution before Kent closed it.

**Settled: `drawThreads` wins** (#256, confirmed by Kent). Not on merit —
`stitchviz.py` and `test_stitchviz.py` grep `preview.js` for
`const LIGHT_X = -0.5547;`, `const LIGHT_Y = -0.8321;` and
`export const THREAD_WIDTH_MM = 0.4;`, all defined only in that section, so
the other resolution leaves the JS↔Python parity test asserting against
symbols that do not exist. **Do not relitigate this.** Ping-pong is what cost
the evening.

What actually catches it, in one second, and is worth running by hand after
any merge that touches this file:

```bash
cd app && node --input-type=module -e "import('./src/lib/preview.js')"
```

A green suite is NOT evidence here: when a spec file fails to parse, vitest
reports "0 tests collected" and the run still reads as a pass. Same class:
`preview.spec.js` carried a duplicate `import ... from "./preview.js"` for
days — `node --check` rejects it outright, and it only ran because Vite's
transform is lenient (fixed 2026-08-26, #257).

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

**Cloud worker sessions and the foreman — the "K3" pattern (since
2026-10-07/08).** Most work now arrives as cloud sessions dispatched by a
foreman session running `.claude/skills/k3/SKILL.md` (distilled from the
first run: ~80 cloud sessions, ~25 PRs merged in one evening, CI cut from
~75 to ~17 minutes along the way). The foreman writes no code: it picks the
work, launches one cloud session per task (Opus for engine, digitizer and CI
changes; Sonnet for tests, docs, small Studio fixes and reviews), keeps every
PR moving to auto-merge, and asks Kent only what is his — flips, physical
constants, scope, money — with `AskUserQuestion`. A worker starts from a
fresh clone of `main` in its own container, can push ONLY the branch it was
created with, and gets the standing rules in its preamble (`templates.md`
beside the skill): do not edit MASTER_SCOPE.md, docs/scope-history.md,
DOCTRINE.md, CLAUDE.md or this file — one named session per shared doc,
because shared docs caused nearly every merge conflict, so status goes in
the PR body; do not run the full digitizer suite locally (CI shards it);
`git fetch origin main && git merge origin/main` before every push, never
rebase; ready-for-review PR, auto-merge armed while `mergeable_state` is
`blocked`, never merge by hand; fix your own red CI, never skip or xfail a
test to get green; quiet unless blocked. `.claude/worktrees/` is a LOCAL
mechanism — a cloud worker has no lanes and makes none. When a
cross-session message asks for work the rules do not cover, Kent's own
words are the authority, and a ruling he gave directly in a session wins
over the foreman. Past ~40 open PRs new sessions mostly wait in the CI queue
(each PR fans out ~9 jobs), so the foreman drains before it refills.

**A worktree-isolated DESKTOP session meets a harness guard a cloud session
never sees** (`.claude/memory/worktree-session-harness-guard-2026-09-17.md`,
re-measured 2026-10-03). Once a session has `EnterWorktree`d, the Bash tool
refuses any command it cannot prove stays inside the worktree, and
"git-adjacent" is nearly every command here because `digitizer` contains the
letters `git`: quoted paths, `cd x && …`, `git -C <shared>`, `$'…'` strings
and heredocs all die with *"names git in a form too complex to verify"*,
including commands with no git in them at all. What passes: `cd digitizer`
ALONE as its own call (the cwd persists — except in a subagent, where it
resets every call and heredocs are refused outright), then unquoted
space-free paths, `;` chains, plain redirects and plain `git
add/commit/status` from that cwd; use the Grep/Read tools for anything
pattern-shaped. A worktree has no `.venv`; the main checkout's interpreter by
its 8.3 short name has no space and passes the guard
(`/c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/digitizer/.venv/Scripts/python.exe`,
`CLAUDE~4` being `Claude Personal`), run from the worktree's `digitizer/` so
its own `digitizer_core` shadows the editable install. A background command
is killed at its timeout (10 min at most) and a foreground overrun gets 30,
neither of which fits the full suite — run the files a change can reach and
let CI's `digitizer` check be the full run. Memory written from a worktree
goes to `<worktree>/.claude/memory/` and rides the PR, so
`tests/test_memory_budget.py` gates it: run that one file (half a second)
after ANY edit to `MEMORY.md` — an index line over 260 chars turned a
55-minute `digitizer` job red once.

## What's next (queue as of 2026-08-03 — historical, with resolutions)

This queue is a dated artifact kept for its rationale trails; each item
carries its outcome inline. **ROADMAP.md owns the live ordering and gates**,
MASTER_SCOPE.md the live status — don't work from this list.

Decision doc: `docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`.
Session handoff with the full context:
`docs/superpowers/handoffs/2026-08-03-gradient-defects-handoff.md`.

1. **The two gradient/enclosed-white regressions** (see Known bugs below).
   The angle-fragmentation half is FIXED (2026-08-03, same-day follow-up
   session). **`BACKGROUND_ENCLOSED` is now FIXED too, later 2026-08-04** —
   pipeline, service contract, and Studio Layers-panel restore UI all
   merged to `main`, and the one caveat that kept it from being real
   end-to-end (an opaque-alpha bug that defeated background detection on
   real Studio uploads) is fixed too, merged PR #22; see
   `docs/scope/1-auto-digitizing-quality.md` for the full breakdown. (The
   live-browser verification this bullet used to flag as missing exists
   now — see the Known bugs entry.) The `fix/bg-existence-guard` branch/worktree
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
   reimplementing it, both on `origin/main` now. What's left of this slice:
   M0's corpus leg (above) still waits on Kent; M2/M3 resolved by rejection
   — see item 4. Rationale:
   the satin/fill call is made from `2·area/perimeter`
   (`stage6_satin.py`'s `ribbon_width_mm`, duplicated in `shapefield.py` —
   this bullet's old `stage7_sequence.py:97` pointer is stale, the logic
   lives there now), a statistic the source patent warns against — it
   satins a 20mm disc under a 5mm cap once the edge is serrated — decided,
   when this was queued, without the DT ever being consulted. (No longer
   true: `classify_ribbon` now runs DT gates — `dt_irregular`/`dt_p90_cap`,
   an `explained`-based promotion path, and the photo width floor — on top
   of the width/aspect screen; see item 4's resolution.) Steps 5+ all lean
   harder on that classifier than anything shipped so far. Full
   architecture: `docs/dt-first-architecture-2026-08-01.md` §2 and
   `docs/masters-teardown-2026-08-01.md`.
3. **Photo-digitizing plan steps 5+** (`docs/photo-digitizing-plan-2026-07-31.md`)
   — **rows 6/8/9/10/13 are now built**: direction field (row 6),
   scan-line mono tonal (row 8), meander mono tonal (row 9), streamline
   thread-paint in both its mono and layered-multicolour slices (row 10),
   and chart-restricted weighted k-medoids palette selection (row 13 /
   build-order step 7, `digitizer_core/palette.py` — replaces the photo
   path's per-region nearest-thread snap; the eyes/skin/subject class
   multipliers are FULLY WIRED since 2026-08-05 — eyes/skin off the YuNet
   face priors, subject/background off the rembg mask, both behind the
   `photo_prep` gates, with plain-area degradation when no prior covers a
   region; this bullet said "run at 1.0 until step 3's face priors exist"
   long after they did — see that module's THE CLASS-WEIGHT SEAM) — see
   `docs/scope/1-auto-digitizing-quality.md`
   for the commit-level breakdown. Whatever the plan doc queues past these
   is still open; re-check the plan doc itself rather than trust this
   bullet's row count going forward.
4. **DT-first M2/M3 onward** — the classifier swap itself, the change a
   customer can see. Corpus-gated *and* sew-out-gated, and it needs the
   corpus disagreement table M0 produces before it can be judged.
   **Resolution: the swap as designed was measured and REJECTED**
   (2026-08-11, `docs/dt-first-verdict-2026-08-11.md`): the patented rule as
   printed sends 62/83 clean satins to fill, and every corrected arm loses
   the disagreements it creates — it sits on MASTER_SCOPE's don't-build
   list. What survived instead: the DT consulted as ADDED gates inside
   `classify_ribbon` (`docs/satin-gate-attribution-2026-08-16.md`) and
   Law 31's photo-lane width floor (2026-08-22, see the digitizer section).
   The 37-file corpus leg stays blocked on Kent's local run either way.

A sew-out is still not scheduled — Kent's explicit call: more work first,
don't push for it.

## Known bugs (unresolved, not accepted — Kent's call on the fix)

- **A hand-drawn shape with an anchor a pixel from the last one sews a spike
  at that corner — the gesture that made them is FIXED 2026-10-03, the offset
  is NOT (MASTER_SCOPE defect 55).** The short edge to such an anchor doubles
  back, and `offsetRing` gives its end the whole mitre clamp, three times the
  pull compensation: on terry a 40 mm box is filled 1.73 mm past the drawn
  ring there, where a clean corner has 0.85. They came from a double-click,
  which is two clicks and then a `dblclick`: the second click was taken as an
  anchor unless it landed within 0.5 canvas px of the first
  (`DUP_POINT_EPS_PX`), and one slip in four was refused as crossing instead,
  so the double-click finished nothing. `ManualPanel.onCanvasClick` now lets
  a click with `detail` 2 go by (the field reads `detail` for its own
  double-click too), so no new shape gets one. **Still open:** a shape saved
  before then keeps its anchor and its spike, and two anchors dragged to one
  hoop corner make another. Curing those means the offset (a bevel past the
  clamp), which moves every sharp corner under a preset: Kent's call, not
  built. It is NOT the closed-ring wedge fixed the same day (that is a point
  said twice to within rounding, and no Studio lane sends one), though it is
  the same function and the same clamp. `node tools/closed-ring-census.mjs`,
  table 4; `app/e2e/manual-double-click.spec.js` drives the gesture in a
  real browser.

**One open as of 2026-10-03, above (its offset half).** Every entry below this
line is fixed and is kept for its trail. Put a new unresolved bug at the top,
above this line.

- **DST axis transposition — FIXED 2026-09-08, both halves. The phantom end
  stitch is FIXED too (#415).** EMB-Bot's own DST codec was transposed
  against the Tajima/pyembroidery standard in both directions. Four
  independent sources and a clean-room decode confirmed it. It shipped
  undetected because browser DST round-tripped correctly against itself.
  - The importer went standard first, in PR #404.
  - The writer followed in `bca5a504`. `encodeRecord` is now byte-identical
    to `pystitch.DstWriter.encode_record`, and `decodeDSTStandard` is a plain
    alias of `decodeDST`.
  - The phantom end stitch was the `end` record written as a move.
    `src/dst.js` now stops at `if (st.type === "end") break;`.

  **Do not "fix" either half back.** This entry kept saying the writer was
  "still transposed and still Kent's call" for weeks after it was fixed. A
  stale instruction like that is how `crossval-stitch-formats.mjs` came to
  tell its reader to un-fix the axis (memory,
  `stale-diagnostics-and-two-flips-2026-09-13`).

  **One thing stays true:** a `.dst` that EMB-Bot wrote BEFORE the fix is in
  the old dialect and re-imports transposed. Nothing repairs old files. The
  full trail is in CLAUDE.md footgun #1, `dst-codec-axis-discrepancy` in
  memory, and `docs/dst-axis-verdict-2026-07-31.md`.
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
  gained a restore control for it. See
  `docs/scope/1-auto-digitizing-quality.md` for the
  commit-level breakdown. **The one caveat that kept this from working
  end-to-end through the actual UI is fixed too, merged PR #22:** Studio's
  real upload path manufactured an opaque alpha channel that defeated
  background detection entirely; a fully-opaque channel is now discarded
  as information-free. Verified post-merge at the HTTP level (opaque-RGBA
  twin of the repro fixture now matches its RGB original exactly), and the
  live-browser gap this sentence used to flag is closed:
  `app/e2e/digitize-background-enclosed.spec.js` drives the full flow —
  real upload, real service, banner, restore, re-stitch — through the real
  DigitizePanel, and runs in the `studio-e2e` CI job.
- **Background detection flooded the subject out on tight photo crops**
  (the snowy-owl report: white bird on a beige wall, the bird's body
  "recognized as background" and deleted) — **FIXED 2026-08-11**, two
  stage-1 guards, both config-gated:
  1. The background-EXISTENCE guard, hand-ported from the orphaned
     `fix/bg-existence-guard` branch (73e0665 — so "closed-by-inference"
     above was wrong: PR #22 fixed a different problem and this one was
     still live). If the modal border color describes less than
     `cfg.bg_border_agreement_min` (0.75) of the border ring, the art runs
     edge to edge: nothing floods, `BACKGROUND_ABSENT` fires. Re-measured
     under the enclosed-regions semantics: real backgrounds agree 0.925-1.0
     with their own ring, full-bleed art 0.355 and below; bare cloth on the
     gradient repro 27.0% -> 1.1% end to end.
  2. The SUBJECT-DOMINATED-BORDER guard (the owl itself — a tight crop
     passes guard 1 because the subject IS the ring's modal color, 0.827 on
     the committed repro). The tell is a second coherent border color (the
     wall peeking through the crop margins): largest coarse color bin among
     ring pixels the modal mask does not claim, >= `cfg.bg_border_rival_min`
     (0.10; measured 0.000-0.021 on every real-background fixture, 0.173 on
     the repro), with the modal color also failing to hold a majority of
     the frame's corners. Nothing floods; `BACKGROUND_UNCERTAIN` with
     `reason: "subject_dominated_border"` says why. Bare cloth on the owl
     repro 93.4% -> 3.0% (pre-fix, the subject's whole body was deleted).
  `bg_mask` is bit-identical on all nine real-background fixtures; the
  stage-2 photo-lane golden was deliberately re-captured for the two
  full-bleed fixtures the existence guard changes (repro_gradient_white_icon,
  photo_subject_stub). New fixture: `digitizer/testdata/photo/
  tight_crop_pale_subject.png`. Tests that pin the ENCLOSED machinery on the
  repro fixture now disable the guards explicitly (`repro_cfg` in
  `tests/test_enclosed_background.py`).

## How-to: sharded CI, reading a golden mismatch, per-lane fill options, and the flags (2026-10-07 → 2026-10-20)

Practical recipes only. What is built, ON or measured lives in MASTER_SCOPE;
the reasoning lives in the code comments named below. Refreshed 2026-10-20
over `5a4c019..0eb5e02` (2026-10-11 → 10-19).

### Sharded digitizer CI (PR #669; wire scope PR #791; durations PR #838)

- **Shape.** `digitizer shard 1/6 … 6/6` (matrix job `digitizer-shard`,
  `timeout-minutes: 45`, `fail-fast: false` so a red PR shows every failure at
  once) each run `pytest -n auto --dist loadgroup --no-loadscope-reorder` on
  their own four-core runner; the required check named `digitizer` is an
  aggregator that `needs` them, runs `if: always()`, and goes green only if
  every shard succeeded AND `digitizer/tools/ci_shard_check.py` proves the
  shards' manifests are one per shard, identical collected lists, pairwise
  disjoint selections, together the whole suite. A red shard, a missing shard
  or a dropped test all fail it. **A cancelled shard set ends the run
  `cancelled`, not red** (a superseded push under cancel-in-progress
  force-cancels the whole run), so a `digitizer` red whose shards all read
  `cancelled` is a superseded run, not a failure — check the head SHA before
  acting on it (`.claude/skills/k3/SKILL.md` §5).
- **Wire scope (Kent's call 2026-10-08, PR #791).** A PR that touches neither
  `digitizer/` nor `.github/` cannot change what the pipeline tests exercise,
  so on such a PR shard 1 runs only the "wire" tests — the files that read
  OUTSIDE `digitizer/` (the Studio's JS, `src/`, the fonts, `docs/`), printed
  by `python -m tools.ci_wire_tests` from `digitizer/`, whose static rule
  classifies a new test the moment it lands (20 files and ~3.6 of 166
  test-minutes when written; 47 files on 2026-10-20) — and shards 2–6 write a marker and stop; `main`
  still runs the full suite on every merge. The aggregator requires all six
  shards to have reached the same decision. Motive, measured: 55 of the 100
  PRs before it touched neither path and each paid ~48 runner-minutes.
  **A docs-only or Studio-only PR therefore proves nothing about the
  digitizer**; its full run is the merge to `main`, which is where PR #982's
  skill-only diff found the Fremont md5 red (next section).
- **Assignment.** `digitizer/tests/_ci_shard.py` (hooked from `conftest.py`)
  gives whole test FILES to shards, longest first onto the lightest shard,
  weighted by `digitizer/tests/.shard_durations.json` (per-file seconds).
  Whole files, so module-scoped fixtures are computed once. A file missing
  from the JSON gets the median, so a new test file needs no refresh — **but
  add a new LONG file by hand** (`"tests/test_foo.py": <seconds>`), as every
  lettering lane of 2026-10-13/15 did (`test_column_ends`,
  `test_bean_counter_hold` at 80 s, `test_fremont_small_lettering` and
  `test_fremont_triage` at 600 s), so the median does not drop a ten-minute
  file onto an already-full shard. Inside a shard `tests/_xdist_groups.py`
  sends tests that share a module fixture or a memoized pipeline run to ONE
  worker and spreads the rest heaviest first; with the one-thread setting
  below, shard 1/6 went 389 s → 248 s.
- **Match CI's environment when you reproduce a shard.** CI sets
  `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and
  `OPENCV_FOR_THREADS_NUM` to `1` (one native thread per xdist worker; left
  alone, OpenCV and OpenBLAS start four threads PER WORKER and sixteen fight
  over four cores — 389 s → 357 s from this alone, and no pinned result
  depends on the thread count). Run one shard locally (inert unless the
  variable is set; a plain `pytest` still runs everything):

  ```bash
  cd digitizer
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENCV_FOR_THREADS_NUM=1 \
  DIGITIZER_SHARD=2/6 DIGITIZER_SHARD_MANIFEST=/tmp/m2.json \
    .venv/bin/python -m pytest tests/ -q -n auto --dist loadgroup --no-loadscope-reorder \
    > log 2>&1; echo "EXIT=$?" >> log
  ```

  Add CI's two `--deselect` node IDs (workflow file) to reproduce its exact
  selection. Run the aggregator's check on a folder of manifests with
  `python digitizer/tools/ci_shard_check.py <dir>`.
- **Changing the shard count** means editing the matrix list, the job name and
  the `DIGITIZER_SHARD: k/6` denominator together — **and a cloud session's
  token cannot push it.** A push that touches `.github/workflows/` is refused
  for the token a cloud worker holds (PR #987, 2026-10-19, which dropped its
  workflow edit and recorded the junit properties from the test instead). The
  2026-10-08 workflow commits came from a session that could; a workflow
  change goes through Kent or a session on his box.
- **Refresh `.shard_durations.json`** when one shard keeps running far longer
  than the rest (stale numbers cost balance, never coverage). Download the
  `digitizer-shard-*` artifacts of one green run (each holds `junit.xml` and
  `shard-manifest.json`) and:

  ```bash
  cd digitizer
  python tools/ci_shard_durations.py shard-1/junit.xml shard-2/junit.xml … shard-6/junit.xml
  ```

  It rewrites the JSON in place; commit it. Relative weights are what matter,
  so a local `--junitxml` also works. **Last full refresh: PR #838,
  2026-10-11**, from `main` run 38184616285 (279 files, 202.9 test-minutes;
  41 files had been sitting on the median). Its own measured result is the
  honest budget: test-minutes balance to zero by construction, wall time did
  not — the shard spread went 4.7 → 3.8 min and the slowest shard 12.0 →
  11.5, because a shard's few long files leave a tail no refresh removes. If a
  tighter spread matters, look at the longest files in the JSON, not at
  another refresh.
- **Trap.** The plugin pops `DIGITIZER_SHARD`/`DIGITIZER_SHARD_MANIFEST` from
  the environment when it runs, so a child `pytest` (e.g. `test_doc_claims.py`
  collects in a subprocess) sees the whole suite. Don't re-add them to a child.

### Reading a golden or md5 mismatch (2026-10-19)

A byte-identical pin can go red on a tree whose engine did not change, and
FOUR wrong stories in a row were told about one such red before the right
variable was recorded (`.claude/memory/detail-spokes-on-2026-10-18.md`;
PRs #980, #983, #987, and the 2026-10-20 cap). Read a mismatch in this order:

1. **Which IPP path read it.** A stitch stream's md5 differs by the code path
   Intel IPP — bundled inside the OpenCV wheel — dispatches to on the host:
   not by platform, not by test order, and not by numpy's SIMD, OpenCV's own
   kernels or OpenBLAS's core type. Measured 2026-10-20 on an AVX-512 Sapphire
   Rapids Xeon with CI's wheels, each candidate forced down in turn: numpy
   (`NPY_DISABLE_CPU_FEATURES`, X86_V4 / ICL / SPR off), OpenCV's AVX512-SKX
   kernels (`OPENCV_CPU_DISABLE=AVX512-SKX`) and OpenBLAS (`OPENBLAS_CORETYPE`
   HASWELL / SKYLAKEX) all left `027d14e6`; `OPENCV_IPP=avx2` read `75f44f90`
   (Kent's Ryzen 7 4700U, CI's EPYC 7763) and `OPENCV_IPP=avx512` read
   `050452` — a Cascade Lake Xeon's red, byte-for-byte — because IPP's AVX-512
   path sub-dispatches on the newer AVX-512 extensions, so Zen 4 (CI's EPYC
   9V45 / 9V74) and Sapphire Rapids agree and Cascade Lake does not; `sse42`
   and `disabled` read two more values nobody has. **So `tests/conftest.py`
   caps the TEST environment at `OPENCV_IPP=avx2`** (Kent's call 2026-10-20;
   OpenCV reads it lazily, on IPP's first use, so import order cannot defeat
   it) and every host reads one value. The shipped service is not capped.
   PR #987's two-value pin keyed on numpy's AVX512F was keyed on a bystander,
   and its earlier env pin "did not take" because `OPENCV_CPU_DISABLE` wants
   OpenCV's hyphenated names (`AVX512-SKX`, not `AVX512_SKX`; an unknown name
   is ignored with a printed warning) and numpy 2.5 refuses `AVX512F` outright
   (its groups are `X86_V3 X86_V4 AVX512_ICL AVX512_SPR`) — and neither was
   the mover. **A switch proves a library is the mover only when the library
   confirms it took**: `cv2.ipp.getIppVersion()` names the path (`(l9)` is
   AVX2), `cv2.getCPUFeaturesLine()` marks a disabled feature with `?`, and
   numpy's `__cpu_features__` drops what it disabled.
   `tests/test_detail_spokes.py` holds the pattern: ONE md5 beside the counts,
   `test_test_environment_caps_ipp_at_avx2` as the tripwire that separates
   "the cap did not take" from "the engine changed", and junit properties
   (`record_property`) naming the CPU model, the hardware's avx512 flags,
   numpy's enabled SIMD, OpenCV's feature line and IPP's path on every run,
   green or red. **Before theorising about a stream red, read those
   properties** (or print `_host_cpu()` from that file locally). Four
   requests through one service process returned byte-identical designs: it
   is not a product defect. Pin a new stream the same way — one value, no
   tolerance, the host named in the assertion message.
2. **Is it one of CI's two deselects.** CI deselects TWO golden node IDs since
   2026-10-08 (the `photo/enthusiast_logo.png` rows of
   `test_flat_lane_byte_identical` and `test_stage2_photo_segment`); the towel
   `test_pushcomp` row was re-pinned that day and its deselect removed (three
   machines, AVX-512 and forced-AVX2 dispatch alike, compute the tuple in
   `GOLDEN_FLAG_OFF`). PR #987 names the open hypothesis: the two that remain
   may be host SIMD too — AVX-512 runners against AVX2 machines — rather than
   "platform numerics". Unproven; the workflow is untouched.
3. **Is it a pin a flip moved.** A flip re-pins the md5s of every test whose
   fixture it reaches, and the flip PR says which (PR #977 moved two
   `test_small_text_counter_guard` pins and gave the reason). A pin that moved
   with no such PR is a regression.
4. **Only then re-capture.** `tools/recapture_flat_lane_key.py` is still the
   only sanctioned way to move a flat-lane golden, and the one-minute
   `workflow_dispatch` recipe in failure class 1 under "Running things" still
   applies — but a cloud token cannot push that workflow either (above).

### Per-lane fill options in `app/src/lib/generate.js`

`generateElement` passes engine options per lane; the engine defaults stay
OFF, so a lane opts in by passing the key to `EMB.buildQualityDesign`:

- **`fillColumns: true`** — a fill is sewn column by column so no thread
  crosses a cut-out or notch. **All three lanes pass it since 2026-10-08**
  (manual since 10-07; basic shapes and the image lane on 10-08, the image
  lane at +10.4% stitches on real logos, Kent's call with that price
  measured — `tools/fill-columns-lanes.mjs`). This bullet said "manual lane
  only" for ten days after that. Test: `app/src/lib/generate.spec.js`.
- **`cutFloats: true`** (`src/digitize.js`, default off) — a float the DST
  writer would lay as three or more jump records becomes a real `trim` in the
  stream (and so gets ties). **The manual and basic-shape lanes pass it
  (2026-10-08, sequenced after `fillColumns`); the image lane does not**
  (MASTER_SCOPE "Waiting on Kent" 28). `node tools/cut-floats-shapes-sheet.mjs`
  prints the per-family preset table.
- `ties`, `fillStagger`, `dedupeHoles` — no lane passes them ("Waiting on
  Kent" 23 / 24 / 25; the cut-outs section above has each one's rule and
  census tool).
- The "Design file" (imported) lane reads `displayResult(element)` from
  `digitizer.js` rather than `element.result`.

### Digitizer flags: ON since 2026-10-11, and built OFF (all `PipelineConfig` fields)

Check the live default before relying on this list —
`grep -n "<flag>: " digitizer/digitizer_core/config.py` — and read the
comment block above it, which carries the measurement and the flip in Kent's
words. **Three registries travel with every flip, and a flip PR touches all
three:** `tests/conftest.py`'s `PRE_FLIP` (the pre-flip value, so a test
pricing one OTHER flag measures against the engine its arms were made on —
the dict's comments are the flip log), `tools/pro_parity/flagcost.py`'s
`FLAGS`, and `tests/test_off_flags_smoke.py`, which enumerates every bool
field that defaults False and runs the pipeline with it True — a flag leaves
that list by itself when it flips. `tools/off_flags_sheet.py` draws the OFF
set.

**Flipped ON since 2026-10-11 (Kent's calls, in order):**

- `two_tone_snap` — ON 2026-10-11 (PR #821; Kent's approval 10-08, "fix the
  roof-line bug, then flip"; defect 58): a black-and-white raster is
  thresholded to its two inks before any region exists.
- `clip_parent_keeps_ink` — ON 2026-10-12 (PR #856, Kent 10-12; half of
  defect 61): after stage 5's clip the shape keeps the piece carrying its
  INK, not the largest. `clip_keep_pieces` (PR #853) stays OFF.
- `lettering_columns` — ON 2026-10-12 (PR #863, Kent's ruling 10-12): the
  Column lane sews lettering as columns. Its guards followed on 10-13:
  `lettering_columns_skip_blobs` + `lettering_columns_ink_link` (PR #890),
  `lettering_columns_icon_guard` (PR #899), `lettering_columns_square_ends` +
  `lettering_columns_inside_connectors` (PR #922). Still OFF in the family:
  `lettering_columns_small_stem` (PR #896), `lettering_columns_fold_cuts` and
  `lettering_words` (below).
- `small_glyph_keep` — ON 2026-10-13 (PR #908; Kent, option A): stage 4 keeps
  a rescued small glyph's counters and its ink under an earlier colour.
- `small_text_true_size` — ON 2026-10-14 (PR #955; Kent, WoK 56 option A):
  small lettering is re-traced at its true size and thin letters sew as bean
  centrelines. **It is a SWITCH, not a flag**: ON, it fills seven other
  fields from `config.SMALL_TEXT_TRUE_SIZE` (`small_text_keep_stray_lines`
  among them — PR #960's THE fix, live only because the switch fills it), and
  `None` on one of the seven no longer means off. Build a fresh
  `PipelineConfig(..., small_text_true_size=False)` for the OFF engine;
  `dataclasses.replace` keeps the filled values. Its counter guard is
  `SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM` 0.45 mm × 40 / `thread_wt`, an unsewn
  gate-1 candidate 0.011 mm above the measured loss
  (`.claude/memory/small-text-true-size-guard-2026-10-15.md`). Measure small
  text on `tools/fremont_triage.run_arm` (the Studio's own `/digitize`
  request), not on `run_stages`: they cluster differently.
- `text_cluster_rescued_ink_link` — ON from its first commit, 2026-10-15 (PR
  #976, on Kent's directive to clear his five red circles; four of the five
  were a stale service on his box): the text tagger's RESCUED round links on
  one ink (CIEDE2000 20 on the job's chart), as round 2 has since 09-03, so
  Fremont's rescued E at 80 mm no longer joins the tan date. Round-1
  partitions identical on 12 of 17 corpus designs; the function's own default
  stays False and the pipeline passes the config's value.
- `bean_letter_counter_hold_mm` = 0.25 and `bean_letter_bay_hold` = 0.2 — ON
  2026-10-15 (PR #977; Kent's "flip both holds ON" over stitching out first):
  needle points held off a small counter (#952) and stations off an open bay
  (#967). Plain defaults, deliberately not switch values, so an explicit
  `None` is OFF everywhere and the sew-out card tools can pin it. Only
  designs with bean letters move, by a few stitches each; both values are
  gate-1 candidates the cards settle.
- `detail_spokes` — built OFF 2026-10-15 (PR #980), ON 2026-10-16 "tightened"
  (PR #983, merged 10-18): a sub-floor detail of another colour enclosed by
  one shape with ≥ `MIN_TIPS` 4 tips sews as one spoked run on top of its
  host (Fremont's Wisconsin star); the spoke floor is
  `machine.DETAIL_SPOKE_MIN_MM` 1.45 × width / 92.6. Its Fremont OFF pin is
  the SIMD-keyed md5 above.
- Earlier than the range but corrected here, because this file had them
  wrong: `blend_fallback_underlay` ON since 2026-10-07 (it said False);
  `satin_slab_serifs` ON since 2026-10-08, together with
  `satin_free_end_square` (it said OFF); `satin_join_square` True, capped by
  `_STRAIGHT_MAX_MOVE_HALVES = 0.6` (a bend is not a corner);
  `letterform_priors_k` 0.75.
- Browser engine, same fortnight: `underlayDirection` ON (PR #836, Kent
  10-11) and `satinZigzag` ON under a width cap (PRs #904 / #930, Kent
  10-13 / 10-14) — "Architecture map", `satin.js` / `satinplay.js`.

**Built OFF since 2026-10-11 and waiting on Kent (the ones a session will
meet):**

- `open_cored_counters` (PR #988, 2026-10-19): a small counter round a
  page-coloured core stays a hole of its letter (golden_tee's O at 4–5 mm).
  Opens the O only a little and makes five false positives on the phone
  screenshot; the PR's own read is "stays OFF until the satin tiers hold off
  the hole and a guard keeps it off non-lettering detail".
- `lettering_columns_fold_cuts` (built OFF 2026-10-13, PRs #887 / #893; cures
  PR #972, 10-15; sewn judge + coverage guard PR #986, 10-19): cuts a
  lowercase shoulder where a column folds. FLIP-READY by its own numbers (no
  glyph sews worse ON at 50 / 80 / 120 mm; lowercase folds 5 → 0 at 80 mm)
  **and costs 2–3.4× the digitize time on lowercase**, because the judge sews
  every candidate cut. Kent's call; the instrument is `tools/lowercase_angle.py`
  plus `outline_cut.sewn_knots`.
- `lettering_words` (built OFF 2026-10-08): the one-word-model lettering
  tagger. MASTER_SCOPE 57 says NOT ripe — a flip would SHRINK the Column lane
  on golden_tee (9 → 6 shapes); judge any flip with
  `tools/script_lowercase_census.py`.
- `thread_wt` (40, a PROFILE, not a flag) and the `hairline` tier (PR #848,
  2026-10-11): thread weight moves satin spacing and the hairline tier's
  admission and run width — deliberately not the minimum stitch, fill row
  spacing or the stage-4 area floor; 60 and 75 are unsewn candidates.
  `hairline` sews a one-thread stroke as one run instead of the three-pass
  bean; every `hairline_*` sibling (`_over_ground`, `_from_lines`,
  `_lines_strand_test`, `_lines_strand_mass`, `_lines_chain`,
  `_lines_gradient`, `_lines_logo_refusal`, `_coverage_guard`) is OFF and
  most are measured negatives — read `config.py` before building a ninth.
- `forbid_gap_mm` (PR #846, 10-11; `None` is OFF): closes sub-threshold gaps
  between colours (defect 47, Law 26); 0.8 is the documented candidate and
  waits on card block 6.
- `small_print_floor` (PRs #873 / #878 / #880, 10-12/13): no Column-lane
  stitch over a letter counter; reaches the run and fill tiers.
- Also OFF: `small_lettering_skeleton` (#913, #936),
  `small_dot_rung_lettering` (#939, #975), `small_letter_ties` (#956),
  `ink_ground_ring_mm` (#958), `bean_letter_passes` (#950),
  `edge_cap_bean_pitch_mm` (#969), `preflight_glyph_metric` (#945),
  `fill_technique="fur"` (#920, API-only), `hair_regions_directional` (#925, a
  measured negative), `subpixel_corner_runs`, `bg_structural`,
  `clip_keep_pieces` (#853). `coverage_edges` is DEPRECATED (Kent 2026-10-12:
  no). `test_off_flags_smoke.py`'s `OFF_FLAGS` is the live list.

**Determinism rule for `medial_axis`.** Always call
`skimage.morphology.medial_axis(..., rng=0)`. With the default `rng=None`
skimage breaks ties from OS entropy and the lane sews a different design on
every run (golden_tee gave 8,312 / 8,318 / 8,319 / 8,315 stitches).
`stage6_satin`, `shapefield` and `outline_cut` already pass it; any new
caller must. Spot-check a new call site by running the same input twice in
separate processes and diffing the stitch streams.

### New `tools/` scripts (engine, run from repo root)

- `node tools/file-cut-census.mjs [srcDir] [--set shapes|lettering|image|<set-file>] [--on flag[=value]] [--every K] [--jobs N] [--json out] [--keep dir] [--against otherSrc]`
  — what a machine CUTS, read off the written PES/EXP/DST rather than the
  builder's stream; `--against` diffs two engines. Set files:
  `tools/file-cut-sweep-set.mjs` (the 8,255-design sweep),
  `file-cut-satin-set.mjs` (hand-drawn shapes set to satin),
  `file-cut-import-set.mjs` (imported stitch files and `combineDesigns` pairs).
  `--every 10` is the quick look.
- `node tools/travel-sheet.mjs out.svg [--against otherSrc]` — draws four
  designs (satin T, thin star, imported file, lettering + import) from what a
  third-party reader makes of each file: needle-down, sewn and travelled.
- `node tools/crossval-stitch-formats.mjs` — the cross-validation harness
  behind `node --test`'s format tests; needs a venv with `pystitch`.
- `digitizer/tools/` additions (each has a docstring with usage):
  `ci_shard_check.py`, `ci_shard_durations.py` (above); `fan_census.py`,
  `n_fan_spies.py`, `letter_band.py` (letter-fan / lettering measurements);
  `eye_pairs_price.py`, `eye_pairs_gallery.py` (labelled thread pairs for
  Kent's sitting); `letterform_priors_spike/` (the refit spike).
- Since 2026-10-11: `tools/underlay-direction-measure.mjs` / `-sheet.mjs` /
  `-logo-sheet.mjs` (defect 57's instrument and renders),
  `tools/satin-zigzag-cap.mjs` (the lettering zigzag's width cap, PR #930),
  `tools/small-cap-census.mjs` (85 fonts × 5 caps) and
  `tools/crossstitch-arm-census.mjs` (the worst X arm per font per cap
  against the machine limit — why `crossfill` splits an arm past one DST
  record into collinear sub-segments since 2026-10-13),
  `tools/svg-import-gate.mjs` (the 2026-07-27 plan's SVG import risk gate,
  measure only).
- `digitizer/tools/` gained about sixty scripts in the same nine days
  (`git diff --stat 5a4c019..main -- digitizer/tools`), nearly all
  one-question instruments named in their PR bodies — list the directory
  rather than this file. Three conventions now gate every one of them, each
  enforced by a test: **`--help` answers in under 30 s and exits 0**
  (`tests/test_tools_help.py`, PR #965 — a hand-parsed `argv` that took
  `--help` as data ran a full 26 s digitize and passed on exit 0);
  **a tool that writes or reads a `.md` is listed in
  `tests/test_tools_console.py`'s `NAMES_ONLY` / `DOC_READERS`**; and
  **a render committed under `docs/renders/` needs an entry in
  `docs/asset-provenance.json`** (`node --test test/asset-provenance.test.js`,
  which every lettering PR of the fortnight ran). Two to know by name:
  `tools/fremont_triage.py` replays the Studio's own `/digitize` request for
  Hotel Fremont at Kent's settings (`run_arm` is the number every PR table
  quotes; `ARMS["small_glyph_keep_off"]` is the engine as he sewed it), and
  `tools/small_lettering_compare.py --corpus` is the 17-design lettering
  corpus (`corpus_designs`) those tables are measured over.

## Running things

Pass counts are gone from this section on purpose — the counts-are-gone
convention: a total that drifts with normal work is never hard-coded in a
doc; run the suite for today's number and judge the run by its expected
failure classes instead (precedent: fb2cc18, which dropped the hard-coded
`tools/` script count the same way). Engine and Studio suites are expected
CLEAN — engine verified clean 2026-08-17, Studio 2026-08-11 — so any
failure in those two is a regression, with two caveats. One: the engine's
PES/EXP/DST cross-validation tests (`test/crossval-stitch-formats.test.js`)
skip quietly on a machine whose digitizer venv can't import pystitch, and a
green run with them skipped proves less than it looks (CLAUDE.md's venv
note is the trap; under CI they throw instead of skipping, and the engine
job installs pystitch so they run for real). Two: **a loaded box forges
Studio failures** — the specs' `preloadAllFontsSync` beforeAll decodes the
whole 85-font library under vitest's 10s hook timeout, and on 2026-08-22 that
failed 5 spec files under pip/pytest contention, 3 on a second loaded run,
0 solo; re-run solo before calling a Studio red a regression. The
digitizer's three expected failure/skip classes are documented below the
command block.

**CI now exists.** `.github/workflows/python-package-conda.yml` (PR #37
rewrote Kent's initial stock conda template to run the three commands
below for real) runs on every push and pull request — **four** required
checks, engine / studio / digitizer / studio-e2e (since 2026-10-08 `digitizer`
is an aggregator over six `digitizer shard k/6` jobs — "Sharded digitizer CI"
below), each shard deselecting **two**
golden tests by node ID since 2026-10-08 (CI's OWN list, not the same set
that fails on Kent's Windows machine — see the failure classes below). It was
five until 2026-08-22, when the remove-and-see check below was finally run,
and three until the towel row was re-pinned on 2026-10-08. A PR that touches
neither `digitizer/` nor `.github/` gets the WIRE scope — shard 1 runs the
wire files (47 on 2026-10-20) and the other five stop — so a green `digitizer` on such a PR proves
nothing about the pipeline (the How-to section above). Every PR needs its
Actions run green in addition to a local pass before merging.

**The `runner_id: 0` outage is OVER — do not merge past a red check on its
account.** From 2026-08-09 this file carried a standing "unresolved"
note: CI checks from PR #106 onward died in ~2-4 seconds with `runner_id:
0`, no runner ever assigned, and Kent was merging past red checks that
matched that signature. That workaround is retired. Runs now get real
runners and execute to completion — run 646 on `main` assigned
`runner_id: 1000001710` and spent 12m47s inside its `Digitizer tests`
step before failing, and runs 649/653/654 the same day were green at
13–18 minutes apiece. **A red check today is a real failure, so read the
job log rather than assuming the old signature.** *(confirmed 2026-08-21 —
GitHub Actions API, runs 32486606246 / 32490814989 / 32493902438 /
32494954449 on `main`)*

```bash
node --test                 # engine tests (root) — expected clean
cd app && npm install && npm run dev     # Studio dev server
tools/start-emb-bot.ps1     # Windows: both servers in their own windows + opens the browser
cd app && npm test          # Studio tests (vitest) — expected clean
node tools/build-embf.mjs   # rebuild the binary font library (see section above)
node tools/studio-raster.mjs FILE...   # the Studio's PREVIEW raster (1,200-px long-edge cap, its own rasterize.js in
                                       # Playwright's Chromium) -> digitizer/.cache/studio-raster/. What the panel SENT
                                       # until 2026-09-20 and still sends for SVG/GIF/oversize; rasters now go as the
                                       # file (DOCTRINE 2026-09-19/20)

cd digitizer && .venv/Scripts/python -m pytest -q -n auto   # Python digitizer tests (runtime + expected failures below)
cd digitizer && .venv/Scripts/python -m digitizer_service   # service on 127.0.0.1:8721

python3.12 -m venv rembg_isolated/venv                      # REQUIRED for deploy — see below
rembg_isolated/venv/bin/pip install -r rembg_isolated/requirements.txt
```

**The isolated rembg venv is a DEPLOY REQUIREMENT as of 2026-08-24**, not an
optional extra — Kent's ruling the day `photo_prep` and
`photo_prep_background_removal` both became shipped defaults. A box without
it still completes every job, but every photo-class job takes the plain
classical route and the subject cutout never runs, which on the acceptance
portraits is the difference between 29 regions and 110. Build it wherever
the service actually runs; `digitizer/rembg_isolated/README.md` is the
authority, including why it cannot live in the shared venv (numba refuses
numpy>=2.5, which the shared venv pins for the k-means goldens).

Two consequences worth knowing before they cost you an hour:

- **CI does not build it**, deliberately. So CI exercises the FALLBACK, not
  the cutout, and a green CI run is not evidence about the cutout path.
- **A missing venv now skips tone/texture/face prep too**, not just the
  cutout. That is the fix, not a bug: prep without the cutout is the worst
  arm the acceptance harness measures — worse than no prep at all on all
  four portraits — so the old behaviour failed in the expensive direction.
  An explicit `photo_prep=True` with the cutout flag OFF still gets prep
  alone; only a cutout that was asked for and could not be delivered
  triggers the skip.

**No pass counts here anymore — judge a run by its failure classes.** The
totals this note used to carry (654/658, ~7-11 min) were measured in the
2026-08-03-era dev container and sat unedited while the suite roughly
doubled; per the counts-are-gone convention (defined at the top of this
section), run the suite for today's numbers. What stays true is which
failures are EXPECTED:

0. **The Studio e2e suite looks flaky locally when the digitizer service is
   down.** `npx playwright test` fails 2-3 of the `digitize-*` specs, each
   taking ~5 minutes, while every one of them PASSES run alone in ~5 seconds.
   Not a flake and not a regression: those specs each bootstrap the service
   themselves, which under Playwright's two parallel workers is slow and racy.
   With the service already up the same suite is 15/15 in ~35s. `npm run dev`'s
   `predev` starts it via `app/scripts/ensure-digitizer.mjs` -- which until
   2026-08-26 only looked for the WINDOWS venv (`.venv/Scripts/python.exe`) and
   so silently declined to start anything on Linux. If you see this pattern,
   check `curl 127.0.0.1:8721/health` before suspecting your diff.
   *(root-caused 2026-08-26, after it cost a session twenty minutes)*

1. **Golden/byte-identical mismatches on any machine that didn't capture
   the golden.** Per-fixture platform divergence, not version skew — every
   geometry-relevant pip pin matches `requirements.txt` exactly, and one
   such failure traces to a single contour on one region of 31
   (`.claude/memory/windows-goldens-fail-locally.md`). Goldens are
   re-captured on Linux, never on Windows (MASTER_SCOPE.md gotchas — moved
   from ROADMAP 2026-08-19; PR #159 is the sanctioned pattern), so WHICH
   parametrizations mismatch depends
   on where each golden was pinned, and the set moves when one is
   re-captured. The concrete per-machine set lives in ONE place — the
   MASTER_SCOPE "Gotchas" matrix ("The golden divergence is PER-FIXTURE,
   not per-platform") — with cause detail in
   `docs/pro-parity-real-art-2026-08-15.md` §0b. CI deselects TWO node
   IDs since 2026-10-08 (list + rationale in the shard job's header comment
   in `.github/workflows/python-package-conda.yml`); it was five until
   2026-08-22 and three until the towel `test_pushcomp` row was re-pinned —
   this sentence said "five" for hours after the workflow said three, and
   "three" for twelve days after it said two. **A stream md5 also differs
   by the host's SIMD class** (AVX-512 runners against AVX2 machines, found
   2026-10-19), which no platform matrix predicts: read "Reading a golden or
   md5 mismatch" in the How-to section before calling any of this a
   regression.
   **The remove-and-see check is no longer unowned — it was run 2026-08-22.**
   On Linux with the digitizer job's exact Python (3.12) and requirements.txt
   pinned exactly, two of the five deselects (`logo_alpha.png` on the flat-lane
   and photo-dispatch goldens) PASS and three FAIL; the same split holds on
   3.13, so it is not version skew. Those two are now removed from the
   workflow, restoring the coverage they were costing, and the list was
   three — two since 2026-10-08, when the towel tuple proved identical on
   three machines, AVX-512 and forced-AVX2 alike, and went back into
   `tests/test_pushcomp.py`'s `GOLDEN_FLAG_OFF`.
   A golden failure outside the matrix's expected cell is a REAL regression,
   not this note being stale.
   **Re-capturing on the judging machine takes a minute, not a session
   (2026-09-09, PR #432).** A temporary `workflow_dispatch` workflow on the
   branch (`git show 1c9fcba:.github/workflows/recapture-goldens.yml` for the
   template) checks out the pre-change ref as a worktree, runs
   `tools/recapture_flat_lane_key.py <key> --pre-change-tree ../../pre/digitizer`
   per key — which writes a key ONLY after that machine reproduces the old
   entry byte-for-byte on the pre-change engine — prints `pushcomp_pins.py`
   in both trees, commits the JSON back to the branch and uploads the log as
   an artifact. The whole job ran in 66 seconds on ubuntu-latest. Two traps:
   a workflow that exists only on a feature branch is NOT registered until
   something runs it (`workflow_dispatch` answers 404), so the file carries a
   one-shot `push` trigger on its own path; and the enthusiast key is refused
   by the guard on the runner too — it is the platform red CI deselects and
   stays exactly as it was. Remove the workflow with the commit after the one
   that lands the goldens, and `git pull` before pushing anything else: the
   bot's commit is on the branch now.

2. **OCR tests skip when the `tesseract` binary is not on PATH — except on
   CI, where a missing binary fails loud.** `textcluster.py`'s
   OCR-confidence gate and OCR-suggested-text passes call the real binary
   through `pytesseract`; CI apt-installs `tesseract-ocr` (see the
   workflow), most dev machines don't have it. The five tests that assert
   a REAL read (not a mocked one) carry the shared `requires_tesseract`
   marker (`digitizer/tests/conftest.py`, since 2026-08-17), which skips
   only when the binary is missing AND `CI` is unset — so a workflow
   refactor that loses the tesseract install fails the job instead of
   going dark behind quiet skips. Before the marker these five FAILED on
   a tesseract-less machine and read as unexplained local reds. A local
   skip means "install tesseract to exercise OCR end-to-end", not that
   anything is broken.

   **But do not read a local skip as "nothing to see here" before you
   push — a green local suite with these five skipped is NOT the same run
   CI makes.** Corrected 2026-08-21, the hard way: a `stage6_satin` change
   passed the full local suite (same failure set as baseline, canary clean)
   and CI still went red, because the only test that could see half of what
   the change did was one of the five. `_prune_spurs` is shared with
   `textcluster.py`, and `test_ocr_gate.py` was the sole coverage of that
   path. **On Linux `sudo apt-get install -y tesseract-ocr` takes about a
   minute** — do it before trusting a local run on anything touching
   `textcluster.py`, `stage6_satin.py`'s skeleton helpers, or
   `shapefield.py`. Cheaper than a CI round trip.

3. **Three MORE tests skip for reasons that are NOT tesseract, so a local
   run shows 8 skips and not 5** — on a box with neither tesseract nor the
   rembg venv. **The TOTAL is environment-dependent and the per-class rows
   below are the real content**; two levers move it, and both are things a
   session may well have just changed. Installing tesseract removes 5;
   building `rembg_isolated/venv` removes 2. A cloud container with
   tesseract preinstalled and the rembg venv built shows **1** — measured
   2026-08-24, and that lone skip is the opencv-contrib inversion, which
   never goes away.** Measured 2026-08-22 by grouping every
   skip reason in a full `-rs` run, because the count not matching this
   section's only documented skip class is the kind of small discrepancy a
   session burns twenty minutes on:

   | count | file | reason |
   |---|---|---|
   | 5 | `test_ocr_gate` / `test_ocr_suggest` / `test_pipeline` / `test_service` | tesseract binary off PATH (class 2 above) |
   | 2 | `test_background_removal.py` | the isolated rembg venv is not built — `digitizer/rembg_isolated/README.md` |
   | 1 | `test_photo_prep.py` | opencv-**contrib** IS installed, so the no-contrib fallback branch cannot fire |

   The last one inverts the usual reading: it skips because the environment
   is MORE complete, not less. It is half of a deliberate either/or pair in
   `test_photo_prep.py` — `..._without_contrib_falls_back_to_bilateral` and
   `..._with_contrib_takes_the_real_path` carry opposite `skipif`s, so
   exactly one of the two always runs and neither is ever a provisioning
   gap. What it means in practice: on a box pinned to `requirements.txt`
   (which brings contrib) you are testing the real rolling-guidance path,
   and the bilateral fallback is untested by construction — verified at
   source 2026-08-22, not inferred from the skip string.

   To re-derive this list rather than trusting it:
   `python -m pytest tests/ -q -n auto -rs 2>&1 | grep '^SKIPPED' | sed 's/:[0-9]*:/: /' | sort | uniq -c`

4. **`rembg_isolated/venv` changes what a photo-lane test sees.** Where
   the venv is built, stage 1 really cuts the subject out. CI never builds
   it, so in CI the cutout is requested but unavailable, and the job skips
   prep entirely. Until 2026-10-02 four tests went RED on every machine
   with the venv and green in CI, although each was about something other
   than the cutout: `test_shade_palette_demand.py::test_pipeline_gate_
   photo_classes_only[photo_subject-...]`, `test_photo_sequencing.py::
   test_photo_class_plan_is_depth_sorted_end_to_end`, `test_merge_
   adjacent_same_thread.py::test_the_pipelines_own_output_no_longer_
   needs_the_merge` and `test_is_photographic.py::test_declaring_a_
   gradient_photograph_brings_it_inside_max_colors`. They now pin
   `photo_prep=False` (#553), which IS CI's route:
   `test_background_removal`'s `test_an_unavailable_cutout_falls_back_to_
   no_prep_at_all` asserts the two produce the same geometry. **Do not pin
   `photo_prep_background_removal=False` instead.** That runs prep without
   the cutout, a third route neither machine takes, and the most expensive
   arm on the acceptance sheet. **A new test that runs a photo class end to
   end on defaults needs the same pin, unless the cutout is what it
   tests.** When you attribute a red set against a pre-change worktree,
   still give that worktree the same venv state first; a worktree has none.
   One symptom remains under a loaded 4-core full run:
   `test_real_background_removal_on_a_real_photo` can report *"rembg worker
   timed out after 60s"*. That is contention, not the engine; it passed
   alone in 7 s the same hour.

Anything red outside classes 1 and 4 is unexplained and yours to chase, and
any skip outside classes 2-3 is a new one — chase that too.
Runtime moves with the suite, so this file carries no figure: CLAUDE.md
does (about 45 minutes for a full run on a four-core cloud container with
`-n auto`, measured 2026-09-14, and 1.8× that when a second suite overlaps
it — the "~7 min" that stood here was the 2026-08-22 suite). `-n auto` is
in the command because pytest-xdist is pinned in `requirements.txt` and
parallel runs are verified to produce the identical pass/fail set (the
workflow comment says how). A worker session does not run the full suite
at all: CI's six shards are the full run (the How-to section); run the
files a change can reach, and `tests/.shard_durations.json` says what each
one costs.

`EMB-Bot-standalone.html` is **DELETED 2026-08-04, Kent's call**, and
`EMB-Bot.html` itself (plus `src/app.js`) followed on **2026-08-08**
(commit `cd9dfcb`, "remove legacy standalone tool") — do not regenerate
either. `tools/bundle.mjs` (the standalone's rebuild step) was doubly dead
— its input and its output both deleted — and is itself **deleted
2026-08-11**. The Studio has no CDN runtime dependencies (jsPDF is
npm-bundled, Inter via fontsource, fonts ship locally as `.embf`).

### What a cloud worker session has, and has not (measured 2026-10-20)

Every fact here was read off this session's own container; CLAUDE.md owns
the venv trap in full.

- **Four cores.** `nproc` 4, so `-n auto` is `-n 4` and a full digitizer run
  is about 45 minutes (CLAUDE.md), 1.8× that if a second suite overlaps it.
  The foreman's standing rule is not to run it: run the files a change can
  reach and let CI's six shards be the full run.
- **`python3` is NOT 3.12** — 3.11 on 2026-08-22, 3.13 here — and
  `python3.12` is installed. Build the venv from `digitizer/` as
  `python3.12 -m venv .venv && .venv/bin/pip install -e ".[service,dev]"`
  (CLAUDE.md has why `requirements.txt` alone leaves a venv with no pystitch,
  and why `[service]` alone cannot collect `test_service.py`); the
  interpreter is `.venv/bin/python` wherever this file says `.venv/Scripts/`.
- **No venv is built in a fresh container**: not `digitizer/.venv`, not
  `rembg_isolated/venv`, not `sam2_isolated/venv`. A photo-class job
  therefore takes the no-prep route, exactly CI's (failure class 4 below),
  and `test_background_removal` shows its two skips (class 3); a photo-lane
  number from a worker without the rembg venv is a CI number, not a
  Kent's-box number, and the eye-pairs renders say so in their confound badge.
- **No `tesseract`** on this image (it was preinstalled on the 2026-08-24
  container; it is not here). `sudo apt-get install -y tesseract-ocr` takes
  about a minute and is required before trusting a local run on anything
  touching `textcluster.py`, `stage6_satin.py`'s skeleton helpers or
  `shapefield.py` (class 2).
- **The clone can be SHALLOW.** This one held 288 commits, so
  `git log 5a4c019..origin/main` answered *"bad revision"* for a commit nine
  days old, and `git cat-file -t` agreed — three independent checks will
  confirm history that is merely not fetched (CLAUDE.md footgun 8's cousin).
  `git fetch --unshallow origin` first; it brings every remote branch with it.
- **The token cannot push a workflow file** (the How-to section), and
  `git push --force-with-lease` and `git clean -fd` are blocked by the
  sandbox ("Working conventions").
- **No `scratch_*`, no `.claude/worktrees/`, no `.superpowers/`** — the
  gitignored reference material lives on Kent's box only; "pull the corpus"
  (`.claude/skills/pull-corpus/SKILL.md`) is how a fixture gets here.

### Proving the Studio runs: the smoke driver (PR #982, 2026-10-16)

`node .claude/skills/run-emb-bot/driver.mjs smoke --serve --port 5199` is the
one command that proves both Studio lanes in a headless Chromium: the
lettering lane always, the artwork auto-digitize lane when a digitizer
service answers on 8721. It starts its own Vite on 5199, tears it down, and
prints one caption per lane, both ending `… in hoop` (the canvas caption; the
left panel's `.dgp-stats` is not it). Treat the counts as a shape, not a pin
— `.claude/skills/run-emb-bot/SKILL.md` carries the latest measured pair and
the commit it was read at.

**The two lanes must report DIFFERENT captions.** Identical numbers on both
lines were the 2026-10-16 false green: the Studio persists the current
design in `localStorage` (`app/src/lib/projects.js`), lane 2's reload kept
lane 1's lettering on the page, and the poller accepted that caption while
the digitize still read "Sending your art…" — exit 0, both lines the same.
The driver now clears `localStorage` before lane 2 and accepts only a
caption that differs from the pre-click one (`waitCaption(ms, notEqual)`).
The same run found lane 1 waiting 30 s for a wizard tile the 2026-09-30
configurator redesign had removed; it now fills the `Type a name or word`
placeholder, as `typeText` in `app/e2e/helpers.js` does. **If a smoke times
out on a locator, check the e2e helpers before the app** — the driver is
under no test. Same class as the Studio's own `pollJob` bug the day before
(PR #981, "Hard-won lessons"): a poller that accepts a stale result reads as
green.

### Prepping the pro-parity corpus — budget for Hotel Fremont

`digitizer/tools/pro_parity/prep_all.py` re-digitizes all 23 customer designs and needs
`PRO_PARITY_ROOT` pointing at Kent's `Embroidery Files` and `PRO_PARITY_OUT`
at a scratch dir OUTSIDE the tree (the loose files are customer work and this
repo is public). Most designs take 2–20 minutes each.

**`hotel_fremont_hat` takes ~87 minutes on its own** — 5203.9 s measured
2026-09-12, all of it inside `run_ours`, and it completes successfully. It is
NOT hung, and a session that kills it will simply pay the cost again: this
happened twice before the run was left alone long enough to finish. Size does
not explain it — `gaulke_jb` is 32,665 pro / 43,780 ours stitches against
Fremont's 17,067 / 12,075 and finishes in **155 s**. For contrast on the same
run: `precision_drone` 239 s, `gaulke_roofing_lc` 347 s, `gaulke_plowing_lc`
641 s, `gaulke_plowing_hat` 1200 s.

So a whole-corpus prep is roughly 1.5 hours of ordinary work plus 1.5 hours of
Fremont. Prep the slugs you actually need (`prep_all.py <slug> ...`), and if
you need the whole thing, start it and go do something else. The cause is
unprofiled and filed separately.

### Recapturing `corpus_scorecard_baseline.json`

The baseline once sat unrefreshed through ~15 digitizer commits; the next
recapture folded all of that undiagnosed drift into itself and the change
was misread as noise (docs/scope/1-auto-digitizing-quality.md, the 821d066
correction). Two rules stop a repeat:

1. **Recapture is diff-then-capture, never capture-blind.** Before writing
   the new baseline, run the scorecard at HEAD against the OLD baseline and
   attribute every fixture that moved — to your change, or to a named
   earlier commit, or explicitly as "undiagnosed drift" — in the recapture
   commit's message. An unattributed mover blocks the recapture.
2. **Staleness is measured, not remembered.** The baseline records
   `captured_at_commit`. If `git log --oneline <captured_at_commit>..HEAD
   -- digitizer/digitizer_core` shows landed pipeline commits, any grade
   comparison against the baseline is comparing against a stale ruler —
   say so wherever the comparison is quoted.

### The WSL scorecard box on Kent's laptop (2026-10-02)

Kent's Windows laptop carries a WSL2 Ubuntu 24.04 distro built to match the
CI `digitizer` job: `python3.12` (3.12.3), the pinned `requirements.txt`,
apt `tesseract-ocr` 5.3.4, no `rembg_isolated/venv`. Claude Code does not
run inside it; a Windows session calls in with `wsl`.

**What it is for.** A scorecard `diff` whose OCR and legibility rows read
the way CI's do, without waiting on a cloud routine. Windows cannot give
that (DOCTRINE, the 2026-09-15 platform entry).

**What it is not for.** Capturing a baseline, a golden, or any grade that
gets quoted. `photo/photo_grass_macro.png` scores differently on this box
on both garments with no engine change, so its two rows are the machine's
and not the engine's (DOCTRINE, same entry, the 2026-10-02 addendum).
Captures stay on cloud Linux or CI.

**Layout, all inside the distro's own filesystem:**

- `/root/EMB-Bot` is a plain clone of `origin`. Use it to fetch and to cut
  worktrees. Do not develop in it: nothing under `/root` is backed up and
  no Windows checkout can see its branches.
- `/root/emb-control` is a detached worktree at `2c60cd87`, the commit the
  baseline was captured at when the box was built. **The baseline moved to
  `6e0cb943` on 2026-10-04 and to `d000e370` on 2026-10-05** — re-cut the
  control at the file's own `captured_at_commit` before the next `diff`, or
  its rows compare the wrong commit to the file. Its `digitizer/.venv` is the box's one
  venv. Its `corpus_scorecard_baseline.json` is overwritten with
  `origin/main`'s copy on purpose (the control compares that commit to
  that file), so the tree reads dirty.
- The distro has no Linux user, only root. `-u root` is not optional.

**Scoring a branch.** Put the commands in a script and run the script; see
the quoting trap below.

```bash
# run as: wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/path/to/script.sh
cd /root/EMB-Bot && git fetch origin
git worktree add --detach /root/wt-NAME origin/BRANCH
cd /root/wt-NAME/digitizer
/root/emb-control/digitizer/.venv/bin/python tools/corpus_scorecard.py diff \
    > /root/NAME.log 2>&1; echo "EXIT=$?" >> /root/NAME.log
git -C /root/EMB-Bot worktree remove /root/wt-NAME
```

The borrowed interpreter works because the tool puts its own tree on
`sys.path` *(verified 2026-10-02 — a fresh worktree at `5c99b460` imported
`digitizer_core` from itself, not from the control tree)*. Rebuild the venv
only when `requirements.txt` moves: `python3.12 -m venv .venv`, then
`.venv/bin/pip install -r requirements.txt`. `uvloop` installs on Linux,
so nothing is filtered out the way it is on Windows.

**Budget 35 minutes for the plain tool.** `diff` is serial and took 34.4
minutes for the 52 rows. `/root/scorecard_pool.py` on the box scores the
same rows in a 6-worker pool in 18.0 minutes, then prints the tool's own
`diff` and a zero-tolerance leaf comparison beside it; run it with the same
interpreter from the worktree's `digitizer/`. The two reported the same
movers, line for line. *(measured 2026-10-02 — both at `2c60cd87`)*

**Reading the result.**

- Read the log from Windows at
  `\\wsl.localhost\Ubuntu-24.04\root\NAME.log`, or copy it to `/mnt/c/...`.
- `photo_grass_macro` on either garment: ignore. Stitch counts two off on
  `region_blobs` or `repro_gradient_white_icon`: also the box.
- Rule 2 above still applies. A `diff` at a commit past the baseline's
  `captured_at_commit` shows every pipeline change landed since, and those
  are not the box's either. To judge one change, score its base and its
  head and compare the two logs.

**Traps, each hit while setting it up:**

- **PowerShell to `wsl` to `bash -c` mangles `$` and nested quotes.** A
  `sed` range and a `python -c` both failed that way. A script file run by
  path has no quoting to lose.
- **`wslpath` handed a Windows path through PowerShell drops the
  backslashes.** Write the `/mnt/c/...` form yourself.
- **Work under `/root`, never under `/mnt/c`.** The Windows drive is slow
  from inside WSL and the Windows venvs are not Linux venvs.
- **The VM holds its RAM until it idles out.** `wsl --shutdown` when done.
- **`wsl --unregister Ubuntu-24.04` deletes the distro and everything in
  `/root` with no confirmation.** That is the uninstall, not a reset.

### The eye-pairs reveal gallery (2026-09-17)

`cd digitizer && python -m tools.eye_pairs_gallery` reads the yardstick's
`eye_pairs_out/` (`pairs.json`, `arms.json`, `picks.jsonl`, `features.json`,
`renders/`) and writes `eye_pairs_out/gallery/index.html` + `img/`, each
distinct render shipped once, re-encoded under the artifact's size limit.
**It refuses until every pair is picked** — the page names arms, and naming
one mid-sitting breaks the repeat controls; the refusal is the same rule as
the yardstick's `--reveal`. Publish `index.html` as an Artifact with `img/*`
as `files` and `capabilities: {db: {}, downloads: true}`. Kent's per-pair
"did the arm do what it claims" and per-arm rulings (`flip ON` / `keep OFF`
/ `needs work`) land in the artifact's `db` (`notes/<pair>`,
`rulings/<arm>`) — never in the page, so a republish cannot overwrite them
(the 08-27 artifact trap); read them back with `ArtifactData` and commit
them as `docs/eye-pairs-<date>/kent-notes.json`. No score or agreement
figure appears on the page (`acceptance_ab`'s rule; ROADMAP gate 4) — the
instrument chips show only which way each metric points against his pick,
and the "disagreements" filter IS the exit-clause list. Spec:
`docs/superpowers/specs/2026-09-17-eye-pairs-gallery-design.md`; the
generator imports nothing from `tools/eye_pairs/` and pins its arm and
metric tables by test.

**The labelled page (2026-09-18) and its two later flags.** `--labelled`
builds the before | after page straight from `--render`'s output, no picks:
BEFORE left, AFTER right, the arm named, Kent's verdict taken on the page
and stored under `<arm>__<fixture>`. `--tables corpus.json` puts a measured
table (`{arm: {caption, columns, rows}}`) under that arm's head so the eye
and the instruments sit on one page (2026-09-30; refused for an arm the page
does not show or a ragged row). `--sitting <tag>` keys a SECOND look at an
arm Kent has judged before as `<arm>__<fixture>__<tag>` (letters, digits,
`.`, `-`; the ruling `<arm>__<tag>`), so the earlier verdicts neither pre-fill
the new pairs nor get overwritten — read the page's store with `ArtifactData`
before every republish, and never make room by moving his documents
(DOCTRINE 2026-09-30). The built page is republished to the SAME artifact
URL each sitting; the sittings' READMEs live in `docs/eye-pairs-<date>/`.


### The labelled before | after page — "Flag Before After" (2026-09-18)

`cd digitizer && python -m tools.eye_pairs_gallery --labelled` is the same
generator's OTHER page: every rendered arm beside shipped, **BEFORE on the
left and AFTER on the right, the flag named**, Kent's verdict taken on the
page (`after is better` / `before is better` / `no difference` / `both
bad`, then *did the flag do what it claims* and a note; per arm, his
ruling). It reads only `--render`'s output (`features.json`, `designs/`,
`renders/`) — **no `--pair`, no sitting, no pick**; an arm whose stitches
equal shipped's is counted as *identical, not shown*, an arm that raised as
*failed*. Pair ids are `<arm>__<fixture>`, not opaque, so a note keyed by
one survives a re-render, a new arm, and a republish. Instrument chips stay
hidden until he has given a verdict, then colour by agreement with it; the
per-arm tally is a count of his verdicts, never a rate. **Every pair carries
a change locator (2026-09-29)**: the generator blurs both renders by 0.6 mm
(the 09-18 review's measure — stitch texture gone, shape and shade kept),
thresholds the per-channel difference, and keeps up to three boxes by area;
the page outlines them on both renders and *zoom to change* drives the
synced zoom to each in turn. It finds shape and coverage changes, not
texture: an angle-only pair (five of the 77) says *no change found after
blur* instead. No share or figure reaches the page. Published as
https://claude.ai/artifact/6mjKrbnCX21MM9gQUry4Zp — **republish to that
URL**, never a new one: his notes live in its `db`, keyed by those ids.

**The needle-holes toggle, and a second engine snapshot (2026-09-30).**
`--render` writes `renders/<fixture>__<arm>__holes.jpg` beside every thread
render — `stitchviz.render_penetrations`: the render faded to 35% over the
cloth on the SAME frame, a dot at every `stitch` record, none at a jump —
and the page's *thread | needle holes* control swaps every view's source in
place, so the zoom, the verdicts and the locator's boxes stay put. Built
because the thread render cannot show a split column's mid-column
penetration (the comb, `docs/renders/split-comb-2026-09-30/`); a run
rendered before the map existed gets it on the next `--render` from the
kept designs, no digitize, and a sitting with no map shows no toggle. The
ref arms are `REF_ARMS` in the generator (`ref_0827`; `ref_0930am`, the
morning of 2026-09-30 before #577/#578/#579) and the page reads `is_ref`
and `ref_label` off the record, never an id — it used to test the one
literal `ref_0827`. The evening sitting on the day's three lettering
changes is `docs/eye-pairs-2026-09-30/` (tag `evening-0930`). **A ref
worktree gets the photo-prep venv linked in** (`refarm.link_photo_prep`,
the row's `photo_prep_env`, read by the page's confound badge): the venv
is gitignored and lives in the primary checkout only, so before this a
photo-class fixture's ref side skipped prep and the pair compared lanes
(tires, 2,500 against 2,646 from the same commit; Kent's one "before
better" of that evening).

**Back stitching by one rule, and a pro's file as an arm (2026-10-01).**
`digitizer/tools/underlay_cover.py` reads the STITCHES of ours or a machine
file in sew order at 0.4 mm and calls a stitch back stitching when most of
its thread ends up under thread sewn six or more stitches later (the gap
excludes a cross's own neighbours); the pattern is read from the stitch's
shape — run, zigzag (sawtooth, or this engine's ladder: cross, a walk along
the rail, cross back, which `satin_columns` cannot see) or lattice rows —
with the top thread's support and the holes more than 1 mm inside the
sewn area, per block and for one band (`--crop 0.68 1.0` is MARINE on
Becker). Built for Kent's verdict on the pro pair; what it found and the
trap it walked into (an underlay flag that was a no-op on lettering) are
in `docs/eye-pairs-2026-09-30/README.md`. The page's third kind of arm,
`__file__` (`tools/eye_pairs/filearm.py`), puts a stitch file beside our
digitize of the same fixture; the gallery labels it OURS | THE PRO and
takes a verdict and a note, no ruling.

Two things it is not. It is **not the blind sitting** — a verdict given
knowing which side is the flag is evidence for a *ruling*, and never enters
the yardstick's agreement statistic (§4 of the eye-pairs spec needs the
blind picks). And judging a pair here first **contaminates a later blind
sitting on the same pairs**: he will have seen which side is which. Kent
chose the labelled page with that known (2026-09-18); if the sitting is
still wanted, run it on fixtures he has not judged here, or accept the
contamination and say so in the reveal. His first sitting on it (34 pairs,
six flags) is `docs/kent-review-2026-09-18.md` — *record it and stop*, all
six stay OFF; the 2026-09-18 republish added the other five flags and the
08-27 engine, which he has not judged.

The first copy was made by hand on Kent's box and its generator never
reached the repo; the 2026-09-18 rebuild ran in a cloud container as four
parallel `--render --out <lane> --fixtures …` lanes (three of three logos
each for the flag arms, one for `ref_0827` on all nine — its worktree path
is fixed, so two ref lanes would collide), then
`python -m tools.eye_pairs.merge eye_pairs_out <lane> …`: rows are unioned,
the FIRST lane listed wins a (fixture, arm) that two lanes both rendered,
and it refuses if two lanes disagree on a design's bytes or a fixture's
source hash — which is how a base digitized once per lane is shown to be
the same design. Budget an hour on four cores; `fremont` is ~2.5 min an
arm under contention and `tires` ~80 s (photo-scene prep), the rest under
25 s. `rembg_isolated/venv` was built first so photo-class fixtures got the
cutout the product ships; without it every such render differs from Kent's
box on BOTH sides.

### Eye pairs — the blind A/B picker (2026-09-17)

`python -m tools.eye_pairs` (from `digitizer/`) is the instrument for ROADMAP
phase 1's second clause, *"nothing he judges better ever scores worse"*. It
is the only place Kent's eye is recorded as DATA rather than prose. Spec:
`docs/superpowers/specs/2026-09-17-eye-pairs-design.md`.

    .venv/Scripts/python -m tools.eye_pairs --render     # hours; resumable; --fixtures/--arms scope it
    .venv/Scripts/python -m tools.eye_pairs --pair       # builds the sitting; prints a COUNT only
    .venv/Scripts/python -m tools.eye_pairs --serve      # http://127.0.0.1:8731 — left / right / space / u
    .venv/Scripts/python -m tools.eye_pairs --reveal     # refuses until every pair is picked

- **Do not open `eye_pairs_out/arms.json`, `features.json` or `designs/`
  before `--reveal`.** They say which picture is which. The picker cannot
  serve them (404 by whitelist); a text editor can.
- **`eye_pairs_out/picks.jsonl` is Kent's sitting and is NOT regenerable.**
  A finished sitting is committed from `docs/eye-pairs-<date>/`
  (`picks.jsonl`, `pairs.json`, `arms.json`, `sitting.json`), never from
  `eye_pairs_out/`; until that copy exists the gitignored file is the only one.
- Adding a sitting is adding a row to `ARMS` in `tools/eye_pairs/pairs.py`,
  then `--render` (only the new arm digitizes) and `--pair`. `--pair`
  refuses to build any pair set but the one `sitting.json` records once
  picks exist — move the old log aside first. A `--render` scoped with
  `--fixtures`/`--arms` never touches the sitting.
- The 08-27 arm runs the old engine from a worktree under the system temp
  dir. Whether it is ENVIRONMENT-confounded is **measured at `--render`, not
  assumed** (2026-09-18): the rembg venv present for today's engine and for
  the old one, and whether `requirements.txt` changed since `25da2fe`.
  `--reveal` prints which fact fired and on which fixtures. It depends on
  where you render from: on Kent's machine the main checkout has the rembg
  venv (checked 2026-09-18) and a fresh worktree never does, so from there
  photo-class fixtures ARE confounded; from a `.claude/worktrees/` lane
  neither engine has it and they are not.
- **One `--render` at a time.** It discards and rebuilds
  `%TEMP%/eye-pairs-ref-25da2fe` on start, which is the running render's
  engine if one is already going.
- **Do not `--pair` while `--serve` is up.** The picker notices (it polls the
  sitting's hash, shows a banner, and the server 409s further picks) — but
  the fix is still to stop `--serve`, start it again and reload.
- A metric that *agrees* can be trusted for the DIRECTION of a same-design
  A/B and nothing more: not across designs, not across routes, not as a
  quality percentage, and never as grounds to advance a phase — that is Kent's.

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
    and `buildLetteringDesign` (text path) both live here. Two region inputs
    the manual lane's Column and Line modes depend on: a region with authored
    rails sews satin between them (2026-10-01), and a region with an authored
    path sews one run along it and nothing else of it (`runAlongPath`,
    2026-10-11). Since 2026-10-12 (PR #860) the engine refuses five bad inputs
    cleanly instead of emitting garbage — tatami `rowSpacing` ≤ 0 (`fill.js`),
    an empty ring's NaN size (here), and DST/PES extent and colour overflow
    (the writers); `test/engine-edge-cases.test.js` and
    `test/export-edge-designs.test.js` pin them.
  - `satinplay.js` / `satinfont.js` / `satin.js` — satin column generation.
    `satinplay.js`'s `emitZigzag` + `satinFromRails` is the current quality
    lever for lettering (rails+rungs → clean zigzag, not auto-skeletonized).
    `satinfont.js` also routes bean/running-stitch runs, but ONLY at a length
    the font itself authored — gate 1 bars inventing one, so a run without a
    length is skipped, not defaulted.
    **`satinZigzag` is ON in `buildLetteringDesign` since 2026-10-13** (PR
    #904, Kent's ruling on a before/after render, NOT a sew-out): `emitZigzag`
    used to alternate the leading rail (A1, B1, B2, A2 …) — a needle every
    `SATIN_SPACING_MM` on each rail but only every other stitch crossing, one
    crossing per station against the Python order's two, half the thread,
    since the file was written (DOCTRINE 2026-10-13). **Capped since
    2026-10-14** (PR #930, Kent): only a column narrower than
    `satinfont.SATIN_ZIGZAG_MAX_WIDTH_MM` (= `SPLIT_SATIN_ABOVE_MM`) zigzags,
    because where split satin fires the return leg becomes a cross with its
    own comb and a wide-column design nearly doubles (manga_impact "AB" on a
    Full Back 27,033 → 48,079). `satinZigzag: false` is the old stream,
    `satinZigzagMaxMm` overrides the cap in final mm and `false` lifts it;
    `layoutText` and the emitter themselves still default off.
    `tools/satin-zigzag-cap.mjs` prices it. **`underlayDirection` is ON in
    `buildQualityDesign` since 2026-10-11** (PR #836, Kent; built OFF in
    #822; defect 57): a satin column starts at the end nearer where its
    underlay ends (`satin.startNear`), so a bar's centre-run underlay no
    longer ends at the far end from where its column starts;
    `underlayDirection: false` restores the old order, and
    `tools/underlay-direction-measure.mjs` plus the two `-sheet` scripts are
    its instrument and renders. `buildLetteringDesign` takes the same flag
    since PR #990 (2026-10-20), built OFF there beside `dedupeHoles`.
  - `crossfill.js` — cross-stitch fill for pixel-art lettering fonts. Written
    from first principles, NOT ported: Ink/Stitch's is GPL-3.0 and this product
    is sold. The grid is MEASURED from the glyph outlines, in glyph units, so
    no physical constant is chosen. Must load BEFORE `satinfont.js`, and like
    every engine file it needs registering in all THREE places (see
    "Engine-file lists live in THREE places" in the font-library section).
  - `fabrics.js` — 7 fabric presets driving pull-comp/underlay/density/trim.
    **Hand-ported to `digitizer_core/fabrics.py` and they must not drift** —
    the two engines have to make the same physical choice on the same
    garment. They DID drift for a month (corpus law 26 landed in Python only;
    the browser ran an extra crosshatch pass under every knit fill on
    left_chest/beanie/sleeve, +1.4–5.7% stitches). `digitizer/tests/
    test_fabric_wire.py` now compares both tables field-for-field, both
    `GARMENT_FABRIC` maps, both fallback defaults, and the second hand-copied
    pair `FILL_ROW_MM`/`SATIN_SPACING_MM`. It asserts AGREEMENT, never a
    value — the numbers themselves are gate 1.
  - `flatten.js` — medianCut → modeFilter → absorbSmallRegions pipeline.
    `absorbSmallRegions` labels the image ONCE and then keeps each
    component's pixels itself (2026-10-04). Before that it labelled the whole
    image again after every absorb, and the Studio's tab froze for minutes on
    a photograph. The old loop is kept word for word in
    `test/flatten.test.js` as the definition of what is absorbed into what and
    in which order: change the engine's version and that file says whether a
    pixel moved. `node tools/flatten-census.mjs` prints what the Studio's own
    flatten costs on every testdata PNG, step by step, and with `--hashes` the
    hash of what it returns, to diff two engines.
  - `fonts/` — pre-digitized font library: `manifest.json` (85
    shipping fonts — recount it, the number drifts) + `bin/*.embf` binaries
    + `.LICENSE.txt` sidecars, parsed offline from Ink/Stitch's open-source
    font set. Only 17 fonts have committed per-font JSON sources here; the
    other 68 import from gitignored `scratch_ink/_out` at build time, which
    is why `build-embf` runs the QC gate itself (see the font section).
    (The old "14 fonts" count here was the legacy eager registry
    `src/fonts/satin-fonts.js`, which is out of the shipping pipeline.)
    Also `manifest-coverage.json` (2026-09-07): which code points each shipped
    font can set, derived from the BINARIES by `tools/build-font-coverage.mjs`
    so a cloud checkout without `scratch_ink/` can still rebuild it. It powers
    "this font can't stitch X — these can". **The `manifest` prefix is
    load-bearing**: every other `*.json` in `src/fonts/` is read as a font
    SOURCE by both `build-embf.mjs` and `test/embf-guard.test.js`, whose stated
    invariant is "static JSON here ⇒ shipped". A new artifact here takes the
    prefix; it does not widen that filter.
  - `dst.js` / `exp.js` / `pes.js` — stitch file encoders. DST is
    byte-verified/primary; PES is best-effort. All three are cross-validated
    against pystitch as the third-party reference decoder
    (`test/crossval-stitch-formats.test.js`, revived 2026-08-21 after the
    2026-08-11 pystitch swap left it silently skipping — the repo's only
    automated third-party format check; CI runs it loud, see "Running
    things"). **All three share ONE rule for a move too long for a record
    (the chain rule, `dst.js`):** it is sewn, split into stitches at 12.1 mm
    an axis, only when it CONTINUES a sewn run; the move to a stitch that
    follows a jump, a cut, a colour change or the start of the file is
    travel, laid as jumps up to its last record. `exp.js` took it last
    (2026-10-07): until then its file had needle holes along such a move
    that the other two had not. Check a change to one writer against the
    other two at the FILE: `node tools/file-cut-census.mjs` counts the three
    files' needle holes hole by hole, `--against <src>` says which designs'
    files change. Its own three sets leave two lanes out, and they are the
    two that mattered here: `--set tools/file-cut-satin-set.mjs` is a drawn
    shape SET TO SATIN (the "manual" lane is all fills), and `--set
    tools/file-cut-import-set.mjs` the lanes whose stream can OPEN with a
    stitch (an imported stitch file, alone or as a project's second
    element), which no builder's stream does.
- **`app/src/`** — Svelte 5 Studio. `App.svelte` + `ui/` (steps/components) +
  `lib/` (non-DOM logic, each paired with a `.spec.js`): `project.js` (data
  model, v2 = `{version,garmentId,selectedId,elements:[...]}`), `generate.js`
  (bridges to engine), `combine.js` (multi-element stitch merge), `preview.js`
  (2.5D canvas render), `projects.js` (localStorage save/load registry),
  `threads.js` (named thread-color catalog), `hints.js` (onboarding),
  `hoop.js` (hoop fitting — since PR #865, Kent's ruling 2026-10-13 "cap to
  hoop", AUTO-fit sizes to the placement box capped to the largest hoop's
  usable field (`EMB.autoFitBoxMm`), so auto-fit alone never makes an oversize
  design, and `autoCapNote` says so beside the Size controls on a garment
  whose area is bigger; `autofitHoopCap.spec.js`),
  `flow.js` (the step gates — its `isSewable` is the ONE definition of
  "this element has real content", read by the Next button, the review
  headline and the review recap; do not write a fourth), and three modules
  added 2026-09-07, each because a rule had grown a second answer:
  `summary.js` (the review recap, one branch per element type — the
  `{:else}` it replaced assumed text and described an auto-digitized logo as
  `Text — ""`), `imageSource.js` (restores an `image` element's pixels from
  `element.sourcePng` on project load — they used to live only in App's
  unpersisted `runtime` and a refresh deleted them), and `designChart.js`
  (which thread chart the design's cones came from, as a store because
  `ThreadPicker` has nine call sites). A fourth landed the same day for the
  same reason: `rasterize.js` (decode an uploaded file, and decide the pixel
  size to draw it at) — `DigitizePanel`, `ImagePanel` and `TraceImportPanel`
  each held a byte-identical `loadImage` and its own copy of
  `Math.min(1, MAX / longestSide)`, which is right for a raster and wrong for
  a vector, whose "natural" size is a browser default. Never write a fourth
  copy of either. And a fifth, `fontCoverage.js` (which shipped fonts can set a
  given text), pure, with `fontLoader.loadCoverage()` doing the fetch.

  **What is persisted is what survives.** `projects.js` is a plain
  `JSON.stringify(project)`, so anything an element does not carry is gone on
  reload. `runtime` (`{flats, workImages}`) is deliberately NOT persisted —
  that is why `image` elements keep `sourcePng` and why `imageSource.js`
  exists.

  **Two things about that registry are not obvious from reading it (both
  2026-09-07).** First, a design's NAME is derived from its content while it is
  still unnamed — `deriveProjectName` in `project.js`, gated by `isAutoNamed`
  and written by `autoNameProject`; a name the customer types is sticky and is
  never overwritten. Anything that changes `project` must reach `App.persist()`
  or the name silently stops tracking: undo was the one path that did not, and
  the design read HELLO while every name surface read GOODBYE. Second, **a name
  and a project's membership of the registry live ONLY in `embstudio:index`** —
  there is no second copy in the record — so a failed index write is real data
  loss and `renameProject`/`deleteProject` propagate it. `saveProject`
  deliberately does not: its design landed in its own record, and raising "your
  changes aren't being saved" over a saved design would be its own lie. Delete
  writes the index BEFORE removing the record, since a `removeItem` is never
  quota-blocked.
- **`digitizer/`** — Python auto-digitizing engine + optional FastAPI
  service (`digitizer_core/` importable lib, `digitizer_service/` wrapper).
  Own venv, own test suite, own docs. See "The Python digitizer" above.
- **`tools/`** — the build/QC/harness scripts (count drifts; list the directory); notable:
  `build-font.mjs` (Ink/Stitch font → JSON font library),
  `run-digitize.mjs` / `run-flatten.mjs` / `render-dst.mjs` (Node-side
  pipeline runners so you can test digitizing on a real image without a
  browser — useful since the browser tool here can't do file uploads).
  (`bundle.mjs`, the deleted standalone page's builder, is itself
  deleted — see "Running things".)
- **`docs/superpowers/specs/` + `/plans/`** — every feature slice has a spec
  + plan written before building. Read the relevant one before extending that
  area; they contain the "why," not just the "what."
- **`.superpowers/sdd/progress.md`** — task-by-task ledger for the Studio
  slices (1–8). Gitignored and local to Kent's machine — a cloud checkout
  does not have it (`.superpowers/` is `.gitignore` line 2; nothing under it
  was ever committed). Doesn't cover the font-editing round (that used a
  plain worktree, not `subagent-driven-development`) — see the spec/plan
  above for that instead.

## Known limitations

**See [`MASTER_SCOPE.md`](MASTER_SCOPE.md) for current status, confidence,
and open issues per capability area** — that's the live dashboard; this
section used to duplicate it and the two drifted, so it doesn't try to be
exhaustive here anymore. It holds current state only: per-area supporting
detail is in [`docs/scope/`](docs/scope/), and dated snapshots — test counts,
corpus grades, "landed PR #N" — are in
[`docs/scope-history.md`](docs/scope-history.md), which is append-only and
should never be quoted as live status. The one exception: the *design decision* that
photographic/gradient art can't reach pro quality via auto-digitizing is
architectural, not a status snapshot — see "the one rule" above, which stays
here since it explains *why*, not *what's currently true*.

## Working conventions this project has settled on (don't relitigate)

- **Process:** brainstorm → write spec → write plan → build (via
  `subagent-driven-development` in a git worktree, or ULTRACODE workflows for
  bigger slices) → review (multi-lens/adversarial before merge). This repo
  has done this ~10 times; deviating without reason will surprise Kent.
  Since 2026-10-07 the build step mostly runs as cloud worker sessions
  dispatched by a foreman (the K3 pattern under "Branches & worktrees");
  the spec-then-plan habit and the adversarial review before merge are
  unchanged, and the PR body is where a worker's measurements and its asks
  to Kent go.
- **Additive, back-compat engine changes.** New `opts.*` fields default to
  exactly today's output when absent — no migration step, no behavior change
  for existing callers. Keep doing this.
- **Verify claims, don't trust prior summaries at face value** — this very
  cookbook exists because a memory note said work was "merged to main" when
  it was actually sitting unmerged in a worktree. `git log` is ground truth.
- **In a cloud session, `git push --force-with-lease` and `git clean -fd` are
  BLOCKED** by the sandbox's destructive-git classifier, and you will meet them
  the moment a designated branch's PR merges: restarting that branch from
  `main` makes the next push non-fast-forward. The working fix is to **merge the
  old, already-merged head back in** — non-destructive, and the two-dot diff
  against `main` stays exactly your change. Confirm first with `git cherry
  origin/main origin/<branch>` that the remote head carries only merged content.
  To clear untracked leftovers, `rm` the specific files after checking each
  against `main`; the blanket clean is refused. *(hit twice, 2026-09-12/13 —
  if this becomes routine, a Bash permission rule in `.claude/settings.json`
  is Kent's call.)* The rest of what a cloud container lacks — a shallow
  clone, no venvs, no tesseract, no workflow push — is under "Running
  things", "What a cloud worker session has".
- **Never edit a tracked file from a STALE working tree.** A branch left behind
  `main` will happily let you append to an old copy and commit the whole
  regression: on 2026-09-18 this nearly re-bloated `.claude/memory/MEMORY.md`
  from main's compacted 13,393 characters back to the 48,872 the overflow fix
  had just removed. `git checkout -B <branch> origin/main` (or at minimum
  `git checkout origin/main -- <file>`) BEFORE editing, and read the size or
  content back afterwards.
- **A Studio change is not verified until it has been LOOKED AT in a
  browser.** The suite is broad on logic and near-silent on presentation: a
  2026-08-25 sweep found an invisible primary CTA (white on white, every step
  of the wizard) and a canvas menu that created elements with no feedback,
  both live on `main`, neither failing a spec. Drive the running app at more
  than one width, and read computed styles rather than the stylesheet —
  cascade bugs do not show up in the rule you are looking at.
- **Looking at it in a browser is not enough for what the app GENERATES.**
  The convention above catches what a screen shows; it does not catch what a
  downloaded file contains. The printed worksheet was covered by three tiers of
  test — a call recorder, a real-PDF byte/structure check, and a text
  extraction compared against the screen — and on 2026-09-07 all three passed
  while the operator's thread list was being drawn at y = 11.09 in on an
  11.00 in page, i.e. off the paper, with a blank second page after it. **A
  string is in a PDF's content stream whether or not it lands on the sheet**,
  and the recorder logged `text(str, x, y)` without recording which PAGE, so it
  could not have answered the question even in principle. Render the artifact
  and look at it (`pypdfium2` is one call), and for stitch files decode with
  `pystitch` and DRAW it — CLAUDE.md footgun #1 exists because a swapped
  bounding box fits a quarter turn and a mirror equally.
- **Hand-written asset paths are document-relative, never `/…`.**
  `app/vite.config.js` sets `base: "./"`, whose entire purpose is that the
  bundle works wherever it is served, and Vite honours it for everything it
  owns. Five hand-written `/fonts/…` paths did not, so below the domain root
  the lettering lane produced nothing (7x 404 on `manifest.json`) and the font
  LICENCE links 404'd with it. No test could see it: every suite here runs
  against the dev server at a root, where both forms resolve identically.
  `app/src/lib/assetPaths.spec.js` pins the rule at source level.
- **A regression test must be run against the real broken state before you
  trust it.** The first spec written for the 2026-08-25 simulator regression
  passed with the bug deliberately re-introduced, because the repro was
  narrower than assumed. A green new test proves nothing until you have
  watched it go red.
- **A clean git merge of two green branches is not a safe merge.** On
  2026-08-25 `main` was broken three times in one evening by merges that
  produced no conflict and no failing check: two rival thread renderers
  merged into one function, then two opposite fixes for that merged into a
  file with both call sites and neither definition. Each branch was green on
  its own; the union did not parse. After merging anything into a file a
  parallel lane is also editing, run the module's own parse check by hand
  (see the `preview.js` section) rather than trusting the suite — a module
  that fails to load reports as "0 tests collected", which reads as a pass.
- When adding a font: must carry real hand-authored Ink/Stitch stitch data —
  `<path inkstitch:satin_column>` rails+rungs for satin fonts, and since
  2026-08-21 also run/bean fonts whose runs carry an AUTHORED stitch
  length and cross-stitch fonts with a measurable grid (this line was
  satin-only before those lettering paths existed). What stays rejected is
  the outline-only font, which can only auto-trace — Kent has already ruled
  that lower quality than hand-authored stitch data. Full recipe + license
  gate: `.claude/skills/add-font/SKILL.md` / `tools/build-font.mjs` usage.

## Who's asking for what

Kent (`kent@sdwheel.com`) drives every product decision here via
AskUserQuestion-style brainstorming — he's picked the MVP scope, the font
list, the rejected fonts (too ornate / broken metrics / license-restricted),
and every "build vs. defer" call listed above. Don't assume a feature is
wanted just because it'd be a nice engine capability; check for an existing
spec/decision first, and if there isn't one, ask him rather than guessing.
