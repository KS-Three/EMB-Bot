# EMB Bot — Embroidery Digitizer

EMB Bot is a local, browser-based auto-digitizer and lettering tool. It turns a
logo/image or typed text into machine-embroidery stitch files, with a live
stitch preview — no account, no subscription, everything running on your own
machine.

The product is **EMB Bot Studio** (the `app/` folder): a guided Svelte app
(garment → content → review → download). Stitch math and file encoding are
hand-written JavaScript (`src/`); a Python auto-digitizing engine
(`digitizer/`) runs behind an optional localhost service for the image
auto-digitize path — see `digitizer/README.md`.

## Quick start

The Studio has a live stitch preview, multi-element designs, saved projects,
and a **55-font pre-digitized satin library** loaded on demand. Fonts are
picked in a searchable browser (search box, Sans/Serif/Script/Display/Small
filters, per-font recommended size ranges) whose grid uses pre-rendered
preview images — browsing never downloads font data; only picking a font
does. A "Font credits" screen lists every font's license and attribution,
generated from the library manifest:

```
cd app
npm install   # first time only
npm run dev   # then open http://localhost:5173
```

The Studio has **no CDN runtime dependencies**: jsPDF is bundled from npm,
Inter comes via fontsource, and the satin fonts ship locally as `.embf`
binaries. Nothing is fetched from Google Fonts or any other third-party host
at runtime.

## Image mode — the flatten-first workflow

Embroidery thread is flat, solid color, so the first real step (the one a human
digitizer does by hand) is collapsing your art down to a handful of thread
colors. EMB Bot makes that step **visible and controllable**:

1. Switch to **Image** and upload a logo (PNG/JPG; PNG transparency is honored).
   Optionally check **Remove background**.
2. The **Flattened art** panel shows your image reduced to N colors (the
   **Colors** slider, 2–8; the auto-digitizer's own Colors control goes to 12)
   with cleanup — stray specks are absorbed into their surrounding color and
   ragged edges smoothed. This preview is exactly what will stitch.
3. Use the **swatch bar** to fix the merge: click the swatches that should be
   one thread (e.g. three near-identical grays), then **Merge selected**.
   **Reset colors** returns to the automatic result. Each swatch also has an
   **angle** field (blank = auto) to force that color's stitch direction.
4. **Download flat PNG** exports the flattened art at full resolution
   (transparent background preserved) — useful on its own for prepping art.
5. Pick **Garment / placement**, **Fabric** (auto-set by the garment; override
   if needed), **Output format**, **Fill density**, and **Outline** / 
   **Underlay** toggles.
6. **Generate** to see the stitch simulation and stats, then **Download** the
   stitch file or **Export PDF** for a printable worksheet.

## Text mode

Switch to **Text**, type your text, pick a font from the 55-font pre-digitized
satin library, set garment/fabric/format/density, and **Generate**. Library
fonts sew as hand-authored satin columns (adapted from the Ink/Stitch open
embroidery font collection), not auto-traced outlines.

## What the stitch engine does

- **Hole-aware tracing** — rings and letter counters (O, A, D, e, o…) stitch as
  true rings, not filled discs.
- **Satin vs. fill** — genuinely thin shapes get satin columns; broader shapes
  get tatami fill. The cut-off at final size is **~5 mm** through the
  auto-digitizer and **~3 mm** through the browser engine, which is what text and
  hand-drawn shapes use.
- **Per-shape stitch angle** — each element's fill follows its own axis for
  sheen and dimension; override per color in the swatch bar.
- **Underlay** — foundation stitching under fills/satin (edge-run, lattice,
  double-lattice, center-run, or zigzag), chosen by the fabric preset.
- **Pull compensation** — fills and satin are grown slightly so they sew to
  true size after the fabric distorts; amount comes from the fabric preset.
- **Trims & sequencing** — real trim commands (so thread isn't dragged across
  the design), nearest-neighbor shape ordering to shorten travel, color order
  light→dark, and **center-out** sewing on caps for crown-distortion control.

### Fabric presets

The **Fabric** dropdown drives pull compensation, underlay style, density, and
trim distance. Each garment auto-selects a sensible default (hat → structured
cap, polo → pique knit, sweatshirt → fleece, towel → terry, etc.); you can
override it. Presets are starting points — **stitch a test on your machine and
tell me if a fabric needs tuning**, and the preset gets adjusted. Defined in
`src/fabrics.js`.

## Outputs

| Format | Machine | Notes |
|---|---|---|
| **.DST** | Tajima | **Primary / most reliable.** Built and tested against known-correct stitch/jump/color/trim record encodings. Default. |
| **.EXP** | Melco | Solid, standard support (incl. trim control). |
| **.PES** | Brother | **Best-effort** — reverse-engineered; always test-stitch before a production run. |
| **.PNG** | — | Flat preview image of the stitch simulation. |
| **.SVG** | — | Vector outline of the design (not a stitch file). |
| **PDF worksheet** | — | Printable sheet: preview, placement, dimensions, stitch/color counts, numbered thread-color sequence. |

## Garment / placement sizes

Design is scaled (aspect preserved) to fit the chosen placement box. Sizes in
`src/garments.js`: Hat Front 5.0×2.25, Left Chest 4.0×4.0, Full Back 12×12,
Beanie 4.5×2.5, Sleeve 3×3, Tote 8×8, Jacket Back 12×10, Patch 3.5×3.5, Towel
6×6, Blanket 10×8 (inches). A note warns if the fitted design exceeds a typical
~200 mm hoop.

## Honest limits

This is a strong auto-digitizer **for clean, flat-color art** — not a
replacement for a professional digitizer's judgment on complex or critical work.

- **Feed it flat art.** Solid colors and clear edges digitize well. Photos and
  gradients are inherent to the *medium's* limits — thread can't do
  continuous tone. The flatten step reduces them to poster-like color blocks;
  simplify heavily (or provide vector/spot-color art) for a good result.
- **Size matters.** Small stacked text (below ~4 mm cap height, common when a
  busy logo is shrunk to a hat) falls below what thread can hold and breaks up.
  Size the text up relative to the artwork, or drop the smallest lines.
- **Lettering inside images is fill/satin by shape, not per-stroke satin.**
  Whole letters fill (hole-aware); only genuinely thin strokes satin. A
  professional would hand-build satin per stroke on fine text. (Typed text
  from the font library doesn't have this limit — those letters *are*
  hand-built satin columns.)
- **PES is best-effort; fabric presets are starting points.** Verify both on
  your machine.
- **For commercial/high-stakes work, check the file in real digitizing
  software** (Wilcom, Hatch) before stitching.

## Files & architecture

- **`app/`** — EMB Bot Studio, the Svelte 5 + Vite product: `App.svelte` +
  `ui/` (wizard steps/components) + `lib/` (non-DOM logic, each module
  paired with a spec file). Loads the engine via `<script>` tags
  (`app/index.html`) as the global `EMB`.
- **`src/*.js`** — engine modules, each usable as a browser `<script>`
  (attaching to a global `EMB`) and as a CommonJS module (Node tests):
  units, garments, **fabrics**, fill/satin stitch engines, geometry
  (hole-aware `traceRegions`), quantize, **flatten** (mode filter / small-region
  absorb / manual merge), **digitize** (the quality orchestrator: satin/fill
  classification, per-shape angle, underlay, pull comp, trims, sequencing),
  DST/EXP/PES encoders, SVG export, stitch-model, canvas renderer, and the
  PDF worksheet.
- **`digitizer/`** — Python auto-digitizing engine (`digitizer_core/`) +
  optional FastAPI service (`digitizer_service/`, loopback-only) for the
  image auto-digitize path. Own venv, own tests, own README.
- **`src/fonts/`** — the satin font library. `manifest.json` (per-font
  metadata: tier, group, license id, glyph count) + `bin/*.embf`, a compact
  binary format (quantize ×4 → per-ring delta → Int16; decoder in
  `src/fontbin.js`) + per-font `.LICENSE.txt` sidecars, which ship with the
  built app. The Studio fetches the manifest at boot and each font's
  binary on first use. Rebuild after tier/source changes:
  `node tools/build-embf.mjs` (needs `scratch_ink/` — see COOKBOOK).
  Only fonts classified **verified** ship; see the tier rules in COOKBOOK.md.
- **`tools/`** — see the directory itself: the build/QC/harness scripts (plus
  `palettes/` thread-brand charts and `font-categories.json`). Highlights:
  `build-embf.mjs` (font library rebuild), `qc-font.mjs` (font tier gate),
  `png.mjs` + `render-dst.mjs` + `run-flatten.mjs` / `run-digitize.mjs`
  (Node-side decode/render/pipeline harness for testing digitizing on real
  images without a browser).
- **`docs/superpowers/specs/`** — design specs, including the pro-stitch roadmap
  (trims/sequencing ✓, fabric presets ✓, angles ✓, sequencing polish).
- **`test/*.test.js`** — unit tests for every non-DOM engine module
  (`node --test`); the Studio's own suite runs with `cd app && npm test`.
