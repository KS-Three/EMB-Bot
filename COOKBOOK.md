# EMB Bot — Cookbook for the next Claude agent

Handoff doc. Read this before touching code. Full blow-by-blow history lives in
Kent's memory file `emb-bot-digitizer.md` (in the operator's Claude memory
store, not this repo) — this file is the repo-local, self-contained version.

## What this is

Browser-based embroidery auto-digitizer + guided lettering studio. Zero
server, zero Python/OpenCV — all stitch math is hand-written JS. Two
front-ends share one engine:

- **`EMB-Bot.html`** / **`EMB-Bot-standalone.html`** — original single-page
  tool (image-to-stitch + text-to-stitch, manual controls).
- **`app/`** — "EMB Bot Studio", a Svelte 5 + Vite guided wizard (garment →
  content → review → download) built on top of the same engine via
  `window.EMB` (loaded through `<script>` tags, engine untouched).

Read the top-level [README.md](README.md) first — it's accurate and
user-facing (outputs, fabric presets, honest limits, file map). This cookbook
covers what the README doesn't: current work-in-progress state, gotchas, and
where the bodies are buried.

## Binary font library (Slice 10 Stage A, 2026-07-27)

The Studio's fonts live in `src/fonts/manifest.json` + `src/fonts/bin/*.embf`
(**69 fonts**), lazily fetched per font by `app/src/lib/fontLoader.js`. The
old eager `src/fonts/satin-fonts.js` (21 fonts) is OUT of the Studio pipeline
but still used by legacy `EMB-Bot.html` pending its audit — do not delete it.

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
  only — `precious` is excluded (GPL-3.0); `milli_marif_bold` is
  grandfathered with an ad-hoc license (flagged to Kent). `ondulamarif_XL`
  was demoted by QC (letter glyphs runs-only → 0 stitches).
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
- Known perf item for Stage B: opening the font dropdown lazily fetches ALL
  fonts for thumbnails (~30 MB). Stage B's browser must use pre-rendered
  preview images instead.

## Font editing abilities Round 1 — merged 2026-07-27

Rotation, per-letter color, bold/thin weight, slant/italic for text elements.
Was previously sitting unmerged in a worktree (a memory note wrongly called
it "merged" — always verify with `git log`, don't trust prior claims at face
value). Fast-forward merged into `main`, worktree removed, branch deleted.
169/169 engine + 182/182 app tests green on `main` as of this writing.
Spec/plan: `docs/superpowers/specs/2026-07-27-font-editing-abilities-design.md`
and `docs/superpowers/plans/2026-07-27-font-editing-abilities.md`. Two
abilities were explicitly deferred (condensed/expanded width, mixed
per-letter size) — both risk distorting satin column width unevenly along
curves; prototype before committing.

`main` is ahead of `origin/main` locally (not pushed) — push is a
user-confirm action, not done automatically.

## Running things

```bash
node --test                 # engine tests (root) — 202/202 as of this writing
cd app && npm install && npm run dev     # Studio dev server
cd app && npm test          # Studio tests (vitest) — 188/188 as of this writing
node tools/build-embf.mjs   # rebuild the binary font library (see section above)
```

The standalone rebuild step (`node tools/bundle.mjs`) is RETIRED along with
`EMB-Bot-standalone.html` — do not rebuild it as features land.

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

## Known limitations (all intentional, all explained to Kent, all accepted)

- Photographic/gradient art can't reach pro quality via auto-digitizing —
  see "the one rule" above.
- Small stacked text (< ~4mm cap height at final size) drops below what
  thread can hold — physics, not a bug. Size up or drop small lines.
- PES output is best-effort (reverse-engineered format); verify on-machine.
- Fabric presets are starting points, not guarantees — Kent test-stitches
  and reports back if one needs tuning.
- Rotation doesn't re-trigger hoop auto-fit — a design that auto-fit before
  a non-180° rotation can visually overflow the hoop. Documented, not yet
  fixed.
- `±30°` adjacent-same-color contrast heuristic (roadmap item) — not built.
- Condensed/expanded width and mixed per-letter size — deferred, see above.

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
