# EMB Bot Studio

A browser-only, beginner-first embroidery tool (21 satin fonts, quick-start templates, letter spacing, printable PDF worksheet, MULTI-ELEMENT designs): pick what you're making → add
**text** (pre-digitized satin fonts) or a **logo/image** (auto-flattened to
thread colors, with swatch merging) → watch the realistic 2.5D field render
live → download a stitch file. No accounts, no server.

Sizing: the field shows the real hoop/garment area — drag the design's corner handles to resize (stitches truly regenerate at each size, so density stays correct), drag the body to reposition, or use the Size panel (W/H, inches or mm, Auto-fit). Below ~5 mm the app warns that thread can't stitch that small.

Multi-element: a design can hold several elements (text lines and images) — add via "+ Text"/"+ Image", click to select on the field or in the list, move/resize each independently; elements sew in list order with a trim + color change between them. Image swatches each get a THREAD color picker (art stays the same, the thread color changes).

Image mode notes: art is flattened to 2–8 thread colors (median-cut + smoothing,
optional background removal); chips show each color's share and can be merged.
Clean, flat-color art stitches best — photos with gradients won't stitch cleanly,
and the UI says so.

It reuses the proven stitch engine in the repo's `../src` (satin fonts,
underpathing, exporters) — that engine is the source of truth and is **not**
modified by this app. The engine is loaded via `<script>` tags in `index.html`
and read from `window.EMB`.

## Develop

```bash
cd app
npm install
npm run dev      # http://localhost:5173
```

`predev`/`prebuild` run `scripts/copy-engine.mjs`, which copies the engine
modules (in dependency order) and the satin-font library from `../src` into
`public/engine/` so the browser can load them.

## Build (static)

```bash
npm run build    # -> app/dist/  (index.html + assets + engine/)
npm run preview  # serve the built dist locally to sanity-check
```

`dist/` is fully static and self-contained (except the CDN libs the image/PDF
paths use; the text path works offline). Deploy by dropping `dist/` on any static
host.

## Deploy

- **Netlify / Vercel / Cloudflare Pages:** build command `npm run build`,
  publish directory `app/dist`.
- **GitHub Pages:** publish `app/dist` (Vite `base` is `"./"`, so it works from a
  sub-path).

## Structure

- `src/lib/` — logic (all unit-tested with Vitest, `*.spec.js`):
  - `emb.js` — engine accessor (`window.EMB`)
  - `project.js` — the project model; `flow.js` — guided-step state machine
  - `generate.js` — project → `EMB.buildLetteringDesign` → design
  - `strands.js` + `preview.js` — the 2.5D `renderRealistic` thread renderer
  - `exporters.js` + `download.js` — DST/EXP/PES/SVG export + browser download
  - `save.js` — localStorage project save/round-trip
- `src/ui/` — Svelte components: `App.svelte` (owns state) + the 4 step
  components + `StepNav`, `FontGallery`, `theme.css`.

## Test

```bash
npm test                 # Vitest (app logic)
# engine is guarded separately at the repo root: `node --test`
```

App test files use `.spec.js` so the repo-root `node --test` (engine gate) never
picks them up.
