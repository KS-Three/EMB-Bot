# Studio Slice 3: Interactive Sizing & Placement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user interactively resize and reposition the design on the garment — drag corner handles / drag to move directly on the embroidery field, plus exact width/height inputs — with stitches truly REGENERATED at each size (correct density), and plain-English guardrails against unsewably small lettering.

**Architecture:** (1) The engine's two design builders accept an explicit `targetWidthMm` (overriding auto-fit, still clamped to the hoop) and `offsetXMm/offsetYMm` (translation from hoop center) — density correctness is preserved because the existing fit-scale machinery is reused. (2) The field switches from design-fit rendering to **hoop-space rendering**: the canvas frames the garment area (hoop outline), the design draws inside at true relative size/position. (3) EmbroideryField gains selection + pointer interactions (corner-resize, drag-move) that update `project.sizeMm/offsetXMm/offsetYMm`; a size readout + W×H inputs in the panel stay in sync.

**Tech Stack:** unchanged — engine dual-mode JS (`src/`, guarded by `node --test`), Svelte 5 + Vite app (`app/`, Vitest `.spec.js`). Branch `feat/studio-sizing`.

## Global Constraints

- Engine changes ARE allowed this slice (Tasks 1) but must be **additive & back-compat**: with the new opts absent, output must be byte-identical to today (existing 139 tests prove it; add new tests for the new opts). App tests keep using `.spec.js`.
- Size semantics: `project.sizeMm = null` → auto-fit (today's behavior). `sizeMm = number` → target design WIDTH in mm, clamped to the garment hoop. Height follows aspect.
- Offset semantics: `offsetXMm/offsetYMm` = design-center offset from hoop center, mm, +x right / +y UP (DST convention). Clamped so the design bbox stays inside the hoop.
- Guardrail: if the generated design's height < 5 mm (or width < 5 mm), show a friendly warning in the field meta ("Smaller than 5 mm — thread can't stitch this cleanly") — do NOT block.
- All engine calls remain `EMB.*`; no stitch math in the app.

---

### Task 1: Engine — explicit size + offset in both builders

**Files:**
- Modify: `src/digitize.js` (`buildLetteringDesign`, `buildQualityDesign`)
- Test: `test/digitize.test.js` (append)

**Interfaces:**
- Produces: both builders accept `opts.targetWidthMm` (number|undefined) and `opts.offsetXMm`, `opts.offsetYMm` (numbers, default 0).
  - `targetWidthMm`: replaces the auto fit — `scale = clamp(targetWidthMm, 1, hoopWmm) / bboxWmm`, then ALSO clamped so height fits the hoop (`scale = min(scale, hoopHmm/bboxHmm)`). Everything downstream (density two-pass in lettering, rowPx etc. in quality) already derives from the fit scale, so correctness holds.
  - Offsets: after the existing center transform, add `Math.round(offsetXMm * DST_UNITS_PER_MM)` to every stitch x and `+offsetYMm...` to y (DST y is already up). widthMM/heightMM in the returned design stay the DESIGN dims (not hoop).
- Back-compat: opts absent ⇒ identical output (assert via existing tests passing untouched).

- [ ] **Step 1: Write failing tests** (append to `test/digitize.test.js`):

```js
test("buildLetteringDesign: targetWidthMm sets the final width (clamped to hoop)", () => {
  const font = /* load a satin font: */ (() => { const fs = require("node:fs"); return JSON.parse(fs.readFileSync(__dirname + "/../src/fonts/geneva_simple.json", "utf8")); })();
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8 };
  const d40 = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm: 40 });
  expect_close(d40.widthMM, 40, 1.5);
  const dHuge = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm: 500 });
  assert.ok(dHuge.widthMM <= 5 * 25.4 + 1, "clamped to hoop width");
});
test("buildLetteringDesign: offsets translate all stitches", () => {
  const font = (() => { const fs = require("node:fs"); return JSON.parse(fs.readFileSync(__dirname + "/../src/fonts/geneva_simple.json", "utf8")); })();
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const d0 = DG.buildLetteringDesign(font, "AB", base);
  const d10 = DG.buildLetteringDesign(font, "AB", { ...base, offsetXMm: 10, offsetYMm: -5 });
  const s0 = d0.stitches.find((s) => s.type === "stitch");
  const s1 = d10.stitches.find((s) => s.type === "stitch");
  assert.strictEqual(s1.x - s0.x, 100); // 10mm = 100 DST units
  assert.strictEqual(s1.y - s0.y, -50);
});
```

(Adapt to the file's existing assert style — it uses node:assert, not expect; `expect_close` above means `assert.ok(Math.abs(a-b)<=tol)`. Follow the file's conventions.)
- [ ] **Step 2: Run to verify FAIL** — `node --test test/digitize.test.js`.
- [ ] **Step 3: Implement** in `src/digitize.js`. In `buildLetteringDesign`: after computing `fit`, if `o.targetWidthMm` is a finite number > 0: `const hoopW = garments.inToMm(garment.widthIn)`-style (use existing units helpers; hoop dims are `fit.targetWmm` is the FIT result — instead compute hoop from garment via the same call fitScale uses; read fitScale in src/garments.js first) → `sc = min(clamp(targetWidthMm,1,hoopWmm)/bboxWmm, hoopHmm/bboxHmm)`. Same pattern in `buildQualityDesign` right where `fit.scale` is read (line ~218). Offsets: in both builders' `T(...)`, add `dx = Math.round((o.offsetXMm||0)*units.DST_UNITS_PER_MM)` etc. Report widthMM/heightMM as `bbox*sc` when targetWidthMm is set (not fit.targetWmm).
- [ ] **Step 4: Run FULL engine suite** — `node --test` → all previous 139 pass + new ones.
- [ ] **Step 5: Commit** — `git commit -m "feat(engine): explicit targetWidthMm + offset in design builders (back-compat)"`

---

### Task 2: App — project fields + generate pass-through

**Files:**
- Modify: `app/src/lib/project.js` (+spec), `app/src/lib/generate.js` (+specs)

**Interfaces:**
- `defaultProject()` gains `offsetXMm: 0, offsetYMm: 0` (`sizeMm: null` already exists).
- Both `generateDesign` and `generateImageDesign` pass `targetWidthMm: project.sizeMm || undefined, offsetXMm: project.offsetXMm || 0, offsetYMm: project.offsetYMm || 0`.

- [ ] **Step 1: Failing tests** — project defaults include the new fields; generate: a project with `sizeMm: 40` yields `design.widthMM ≈ 40`; with `offsetXMm: 10` first stitch shifts +100 DST x vs offset 0 (mirror the engine test at the adapter level, text mode only is fine).
- [ ] **Step 2-4: Implement, verify targeted + full app suite (26+), commit** — `git commit -m "feat(app): size/offset in project + generate pass-through"`

---

### Task 3: Hoop-space field rendering

**Files:**
- Modify: `app/src/lib/preview.js` (+spec)
- Modify: `app/src/ui/EmbroideryField.svelte`

**Interfaces:**
- New: `hoopTransform(garment, cw, ch, pad) → { scale, ox, oy, hoopWmm, hoopHmm }` — maps HOOP mm-space (origin = hoop center, +y up) into the canvas: `scale = min((cw-2p)/hoopWmm, (ch-2p)/hoopHmm)`, `ox = cw/2`, `oy = ch/2`. Canvas point = `(ox + xMm*scale, oy - yMm*scale)`.
- `renderRealistic(canvas, design, opts)` gains `opts.hoop = { garment }`: when present, use `hoopTransform` (converting stitch DST units → mm via /10) instead of design-fit `fitTransform`; also draw the hoop as a rounded-rect outline + subtle stitch-limit dashed inset. Design-fit path stays for thumbnails (FontSelect passes no hoop).
- `EmbroideryField` passes `hoop: { garment: EMB.getGarment(project.garmentId) }` and keeps stats/meta as today. Returns of `renderRealistic` when hooped: `{ toCanvas(xMm,yMm), designBBoxMm }` (the field interaction task needs them; plain object return, still cheap).

- [ ] **Step 1: Failing spec for `hoopTransform`** (pure math: 5×2.25in garment on 640×420 canvas → scale = min(...); center maps to canvas center; +y up).
- [ ] **Step 2-3: Implement + hook into EmbroideryField.** Draw order: fabric bg → hoop outline → strands (converted DST→mm) → nothing else.
- [ ] **Step 4: Verify** — app suite green; `npm run build` clean.
- [ ] **Step 5: Commit** — `git commit -m "feat(app): hoop-space field rendering (design at true size/position in garment frame)"`

---

### Task 4: Field interaction — select, corner-resize, drag-move

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte`
- Create: `app/src/lib/interact.js` (+spec) — the pure hit-test/drag math so it's testable

**Interfaces (`interact.js`, all pure):**
- `designRectPx(designBBoxMm, T) → {x,y,w,h}` (canvas-space rect via the hoop transform T)
- `hitTest(rectPx, px, py, handleR=8) → "none"|"body"|"nw"|"ne"|"sw"|"se"`
- `dragResize(startRectMm, handle, dxMm, dyMm, minWmm=5, maxWmm=hoopW) → newWidthMm` (aspect-locked from the dragged corner)
- `dragMove(startOffset, dxMm, dyMm, designWH, hoopWH) → {offsetXMm, offsetYMm}` (clamped so the design stays inside the hoop)

**Behavior in EmbroideryField:**
- Design always selectable: hovering shows move cursor over it; a thin selection box + 4 corner handles draw whenever the pointer is over the field (keep it simple: always show handles when a design exists).
- Pointerdown on a corner → resize drag: convert pointer delta to mm via the hoop transform; live-update `project.sizeMm` (dispatch `update`) — regeneration is fast for text; throttle regenerate to ~60ms trailing for smoothness (requestAnimationFrame gate).
- Pointerdown on body → move drag: updates `offsetXMm/offsetYMm` (clamped). Moving does NOT regenerate stitches (offset is a translation) — pass offsets straight to the builder via project (cheap regen is fine too if simpler; note which you chose).
- Guardrail: after generation, if `design.widthMM < 5 || design.heightMM < 5`, meta shows the warning text from Global Constraints alongside stats.
- Dispatch pattern: EmbroideryField now needs `on:update` wired in App.svelte (it currently only receives props) — add it.

- [ ] **Step 1: Failing specs for interact.js** (hitTest corners/body/none; dragResize respects min 5mm and aspect; dragMove clamps inside hoop).
- [ ] **Step 2-3: Implement lib + wire pointer events** (pointerdown/pointermove/pointerup + setPointerCapture on the canvas).
- [ ] **Step 4: Verify** — app suite green, build clean.
- [ ] **Step 5: Commit** — `git commit -m "feat(app): drag-resize + drag-move the design on the field"`

---

### Task 5: Panel size controls (synced)

**Files:**
- Modify: `app/src/ui/ContentStep.svelte` (or a small `SizePanel.svelte` used by it), `app/src/ui/theme.css`

**Behavior:**
- A compact "Size" row visible in BOTH modes: `W [__] × H [__] in|mm` (unit toggle, default inches since Kent's US-based), plus an "Auto-fit" button that resets `sizeMm=null, offsets=0`.
- W input sets `sizeMm` (converted to mm); H is derived/readonly (aspect-locked) showing the generated `heightMM`.
- Values live-sync with handle drags (they read the same project fields + last design dims).
- Below 5mm the input shows the same guardrail warning inline.

- [ ] **Step 1-2: Implement + verify** (build clean, suite green — UI only).
- [ ] **Step 3: Commit** — `git commit -m "feat(app): size panel (W/H, in/mm, auto-fit) synced with field handles"`

---

### Task 6: Browser acceptance + docs (controller)

- [ ] Drive live: text design → drag corner (design resizes, density stays right — stitch count grows with size) → drag to reposition (stays in hoop, DST reflects offset) → W input in inches → auto-fit reset → tiny-size warning shows below 5mm → image mode gets the same handles → DST decode check with offset. Text+image regression.
- [ ] Update `app/README.md` (sizing paragraph). Ledger + commit.

---

## Notes for the implementer
- Read `src/garments.js` `fitScale` BEFORE Task 1 — reuse its hoop-mm derivation; do not duplicate conversion constants.
- DST units are 0.1 mm (`units.DST_UNITS_PER_MM` = 10): preview converts stitch coords → mm via /10.
- FontSelect thumbnails must keep design-fit rendering (no hoop) — don't regress them.
- The 2.5D Y-flip is already handled in preview.js — hoopTransform must keep +y-up → canvas-down consistent with it.
