# EMB Bot Studio

A beginner-first embroidery design studio (Svelte 5 + Vite). Pick what you're
making, then build the design from elements — **text** in pre-digitized satin
fonts, a **logo/image** (auto-digitized when the local service is up, else
flattened to thread colors by the browser engine — decided when the element is
added), traced or preset **shapes**, or an imported stitch file — arranged on a
realistic 2.5D thread preview, then download machine-ready files (DST / EXP /
PES in the browser; JEF / XXX / VP3 written by the digitizer service; plus SVG,
PNG, and a printable PDF worksheet). Guided steps: garment → content (add and
arrange elements, with the live preview and review summary) → download. Elements sew in list order with a trim + color
change between them. Resizing regenerates text/shape/image stitches so density
stays correct; imported and auto-digitized elements scale their baked stitches
instead — density changes with size, and their panels say so.

Local-first, no accounts, no cloud: designs live in the browser (a
localStorage-backed projects drawer) and as portable `.embproj` files
(`src/lib/projectFile.js`). The one server is the **optional local digitizer
service** — the Python pipeline in `../digitizer`, served by FastAPI on
`127.0.0.1:8721`, loopback-only. The Studio runs without it, but the image
auto-digitize path needs it, and purely-digitized projects prefer its
pystitch `/export` for stitch files. (The browser's own DST encoder wrote X
and Y swapped until 2026-09-08; it now matches the standard, but a `.dst`
written before that fix re-imports transposed — see `../CLAUDE.md` footgun 1.)

Text, shape, and image-flatten stitch math is the proven JS engine in
`../src` (satin fonts, underpathing, exporters) — the source of truth, **not**
modified by this app. It is loaded via `<script>` tags in `index.html` and read
from `window.EMB`. The satin font library is defined by
[`../src/fonts/manifest.json`](../src/fonts/manifest.json) and fetched lazily
as `.embf` binaries.

## Develop

```bash
cd app
npm install
npm run dev      # http://localhost:5173

# optional, auto-digitize path — run in a SECOND terminal (npm run dev blocks):
cd ../digitizer && .venv/Scripts/python -m digitizer_service   # 127.0.0.1:8721
```

(First run: create the service venv per `../digitizer/README.md` — it needs the
`pip install -e ".[service,dev]"` step, not just Setup. On Windows,
`../tools/start-emb-bot.ps1` does all of it: venv, both servers, browser.)

`predev`/`prebuild` run `scripts/copy-engine.mjs`, which copies the engine
modules (in dependency order) into `public/engine/` and the satin-font library
(manifest, `.embf` binaries, license texts, previews) into `public/fonts/`.
The engine file list lives in THREE places that must stay in sync —
`ENGINE_FILES` in `scripts/copy-engine.mjs`, `ENGINE_KEYS` in
`src/lib/emb.js`, and the `<script>` tags in `index.html`.
`src/lib/engineList.spec.js` checks that the three agree, so a miss fails
`npm test`; add a new engine file to all three, in dependency order.

## Build (static)

How the product is delivered: since Kent's 2026-11-10 ruling it is one local
Windows app, where the digitizer service also serves the built Studio on one
loopback port; the hosted web Studio (PR #550) was reversed on 2026-09-28. See
`../PRODUCT.md` ("Launch posture") and launch row 8. The static-hosting notes
below describe what `dist/` is capable of, not the delivery plan.

```bash
npm run build    # -> app/dist/  (index.html + assets + engine/ + fonts/)
npm run preview  # serve the built dist locally to sanity-check
```

`dist/` is fully static and self-contained, with zero CDN runtime dependencies
(jsPDF is npm-bundled, Inter ships via `@fontsource-variable/inter`, fonts are
local `.embf`). Deploy by dropping `dist/` on any static host. Auto-digitizing
works only when the app itself is served from localhost — the service accepts
localhost origins only, so a hosted copy can't reach it.

## Deploy

- **Netlify / Vercel / Cloudflare Pages:** base directory `app`, build command
  `npm run build`, publish directory `dist`.
- **GitHub Pages:** font URLs are relative since 2ccca02c (guarded by
  `src/lib/assetPaths.spec.js`), but the engine `<script>` tags in
  `index.html` are still root-absolute (`/engine/…`), so a sub-path project
  page would still fail to load the engine. Use a root or custom-domain site.

## Structure

- `src/lib/` — plain-JS app logic, one concern per module (project model,
  wizard flow, stitch generation, the 2.5D renderer, exporters, the digitizer
  client, save/projects). Unit-tested with Vitest — `*.spec.js` files sit
  alongside the modules they cover.
- `src/App.svelte` + `src/ui/` — the Svelte layer: `App.svelte` owns state; the
  step screens and the panels they open (font browser, auto-digitize, manual
  trace, shapes, thread picker, projects drawer, …). `*.testHarness.svelte`
  files exist only for component tests.
- `e2e/` — Playwright suite: 82 spec files, 243 tests when CI last counted
  (2026-11-07): configurator smoke, the digitize / manual-trace /
  text-conversion contracts, field editing, download and project round trips.
  Runs in CI as the `studio-e2e` job (two shards).
- `scripts/copy-engine.mjs` — the engine copy step above.

## Test

```bash
npm test                          # Vitest (app logic + components)
npx playwright test --workers=1   # e2e (one worker: specs share one service)
```

`--workers=1` is the safe local default. CI is faster: it runs the service-free
specs on 4 workers and only the digitizer-service specs serially
(`.github/workflows/python-package-conda.yml`, `studio-e2e shard k/2`).

App test files use `.spec.js` so the repo-root `node --test` (engine gate)
never picks them up; the engine is guarded separately at the repo root.
The service-gated e2e specs reuse a digitizer that already answers `/health`,
otherwise start one themselves from `../digitizer/.venv` — and skip when
neither works.

Deep material — architecture, gotchas, current work-in-progress state — lives
in [`../COOKBOOK.md`](../COOKBOOK.md); the repo-level
[`../README.md`](../README.md) is the user-facing overview of the whole
project.
