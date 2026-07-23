# EMB Bot — Embroidery Digitizer

EMB Bot is a local, browser-based auto-digitizer and lettering tool. It turns a
logo/image or typed text into machine-embroidery stitch files, with a live
stitch preview, right in your browser — no install, no server, no account.

It runs as a single HTML page. There is no backend: image processing, color
flattening, contour tracing, stitch generation, and file encoding all happen
client-side in JavaScript.

## Quick start

Open one of these in a modern desktop browser (Chrome, Edge, Firefox):

- **`EMB-Bot.html`** — the development version. Loads its modules from the
  `src/` folder next to it, so keep the folder structure intact.
- **`EMB-Bot-standalone.html`** — a single portable file with every local
  module inlined. Copy just this one file anywhere and it still works.

Either way **you need an internet connection**, even though everything runs
locally: the page loads two libraries and (in Text mode) font data from a
CDN at runtime — opentype.js 1.3.4 (font outlines), jsPDF 2.x (PDF worksheet),
and ~137 Google Fonts fetched on demand. A banner warns you if they fail to
load, so the tool never silently produces broken output.

## Image mode — the flatten-first workflow

Embroidery thread is flat, solid color, so the first real step (the one a human
digitizer does by hand) is collapsing your art down to a handful of thread
colors. EMB Bot makes that step **visible and controllable**:

1. Switch to **Image** and upload a logo (PNG/JPG; PNG transparency is honored).
   Optionally check **Remove background**.
2. The **Flattened art** panel shows your image reduced to N colors (the
   **Colors** slider, 2–12) with cleanup — stray specks are absorbed into their
   surrounding color and ragged edges smoothed. This preview is exactly what
   will stitch.
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

Switch to **Text**, type your text, pick a font from the ~137-font catalog, set
garment/fabric/format/density, and **Generate**. Thin strokes are stitched as
satin columns; broader letter bodies as fills.

## What the stitch engine does

- **Hole-aware tracing** — rings and letter counters (O, A, D, e, o…) stitch as
  true rings, not filled discs.
- **Satin vs. fill** — genuinely thin shapes (≤ ~3 mm at final size) get satin
  columns; broader shapes get tatami fill.
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
- **Lettering is fill/satin by shape, not per-stroke satin.** Whole letters
  fill (hole-aware); only genuinely thin strokes satin. A professional would
  hand-build satin per stroke on fine text.
- **PES is best-effort; fabric presets are starting points.** Verify both on
  your machine.
- **For commercial/high-stakes work, check the file in real digitizing
  software** (Wilcom, Hatch) before stitching.

## Files & architecture

- **`EMB-Bot.html`** — app shell (markup, styles, CDN `<script>` tags) plus the
  `src/*.js` modules loaded in dependency order, `app.js` last.
- **`src/*.js`** — modules, each usable as a browser `<script>` (attaching to a
  global `EMB`) and as a CommonJS module (Node tests):
  units, garments, **fabrics**, fill/satin stitch engines, geometry
  (hole-aware `traceRegions`), quantize, **flatten** (mode filter / small-region
  absorb / manual merge), **digitize** (the quality orchestrator: satin/fill
  classification, per-shape angle, underlay, pull comp, trims, sequencing),
  DST/EXP/PES encoders, SVG export, stitch-model, font catalog, canvas renderer,
  PDF worksheet, and `app.js`.
- **`EMB-Bot-standalone.html`** — single-file portable build (inline `src/*.js`,
  CDN tags left remote). Regenerate after any `src/` or `EMB-Bot.html` change:

  ```
  node tools/bundle.mjs
  ```

- **`tools/`** — `bundle.mjs` (standalone builder), `check-fonts.mjs` (font-URL
  health check), `png.mjs` + `render-dst.mjs` + `run-flatten.mjs` /
  `run-digitize.mjs` (Node-side decode/render/pipeline harness for testing
  digitizing on real images without a browser).
- **`docs/superpowers/specs/`** — design specs, including the pro-stitch roadmap
  (trims/sequencing ✓, fabric presets ✓, angles ✓, sequencing polish).
- **`test/*.test.js`** — unit tests for every non-DOM module. Run:

  ```
  node --test
  ```
