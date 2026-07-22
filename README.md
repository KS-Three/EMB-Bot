# EMB Bot — Embroidery Digitizer

EMB Bot is a local, browser-based auto-digitizer and lettering tool. It turns a
logo/image or typed text into machine-embroidery stitch files, with a live
stitch preview, right in your browser — no install, no server, no account.

It runs as a single HTML page. There is no backend: image processing, color
quantization, contour tracing, stitch generation, and file encoding all happen
client-side in JavaScript.

## Quick start

Open one of these in a modern desktop browser (Chrome, Edge, Firefox):

- **`EMB-Bot.html`** — the development version. Loads its modules from the
  `src/` folder next to it, so keep the folder structure intact.
- **`EMB-Bot-standalone.html`** — a single portable file with every local
  module inlined. Copy just this one file anywhere and it still works.

Either way **you need an internet connection**, even though everything runs
locally: the page loads two libraries and (in Text mode) font data from a
CDN at runtime:

- [opentype.js](https://github.com/opentype/opentype.js) 1.3.4 — reads font
  outlines
- [jsPDF](https://github.com/parallax/jsPDF) 2.x — builds the PDF worksheet
- ~137 Google Fonts `.ttf` files, fetched on demand from a jsDelivr mirror
  when you pick a font in Text mode

If those fail to load (e.g. no internet), a banner at the top of the page
says so — the tool doesn't silently produce broken output.

### Image mode

1. Switch to **Image**.
2. Upload a logo (PNG/JPG/etc.). Optionally check **Remove background** to
   knock out a solid-colored backdrop.
3. Choose **Colors** (2–12), **Garment / placement**, **Output format**,
   **Fill density**, and whether to add an **Outline stitch**.
4. Click **Generate** to see the stitch simulation and stats (stitch count,
   color count, physical size).
5. Click **Download** for the stitch file, or **Export PDF** for a
   printable stitch-out worksheet (rendered preview, dimensions, stitch/color
   counts, and an ordered thread-color swatch list).

### Text mode

1. Switch to **Text**.
2. Type your text and pick a font from the ~137-font catalog (sans, serif,
   slab, script, mono, and display styles).
3. Choose garment, format, density, and outline as above, then **Generate**.

## Outputs

| Format | Machine | Notes |
|---|---|---|
| **.DST** | Tajima | **Primary / most reliable.** The encoder was built and checked against known-correct stitch/jump/color-change record encodings. Use this as your default. |
| **.EXP** | Melco | Solid, standard support. |
| **.PES** | Brother | **Best-effort.** Brother's format is proprietary and reverse-engineered here — always stitch out a test on your own machine/software before a production run. |
| **.PNG** | — | Flat preview image of the stitch simulation. |
| **.SVG** | — | Vector outline of the design (not a stitch file). |
| **PDF worksheet** | — | One-page (or more) printable sheet: rendered stitch preview, garment placement, dimensions, stitch/color counts, and a numbered thread-color sequence. |

Output format defaults to **DST**.

## Garment / placement sizes

Pick a placement and the design is automatically scaled (aspect preserved) to
fit inside its box. Sizes are defined in `src/garments.js`:

| Placement | Size (in) | Size (mm) |
|---|---|---|
| Hat Front | 5.0 × 2.25 | 127.0 × 57.2 |
| Left Chest | 4.0 × 4.0 | 101.6 × 101.6 |
| Full Back | 12.0 × 12.0 | 304.8 × 304.8 |
| Beanie | 4.5 × 2.5 | 114.3 × 63.5 |
| Sleeve | 3.0 × 3.0 | 76.2 × 76.2 |
| Tote | 8.0 × 8.0 | 203.2 × 203.2 |
| Jacket Back | 12.0 × 10.0 | 304.8 × 254.0 |
| Patch | 3.5 × 3.5 | 88.9 × 88.9 |
| Towel | 6.0 × 6.0 | 152.4 × 152.4 |
| Blanket | 10.0 × 8.0 | 254.0 × 203.2 |

If the fitted design is larger than a typical ~200 × 200 mm (~8 in) hoop, a
warning note appears above the stats telling you the exact size so you can
confirm your hoop/machine can take it.

## Honest limits

This is an **auto-digitizer for simple jobs**, not a replacement for
professional digitizing software:

- **Best for clean, flat-color logos.** A logo with a handful of solid
  colors and clear edges digitizes well.
- **Photos embroider poorly — that's inherent to the medium, not a bug.**
  Embroidery can't reproduce continuous-tone gradients the way a printer can;
  a photo will get reduced to a handful of flat color regions (like the rest
  of the pipeline) and will look like a poster, not a photograph. Simplify to
  a few flat colors before feeding in a photo, or expect a poster-ized
  result.
- **Lettering uses fill + outline, not true satin.** Text is digitized as a
  tatami fill with a running-stitch outline. That's robust and predictable
  across all three stitch formats, but it isn't the raised, glossy
  satin-column lettering a professional digitizer would hand-build for small
  or fine text.
- **PES is best-effort.** See the Outputs table above — verify before you
  run a job on it.
- **For anything commercial or high-stakes, check the output in real
  digitizing software** (e.g. Wilcom, Hatch) before you stitch it. This tool
  is built for quick, simple jobs and prototypes, not to replace a
  professional digitizer's judgment on a complex or critical design.

## Files & architecture

- **`EMB-Bot.html`** — the app shell (markup, styles, CDN `<script>` tags)
  plus fourteen `<script src="src/...">` tags loaded in dependency order.
- **`src/*.js`** — the individual modules (units, garments, geometry,
  quantize, fill/outline stitch engine, DST/EXP/PES encoders, SVG export,
  stitch-model assembly, font catalog, canvas renderer, PDF worksheet
  builder, and `app.js` wiring it all to the DOM). Each module is written to
  work both as a classic browser `<script>` (attaching to a global `EMB`
  object) and as a CommonJS module (for the Node test suite).
- **`EMB-Bot-standalone.html`** — a single-file portable build with every
  local `src/*.js` module inlined verbatim. Generated by
  `tools/bundle.mjs`; the two CDN `<script>` tags are left as remote
  references (this file still needs internet access, just not the `src/`
  folder). Regenerate it after any change under `src/` or to `EMB-Bot.html`:

  ```
  node tools/bundle.mjs
  ```

- **`tools/check-fonts.mjs`** — a maintenance script that pings every font
  URL in `src/fonts.js` to confirm it still resolves; useful if the upstream
  Google Fonts mirror ever renames or drops a file.
- **`test/*.test.js`** — unit tests for every module that doesn't require a
  browser DOM (encoders, geometry, fill, quantization, garments, units,
  stitch-model assembly). Run with:

  ```
  node --test
  ```
