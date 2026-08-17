# EMB Bot Studio

A beginner-first embroidery design studio (Svelte 5 + Vite). Pick what you're
making, then build the design from elements — **text** in pre-digitized satin
fonts, a **logo/image** (auto-digitized when the local service is up, else
flattened to thread colors by the browser engine — decided when the element is
added), traced or preset **shapes**, or an imported stitch file — arranged on a
realistic 2.5D thread preview, then download machine-ready files (DST / EXP /
PES, plus SVG, PNG, and a printable PDF worksheet). Guided steps: garment →
content → create → download. Elements sew in list order with a trim + color
change between them. Resizing regenerates text/shape/image stitches so density
stays correct; imported and auto-digitized elements scale their baked stitches
instead — density changes with size, and their panels say so.

Local-first, no accounts, no cloud: designs live in the browser (a
localStorage-backed projects drawer) and as portable `.embproj` files
(`src/lib/projectFile.js`). The one server is the **optional local digitizer
service** — the Python pipeline in `../digitizer`, served by FastAPI on
`127.0.0.1:8721`, loopback-only. The Studio runs without it, but the image
auto-digitize path needs it, and purely-digitized projects prefer its
pystitch `/export` for stitch files (the browser's own DST encoder has a
known axis dispute with third-party software — see `../COOKBOOK.md`).

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
`src/lib/emb.js`, and the `<script>` tags in `index.html`. No test guards
this; miss one and fonts break only in the live browser while tests stay
green.

## Build (static)

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
- **GitHub Pages:** root/custom-domain sites only — Vite `base` is `"./"`, but
  fonts are fetched root-absolute (`/fonts/…`), so a sub-path project page
  breaks every font.

## Structure

- `src/lib/` — plain-JS app logic, one concern per module (project model,
  wizard flow, stitch generation, the 2.5D renderer, exporters, the digitizer
  client, save/projects). Unit-tested with Vitest — `*.spec.js` files sit
  alongside the modules they cover.
- `src/App.svelte` + `src/ui/` — the Svelte layer: `App.svelte` owns state; the
  step screens and the panels they open (font browser, auto-digitize, manual
  trace, shapes, thread picker, projects drawer, …). `*.testHarness.svelte`
  files exist only for component tests.
- `e2e/` — Playwright suite: wizard smoke plus the digitize / manual-trace /
  text-conversion contracts. Runs in CI as the `studio-e2e` job.
- `scripts/copy-engine.mjs` — the engine copy step above.

## Test

```bash
npm test                          # Vitest (app logic + components)
npx playwright test --workers=1   # e2e (one worker: specs share one service)
```

App test files use `.spec.js` so the repo-root `node --test` (engine gate)
never picks them up; the engine is guarded separately at the repo root.
The service-gated e2e specs reuse a digitizer that already answers `/health`,
otherwise start one themselves from `../digitizer/.venv` — and skip when
neither works.

Deep material — architecture, gotchas, current work-in-progress state — lives
in [`../COOKBOOK.md`](../COOKBOOK.md); the repo-level
[`../README.md`](../README.md) is the user-facing overview of the whole
project.
