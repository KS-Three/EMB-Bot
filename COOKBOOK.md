# EMB Bot — Cookbook for the next Claude agent

Handoff doc. Read this before touching code. Full blow-by-blow history lives in
`.claude/memory/emb-bot-digitizer.md` (moved into the repo 2026-08-14, indexed
by `.claude/memory/MEMORY.md`) — this file is the self-contained handoff.

## What this is

Browser-based embroidery auto-digitizer + guided lettering studio, plus a
Python digitizing engine that runs as a localhost service. Two parts:

- **`app/`** — "EMB Bot Studio", a Svelte 5 + Vite guided wizard (garment →
  content → review → download) built on top of the JS stitch engine via
  `window.EMB` (the `src/*.js` modules, copied into `app/public/engine/` by
  `app/scripts/copy-engine.mjs`).
- **`digitizer/`** — Python 3.14 auto-digitizing pipeline (OpenCV, scikit-image,
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
- **Two builds from one tree.** `node tools/build-embf.mjs` writes the
  **sellable** library (85 fonts, everything inside `ALLOWED_LICENSES`).
  `node tools/build-embf.mjs --personal` writes Kent's private library (120
  fonts, adding ShareAlike / NC / GPL / pulled) to `bin-personal/` +
  `manifest-personal.json` — both gitignored, so a fresh clone or CI cannot
  produce a build containing them. The split is at BUILD time on purpose: a
  runtime toggle is not a distribution boundary. `copy-engine.mjs` serves the
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
  stayed green). Keep all three in sync; legacy `EMB-Bot.html` is a separate,
  fourth list that stays on the old registry.
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
  empty. If you add a code path that builds lettering, pass it through.
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
  or set `PYTHONPATH=.`. **`.venv/Scripts/` is Kent's Windows box; on Linux —
  every cloud session — the same interpreter is `.venv/bin/python`, and that
  substitution is the only difference. It applies to every `.venv/Scripts/`
  path in this file.** No test count is quoted here on purpose — see
  "Running things" below for the expected *failure classes*, which are what
  actually tells you whether a red run is a regression. *(a count lived here
  until 2026-08-21 and had drifted several hundred tests out of date;
  MASTER_SCOPE rule 6 bans counts in prose for exactly this reason)*
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
  minutes to **9 passed / 4 failed in 46 seconds**. The 4 still red are
  PRE-EXISTING and unrelated — verified by running them at `1ab138d`, before
  the node-drag fix, where they fail identically. They are product questions
  for Kent, not test rot, and they are only visible now because the suite
  runs at all:
  - `digitize-background-enclosed` (×2): `.dgp-enclosed-banner` never
    appears. The banner is gated on `unstitchedRows.length`, so the pipeline
    is no longer flagging `BACKGROUND_ENCLOSED` on that fixture at all.
  - `digitize-boundary-edit`: after Save boundary + Apply, `.dgp-stats` is
    still **exactly** `2,153 stitches · 80×30 mm · 2 colors` — the panel
    editor's vertex drag changed nothing in the design. Same family as the
    node-density finding below; worth measuring the mm size of the drag that
    spec actually performs before assuming it is the same cause.
  - `manual-trace-import`: the `Edit points` button is never found, though
    `ManualPanel.svelte:846` still renders it — so something earlier in that
    flow (add shapes) is not completing.

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

- **Never pipe pytest to `tail`** — you get tail's exit code, so a red
  suite reports success. Redirect to a file and check `$?` directly. Cost a
  false "suite green" claim on 2026-08-11.

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
   real Studio uploads) is fixed too, merged PR #22; see
   `docs/scope/1-auto-digitizing-quality.md` for the full breakdown,
   including the one thing still not
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
   the satin/fill call is made from `2·area/perimeter`
   (`stage6_satin.py`'s `ribbon_width_mm`, duplicated in `shapefield.py` —
   this bullet's old `stage7_sequence.py:97` pointer is stale, the logic
   lives there now), a statistic the source patent warns against — it
   satins a 20mm disc under a 5mm cap once the edge is serrated — decided
   without the DT ever being consulted. Steps 5+ all lean harder on that
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
   see that module's THE CLASS-WEIGHT SEAM) — see
   `docs/scope/1-auto-digitizing-quality.md`
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
  gained a restore control for it. See
  `docs/scope/1-auto-digitizing-quality.md` for the
  commit-level breakdown. **The one caveat that kept this from working
  end-to-end through the actual UI is fixed too, merged PR #22:** Studio's
  real upload path manufactured an opaque alpha channel that defeated
  background detection entirely; a fully-opaque channel is now discarded
  as information-free. Verified post-merge at the HTTP level (opaque-RGBA
  twin of the repro fixture now matches its RGB original exactly); a live
  browser run of the full flow hasn't happened yet.
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

## Running things

Pass counts are gone from this section on purpose — the counts-are-gone
convention: a total that drifts with normal work is never hard-coded in a
doc; run the suite for today's number and judge the run by its expected
failure classes instead (precedent: fb2cc18, which dropped the hard-coded
`tools/` script count the same way). Engine and Studio suites are expected
CLEAN — engine verified clean 2026-08-17, Studio 2026-08-11 — so any
failure in those two is a regression, full stop. The digitizer's two
expected failure classes are documented below the command block.

**CI now exists.** `.github/workflows/python-package-conda.yml` (PR #37
rewrote Kent's initial stock conda template to run the three commands
below for real) runs on every push and pull request — **four** jobs, engine
/ studio / digitizer / studio-e2e, the digitizer job deselecting **five**
golden tests by node ID (CI's OWN list, not the same set that fails on
Kent's Windows machine — see the failure classes below). Every PR needs its
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

cd digitizer && .venv/Scripts/python -m pytest -q -n auto   # Python digitizer tests (runtime + expected failures below)
cd digitizer && .venv/Scripts/python -m digitizer_service   # service on 127.0.0.1:8721
```

**No pass counts here anymore — judge a run by its failure classes.** The
totals this note used to carry (654/658, ~7-11 min) were measured in the
2026-08-03-era dev container and sat unedited while the suite roughly
doubled; per the counts-are-gone convention (defined at the top of this
section), run the suite for today's numbers. What stays true is which
failures are EXPECTED:

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
   `docs/pro-parity-real-art-2026-08-15.md` §0b. CI deselects five node
   IDs (list + rationale in `.github/workflows/python-package-conda.yml`);
   those deselected tests never RUN on CI, so their ubuntu-latest behavior
   is inferred from the deselects' history, not measured — the workflow
   comment's remove-and-see check is standing and unowned. A golden
   failure outside the matrix's expected cell is a REAL regression, not
   this note being stale.

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

Anything red outside those two classes is unexplained and yours to chase.
Runtime: 21:34 serial, measured 2026-08-17 on Kent's machine — which is
why the command above carries `-n auto`: pytest-xdist is pinned in
`requirements.txt`, and parallel runs are verified to produce the
identical pass/fail set (see the workflow comment for how).

`EMB-Bot-standalone.html` is **DELETED 2026-08-04, Kent's call**, and
`EMB-Bot.html` itself (plus `src/app.js`) followed on **2026-08-08**
(commit `cd9dfcb`, "remove legacy standalone tool") — do not regenerate
either. `tools/bundle.mjs` (the standalone's rebuild step) was doubly dead
— its input and its output both deleted — and is itself **deleted
2026-08-11**. The Studio has no CDN runtime dependencies (jsPDF is
npm-bundled, Inter via fontsource, fonts ship locally as `.embf`).

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
    `satinfont.js` also routes bean/running-stitch runs, but ONLY at a length
    the font itself authored — gate 1 bars inventing one, so a run without a
    length is skipped, not defaulted.
  - `crossfill.js` — cross-stitch fill for pixel-art lettering fonts. Written
    from first principles, NOT ported: Ink/Stitch's is GPL-3.0 and this product
    is sold. The grid is MEASURED from the glyph outlines, in glyph units, so
    no physical constant is chosen. Must load BEFORE `satinfont.js`, and like
    every engine file it needs registering in all THREE places (see
    "Engine-file lists live in THREE places" in the font-library section).
  - `fabrics.js` — 7 fabric presets driving pull-comp/underlay/density/trim.
  - `flatten.js` — medianCut → modeFilter → absorbSmallRegions pipeline.
  - `fonts/` — pre-digitized font library: `manifest.json` (85
    shipping fonts) + `bin/*.embf` binaries + per-font JSON sources and
    `.LICENSE.txt` sidecars, parsed offline from Ink/Stitch's open-source
    font set. (The old "14 fonts" count here was the legacy eager registry
    `src/fonts/satin-fonts.js`, which is out of the shipping pipeline.)
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
  slices (1–8). Doesn't cover the font-editing round (that used a plain
  worktree, not `subagent-driven-development`) — see the spec/plan above for
  that instead.

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
- **Additive, back-compat engine changes.** New `opts.*` fields default to
  exactly today's output when absent — no migration step, no behavior change
  for existing callers. Keep doing this.
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
