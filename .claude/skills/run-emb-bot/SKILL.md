---
name: run-emb-bot
description: Launch, build, and test EMB-Bot — the Svelte Studio app, the standalone HTML bundle, the JS stitch engine's Node test harness, and the Python digitizer service. Use when asked to run, start, build, verify, or test EMB-Bot, or after changing src/, app/, tools/, or digitizer/.
---

# Running EMB-Bot

EMB-Bot has two independent stacks: a browser-side JS stitch engine (primary
product, no backend) and an optional Python digitizer service. Pick the
section for what changed.

## Studio app (primary product — `app/`)

Svelte + Vite. This is what most feature work touches.

```
cd app
npm install        # first time only
npm run dev         # http://localhost:5173
```

- `npm run build` — production build (also runs `predev`/`prebuild`'s
  `node scripts/copy-engine.mjs` automatically, which syncs the engine from
  `src/` into the app).
- `npm run test` — Vitest (`vitest run`).
- `npm run preview` — serve the production build locally.

If you changed anything under `src/`, the Studio picks it up via
`copy-engine.mjs` on its own `predev`/`prebuild` hook — no manual step needed
for the app itself. The manual step below is only for the *standalone* file.

## Verifying a UI change live (Playwright MCP)

With `npm run dev` running, the `playwright` MCP server (declared in
`.mcp.json`, launched via `tools/mcp-playwright.mjs`) can drive a real
headless browser against `http://localhost:5173` — navigate the wizard,
click through garment/font pickers, and take snapshots/screenshots to
confirm a change actually works, not just that tests pass. Prefer this over
claiming a frontend change works from reading the diff alone.

## Standalone bundle — rebuild after any `src/` or `EMB-Bot.html` change

`EMB-Bot-standalone.html` is a committed, inlined artifact — it is **not**
regenerated automatically. Anyone testing the standalone file (or the plain
`EMB-Bot.html` + `src/` combo) after an engine change is looking at stale
code until this runs:

```
node tools/bundle.mjs
```

## JS engine tests — no browser needed

`src/*.js` modules double as CommonJS for Node tests (`test/*.test.js`,
covers every non-DOM module):

```
node --test
```

To exercise the digitizing pipeline itself against a real image without a
browser, use the Node-side harness in `tools/`:

- `tools/run-digitize.mjs` — run the full digitize pipeline on an image
- `tools/run-flatten.mjs` — run just the color-flatten step
- `tools/render-dst.mjs` — render a `.DST` file to PNG for visual inspection
- `tools/png.mjs` — PNG decode/encode helper used by the above

These exist specifically because the browser tool available in agent
sessions can't do file uploads — this is the way to test digitizing on a
real image in this environment.

## Font library

Rebuild after tier/source changes to the satin font library (needs
`scratch_ink/` — see COOKBOOK.md for how to obtain it):

```
node tools/build-embf.mjs
```

`tools/check-fonts.mjs` does a font-URL health check (CDN-fetched Google
Fonts used by the older eager 21-font registry, not the Studio's library).

## Python digitizer (`digitizer/`)

Independent Python package + optional FastAPI service. Own venv, own tests,
own docs (`digitizer/README.md`, `digitizer/docs/`).

**This environment is Linux** — use `.venv/bin/python`, not the
`.venv/Scripts/python` path shown in `digitizer/README.md` (that's the
Windows form; swap `Scripts` for `bin` and drop the `.exe` throughout).

Setup:

```
cd digitizer
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the test suite (127 tests, all offline):

```
.venv/bin/python -m pytest -q
```

Run via `python -m pytest`, not a bare `pytest` — this puts the working
directory on `sys.path` so `digitizer_core` imports without a separate
install step.

Run the service (adds `service` extra):

```
.venv/bin/python -m pip install -e ".[service,dev]"
.venv/bin/python -m digitizer_service          # binds 127.0.0.1:8721
```

Regenerate thread charts after changing `tools/palettes/*.gpl`:

```
.venv/bin/python tools/gen_charts.py
```

Regenerate the synthetic test fixtures in `testdata/`:

```
.venv/bin/python tools/make_test_logo.py
```

## Which stack to touch

- UI, garment/fabric options, Studio flow, font browsing → `app/` (Studio).
- Stitch engine internals (fill, satin, DST/EXP/PES encoding), used by both
  the browser and `node --test` → `src/`.
- Server-side auto-digitizing quality (segmentation, region forming, stitch
  planning quality) → `digitizer/digitizer_core`.
- HTTP API for the digitizer → `digitizer/digitizer_service`.

Cross-stack conventions that must stay in sync (see `digitizer/README.md`
"Conventions" table for the full list): fabric presets mirror `src/fabrics.js`
exactly; thread brand ids match `app/src/lib/threadBrandsIndex.js` exactly.
Changing one without the other silently breaks the match.

## DST codec — do not use as a correctness reference

EMB-Bot's own DST encoder/decoder (`src/dst.js` / `src/dstimport.js`) is
transposed vs. the Tajima/pyembroidery standard (confirmed, unresolved — see
CLAUDE.md and `digitizer/README.md`'s "Open finding" section). It round-trips
correctly with itself but reads wrong-orientation in third-party software.
When verifying DST output for correctness (not just round-tripping), decode
through pyembroidery (`digitizer/`'s dependency), never through
`src/dstimport.js`.
