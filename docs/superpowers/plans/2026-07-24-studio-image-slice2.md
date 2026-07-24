# Studio Slice 2: Photo/Logo Digitizing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a photo/logo input path to EMB Bot Studio's guided flow: upload art → auto-flatten to N thread colors (with live preview + merge) → generate stitches → same 2.5D field and download.

**Architecture:** New app modules wrap the engine's PROVEN image pipeline (the old tool's exact flow): `prepRGBA → (knockoutBackground) → medianCut → modeFilter → absorbSmallRegions` = flatten state; `per-color masks → traceRegions → simplify → despeckle` = regions; `EMB.buildQualityDesign(regions, …)` = design. The guided flow gains a content-type choice (Text vs Image) after Garment; the project model gains image fields; the field/download steps are unchanged (they consume a design either way).

**Tech Stack:** Same as Slice 1 — Svelte 5 + Vite 8, Vitest (`*.spec.js`), engine via `window.EMB`. Branch `feat/studio-image`.

## Global Constraints

- **Do NOT modify `src/*.js`** (engine). Repo-root `node --test` (139) stays green.
- App code only under `app/`. App tests use `.spec.js` (never `.test.js`).
- **Reuse the proven pipeline values** (from the old tool, `src/app.js:13-21`, copy exactly):
  `WORK_MAX_PX = 480`, `NOMINAL_LONG_MM = 50`, `SIMPLIFY_TOL = 1.6`, `MODE_FILTER_ITERS = 2`, `ABSORB_SHARE = 0.0005`, `DESPECKLE_SHARE = 0.0004`, `MAX_SHAPES_PER_COLOR = 60`, `ALPHA_CUTOFF = 128`.
- Engine functions used (all confirmed on `EMB`): `medianCut(rgba, n)` → `{palette, indices}`, `knockoutBackground(rgba, w, h, {})`, `modeFilter(indices, w, h, {iterations})`, `absorbSmallRegions(indices, w, h, minPx)`, `indicesToRGBA(indices, palette, w, h)`, `paletteShares(indices, nPalette)`, `mergeColors(palette, indices, idxList)`, `traceRegions(mask, w, h)`, `simplify(ring, tol)`, `buildQualityDesign(regions, opts)`, `getGarment(id)`, `getFabric(id)`/`fabricForGarment(id)`.
- Beginner-honest copy: the image step must tell users clean/flat art works best (photos with gradients won't stitch well).

---

### Task 1: Project model + flow gain an image mode

**Files:**
- Modify: `app/src/lib/project.js`
- Modify: `app/src/lib/flow.js`
- Modify: `app/src/lib/project.spec.js`, `app/src/lib/flow.spec.js`

**Interfaces:**
- Produces (project): `defaultProject()` gains `mode: "text"`, `nColors: 4`, `removeBg: true`. (The image bitmap itself is NOT in the project — it's runtime-only state; see Task 2.)
- Produces (flow): `STEPS = ["garment", "content", "create", "download"]`; `canAdvance("content", p)` → always true (it's a mode choice); `canAdvance("create", p)` → for mode "text": text non-empty + fontKey; for mode "image": `p._hasImage === true` (a runtime flag the UI sets when an image is loaded).

- [ ] **Step 1: Update the failing tests** — in `project.spec.js` add:

```js
test("defaults include image-mode fields", () => {
  const p = defaultProject();
  expect(p.mode).toBe("text");
  expect(p.nColors).toBe(4);
  expect(p.removeBg).toBe(true);
});
```

In `flow.spec.js` REPLACE the steps-order test and add gating tests:

```js
test("steps order", () => { expect(STEPS).toEqual(["garment","content","create","download"]); });
test("create step gates by mode", () => {
  const p = defaultProject(); // mode text, empty text
  expect(canAdvance("create", p)).toBe(false);
  expect(canAdvance("create", update(p, { text: "Hi" }))).toBe(true);
  const pi = update(p, { mode: "image" });
  expect(canAdvance("create", pi)).toBe(false);
  expect(canAdvance("create", update(pi, { _hasImage: true }))).toBe(true);
});
test("content step always advances", () => {
  expect(canAdvance("content", defaultProject())).toBe(true);
});
```

- [ ] **Step 2: Run tests to verify they fail** — `cd app && npx vitest run src/lib/project.spec.js src/lib/flow.spec.js`. Expected: FAIL.
- [ ] **Step 3: Implement** — `project.js` defaults add `mode: "text", nColors: 4, removeBg: true`. `flow.js`:

```js
export const STEPS = ["garment", "content", "create", "download"];
export function canAdvance(step, project) {
  if (step === "garment") return !!project.garmentId;
  if (step === "content") return true;
  if (step === "create") {
    if (project.mode === "image") return project._hasImage === true;
    return project.text.trim().length > 0 && !!project.fontKey;
  }
  return true;
}
```

(`nextStep`/`prevStep` unchanged — they derive from STEPS.)
- [ ] **Step 4: Run tests to verify they pass.**
- [ ] **Step 5: Commit** — `git add app/src/lib/project.* app/src/lib/flow.* && git commit -m "feat(app): image mode in project model + 4-step flow with content choice"`

---

### Task 2: Flatten adapter (image → flatState)

**Files:**
- Create: `app/src/lib/flatten.js`
- Test: `app/src/lib/flatten.spec.js`

**Interfaces:**
- Consumes: `EMB.medianCut`, `EMB.knockoutBackground`, `EMB.modeFilter`, `EMB.absorbSmallRegions`, `EMB.indicesToRGBA`, `EMB.paletteShares`, `EMB.mergeColors`.
- Produces:
  - `flattenRGBA(rgba, w, h, { nColors, removeBg }) → { palette:[[r,g,b]…], indices:Uint8Array, w, h }` — the pure pipeline on raw pixels (testable in Node).
  - `flatToRGBA(flat) → Uint8ClampedArray` — for painting the preview.
  - `flatShares(flat) → number[]` — share per palette entry.
  - `mergeFlat(flat, idxList) → flat` — new flat with palette entries merged (wraps `EMB.mergeColors`).
  - Constants exported: `WORK_MAX_PX`, `ALPHA_CUTOFF` (used by the UI's canvas prep).

- [ ] **Step 1: Write the failing test** (engine `beforeAll` loader same as Slice 1 tests — require `units,garments,fabrics,fill,geometry,quantize,flatten,satin,satinplay,satinfont,dst,exp,fonts,digitize` then eval satin-fonts; set `globalThis.window = globalThis`):

```js
// build a synthetic 24x16 two-color image: left half red, right half blue
function synthRGBA(w, h) {
  const rgba = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = (y * w + x) * 4;
    if (x < w / 2) { rgba[o] = 200; rgba[o + 1] = 30; rgba[o + 2] = 30; }
    else { rgba[o] = 30; rgba[o + 1] = 30; rgba[o + 2] = 200; }
    rgba[o + 3] = 255;
  }
  return rgba;
}
test("flattenRGBA reduces to the requested palette and covers all pixels", async () => {
  const { flattenRGBA, flatShares } = await import("./flatten.js");
  const w = 24, h = 16;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  expect(flat.palette.length).toBe(2);
  expect(flat.indices.length).toBe(w * h);
  const shares = flatShares(flat);
  expect(shares.length).toBe(2);
  expect(shares[0] + shares[1]).toBeCloseTo(1, 1);
});
test("mergeFlat collapses two entries into one", async () => {
  const { flattenRGBA, mergeFlat } = await import("./flatten.js");
  const w = 24, h = 16;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  const merged = mergeFlat(flat, [0, 1]);
  expect(merged.palette.length).toBe(1);
});
```

- [ ] **Step 2: Run to verify FAIL.**
- [ ] **Step 3: Implement `app/src/lib/flatten.js`:**

```js
import { EMB } from "./emb.js";
export const WORK_MAX_PX = 480;
export const ALPHA_CUTOFF = 128;
const MODE_FILTER_ITERS = 2;
const ABSORB_SHARE = 0.0005;

export function flattenRGBA(rgba, w, h, opts) {
  const o = opts || {};
  let px = rgba;
  if (o.removeBg) px = EMB.knockoutBackground(px, w, h, {});
  const quant = EMB.medianCut(px, o.nColors || 4);
  let indices = EMB.modeFilter(quant.indices, w, h, { iterations: MODE_FILTER_ITERS });
  indices = EMB.absorbSmallRegions(indices, w, h, Math.round(w * h * ABSORB_SHARE));
  return { palette: quant.palette.map((c) => c.slice()), indices, w, h };
}
export function flatToRGBA(flat) { return EMB.indicesToRGBA(flat.indices, flat.palette, flat.w, flat.h); }
export function flatShares(flat) { return EMB.paletteShares(flat.indices, flat.palette.length); }
export function mergeFlat(flat, idxList) {
  const m = EMB.mergeColors(flat.palette, flat.indices, idxList);
  return { palette: m.palette, indices: m.indices, w: flat.w, h: flat.h };
}
```

NOTE for implementer: confirm `EMB.mergeColors`'s exact return shape by reading `src/flatten.js:158` and adapt `mergeFlat` accordingly (it may return `{palette, indices}` or mutate — match reality; the test pins behavior).
- [ ] **Step 4: Run to verify PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(app): flatten adapter (image -> flat palette state)"`

---

### Task 3: Image regions + generate integration

**Files:**
- Create: `app/src/lib/imageRegions.js`
- Modify: `app/src/lib/generate.js`
- Test: `app/src/lib/imageRegions.spec.js`

**Interfaces:**
- Consumes: `EMB.traceRegions`, `EMB.simplify`, `EMB.buildQualityDesign`, flatState from Task 2.
- Produces:
  - `flatToRegions(flat) → { regions, pxPerMm }` — the old tool's `imageToRegions` logic verbatim (per-color mask → traceRegions → simplify(1.6) → despeckle `w*h*0.0004`, holes ≥ max(6, despeckle*0.3), cap 60 shapes/color, `pxPerMm = max(w,h)/50`).
  - `generate.js` gains: `generateImageDesign(flat, project) → design` calling `EMB.buildQualityDesign(regions, { garment, fabric: EMB.getFabric(EMB.fabricForGarment(project.garmentId)), pxPerMm, densityMm: 0.4, satinMaxWidthMm: 3.0, underlay: project.underlay })`. Throws `"No shapes found…"` when regions are empty. (Keep the existing `generateDesign` for text untouched.)

- [ ] **Step 1: Write the failing test** (same engine loader; reuse the synthetic two-color image from Task 2's test):

```js
test("flatToRegions traces one region per palette color", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { flatToRegions } = await import("./imageRegions.js");
  const w = 96, h = 64; // big enough to survive despeckle
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  const { regions, pxPerMm } = flatToRegions(flat);
  expect(regions.length).toBe(2);
  expect(regions[0].shapes.length).toBeGreaterThan(0);
  expect(pxPerMm).toBeCloseTo(96 / 50, 2);
});
test("generateImageDesign produces stitches from a flat", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { generateImageDesign } = await import("./generate.js");
  const { defaultProject } = await import("./project.js");
  const w = 96, h = 64;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  const d = generateImageDesign(flat, defaultProject());
  expect(d.stitchCount).toBeGreaterThan(100);
  expect(d.colorCount).toBe(2);
});
```

- [ ] **Step 2: Run to verify FAIL.**
- [ ] **Step 3: Implement** — port `src/app.js:318-358` (`imageToRegions`) into `flatToRegions` with the constants from Global Constraints (area() helper: shoelace/2). `generateImageDesign` per the interface above.
- [ ] **Step 4: Run to verify PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(app): image regions + generateImageDesign (flat -> stitches)"`

---

### Task 4: UI — content choice + image step

**Files:**
- Create: `app/src/ui/ContentStep.svelte` (mode toggle + per-mode content)
- Create: `app/src/ui/ImagePanel.svelte` (upload, flatten preview, colors slider, remove-bg toggle, swatch merge)
- Modify: `app/src/ui/TextStep.svelte` → becomes the text panel inside ContentStep (keep the file; ContentStep imports it)
- Modify: `app/src/App.svelte` (steps: garment → content → create/download wiring; hold runtime image state)
- Modify: `app/src/ui/EmbroideryField.svelte` (render image designs too)
- Modify: `app/src/ui/DownloadStep.svelte` (works for both modes)

**Interfaces:**
- `App.svelte` owns runtime image state: `let flat = null` (flatState) and raw `let imageBitmap = null`; passes them down; sets `apply({ _hasImage: !!flat })` when flatten completes.
- `ImagePanel` events: `on:flat` (detail = new flatState) fired after load/recompute/merge; App stores it.
- `EmbroideryField` props gain `flat` — when `project.mode === "image" && flat`, it builds the design via `generateImageDesign(flat, project)`; else the text path as today. Field hint copy for image mode: "Upload a logo or clean art — flat colors stitch best."
- `DownloadStep` calls the right generator by mode (accepts `flat` prop too).

Implementation notes (concrete):
- Upload: `<input type="file" accept="image/*">` → `createImageBitmap(file)` (fallback `new Image` + object URL) → draw to an offscreen canvas at `WORK_MAX_PX` long side → `getImageData` → zero alpha < `ALPHA_CUTOFF` (port `prepRGBA` from `src/app.js:95-108`) → `flattenRGBA`.
- Flatten preview: paint `flatToRGBA(flat)` to a small canvas, `imageSmoothingEnabled = false`, integer upscale (port `renderFlatPreview`, `src/app.js:140-164`).
- Swatches: chips colored per palette entry + share % (from `flatShares`), click = toggle select, "Merge selected" button calls `mergeFlat` and re-emits; "Reset" re-runs `flattenRGBA` from the kept working RGBA.
- Colors slider 2–8 (default 4 = `project.nColors`); Remove background checkbox = `project.removeBg`; both re-run flatten (on change).
- Honest-copy line under the upload control: "Best results: logos and flat-color art. Photos with gradients won't stitch cleanly."
- This is UI: verify with `npm run build` (clean) + `npx vitest run` (no regressions) + static checks; controller does browser acceptance.

- [ ] **Step 1: Build ContentStep with mode toggle** (two big tabs/tiles: "Text" / "Logo or image"), rendering TextStep's controls or ImagePanel by `project.mode`; dispatches `update({ mode })`.
- [ ] **Step 2: Build ImagePanel** per the notes above.
- [ ] **Step 3: Rewire App.svelte** — steps garment/content/create/download; "create" shows a summary + regenerate hint (the field renders live anyway); hold `flat`, pass to Field + DownloadStep. NOTE: with the persistent field, the "create" step can simply be the download-prep screen; if simpler, collapse to `["garment","content","download"]` and update flow.js + its spec accordingly (implementer's choice — document it).
- [ ] **Step 4: Update EmbroideryField + DownloadStep** for mode dispatch.
- [ ] **Step 5: Verify** — `cd app && npm run build` (clean) and `npx vitest run` (all pass).
- [ ] **Step 6: Commit** — `git commit -m "feat(app): image mode UI — upload, flatten preview, swatch merge, mode dispatch"`

---

### Task 5: Browser acceptance + docs (controller)

- [ ] **Step 1:** `npm run dev`; drive in browser: garment → content: image → upload a test PNG (generate one: two-color logo-ish shape) → flatten preview shows N colors → merge two colors → field renders stitches → download DST; decode via `node tools/render-dst.mjs` to confirm.
- [ ] **Step 2:** Also verify the text path still works end-to-end (no regression).
- [ ] **Step 3:** Update `app/README.md` (image mode paragraph). Commit.

---

## Notes for the implementer
- Engine loader for tests must now ALSO require `quantize.js` and `flatten.js` (the Slice 1 loaders didn't).
- `EMB.mergeColors(palette, indices, idxList)` — confirm return shape at `src/flatten.js:158` before wiring.
- Do NOT reimplement quantize/trace/digitize math — everything is an `EMB.*` call.
