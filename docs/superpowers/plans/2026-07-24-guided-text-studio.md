# Guided Text Studio (Slice 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a browser-only, beginner-first guided web app that turns typed text into a clean, downloadable embroidery file, with a realistic 2.5D preview — reusing the existing stitch engine unchanged.

**Architecture:** A Svelte + Vite static app in `app/`. The proven engine (`src/*.js`, dual-mode IIFEs that populate a global `EMB`) is loaded via `<script>` tags in `index.html` (copied into the build), and the app reads `window.EMB`. A 5-step guided flow drives a plain **project model**; generating calls `EMB.buildLetteringDesign`; the resulting stitch list feeds BOTH a new Canvas-2D 2.5D preview and the existing exporters. Projects save to `localStorage`.

**Tech Stack:** Svelte 4 + Vite 5, Vitest for app-logic tests, the existing zero-dependency engine JS, Canvas 2D. No backend.

## Global Constraints

- **Browser-only.** No server, no accounts, no network calls at runtime except the CDN libs the engine already needs (opentype.js, jsPDF) which are only used by the image/PDF paths — text path must work fully offline.
- **Engine is untouched source of truth.** Do NOT edit `src/*.js` for app reasons; the repo-root `node --test` suite (139 tests) must stay green. App code lives only under `app/`.
- **Reuse, don't reimplement.** Stitch generation, garments, fabrics, fonts, and exporters come from `EMB.*`. The app never re-derives stitches.
- **Deploys as static files.** `npm run build` (in `app/`) must produce a `dist/` that runs by opening `index.html` from a static host (GitHub Pages / Netlify).
- **Fonts:** the 14 satin fonts already in `src/fonts/satin-fonts.js` (registers `EMB.SATIN_FONTS`).
- **Default export format:** DST. Also offer EXP, PES, PNG, SVG, PDF (all already in `EMB`).

---

### Task 1: Scaffold the Svelte+Vite app and load the engine

**Files:**
- Create: `app/package.json`, `app/vite.config.js`, `app/index.html`, `app/src/main.js`, `app/src/App.svelte`
- Create: `app/src/lib/emb.js` (engine accessor)
- Create: `app/scripts/copy-engine.mjs` (copies engine JS into `app/public/engine/`)
- Test: `app/src/lib/emb.test.js`

**Interfaces:**
- Produces: `import { EMB, ENGINE_KEYS } from './lib/emb.js'` — `EMB` is the loaded engine global (throws a clear error if not loaded); `ENGINE_KEYS` is the ordered list of engine script filenames (used by the copy script and index.html).

- [ ] **Step 1: Create `app/package.json`**

```json
{
  "name": "emb-bot-studio",
  "private": true,
  "type": "module",
  "scripts": {
    "predev": "node scripts/copy-engine.mjs",
    "dev": "vite",
    "prebuild": "node scripts/copy-engine.mjs",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^3.1.0",
    "svelte": "^4.2.0",
    "vite": "^5.2.0",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 2: Create `app/scripts/copy-engine.mjs`** — copies the engine modules (in dependency order) + the font registry into `app/public/engine/`, so `index.html` can `<script src>` them and `vite build` includes them.

```js
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const srcDir = join(here, "..", "..", "src");
const outDir = join(here, "..", "public", "engine");
// Dependency order MUST match EMB-Bot.html.
export const ENGINE_FILES = [
  "units.js", "garments.js", "fabrics.js", "fill.js", "geometry.js",
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "satinfont.js",
  "dst.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "fonts.js", "digitize.js", "render.js", "pdfsheet.js",
  "fonts/satin-fonts.js",
];
mkdirSync(join(outDir, "fonts"), { recursive: true });
for (const f of ENGINE_FILES) {
  const from = join(srcDir, f);
  if (!existsSync(from)) throw new Error("missing engine file: " + f);
  copyFileSync(from, join(outDir, f));
}
console.log("copied", ENGINE_FILES.length, "engine files to", outDir);
```

- [ ] **Step 3: Create `app/index.html`** — loads engine scripts (order matters) before the app.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>EMB Bot Studio</title>
    <script src="/engine/units.js"></script>
    <script src="/engine/garments.js"></script>
    <script src="/engine/fabrics.js"></script>
    <script src="/engine/fill.js"></script>
    <script src="/engine/geometry.js"></script>
    <script src="/engine/quantize.js"></script>
    <script src="/engine/flatten.js"></script>
    <script src="/engine/satin.js"></script>
    <script src="/engine/satinplay.js"></script>
    <script src="/engine/satinfont.js"></script>
    <script src="/engine/dst.js"></script>
    <script src="/engine/exp.js"></script>
    <script src="/engine/pes.js"></script>
    <script src="/engine/svgexport.js"></script>
    <script src="/engine/stitchModel.js"></script>
    <script src="/engine/fonts.js"></script>
    <script src="/engine/digitize.js"></script>
    <script src="/engine/render.js"></script>
    <script src="/engine/pdfsheet.js"></script>
    <script src="/engine/fonts/satin-fonts.js"></script>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `app/vite.config.js`**

```js
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
export default defineConfig({ plugins: [svelte()], base: "./" });
```

- [ ] **Step 5: Create `app/src/lib/emb.js`**

```js
// Access the engine global loaded by the <script> tags in index.html.
// The engine modules (dual-mode IIFEs) assign onto globalThis.EMB.
const g = typeof window !== "undefined" ? window : globalThis;
if (!g.EMB || typeof g.EMB.buildLetteringDesign !== "function") {
  throw new Error("Engine not loaded — check the <script src=\"/engine/...\"> tags in index.html and that scripts/copy-engine.mjs ran.");
}
export const EMB = g.EMB;
```

- [ ] **Step 6: Create `app/src/App.svelte`** (placeholder that proves engine access)

```svelte
<script>
  import { EMB } from "./lib/emb.js";
  const fontCount = Object.keys(EMB.SATIN_FONTS || {}).length;
</script>
<main><h1>EMB Bot Studio</h1><p>Engine loaded · {fontCount} satin fonts</p></main>
```

- [ ] **Step 7: Create `app/src/main.js`**

```js
import App from "./App.svelte";
const app = new App({ target: document.getElementById("app") });
export default app;
```

- [ ] **Step 8: Write the failing test `app/src/lib/emb.test.js`** — loads the engine the way tests can (require the CJS modules, which populate `globalThis.EMB`) and asserts the accessor exposes the API.

```js
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // load engine (order matters) — these populate globalThis.EMB
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});
test("emb accessor exposes buildLetteringDesign + satin fonts", async () => {
  const { EMB } = await import("./emb.js");
  expect(typeof EMB.buildLetteringDesign).toBe("function");
  expect(Object.keys(EMB.SATIN_FONTS).length).toBeGreaterThanOrEqual(14);
});
```

- [ ] **Step 9: Install and run** — `cd app && npm install`. Run `npm test`. Expected: PASS. Then `npm run dev` and confirm the page shows "Engine loaded · 14 satin fonts".

- [ ] **Step 10: Commit**

```bash
git add app/ && git commit -m "feat(app): scaffold Svelte+Vite studio, load engine via window.EMB"
```

---

### Task 2: Project model

**Files:**
- Create: `app/src/lib/project.js`
- Test: `app/src/lib/project.test.js`

**Interfaces:**
- Produces:
  - `defaultProject() → { garmentId:string, text:string, fontKey:string, sizeMm:number|null, colorRgb:[number,number,number], underlay:boolean }`
  - `update(project, patch) → project` (returns a new object; never mutates)

- [ ] **Step 1: Write the failing test**

```js
import { test, expect } from "vitest";
import { defaultProject, update } from "./project.js";
test("defaultProject has sane beginner defaults", () => {
  const p = defaultProject();
  expect(p.garmentId).toBe("left_chest");
  expect(p.text).toBe("");
  expect(p.fontKey).toBe("geneva_simple");
  expect(p.colorRgb).toEqual([20, 20, 20]);
  expect(p.underlay).toBe(true);
});
test("update returns a new object and merges", () => {
  const p = defaultProject();
  const q = update(p, { text: "Kent" });
  expect(q.text).toBe("Kent");
  expect(p.text).toBe(""); // original untouched
});
```

- [ ] **Step 2: Run test to verify it fails** — `cd app && npx vitest run src/lib/project.test.js`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement `app/src/lib/project.js`**

```js
export function defaultProject() {
  return { garmentId: "left_chest", text: "", fontKey: "geneva_simple", sizeMm: null, colorRgb: [20, 20, 20], underlay: true };
}
export function update(project, patch) {
  return { ...project, ...patch };
}
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS.
- [ ] **Step 5: Commit** — `git add app/src/lib/project.* && git commit -m "feat(app): project model"`

---

### Task 3: Guided flow state machine

**Files:**
- Create: `app/src/lib/flow.js`
- Test: `app/src/lib/flow.test.js`

**Interfaces:**
- Produces:
  - `STEPS = ["garment","text","preview","download"]`
  - `canAdvance(step, project) → boolean` (e.g. "text" requires non-empty text and a known font)
  - `nextStep(step) → step|null`, `prevStep(step) → step|null`

- [ ] **Step 1: Write the failing test**

```js
import { test, expect } from "vitest";
import { STEPS, canAdvance, nextStep, prevStep } from "./flow.js";
import { defaultProject, update } from "./project.js";
test("steps order", () => { expect(STEPS).toEqual(["garment","text","preview","download"]); });
test("text step blocks empty text", () => {
  const p = defaultProject();
  expect(canAdvance("text", p)).toBe(false);
  expect(canAdvance("text", update(p, { text: "Hi" }))).toBe(true);
});
test("nav", () => {
  expect(nextStep("garment")).toBe("text");
  expect(prevStep("text")).toBe("garment");
  expect(nextStep("download")).toBe(null);
});
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL.
- [ ] **Step 3: Implement `app/src/lib/flow.js`**

```js
export const STEPS = ["garment", "text", "preview", "download"];
export function canAdvance(step, project) {
  if (step === "garment") return !!project.garmentId;
  if (step === "text") return project.text.trim().length > 0 && !!project.fontKey;
  return true;
}
export function nextStep(step) { const i = STEPS.indexOf(step); return i >= 0 && i < STEPS.length - 1 ? STEPS[i + 1] : null; }
export function prevStep(step) { const i = STEPS.indexOf(step); return i > 0 ? STEPS[i - 1] : null; }
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS.
- [ ] **Step 5: Commit** — `git add app/src/lib/flow.* && git commit -m "feat(app): guided flow state machine"`

---

### Task 4: Generate adapter (project → design)

**Files:**
- Create: `app/src/lib/generate.js`
- Test: `app/src/lib/generate.test.js`

**Interfaces:**
- Consumes: `EMB.buildLetteringDesign`, `EMB.getGarment`, `EMB.SATIN_FONTS` (from Task 1).
- Produces: `generateDesign(project) → design` where `design = { stitches, colors, widthMM, heightMM, stitchCount, colorCount, _debug }` (exactly what `buildLetteringDesign` returns). Throws `Error("No characters…")` if the design has zero stitches.

- [ ] **Step 1: Write the failing test** (reuses the engine-loading pattern from Task 1's test)

```js
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});
test("generateDesign produces stitches for text", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  const d = generateDesign(update(defaultProject(), { text: "AB", fontKey: "geneva_simple" }));
  expect(d.stitchCount).toBeGreaterThan(50);
  expect(d.widthMM).toBeGreaterThan(0);
});
test("empty text throws", async () => {
  const { generateDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  expect(() => generateDesign(defaultProject())).toThrow();
});
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL.
- [ ] **Step 3: Implement `app/src/lib/generate.js`**

```js
import { EMB } from "./emb.js";
export function generateDesign(project) {
  const text = (project.text || "").trim();
  if (!text) throw new Error("Type some text first.");
  const fontData = (EMB.SATIN_FONTS || {})[project.fontKey];
  if (!fontData) throw new Error("Unknown font: " + project.fontKey);
  const garment = EMB.getGarment(project.garmentId);
  const design = EMB.buildLetteringDesign(fontData, text, {
    garment, pxPerMm: 8, densityMm: 0.4, underlay: project.underlay,
    rgb: project.colorRgb,
  });
  if (!design.stitchCount) throw new Error("No characters in this font yet — try different text.");
  return design;
}
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS.
- [ ] **Step 5: Commit** — `git add app/src/lib/generate.* && git commit -m "feat(app): generate adapter (project -> design)"`

---

### Task 5: 2.5D preview — strand model (pure, testable)

**Files:**
- Create: `app/src/lib/strands.js`
- Test: `app/src/lib/strands.test.js`

**Interfaces:**
- Produces: `designToStrands(design, opts) → [{ x0,y0,x1,y1, rgb:[r,g,b], kind:"stitch" }]` — one strand per sewn stitch segment (consecutive non-jump `stitches`), in DST units, colored by the active thread block. Skips `jump`/`trim`/`color`/`end`. `opts.colorOverride` (optional `[r,g,b]`) replaces all block colors (for the live color toggle).

- [ ] **Step 1: Write the failing test**

```js
import { test, expect } from "vitest";
import { designToStrands } from "./strands.js";
const design = { colors: [{ r: 10, g: 20, b: 30 }], stitches: [
  { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" },
  { x: 10, y: 0, type: "stitch" }, { x: 10, y: 5, type: "stitch" },
  { x: 40, y: 5, type: "trim" }, { x: 40, y: 5, type: "end" },
]};
test("one strand per consecutive sewn segment, colored by block", () => {
  const s = designToStrands(design, {});
  expect(s.length).toBe(2); // (0,0)->(10,0) and (10,0)->(10,5)
  expect(s[0]).toMatchObject({ x0: 0, y0: 0, x1: 10, y1: 0, rgb: [10, 20, 30] });
});
test("no strand spans a jump/trim boundary", () => {
  const s = designToStrands(design, {});
  expect(s.some(v => v.x1 === 40)).toBe(false);
});
test("colorOverride recolors all strands", () => {
  const s = designToStrands(design, { colorOverride: [200, 0, 0] });
  expect(s[0].rgb).toEqual([200, 0, 0]);
});
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL.
- [ ] **Step 3: Implement `app/src/lib/strands.js`**

```js
export function designToStrands(design, opts) {
  const o = opts || {};
  const strands = [];
  let ci = 0;
  let cur = design.colors && design.colors[0] ? [design.colors[0].r, design.colors[0].g, design.colors[0].b] : [20, 20, 20];
  let prev = null;
  for (const st of design.stitches) {
    if (st.type === "color") { ci++; const c = design.colors[ci]; if (c) cur = [c.r, c.g, c.b]; prev = null; continue; }
    if (st.type !== "stitch") { prev = null; continue; } // jump/trim/end break the strand chain
    if (prev) strands.push({ x0: prev.x, y0: prev.y, x1: st.x, y1: st.y, rgb: o.colorOverride || cur, kind: "stitch" });
    prev = st;
  }
  return strands;
}
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS.
- [ ] **Step 5: Commit** — `git add app/src/lib/strands.* && git commit -m "feat(app): strand model for 2.5D preview"`

---

### Task 6: 2.5D preview — canvas painter

**Files:**
- Create: `app/src/lib/preview.js`
- Test: `app/src/lib/preview.test.js` (guards the fit math; the paint is manually verified)

**Interfaces:**
- Consumes: `designToStrands` (Task 5).
- Produces:
  - `fitTransform(design, canvasW, canvasH, padPx) → { scale, ox, oy }` (maps DST-unit design bounds into the canvas with padding, centered).
  - `renderRealistic(canvas, design, opts)` — clears to a fabric color (`opts.fabric` default `"#e9e6df"`), then for each strand draws a lit thread capsule: a soft dark offset shadow line, then the colored line, then a thin lighter highlight offset toward the light. Uses `fitTransform`. No return value.

- [ ] **Step 1: Write the failing test (fit math only)**

```js
import { test, expect } from "vitest";
import { fitTransform } from "./preview.js";
test("fitTransform centers and scales design into canvas with padding", () => {
  const design = { stitches: [ { x: -100, y: -50, type: "stitch" }, { x: 100, y: 50, type: "stitch" } ] };
  const t = fitTransform(design, 400, 300, 20);
  // design is 200 wide, 100 tall; canvas usable 360x260 -> scale limited by width 360/200=1.8
  expect(t.scale).toBeCloseTo(1.8, 1);
  // centered: midpoint (0,0) maps to canvas center (200,150)
  expect(t.ox).toBeCloseTo(200, 0);
  expect(t.oy).toBeCloseTo(150, 0);
});
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL.
- [ ] **Step 3: Implement `app/src/lib/preview.js`**

```js
import { designToStrands } from "./strands.js";
export function fitTransform(design, cw, ch, pad) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const s of design.stitches) { if (s.type === "color" || s.type === "end") continue; if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x; if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y; }
  const w = Math.max(1, maxX - minX), h = Math.max(1, maxY - minY);
  const scale = Math.min((cw - 2 * pad) / w, (ch - 2 * pad) / h);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  return { scale, ox: cw / 2 - cx * scale, oy: ch / 2 - cy * scale };
}
export function renderRealistic(canvas, design, opts) {
  const o = opts || {};
  const ctx = canvas.getContext("2d");
  const cw = canvas.width, ch = canvas.height;
  ctx.fillStyle = o.fabric || "#e9e6df";
  ctx.fillRect(0, 0, cw, ch);
  const t = fitTransform(design, cw, ch, o.pad || 24);
  const TX = (x) => t.ox + x * t.scale, TY = (y) => t.oy + y * t.scale;
  const strands = designToStrands(design, { colorOverride: o.colorOverride });
  const lw = Math.max(1.5, 2.2 * t.scale); // thread thickness in px (DST units ~0.1mm)
  ctx.lineCap = "round";
  // shadow pass
  ctx.strokeStyle = "rgba(0,0,0,0.28)";
  ctx.lineWidth = lw;
  for (const s of strands) { ctx.beginPath(); ctx.moveTo(TX(s.x0) + 1, TY(s.y0) + 1.5); ctx.lineTo(TX(s.x1) + 1, TY(s.y1) + 1.5); ctx.stroke(); }
  // color pass
  ctx.lineWidth = lw;
  for (const s of strands) { ctx.strokeStyle = `rgb(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]})`; ctx.beginPath(); ctx.moveTo(TX(s.x0), TY(s.y0)); ctx.lineTo(TX(s.x1), TY(s.y1)); ctx.stroke(); }
  // highlight pass (sheen)
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = Math.max(0.6, lw * 0.35);
  for (const s of strands) { ctx.beginPath(); ctx.moveTo(TX(s.x0) - 0.6, TY(s.y0) - 0.9); ctx.lineTo(TX(s.x1) - 0.6, TY(s.y1) - 0.9); ctx.stroke(); }
}
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS.
- [ ] **Step 5: Manual visual check** — add a temporary route/dev harness (or use the Preview step from Task 9) to render "Kent" in Geneva; confirm it reads as shaded thread, not flat lines. (No automated pixel test — jsdom has no canvas2d.)
- [ ] **Step 6: Commit** — `git add app/src/lib/preview.* && git commit -m "feat(app): 2.5D realistic thread preview renderer"`

---

### Task 7: Export adapter + download

**Files:**
- Create: `app/src/lib/exporters.js`
- Test: `app/src/lib/exporters.test.js`

**Interfaces:**
- Consumes: `EMB.encodeDST`, `EMB.encodeEXP`, `EMB.encodePES`, `EMB.designToSVG` (confirm exact names from `src/dst.js`/`exp.js`/`pes.js`/`svgexport.js` during implementation), plus `EMB.render`/`pdfsheet` for PNG/PDF.
- Produces: `exportDesign(design, format) → { bytes:Uint8Array|string, filename:string, mime:string }` for `format` in `"dst"|"exp"|"pes"|"svg"`. (PNG/PDF wired in a later step once names confirmed.)

- [ ] **Step 1: Write the failing test**

```js
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
let design;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  design = generateDesign(update(defaultProject(), { text: "AB" }));
});
test("DST export yields bytes and a .dst filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "dst");
  expect(out.filename.endsWith(".dst")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(100);
});
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL.
- [ ] **Step 3: Implement `app/src/lib/exporters.js`** — map format → engine encoder. Confirm the exact exported names by reading `src/dst.js` etc. (e.g. `EMB.encodeDST(design)`), then:

```js
import { EMB } from "./emb.js";
export function exportDesign(design, format) {
  switch (format) {
    case "dst": return { bytes: EMB.encodeDST(design), filename: "design.dst", mime: "application/octet-stream" };
    case "exp": return { bytes: EMB.encodeEXP(design), filename: "design.exp", mime: "application/octet-stream" };
    case "pes": return { bytes: EMB.encodePES(design), filename: "design.pes", mime: "application/octet-stream" };
    case "svg": return { bytes: EMB.designToSVG(design), filename: "design.svg", mime: "image/svg+xml" };
    default: throw new Error("Unknown format: " + format);
  }
}
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS. If an encoder name differs, fix the mapping and re-run.
- [ ] **Step 5: Create `app/src/lib/download.js`** (browser-only helper; no test — DOM side effect)

```js
export function triggerDownload(out) {
  const blob = out.bytes instanceof Uint8Array ? new Blob([out.bytes], { type: out.mime }) : new Blob([out.bytes], { type: out.mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = out.filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
```

- [ ] **Step 6: Commit** — `git add app/src/lib/exporters.* app/src/lib/download.js && git commit -m "feat(app): export adapter + download helper"`

---

### Task 8: Local save (localStorage + project file)

**Files:**
- Create: `app/src/lib/save.js`
- Test: `app/src/lib/save.test.js`

**Interfaces:**
- Produces: `serialize(project) → string`, `deserialize(string) → project` (round-trips; ignores unknown fields; falls back to `defaultProject()` fields on parse error), `saveLocal(project)`/`loadLocal() → project|null` (localStorage under key `embstudio:last`).

- [ ] **Step 1: Write the failing test**

```js
import { test, expect } from "vitest";
import { serialize, deserialize } from "./save.js";
import { defaultProject, update } from "./project.js";
test("round-trips a project", () => {
  const p = update(defaultProject(), { text: "Team", fontKey: "manga_impact", colorRgb: [200, 0, 0] });
  expect(deserialize(serialize(p))).toMatchObject({ text: "Team", fontKey: "manga_impact", colorRgb: [200, 0, 0] });
});
test("bad input falls back to defaults", () => {
  expect(deserialize("not json")).toMatchObject(defaultProject());
});
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL.
- [ ] **Step 3: Implement `app/src/lib/save.js`**

```js
import { defaultProject } from "./project.js";
export function serialize(project) { return JSON.stringify(project); }
export function deserialize(str) {
  try { const o = JSON.parse(str); return { ...defaultProject(), ...o }; }
  catch (e) { return defaultProject(); }
}
const KEY = "embstudio:last";
export function saveLocal(project) { try { localStorage.setItem(KEY, serialize(project)); } catch (e) {} }
export function loadLocal() { try { const s = localStorage.getItem(KEY); return s ? deserialize(s) : null; } catch (e) { return null; } }
```

- [ ] **Step 4: Run test to verify it passes** — Expected: PASS.
- [ ] **Step 5: Commit** — `git add app/src/lib/save.* && git commit -m "feat(app): local save (localStorage + project round-trip)"`

---

### Task 9: UI — App shell + step components

**Files:**
- Modify: `app/src/App.svelte`
- Create: `app/src/ui/GarmentStep.svelte`, `TextStep.svelte`, `PreviewStep.svelte`, `DownloadStep.svelte`, `StepNav.svelte`, `FontGallery.svelte`
- Create: `app/src/ui/theme.css`

**Interfaces:**
- Consumes: `project.js`, `flow.js`, `generate.js`, `preview.js`, `exporters.js`, `download.js`, `save.js`, `EMB` (garments via `EMB.GARMENTS`/`EMB.getGarment`; fonts via `EMB.SATIN_FONTS`).
- Produces: a working 4-step app. Each step component takes `project` and dispatches `update` events; `App.svelte` owns the `project` + current `step` state.

This task is UI; verify by using it (manual acceptance), not unit tests.

- [ ] **Step 1: `App.svelte`** — owns state, renders the current step + `StepNav`, persists to localStorage on change.

```svelte
<script>
  import { defaultProject, update } from "./lib/project.js";
  import { STEPS, canAdvance, nextStep, prevStep } from "./lib/flow.js";
  import { saveLocal, loadLocal } from "./lib/save.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import TextStep from "./ui/TextStep.svelte";
  import PreviewStep from "./ui/PreviewStep.svelte";
  import DownloadStep from "./ui/DownloadStep.svelte";
  import StepNav from "./ui/StepNav.svelte";
  import "./ui/theme.css";
  let project = loadLocal() || defaultProject();
  let step = "garment";
  function apply(patch) { project = update(project, patch); saveLocal(project); }
  function go(dir) { const s = dir > 0 ? nextStep(step) : prevStep(step); if (s) step = s; }
</script>
<header class="topbar"><span class="logo">EMB&nbsp;Bot Studio</span></header>
<main class="stage">
  {#if step === "garment"}<GarmentStep {project} on:update={(e)=>apply(e.detail)} />
  {:else if step === "text"}<TextStep {project} on:update={(e)=>apply(e.detail)} />
  {:else if step === "preview"}<PreviewStep {project} on:update={(e)=>apply(e.detail)} />
  {:else}<DownloadStep {project} />{/if}
</main>
<StepNav {step} canNext={canAdvance(step, project)} on:back={()=>go(-1)} on:next={()=>go(1)} />
```

- [ ] **Step 2: `StepNav.svelte`** — Back/Next buttons + step dots.

```svelte
<script>
  import { STEPS } from "../lib/flow.js";
  import { createEventDispatcher } from "svelte";
  export let step; export let canNext;
  const d = createEventDispatcher();
</script>
<nav class="stepnav">
  <button on:click={() => d("back")} disabled={step === STEPS[0]}>Back</button>
  <ol>{#each STEPS as s}<li class:active={s === step}>{s}</li>{/each}</ol>
  <button class="primary" on:click={() => d("next")} disabled={!canNext || step === STEPS[STEPS.length-1]}>Next</button>
</nav>
```

- [ ] **Step 3: `GarmentStep.svelte`** — tiles from `EMB.GARMENTS` (confirm the export; else use a small hardcoded list mapping to `EMB.getGarment` ids: `hat_front`, `left_chest`, `shirt_front`, `tote`). Clicking a tile dispatches `update({ garmentId })`.

```svelte
<script>
  import { EMB } from "../lib/emb.js";
  import { createEventDispatcher } from "svelte";
  export let project; const d = createEventDispatcher();
  const tiles = [
    { id: "left_chest", label: "Left chest" }, { id: "hat_front", label: "Hat front" },
    { id: "shirt_front", label: "Shirt front" }, { id: "tote", label: "Tote bag" },
  ].filter(t => { try { return !!EMB.getGarment(t.id); } catch (e) { return false; } });
</script>
<h2>What are you putting this on?</h2>
<div class="tiles">
  {#each tiles as t}
    <button class="tile" class:sel={project.garmentId === t.id} on:click={() => d("update", { garmentId: t.id })}>{t.label}</button>
  {/each}
</div>
```

- [ ] **Step 4: `FontGallery.svelte`** — lists `EMB.SATIN_FONTS`; each entry shows the font `name` and (nice-to-have) a small live thumbnail rendered via `renderRealistic` of that font generating the current text or the font name. Selecting dispatches the key.

```svelte
<script>
  import { EMB } from "../lib/emb.js";
  import { createEventDispatcher } from "svelte";
  export let selected; const d = createEventDispatcher();
  const fonts = Object.entries(EMB.SATIN_FONTS).map(([key, f]) => ({ key, name: f.name || key }));
</script>
<ul class="fontgallery">
  {#each fonts as f}
    <li><button class:sel={f.key === selected} on:click={() => d("pick", f.key)}>{f.name}</button></li>
  {/each}
</ul>
```

- [ ] **Step 5: `TextStep.svelte`** — text input + `FontGallery` + color + size; dispatches `update`.

```svelte
<script>
  import FontGallery from "./FontGallery.svelte";
  import { createEventDispatcher } from "svelte";
  export let project; const d = createEventDispatcher();
  function rgbToHex([r,g,b]){ return "#" + [r,g,b].map(v=>v.toString(16).padStart(2,"0")).join(""); }
  function hexToRgb(h){ return [1,3,5].map(i=>parseInt(h.slice(i,i+2),16)); }
</script>
<h2>Your text</h2>
<input class="textin" type="text" bind:value={project.text} on:input={() => d("update", { text: project.text })} placeholder="Type a name or word" />
<label>Color <input type="color" value={rgbToHex(project.colorRgb)} on:input={(e)=>d("update",{ colorRgb: hexToRgb(e.target.value) })} /></label>
<h3>Font</h3>
<FontGallery selected={project.fontKey} on:pick={(e)=>d("update",{ fontKey: e.detail })} />
```

- [ ] **Step 6: `PreviewStep.svelte`** — generates on mount/param change, paints the canvas, offers a color toggle; shows friendly errors.

```svelte
<script>
  import { onMount } from "svelte";
  import { generateDesign } from "../lib/generate.js";
  import { renderRealistic } from "../lib/preview.js";
  export let project;
  let canvas, error = "", stats = "";
  function paint() {
    error = "";
    try {
      const design = generateDesign(project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      renderRealistic(canvas, design, { colorOverride: project.colorRgb });
    } catch (e) { error = e.message; }
  }
  onMount(paint);
  $: if (canvas && project) paint();
</script>
<h2>Preview</h2>
{#if error}<p class="err">{error}</p>{/if}
<canvas bind:this={canvas} width="640" height="420"></canvas>
<p class="stats">{stats}</p>
```

- [ ] **Step 7: `DownloadStep.svelte`** — format buttons; generates + exports + downloads.

```svelte
<script>
  import { generateDesign } from "../lib/generate.js";
  import { exportDesign } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  export let project; let msg = "";
  function dl(fmt) {
    try { triggerDownload(exportDesign(generateDesign(project), fmt)); msg = "Downloaded " + fmt.toUpperCase(); }
    catch (e) { msg = e.message; }
  }
</script>
<h2>Download</h2>
<div class="formats">
  <button class="primary" on:click={() => dl("dst")}>DST</button>
  <button on:click={() => dl("pes")}>PES</button>
  <button on:click={() => dl("exp")}>EXP</button>
  <button on:click={() => dl("svg")}>SVG</button>
</div>
<p>{msg}</p>
```

- [ ] **Step 8: `theme.css`** — minimal, clean beginner-friendly styling (system font stack, generous spacing, one accent color, large touch targets). Keep it short; not performance-critical.
- [ ] **Step 9: Manual acceptance** — `npm run dev`; walk garment → text ("Kent", try 3 fonts) → preview (looks like thread, color toggle works) → download DST. Open the DST via the repo tool `node tools/render-dst.mjs` to confirm it decodes.
- [ ] **Step 10: Commit** — `git add app/src/ && git commit -m "feat(app): guided 4-step UI (garment/text/preview/download)"`

---

### Task 10: Static build + deploy docs

**Files:**
- Create: `app/README.md`
- Modify: `app/vite.config.js` (already `base: "./"` for portable static hosting)
- Create: `.github/workflows/deploy-app.yml` (optional GitHub Pages build) — only if Kent wants Pages.

- [ ] **Step 1: Build** — `cd app && npm run build`. Expected: `app/dist/` created, containing `index.html`, hashed JS, and `engine/` (copied to `public/` so Vite includes it).
- [ ] **Step 2: Verify the build runs** — `npm run preview`, open the URL, walk the flow, download a DST. Expected: works with no dev server (pure static).
- [ ] **Step 3: Write `app/README.md`** — how to dev (`npm install && npm run dev`), build (`npm run build`), and deploy (drop `dist/` on Netlify, or push to GitHub Pages). Note the engine is copied from `../src` by `scripts/copy-engine.mjs` at pre(dev|build).
- [ ] **Step 4: Commit** — `git add app/README.md .github/ && git commit -m "docs(app): build + deploy instructions"`

---

## Notes for the implementer
- Confirm exact engine export names before wiring (grep `src/dst.js`, `src/exp.js`, `src/pes.js`, `src/svgexport.js`, `src/garments.js` for the encoder/garment accessors — e.g. is it `EMB.encodeDST` and `EMB.getGarment`? adjust `exporters.js`/`generate.js` to match).
- Do NOT modify `src/*.js`. If the engine needs a change, stop and raise it — it affects the 139-test suite and the existing tool.
- The lowercase-"e" tight-curl fan is a separate engine improvement (density-adaptive correspondence in `src/satinplay.js`), tracked in the spec; it is NOT part of this app plan but will improve the preview once done.
