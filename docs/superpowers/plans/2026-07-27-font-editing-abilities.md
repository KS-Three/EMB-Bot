# Font Editing Abilities (Round 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four text-element editing abilities to EMB Bot Studio — rotation (incl. one-click upside-down), per-letter color ranges, bold weight presets, and a bounded slant/italic slider — per the approved spec at `docs/superpowers/specs/2026-07-27-font-editing-abilities-design.md`.

**Architecture:** All four abilities are additive options on the text element (new fields, all defaulting to today's behavior when absent) threaded through `app/src/lib/generate.js` into `src/digitize.js`'s `buildLetteringDesign`, which in turn threads slant into `src/satinfont.js`'s `layoutText`/`routeGlyph` and `src/satinplay.js`'s `emitZigzag`. Rotation and per-letter color are implemented entirely inside `buildLetteringDesign` (a post-transform and a trim/color-insertion pass, respectively); bold reuses the existing, already-tested `pullCompMm` column-widening mechanism; slant is new math in `emitZigzag`, verified analytically before this plan was written (see spike results below).

**Tech Stack:** Vanilla JS engine (`src/*.js`, dual Node/browser UMD modules, tested via `node --test`), Svelte 5 UI (`app/src/**`, tested via Vitest).

## Global Constraints

- Every new element field defaults to a value that reproduces TODAY's exact output when absent (`rotationDeg: 0`, `colorRanges: []`, `weightPreset: "normal"`, `slantDeg: 0`) — no migration needed for existing saved projects, matching this codebase's established `element.field || default` convention (see `app/src/lib/generate.js`'s existing `letterSpacingMm: element.letterSpacingMm || 0`).
- Rotation range: 0–360°. Slant range: -20° to +20° (bounded per the approved spec — wider angles were shown in the pre-plan spike to noticeably lengthen cross-stitches and risk rungs no longer meeting rails cleanly at the very tips).
- Full test suite (`node --test` from repo root + `cd app && npx vitest run`) must stay green after every task.
- Rebuild `EMB-Bot-standalone.html` via `node tools/bundle.mjs` (and re-run `node scripts/copy-engine.mjs` in `app/` for local dev-server testing) after every `src/*.js` change, per this project's established pattern.
- Live-verify every new UI control in the actual Studio dev server before calling its task done (per this project's established pattern — Slices 1-8 and both recent bug fixes were all live-verified in-browser).

---

## Task 1: Rotation (incl. one-click upside-down)

**Files:**
- Modify: `src/digitize.js` (`buildLetteringDesign`, currently lines 524–603)
- Modify: `app/src/lib/generate.js` (`generateElement`, text branch, currently lines 36–50)
- Modify: `app/src/lib/project.js` (`defaultTextElement`, currently lines 6–20)
- Modify: `app/src/ui/TextStep.svelte`
- Test: `test/digitize.test.js`
- Test: `app/src/lib/generate.spec.js`
- Test: `app/src/lib/project.spec.js`

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: `buildLetteringDesign(fontData, text, opts)` accepts `opts.rotationDeg` (number, degrees, default 0). `element.rotationDeg` (number, default 0) is the new project-model field later tasks' UI additions sit alongside in `TextStep.svelte`.

### Step 1: Write the failing engine test for rotation

Add to `test/digitize.test.js` (append near the other `buildLetteringDesign` tests — search the file for `buildLetteringDesign:` to find them):

```js
test("buildLetteringDesign: rotationDeg 180 negates every stitch point relative to unrotated (upside-down = point negation about center)", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "AB", base);
  const d180 = DG.buildLetteringDesign(font, "AB", Object.assign({ rotationDeg: 180 }, base));
  assert.strictEqual(d180.stitches.length, d0.stitches.length, "rotation must not add/remove stitch records");
  for (let i = 0; i < d0.stitches.length; i++) {
    assert.strictEqual(d180.stitches[i].type, d0.stitches[i].type, `type mismatch at record ${i}`);
    assert.ok(Math.abs(d180.stitches[i].x - -d0.stitches[i].x) <= 1, `x mismatch at record ${i}: ${d180.stitches[i].x} vs ${-d0.stitches[i].x}`);
    assert.ok(Math.abs(d180.stitches[i].y - -d0.stitches[i].y) <= 1, `y mismatch at record ${i}: ${d180.stitches[i].y} vs ${-d0.stitches[i].y}`);
  }
  // 180 preserves the bounding box dimensions exactly (a rectangle rotated
  // 180 about its own center has the same axis-aligned bbox).
  assert.ok(Math.abs(d180.widthMM - d0.widthMM) < 0.5, "width should be unchanged at 180deg");
  assert.ok(Math.abs(d180.heightMM - d0.heightMM) < 0.5, "height should be unchanged at 180deg");
});

test("buildLetteringDesign: rotationDeg 90 swaps the reported width/height orientation and rotationDeg 0/absent is byte-identical to today", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "SD WHEEL", base);
  const dExplicit0 = DG.buildLetteringDesign(font, "SD WHEEL", Object.assign({ rotationDeg: 0 }, base));
  assert.deepStrictEqual(dExplicit0, d0, "rotationDeg:0 must be byte-identical to omitting it");
  const d90 = DG.buildLetteringDesign(font, "SD WHEEL", Object.assign({ rotationDeg: 90 }, base));
  // "SD WHEEL" is much wider than tall unrotated; rotated 90 it must become
  // much taller than wide.
  assert.ok(d0.widthMM > d0.heightMM * 2, "fixture assumption: unrotated text is landscape");
  assert.ok(d90.heightMM > d90.widthMM * 2, "rotated 90deg text must report portrait dimensions");
});
```

- [ ] Add the above two tests to `test/digitize.test.js`.

### Step 2: Run tests to verify they fail

Run: `node --test test/digitize.test.js 2>&1 | grep -A5 "rotationDeg"`
Expected: both new tests FAIL (rotationDeg is not yet a recognized option, so `d180`/`d90` come out identical to `d0`, and `dExplicit0` — while still equal to `d0` — doesn't matter yet; the meaningful failures are the `d180`/`d90` assertions).

### Step 3: Implement rotation in `buildLetteringDesign`

In `src/digitize.js`, inside `buildLetteringDesign` (around line 524), make these edits:

Locate this block (around line 559-571):

```js
    const scalePxToDst = sc * (1 / pxPerMm) * units.DST_UNITS_PER_MM;
    const finalMmPerPx = sc / pxPerMm;
    // Pass 2: generate at fit-corrected density so the FINAL satin spacing and
    // pull-comp land at the requested mm regardless of the fit scale (short text
    // scaled up would otherwise sew too sparse).
    const lay = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: densityMm / sc, pullCompMm: pullCompMm / sc, letterSpacingMm: ls, underlay: o.underlay !== false, arcDeg: o.arcDeg || 0 });
    if (!lay.runs.length) return empty;
    const cx = (bb.x0 + bb.x1) / 2, cy = (bb.y0 + bb.y1) / 2;
    // Explicit placement offset (Slice 3): applied AFTER the center transform, in
    // DST space — +x right, +y up (DST convention, already matches T()'s y-flip).
    const offXu = Math.round((o.offsetXMm || 0) * units.DST_UNITS_PER_MM);
    const offYu = Math.round((o.offsetYMm || 0) * units.DST_UNITS_PER_MM);
    const T = (q) => ({ x: Math.round((q.x - cx) * scalePxToDst) + offXu, y: Math.round((cy - q.y) * scalePxToDst) + offYu });
```

Replace with:

```js
    const scalePxToDst = sc * (1 / pxPerMm) * units.DST_UNITS_PER_MM;
    const finalMmPerPx = sc / pxPerMm;
    // Pass 2: generate at fit-corrected density so the FINAL satin spacing and
    // pull-comp land at the requested mm regardless of the fit scale (short text
    // scaled up would otherwise sew too sparse).
    const lay = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: densityMm / sc, pullCompMm: pullCompMm / sc, letterSpacingMm: ls, underlay: o.underlay !== false, arcDeg: o.arcDeg || 0 });
    if (!lay.runs.length) return empty;
    const cx = (bb.x0 + bb.x1) / 2, cy = (bb.y0 + bb.y1) / 2;
    // Explicit placement offset (Slice 3): applied AFTER the center transform, in
    // DST space — +x right, +y up (DST convention, already matches T()'s y-flip).
    const offXu = Math.round((o.offsetXMm || 0) * units.DST_UNITS_PER_MM);
    const offYu = Math.round((o.offsetYMm || 0) * units.DST_UNITS_PER_MM);
    // Whole-element rotation (Font editing abilities Round 1): a rigid rotation
    // of the ALREADY-centered, already-scaled point, applied BEFORE the
    // placement offset -- i.e. rotate the element about its own center, then
    // move the rotated result to its placed position. This never touches
    // column/satin geometry (routeGlyph/layoutText run identically regardless
    // of rotationDeg), so it carries zero stitch-quality risk -- same
    // reasoning as arcDeg/offsetXMm being pure placement, not generation,
    // concerns. rotationDeg=0 (absent) must be byte-identical to no rotation
    // at all: cosR=1/sinR=0 makes the rotated branch collapse to the original
    // px/py unchanged.
    const rotDeg = o.rotationDeg || 0;
    const rotRad = (rotDeg * Math.PI) / 180;
    const cosR = Math.cos(rotRad), sinR = Math.sin(rotRad);
    const T = (q) => {
      const px = (q.x - cx) * scalePxToDst, py = (cy - q.y) * scalePxToDst;
      const rx = rotDeg ? px * cosR - py * sinR : px;
      const ry = rotDeg ? px * sinR + py * cosR : py;
      return { x: Math.round(rx) + offXu, y: Math.round(ry) + offYu };
    };
```

Then locate the final return (around line 601-602):

```js
    const stitchCount = stitches.filter((s) => s.type === "stitch").length;
    return { stitches, colors, widthMM: designWmm, heightMM: designHmm, stitchCount, colorCount: 1, _debug: { nSatin, nFill: 0, nTrims } };
  }
```

Replace with:

```js
    const stitchCount = stitches.filter((s) => s.type === "stitch").length;
    // Rotation (other than a multiple of 180) changes the axis-aligned
    // bounding box relative to the unrotated glyph bbox (e.g. landscape text
    // rotated 90 becomes portrait) -- widthMM/heightMM must reflect the
    // ACTUAL rotated footprint (the field's stats line, SizePanel, and
    // hoop-clamping all ultimately trace back to this value for a
    // single-element project; see combine.js's bboxMmFromStitches for the
    // identical pattern used once multiple elements are combined). Gated on
    // rotDeg (falsy at 0/absent) so the overwhelmingly common unrotated case
    // -- including every existing test -- computes designWmm/designHmm
    // exactly as before, unchanged.
    let outWmm = designWmm, outHmm = designHmm;
    if (rotDeg) {
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const s of stitches) {
        if (s.type === "color" || s.type === "end") continue;
        if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x;
        if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y;
      }
      if (isFinite(minX)) {
        outWmm = (maxX - minX) / units.DST_UNITS_PER_MM;
        outHmm = (maxY - minY) / units.DST_UNITS_PER_MM;
      }
    }
    return { stitches, colors, widthMM: outWmm, heightMM: outHmm, stitchCount, colorCount: 1, _debug: { nSatin, nFill: 0, nTrims } };
  }
```

- [ ] Apply both edits to `src/digitize.js`.

### Step 4: Run tests to verify they pass

Run: `node --test test/digitize.test.js 2>&1 | tail -20`
Expected: PASS for both new tests, and the full file still passes overall.

Then run the full engine suite to confirm no regressions: `node --test 2>&1 | tail -10`
Expected: all tests pass (156 + 2 new = 158).

### Step 5: Commit the engine change

```bash
git add src/digitize.js test/digitize.test.js
git commit -m "Add rotationDeg to buildLetteringDesign (whole-element rotation)"
```

### Step 6: Add `rotationDeg` to the project model

In `app/src/lib/project.js`, in `defaultTextElement` (lines 6-20), add the field:

```js
export function defaultTextElement(id) {
  return {
    id,
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}
```

- [ ] Add `rotationDeg: 0,` to `defaultTextElement`.

### Step 7: Thread `rotationDeg` through `generate.js`

In `app/src/lib/generate.js`, in the text branch of `generateElement` (lines 41-49), add the field:

```js
  return EMB.buildLetteringDesign(fontData, text, {
    garment, pxPerMm: 8, densityMm: 0.4, underlay: element.underlay,
    rgb: element.colorRgb,
    targetWidthMm: element.sizeMm || undefined,
    offsetXMm: element.offsetXMm || 0,
    offsetYMm: element.offsetYMm || 0,
    letterSpacingMm: element.letterSpacingMm || 0,
    arcDeg: element.arcDeg || 0,
    rotationDeg: element.rotationDeg || 0,
  });
```

- [ ] Add `rotationDeg: element.rotationDeg || 0,` to the `buildLetteringDesign` call in `generate.js`.

### Step 8: Write the failing app-level test

Add to `app/src/lib/generate.spec.js` (append after the existing text tests):

```js
test("generateElement: rotationDeg 180 flips the reported bbox — heightMM stays the same as unrotated (fixture is landscape)", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const flat = generateElement(textElement({ text: "SD WHEEL" }), garment, {});
  const rotated = generateElement(textElement({ text: "SD WHEEL", rotationDeg: 180 }), garment, {});
  expect(Math.abs(rotated.widthMM - flat.widthMM)).toBeLessThan(0.5);
  expect(Math.abs(rotated.heightMM - flat.heightMM)).toBeLessThan(0.5);
});
```

Also update the `textElement()` helper (lines 14-20) to include the new field so every test using it stays representative of the real default shape:

```js
function textElement(overrides = {}) {
  return {
    id: "e1", type: "text", text: "", fontKey: "geneva_simple",
    colorRgb: [20, 20, 20], letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true,
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, ...overrides,
  };
}
```

- [ ] Apply both edits to `app/src/lib/generate.spec.js`.

### Step 9: Run app tests to verify pass

Run: `cd app && npx vitest run src/lib/generate.spec.js`
Expected: all pass, including the new test.

### Step 10: Update the `project.spec.js` default-shape assertion

`app/src/lib/project.spec.js` has a hardcoded literal-object assertion (around lines 30-45) that every new `defaultTextElement` field must be added to:

```js
test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    letterSpacingMm: 0,
    arcDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});
```

Replace with:

```js
test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});
```

(The `toEqual(defaultTextElement("e1"))` assertion at line 22, inside `"defaultProject has sane v2 beginner defaults"`, compares against the live function's own output on both sides — it needs no edit and will stay correct automatically as fields are added.)

- [ ] Apply this edit to `app/src/lib/project.spec.js`.
- [ ] Run `cd app && npx vitest run src/lib/project.spec.js` — expect PASS.

### Step 11: Commit the app-model change

```bash
git add app/src/lib/project.js app/src/lib/generate.js app/src/lib/generate.spec.js app/src/lib/project.spec.js
git commit -m "Thread rotationDeg through the text-element project model"
```

(Omit `project.spec.js` from the `git add` if Step 10 made no changes to it.)

### Step 12: Add the rotation UI to `TextStep.svelte`

Current `app/src/ui/TextStep.svelte` ends with the Curve slider (around lines 46-57):

```svelte
<label class="letterspacing">
  <span>Curve</span>
  <input
    type="range"
    min="-180"
    max="180"
    step="10"
    value={element.arcDeg || 0}
    on:input={(e) => patch({ arcDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.arcDeg || 0}°</span>
</label>
```

Add a Rotation control right after it:

```svelte
<label class="letterspacing">
  <span>Curve</span>
  <input
    type="range"
    min="-180"
    max="180"
    step="10"
    value={element.arcDeg || 0}
    on:input={(e) => patch({ arcDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.arcDeg || 0}°</span>
</label>
<label class="letterspacing">
  <span>Rotation</span>
  <input
    type="range"
    min="0"
    max="360"
    step="5"
    value={element.rotationDeg || 0}
    on:input={(e) => patch({ rotationDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.rotationDeg || 0}°</span>
</label>
<button
  type="button"
  class="upsidedown"
  on:click={() => patch({ rotationDeg: (element.rotationDeg || 0) === 180 ? 0 : 180 })}
>
  {(element.rotationDeg || 0) === 180 ? "Right-side up" : "Flip upside-down"}
</button>
```

Add a small style for the new button at the bottom of the `<style>` block (check the file's existing `<style>` section — if TextStep.svelte doesn't have one yet, add one; otherwise append):

```css
.upsidedown {
  margin-top: 8px;
  padding: 6px 12px;
  border: 1px solid var(--tint-border, #ccd6fb);
  border-radius: var(--radius-s, 6px);
  background: var(--surface, #fff);
  cursor: pointer;
  font-size: var(--fs-xs, 12px);
}
```

- [ ] Apply the markup and style edits to `app/src/ui/TextStep.svelte`. (Check the file's actual current `<style>` block content first via Read before appending, since other tasks in this plan also touch it — merge, don't overwrite.)

### Step 13: Rebuild the engine copy and start the dev server

```bash
node tools/bundle.mjs
cd app && node scripts/copy-engine.mjs
```

- [ ] Run both commands.
- [ ] Start (or confirm already running) the Studio dev server (`cd app && npm run dev`, or attach via the preview tool if one is already up on port 5173).

### Step 14: Live-verify rotation in the browser

- [ ] Navigate to the Studio app, go to Content step, add/select a text element, type a short word.
- [ ] Go to Review step. Confirm the "Rotation" slider and "Flip upside-down" button appear below Curve.
- [ ] Drag the Rotation slider to ~90 and confirm the word visibly turns sideways in the field.
- [ ] Click "Flip upside-down" and confirm the word renders upside-down (letters inverted, reading order reversed) and the button label changes to "Right-side up".
- [ ] Click it again and confirm the word returns to normal and the label reverts.
- [ ] Confirm the stats line ("NNN stitches · WxH mm") updates its width/height sensibly as rotation changes (not frozen at the unrotated values).

### Step 15: Commit the UI change

```bash
git add app/src/ui/TextStep.svelte EMB-Bot-standalone.html
git commit -m "Add rotation slider and upside-down toggle to TextStep"
```

---

## Task 2: Per-letter color ranges

**Files:**
- Modify: `src/satinfont.js` (`layoutText`, currently lines 216-322)
- Modify: `src/digitize.js` (`buildLetteringDesign`, as left by Task 1)
- Modify: `app/src/lib/generate.js`
- Modify: `app/src/lib/project.js`
- Create: `app/src/ui/ColorRangesEditor.svelte`
- Modify: `app/src/ui/TextStep.svelte`
- Test: `test/satinfont.test.js`
- Test: `test/digitize.test.js`
- Test: `app/src/lib/generate.spec.js`
- No isolated component test for `ColorRangesEditor.svelte`: confirmed during plan research that this project has zero `app/src/ui/*.spec.js` files and no `@testing-library/svelte` (or equivalent) dependency — every other `.svelte` component in this codebase is covered by engine-level `.spec.js` tests plus live browser verification, not isolated component tests. Follow that existing pattern rather than introducing new test tooling for one component; Step 8's `generate.spec.js` test plus this task's Step 18 live-verification are the coverage for this feature.

**Interfaces:**
- Consumes: `buildLetteringDesign`'s rotation change from Task 1 is unrelated and untouched by this task.
- Produces: `layoutText`'s returned `runs` entries gain a `charIdx` field (integer, index into the original `text` string, `\n` counted as one position, matching `text.slice(startIdx, endIdx)` semantics). `buildLetteringDesign` accepts `opts.colorRanges` (array of `{ startIdx, endIdx, colorRgb: [r,g,b] }`, `startIdx` inclusive / `endIdx` exclusive). `element.colorRanges` (array, default `[]`) is the new project-model field.

### Step 1: Write the failing engine test for `charIdx` tagging

Add to `test/satinfont.test.js` (append near the top-level tests, after the existing straight-layout snapshot test — search for `layoutText: straight single-line`):

```js
test("layoutText: each run carries the charIdx of its source character, matching the original string's index", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false };
  const lay = SF.layoutText(font, "AB", opts);
  // "AB" — every run belongs to either char 0 ("A") or char 1 ("B").
  const idxs = new Set(lay.runs.map((r) => r.charIdx));
  assert.deepStrictEqual([...idxs].sort(), [0, 1]);
  // Runs for "A" all come before runs for "B" (glyphs are placed left to right).
  const firstBIdx = lay.runs.findIndex((r) => r.charIdx === 1);
  assert.ok(lay.runs.slice(0, firstBIdx).every((r) => r.charIdx === 0), "all runs before the first B-run belong to char 0");
});

test("layoutText: charIdx accounts for a skipped space and a newline exactly like the original string's indices", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false };
  // "A B\nC" -> indices: A=0, space=1, B=2, \n=3, C=4
  const lay = SF.layoutText(font, "A B\nC", opts);
  const idxs = new Set(lay.runs.map((r) => r.charIdx));
  assert.deepStrictEqual([...idxs].sort((a, b) => a - b), [0, 2, 4], "space(1) and newline(3) produce no glyph runs, so their indices never appear");
});
```

- [ ] Add both tests to `test/satinfont.test.js`.

### Step 2: Run tests to verify they fail

Run: `node --test test/satinfont.test.js 2>&1 | grep -B2 -A8 "charIdx"`
Expected: FAIL — `r.charIdx` is `undefined` on every run.

### Step 3: Implement `charIdx` tagging in `layoutText`

In `src/satinfont.js`, locate the MEASURE pass (around lines 232-246):

```js
    const lineList = String(text).split("\n").map((lineText) => {
      const chars = Array.from(lineText);
      let penX = 0, prev = null;
      const glyphs = [];
      for (const ch of chars) {
        if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
        const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
        if (!g) { penX += font.advDefault; prev = null; continue; }
        if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
        glyphs.push({ g, ox: penX });
        penX += g.adv + lsUnits;
        prev = ch;
      }
      return { glyphs, adv: penX };
    });
```

Replace with:

```js
    // charIdx (Font editing abilities Round 1, per-letter color): the index
    // of each glyph's SOURCE CHARACTER in the original `text` string,
    // counting "\n" as one position — matching a <textarea>'s native
    // selectionStart/selectionEnd exactly, so the UI can let a user select
    // text and tag that range with a color with zero custom index math.
    const rawLines = String(text).split("\n");
    let globalIdx = 0;
    const lineList = rawLines.map((lineText, lineNum) => {
      const chars = Array.from(lineText);
      let penX = 0, prev = null;
      const glyphs = [];
      for (const ch of chars) {
        const charIdx = globalIdx++;
        if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
        const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
        if (!g) { penX += font.advDefault; prev = null; continue; }
        if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
        glyphs.push({ g, ox: penX, charIdx });
        penX += g.adv + lsUnits;
        prev = ch;
      }
      if (lineNum < rawLines.length - 1) globalIdx++; // the "\n" separator itself
      return { glyphs, adv: penX };
    });
```

Then locate the PLACEMENT pass's glyph loop (around lines 272-282 and 314-318):

```js
      for (const { g, ox } of line.glyphs) {
```

Replace with:

```js
      for (const { g, ox, charIdx } of line.glyphs) {
```

And a few lines down:

```js
        for (const r of gRuns) {
          const pts = r.pts.map(place);
          for (const q of pts) acc(q);
          runs.push({ pts, kind: r.kind, jump: r.jump });
        }
```

Replace with:

```js
        for (const r of gRuns) {
          const pts = r.pts.map(place);
          for (const q of pts) acc(q);
          runs.push({ pts, kind: r.kind, jump: r.jump, charIdx });
        }
```

- [ ] Apply all four edits to `src/satinfont.js`.

### Step 4: Run tests to verify they pass

Run: `node --test test/satinfont.test.js 2>&1 | tail -20`
Expected: PASS for both new tests.

Run the full engine suite: `node --test 2>&1 | tail -10`
Expected: all pass (158 + 2 = 160; unaffected existing tests don't read `charIdx` so adding the field is purely additive).

### Step 5: Commit

```bash
git add src/satinfont.js test/satinfont.test.js
git commit -m "Tag layoutText runs with their source character index"
```

### Step 6: Write the failing engine test for `colorRanges`

Add to `test/digitize.test.js` (near the other `buildLetteringDesign` tests):

```js
test("buildLetteringDesign: colorRanges absent/empty is byte-identical to today's single-color output", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false, rgb: [10, 20, 30] };
  const dNoField = DG.buildLetteringDesign(font, "AB", base);
  const dEmpty = DG.buildLetteringDesign(font, "AB", Object.assign({ colorRanges: [] }, base));
  assert.deepStrictEqual(dEmpty, dNoField);
  assert.strictEqual(dNoField.colors.length, 1);
  assert.ok(!dNoField.stitches.some((s) => s.type === "color"), "no color-change record when there's only one color");
});

test("buildLetteringDesign: a colorRange covering only the first character inserts exactly one trim+color pair at the glyph boundary", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const d = DG.buildLetteringDesign(font, "AB", {
    garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false,
    rgb: [10, 20, 30], colorRanges: [{ startIdx: 0, endIdx: 1, colorRgb: [200, 30, 30] }],
  });
  assert.strictEqual(d.colors.length, 2, "range color + base color");
  assert.deepStrictEqual([d.colors[0].r, d.colors[0].g, d.colors[0].b], [200, 30, 30], "the FIRST-used color is the range's, since char 0 sews first");
  assert.deepStrictEqual([d.colors[1].r, d.colors[1].g, d.colors[1].b], [10, 20, 30]);
  const colorChangeIdxs = d.stitches.map((s, i) => (s.type === "color" ? i : -1)).filter((i) => i >= 0);
  assert.strictEqual(colorChangeIdxs.length, 1, "exactly one color-change boundary for one range covering one of two characters");
  // Every "color" record is immediately preceded by a "trim" record at the same point.
  const ci = colorChangeIdxs[0];
  assert.strictEqual(d.stitches[ci - 1].type, "trim");
  assert.strictEqual(d.stitches[ci - 1].x, d.stitches[ci].x);
  assert.strictEqual(d.stitches[ci - 1].y, d.stitches[ci].y);
});

test("buildLetteringDesign: a colorRange spanning the WHOLE string produces only one color and no color-change records", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const d = DG.buildLetteringDesign(font, "AB", {
    garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false,
    rgb: [10, 20, 30], colorRanges: [{ startIdx: 0, endIdx: 2, colorRgb: [200, 30, 30] }],
  });
  assert.strictEqual(d.colors.length, 1);
  assert.ok(!d.stitches.some((s) => s.type === "color"));
});
```

- [ ] Add all three tests to `test/digitize.test.js`.

### Step 7: Run tests to verify they fail

Run: `node --test test/digitize.test.js 2>&1 | grep -B2 -A10 "colorRange"`
Expected: FAIL — `colorRanges` isn't read yet, so every case produces the single base color with no color-change records (the first and third tests may accidentally pass already; the second must fail).

### Step 8: Implement `colorRanges` in `buildLetteringDesign`

In `src/digitize.js`, inside `buildLetteringDesign`, locate the stitch-emission section (this is immediately after the `T`/rotation block Task 1 added, replacing the current lines ~576-600):

```js
    const stitches = [];
    const colors = [{ r: rgb[0], g: rgb[1], b: rgb[2], name: "Color 1" }];
    const maxStitchMm = o.maxStitchMm || 4;
    const maxStepPx = maxStitchMm / finalMmPerPx;   // longest single stitch (px)
    let nTrims = 0, nSatin = 0, lastPt = null;
    // The router (satinfont) decides jump vs. underpath per run: jump=false means
    // travel as a needle-DOWN running connector (tucked at a junction, covered);
    // jump=true means lift the needle (and trim if the hop is long).
    for (const run of lay.runs) {
      const pts = run.pts;
      if (!pts || pts.length < 2) continue;
      if (run.kind === "satin") nSatin++;
      const start = pts[0];
      if (!lastPt) {
        const f = T(start); stitches.push({ x: f.x, y: f.y, type: "jump" });
      } else if (run.jump) {
        const gapMm = Math.hypot(start.x - lastPt.x, start.y - lastPt.y) * finalMmPerPx;
        if (gapMm > trimAtMm) { const tp = T(lastPt); stitches.push({ x: tp.x, y: tp.y, type: "trim" }); nTrims++; }
        const f = T(start); stitches.push({ x: f.x, y: f.y, type: "jump" });
      } else {
        const gap = Math.hypot(start.x - lastPt.x, start.y - lastPt.y);
        const steps = Math.max(1, Math.ceil(gap / maxStepPx));
        for (let s = 1; s <= steps; s++) { const t = s / steps; const d = T({ x: lastPt.x + (start.x - lastPt.x) * t, y: lastPt.y + (start.y - lastPt.y) * t }); stitches.push({ x: d.x, y: d.y, type: "stitch" }); }
      }
      for (const q of pts) { const d = T(q); stitches.push({ x: d.x, y: d.y, type: "stitch" }); }
      lastPt = pts[pts.length - 1];
    }
```

Replace with:

```js
    // Per-letter color (Font editing abilities Round 1): colorRanges is a
    // list of { startIdx, endIdx, colorRgb } over the ORIGINAL text string's
    // indices (startIdx inclusive, endIdx exclusive — matches
    // text.slice(startIdx,endIdx) / a <textarea>'s selectionStart/End, see
    // layoutText's charIdx tagging). A character not covered by any range
    // uses the element's base `rgb`. Overlapping ranges resolve to whichever
    // one appears FIRST in the array. colorRanges absent/empty means every
    // charIdx resolves to the base rgb, which reproduces today's exact
    // single-color output (colors.length stays 1, no "color" records).
    const colorRanges = Array.isArray(o.colorRanges) ? o.colorRanges : [];
    function colorForCharIdx(idx) {
      for (const r of colorRanges) { if (idx >= r.startIdx && idx < r.endIdx) return r.colorRgb; }
      return rgb;
    }
    const stitches = [];
    const colors = [];
    let curRgb = null;
    function ensureColor(targetRgb) {
      if (curRgb && targetRgb[0] === curRgb[0] && targetRgb[1] === curRgb[1] && targetRgb[2] === curRgb[2]) return;
      colors.push({ r: targetRgb[0], g: targetRgb[1], b: targetRgb[2], name: "Color " + (colors.length + 1) });
      curRgb = targetRgb;
    }
    const maxStitchMm = o.maxStitchMm || 4;
    const maxStepPx = maxStitchMm / finalMmPerPx;   // longest single stitch (px)
    let nTrims = 0, nSatin = 0, lastPt = null, forceJumpNext = false;
    // The router (satinfont) decides jump vs. underpath per run: jump=false means
    // travel as a needle-DOWN running connector (tucked at a junction, covered);
    // jump=true means lift the needle (and trim if the hop is long).
    for (const run of lay.runs) {
      const pts = run.pts;
      if (!pts || pts.length < 2) continue;
      if (run.kind === "satin") nSatin++;
      const runRgb = colorForCharIdx(run.charIdx);
      if (curRgb === null) {
        ensureColor(runRgb);
      } else if (runRgb[0] !== curRgb[0] || runRgb[1] !== curRgb[1] || runRgb[2] !== curRgb[2]) {
        // Color-range boundary: trim (needle up) + color-change marker at the
        // last sewn point, same pattern app/src/lib/combine.js already uses
        // to splice separate elements together.
        if (lastPt) { const tp = T(lastPt); stitches.push({ x: tp.x, y: tp.y, type: "trim" }); stitches.push({ x: tp.x, y: tp.y, type: "color" }); nTrims++; }
        ensureColor(runRgb);
        forceJumpNext = true;
      }
      const start = pts[0];
      if (!lastPt) {
        const f = T(start); stitches.push({ x: f.x, y: f.y, type: "jump" });
      } else if (run.jump || forceJumpNext) {
        const gapMm = Math.hypot(start.x - lastPt.x, start.y - lastPt.y) * finalMmPerPx;
        if (gapMm > trimAtMm && !forceJumpNext) { const tp = T(lastPt); stitches.push({ x: tp.x, y: tp.y, type: "trim" }); nTrims++; }
        const f = T(start); stitches.push({ x: f.x, y: f.y, type: "jump" });
        forceJumpNext = false;
      } else {
        const gap = Math.hypot(start.x - lastPt.x, start.y - lastPt.y);
        const steps = Math.max(1, Math.ceil(gap / maxStepPx));
        for (let s = 1; s <= steps; s++) { const t = s / steps; const d = T({ x: lastPt.x + (start.x - lastPt.x) * t, y: lastPt.y + (start.y - lastPt.y) * t }); stitches.push({ x: d.x, y: d.y, type: "stitch" }); }
      }
      for (const q of pts) { const d = T(q); stitches.push({ x: d.x, y: d.y, type: "stitch" }); }
      lastPt = pts[pts.length - 1];
    }
```

Note: `colors` is now built incrementally instead of pre-seeded — the rest of the function (the `stitchCount`/`outWmm`/return block Task 1 left in place) is unchanged and already reads `colors` by reference, so no further edit is needed there.

- [ ] Apply this replacement to `src/digitize.js`.

### Step 9: Run tests to verify they pass

Run: `node --test test/digitize.test.js 2>&1 | tail -25`
Expected: PASS for all three new tests.

Run the full engine suite: `node --test 2>&1 | tail -10`
Expected: all pass (160 + 3 = 163).

### Step 10: Commit

```bash
git add src/digitize.js test/digitize.test.js
git commit -m "Add per-letter colorRanges to buildLetteringDesign"
```

### Step 11: Add `colorRanges` to the project model and thread it through `generate.js`

In `app/src/lib/project.js`'s `defaultTextElement` (as left by Task 1), add:

```js
export function defaultTextElement(id) {
  return {
    id,
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}
```

In `app/src/lib/generate.js`'s text branch (as left by Task 1), add:

```js
  return EMB.buildLetteringDesign(fontData, text, {
    garment, pxPerMm: 8, densityMm: 0.4, underlay: element.underlay,
    rgb: element.colorRgb,
    colorRanges: element.colorRanges || [],
    targetWidthMm: element.sizeMm || undefined,
    offsetXMm: element.offsetXMm || 0,
    offsetYMm: element.offsetYMm || 0,
    letterSpacingMm: element.letterSpacingMm || 0,
    arcDeg: element.arcDeg || 0,
    rotationDeg: element.rotationDeg || 0,
  });
```

- [ ] Apply both edits.

### Step 12: Write the failing app-level test

Add to `app/src/lib/generate.spec.js`:

```js
test("generateElement: a colorRange covering the first character produces a second thread color", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const d = generateElement(
    textElement({ text: "AB", colorRanges: [{ startIdx: 0, endIdx: 1, colorRgb: [200, 30, 30] }] }),
    garment,
    {}
  );
  expect(d.colors.length).toBe(2);
  expect(d.colors[0]).toMatchObject({ r: 200, g: 30, b: 30 });
});
```

Update the `textElement()` helper again to include `colorRanges: []`:

```js
function textElement(overrides = {}) {
  return {
    id: "e1", type: "text", text: "", fontKey: "geneva_simple",
    colorRgb: [20, 20, 20], colorRanges: [], letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true,
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, ...overrides,
  };
}
```

- [ ] Apply both edits to `app/src/lib/generate.spec.js`.

Also update the `defaultTextElement` shape assertion in `app/src/lib/project.spec.js` (as left by Task 1 Step 10) to add `colorRanges: []` right after `colorRgb`:

```js
test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});
```

- [ ] Apply this edit to `app/src/lib/project.spec.js`.

### Step 13: Run app tests to verify pass

Run: `cd app && npx vitest run src/lib/generate.spec.js src/lib/project.spec.js`
Expected: all pass.

### Step 14: Commit

```bash
git add app/src/lib/project.js app/src/lib/generate.js app/src/lib/generate.spec.js app/src/lib/project.spec.js
git commit -m "Thread colorRanges through the text-element project model"
```

### Step 15: Build the `ColorRangesEditor` component

Create `app/src/ui/ColorRangesEditor.svelte`:

```svelte
<script>
  import { createEventDispatcher } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";

  // Per-letter color ranges editor (Font editing abilities Round 1).
  // Owns none of the actual <textarea> -- TextStep.svelte owns that DOM node
  // and tracks its own selectionStart/selectionEnd, passing the live
  // selection down here as `selection` ({start,end}|null). Range indices
  // match text.slice(startIdx,endIdx) exactly (see layoutText's charIdx
  // tagging in src/satinfont.js), so no custom index math is needed anywhere
  // in this component -- selection.start/end ARE startIdx/endIdx.
  export let text = "";
  export let colorRanges = [];
  export let selection = null; // {start, end} | null

  const d = createEventDispatcher();

  function addRange(rgb) {
    if (!selection) return;
    const next = [...colorRanges, { startIdx: selection.start, endIdx: selection.end, colorRgb: rgb }];
    d("change", next);
  }
  function removeRange(i) {
    const next = colorRanges.filter((_, idx) => idx !== i);
    d("change", next);
  }
</script>

<div class="colorranges">
  {#if selection}
    <div class="cr-pending">
      <span class="cr-label">Color "{text.slice(selection.start, selection.end)}":</span>
      <ThreadPicker rgb={[20, 20, 20]} compact on:pick={(e) => addRange(e.detail)} />
    </div>
  {/if}
  {#if colorRanges.length}
    <ul class="cr-list">
      {#each colorRanges as r, i (i)}
        <li>
          <span class="cr-swatch" style="background: rgb({r.colorRgb[0]},{r.colorRgb[1]},{r.colorRgb[2]})"></span>
          <span class="cr-text">"{text.slice(r.startIdx, r.endIdx)}"</span>
          <button type="button" class="cr-remove" aria-label="Remove color range" on:click={() => removeRange(i)}>×</button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .colorranges { margin-top: 8px; }
  .cr-pending { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .cr-label { font-size: var(--fs-xs, 12px); }
  .cr-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .cr-list li { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs, 12px); }
  .cr-swatch { width: 14px; height: 14px; border-radius: 3px; border: 1px solid var(--tint-border, #ccd6fb); display: inline-block; }
  .cr-remove { border: none; background: none; cursor: pointer; font-size: 14px; line-height: 1; color: var(--danger, #c0392b); }
</style>
```

- [ ] Create this file exactly as shown.

### Step 16: Wire selection tracking and the editor into `TextStep.svelte`

In `app/src/ui/TextStep.svelte`, add selection tracking and mount the new component. The current textarea (lines 24-30):

```svelte
<textarea
  class="textin"
  rows="2"
  value={element.text}
  on:input={(e) => patch({ text: e.target.value })}
  placeholder="Type a name or word"
></textarea>
```

Replace with:

```svelte
<textarea
  bind:this={textareaEl}
  class="textin"
  rows="2"
  value={element.text}
  on:input={(e) => patch({ text: e.target.value })}
  on:select={updateSelection}
  on:mouseup={updateSelection}
  on:keyup={updateSelection}
  placeholder="Type a name or word"
></textarea>
<ColorRangesEditor
  text={element.text}
  colorRanges={element.colorRanges || []}
  {selection}
  on:change={(e) => patch({ colorRanges: e.detail })}
/>
```

In the `<script>` block, add the import and the selection-tracking state/handler (near the top, after the existing imports):

```js
  import FontSelect from "./FontSelect.svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import ColorRangesEditor from "./ColorRangesEditor.svelte";
  import { createEventDispatcher } from "svelte";

  export let element;
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // Per-letter color (Font editing abilities Round 1): tracks the textarea's
  // OWN native selection (selectionStart/selectionEnd) so ColorRangesEditor
  // can offer "color the highlighted text" without any custom range-picker
  // widget. null (no/collapsed selection) hides that offer.
  let textareaEl;
  let selection = null;
  function updateSelection() {
    if (!textareaEl) return;
    const s = textareaEl.selectionStart, e = textareaEl.selectionEnd;
    selection = e > s ? { start: s, end: e } : null;
  }
```

- [ ] Apply all edits to `app/src/ui/TextStep.svelte`.

### Step 17: Rebuild and start the dev server

```bash
node tools/bundle.mjs
cd app && node scripts/copy-engine.mjs
```

- [ ] Run both commands (dev server should already be running from Task 1; if not, start it).

### Step 18: Live-verify per-letter color in the browser

- [ ] In the Studio app's Content step, type a short word (e.g. "Kent") in a text element.
- [ ] Select just the first letter with the mouse in the textarea.
- [ ] Confirm a "Color 'K':" prompt with a thread swatch picker appears below the textarea.
- [ ] Pick a color (e.g. gold) and confirm it's added to a list below, showing the swatch and `"K"`.
- [ ] Go to Review and confirm the first letter now renders in the picked color while the rest stays the base color.
- [ ] Return to Content, click the "×" next to the range, confirm it's removed and the letter reverts to the base color in Review.

### Step 19: Commit

```bash
git add app/src/ui/ColorRangesEditor.svelte app/src/ui/TextStep.svelte EMB-Bot-standalone.html
git commit -m "Add per-letter color range picker to TextStep"
```

---

## Task 3: Bold weight presets

**Files:**
- Modify: `src/digitize.js` (`buildLetteringDesign`, as left by Task 2)
- Modify: `app/src/lib/generate.js`
- Modify: `app/src/lib/project.js`
- Modify: `app/src/ui/TextStep.svelte`
- Test: `test/digitize.test.js`
- Test: `app/src/lib/generate.spec.js`

**Interfaces:**
- Consumes: nothing new from Tasks 1-2.
- Produces: `buildLetteringDesign` accepts `opts.weightPreset` (`"thin" | "normal" | "bold"`, default `"normal"`). `element.weightPreset` (string, default `"normal"`) is the new project-model field.

### Step 1: Write the failing engine test

Add to `test/digitize.test.js`:

```js
test("buildLetteringDesign: weightPreset 'normal' (or absent) is byte-identical to today's output", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const dNoField = DG.buildLetteringDesign(font, "Kent", base);
  const dNormal = DG.buildLetteringDesign(font, "Kent", Object.assign({ weightPreset: "normal" }, base));
  assert.deepStrictEqual(dNormal, dNoField);
});

test("buildLetteringDesign: weightPreset 'bold' widens satin cross-stitches vs 'thin', measured on the same glyph", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  function avgCrossWidth(design) {
    // Consecutive "stitch" records alternate rail-A/rail-B in a satin run;
    // the width-spanning crosses are adjacent pairs. Average the distance
    // between EVERY adjacent stitch pair as a coarse but monotonic proxy for
    // "how wide is this column" -- sufficient to confirm bold > thin without
    // needing to reconstruct which pairs are crosses vs connectors.
    let sum = 0, n = 0, prev = null;
    for (const s of design.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) { sum += Math.hypot(s.x - prev.x, s.y - prev.y); n++; }
      prev = s;
    }
    return n ? sum / n : 0;
  }
  const thin = DG.buildLetteringDesign(font, "H", Object.assign({ weightPreset: "thin" }, base));
  const bold = DG.buildLetteringDesign(font, "H", Object.assign({ weightPreset: "bold" }, base));
  assert.ok(avgCrossWidth(bold) > avgCrossWidth(thin), `bold avg spacing (${avgCrossWidth(bold)}) should exceed thin's (${avgCrossWidth(thin)})`);
});
```

- [ ] Add both tests to `test/digitize.test.js`.

### Step 2: Run tests to verify they fail

Run: `node --test test/digitize.test.js 2>&1 | grep -B2 -A8 "weightPreset"`
Expected: the first test passes trivially (nothing reads weightPreset yet, so both calls are already identical) — that's fine, it's a forward-looking regression pin. The second test FAILS (`thin` and `bold` produce identical output today).

### Step 3: Implement `weightPreset` in `buildLetteringDesign`

In `src/digitize.js`, inside `buildLetteringDesign`, locate the `pullCompMm` line (around line 532, right after `densityMm`):

```js
    const pullCompMm = (fabric && fabric.pullCompMm != null) ? fabric.pullCompMm : (o.pullCompMm == null ? 0.2 : o.pullCompMm);
```

Replace with:

```js
    // Bold/thin (Font editing abilities Round 1): reuses the EXISTING,
    // already-tested pullCompMm column-widening mechanism (satinplay.js's
    // emitZigzag pushes the two rails apart by pullCompMm/2 each) instead of
    // any new geometry -- pullCompMm was built for fabric-pull compensation,
    // but geometrically "push the rails apart by N mm" is exactly what a
    // bolder stroke needs too. "normal" adds 0, so it's byte-identical to
    // today. These two constants are a starting point verified against the
    // default font's tightest letterforms in this task's own steps below;
    // if a different font's tightest glyph collapses a counter at "bold",
    // shrink WEIGHT_OFFSET_MM.bold rather than adding new mechanism.
    const WEIGHT_OFFSET_MM = { thin: -0.15, normal: 0, bold: 0.3 };
    const weightPreset = (o.weightPreset && WEIGHT_OFFSET_MM[o.weightPreset] != null) ? o.weightPreset : "normal";
    const pullCompMm = ((fabric && fabric.pullCompMm != null) ? fabric.pullCompMm : (o.pullCompMm == null ? 0.2 : o.pullCompMm)) + WEIGHT_OFFSET_MM[weightPreset];
```

- [ ] Apply this edit to `src/digitize.js`.

### Step 4: Run tests to verify they pass

Run: `node --test test/digitize.test.js 2>&1 | tail -15`
Expected: both PASS.

Run the full engine suite: `node --test 2>&1 | tail -10`
Expected: all pass (163 + 2 = 165).

### Step 5: Empirically verify "bold" against the tightest letterforms

This step is the real safety check the spec called for — the two constants above are a starting guess, not yet validated against real glyphs with tight counters. Write this script to your session's scratchpad directory (NOT the repo — it's throwaway), e.g. `render_bold_check.mjs`:

```js
import { createRequire } from "module";
import fs from "node:fs";
const require = createRequire(import.meta.url);
global.window = global;
const DG = require("C:/Users/EE-LT-11030/EMB-Bot/src/digitize.js");
const D = require("C:/Users/EE-LT-11030/EMB-Bot/src/dst.js");

const FONTS = ["geneva_simple", "apex_simple_AGS", "aventurina"];
const TEXT = "eaogm"; // tightest-countered lowercase letters + one wide letter
const garment = { widthIn: 8, heightIn: 8 };

for (const fontKey of FONTS) {
  const font = JSON.parse(fs.readFileSync(`C:/Users/EE-LT-11030/EMB-Bot/src/fonts/${fontKey}.json`, "utf8"));
  for (const weightPreset of ["thin", "normal", "bold"]) {
    const design = DG.buildLetteringDesign(font, TEXT, {
      garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false, weightPreset,
    });
    const base = `boldcheck_${fontKey}_${weightPreset}`;
    fs.writeFileSync(`${base}.dst`, Buffer.from(D.encodeDST(design)));
    fs.writeFileSync(`${base}_colors.json`, JSON.stringify(design.colors.map((c) => [c.r, c.g, c.b])));
    console.log(`${base}: ${design.stitchCount} stitches`);
  }
}
```

- [ ] Run it from the scratchpad directory: `node render_bold_check.mjs`, then render each of the 9 resulting `.dst` files to PNG at a large scale so counters are clearly visible: `node C:/Users/EE-LT-11030/EMB-Bot/tools/render-dst.mjs boldcheck_<fontKey>_<weightPreset>.dst boldcheck_<fontKey>_<weightPreset>.png 15 boldcheck_<fontKey>_<weightPreset>_colors.json` (repeat for all 9 combinations).
- [ ] View each "bold" PNG and confirm no counter (the hole in e/a/o/g) has visibly collapsed shut, and no two adjacent strokes have visibly merged into a solid blob. Compare against the matching "thin"/"normal" PNG for the same font as a reference.
- [ ] If any font/glyph looks wrong at `bold: 0.3`, reduce the constant in `src/digitize.js`'s `WEIGHT_OFFSET_MM` (try `0.2`), re-run the script, and re-render just the failing font/preset combination to confirm it's now clean.
- [ ] If a reduction was needed, re-run `node --test test/digitize.test.js` to confirm the "bold widens vs thin" test still passes at the new value (it will, since any positive `bold` value is wider than any negative `thin` value).
- [ ] Delete the throwaway script and all rendered files from the scratchpad (they're diagnostic only, not part of the deliverable).

### Step 6: Commit

```bash
git add src/digitize.js test/digitize.test.js
git commit -m "Add weightPreset (thin/normal/bold) to buildLetteringDesign"
```

### Step 7: Add `weightPreset` to the project model and thread it through `generate.js`

In `app/src/lib/project.js`'s `defaultTextElement` (as left by Task 2), add `weightPreset: "normal",` right after `colorRanges: []`:

```js
export function defaultTextElement(id) {
  return {
    id,
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    weightPreset: "normal",
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}
```

In `app/src/lib/generate.js`'s text branch (as left by Task 2), add `weightPreset: element.weightPreset || "normal",`.

Update the `defaultTextElement` shape assertion in `app/src/lib/project.spec.js` (as left by Task 2 Step 12) to match:

```js
test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    weightPreset: "normal",
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});
```

- [ ] Apply all three edits (`project.js`, `generate.js`, `project.spec.js`).
- [ ] Run `cd app && npx vitest run src/lib/project.spec.js` — expect PASS.

### Step 8: Write the failing app-level test

Add to `app/src/lib/generate.spec.js`:

```js
test("generateElement: weightPreset 'bold' produces a wider average stitch spacing than 'thin' for the same text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  function avgSpacing(d) {
    let sum = 0, n = 0, prev = null;
    for (const s of d.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) { sum += Math.hypot(s.x - prev.x, s.y - prev.y); n++; }
      prev = s;
    }
    return n ? sum / n : 0;
  }
  const thin = generateElement(textElement({ text: "H", weightPreset: "thin" }), garment, {});
  const bold = generateElement(textElement({ text: "H", weightPreset: "bold" }), garment, {});
  expect(avgSpacing(bold)).toBeGreaterThan(avgSpacing(thin));
});
```

Update the `textElement()` helper to include `weightPreset: "normal"`.

- [ ] Apply both edits to `app/src/lib/generate.spec.js`.

### Step 9: Run app tests to verify pass

Run: `cd app && npx vitest run src/lib/generate.spec.js`
Expected: all pass.

### Step 10: Commit

```bash
git add app/src/lib/project.js app/src/lib/generate.js app/src/lib/generate.spec.js
git commit -m "Thread weightPreset through the text-element project model"
```

### Step 11: Add the bold preset UI to `TextStep.svelte`

Add three preset buttons after the Rotation control (from Task 1) in `app/src/ui/TextStep.svelte`:

```svelte
<div class="weightpresets">
  <span class="weightlabel">Weight</span>
  <div class="weightbtns">
    {#each ["thin", "normal", "bold"] as w}
      <button
        type="button"
        class="weightbtn"
        class:active={(element.weightPreset || "normal") === w}
        on:click={() => patch({ weightPreset: w })}
      >{w[0].toUpperCase() + w.slice(1)}</button>
    {/each}
  </div>
</div>
```

Add styles:

```css
.weightpresets { margin-top: 10px; }
.weightlabel { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
.weightbtns { display: flex; gap: 6px; }
.weightbtn {
  padding: 5px 10px;
  border: 1px solid var(--tint-border, #ccd6fb);
  border-radius: var(--radius-s, 6px);
  background: var(--surface, #fff);
  cursor: pointer;
  font-size: var(--fs-xs, 12px);
}
.weightbtn.active {
  background: var(--accent, #4f46e5);
  color: #fff;
  border-color: var(--accent, #4f46e5);
}
```

- [ ] Apply both edits to `app/src/ui/TextStep.svelte`.

### Step 12: Rebuild, restart, and live-verify

```bash
node tools/bundle.mjs
cd app && node scripts/copy-engine.mjs
```

- [ ] Run both commands.
- [ ] In the Studio app, select a text element, confirm three "Weight" buttons appear (Thin/Normal/Bold), with "Normal" active by default.
- [ ] Click "Bold" and confirm the letters visibly thicken in the Review field without any counter looking collapsed.
- [ ] Click "Thin" and confirm the letters visibly thin out.
- [ ] Click back to "Normal" and confirm it matches the original appearance.

### Step 13: Commit

```bash
git add app/src/ui/TextStep.svelte EMB-Bot-standalone.html
git commit -m "Add bold/thin weight preset buttons to TextStep"
```

---

## Task 4: Slant / italic

**Files:**
- Modify: `src/satinplay.js` (`emitZigzag`, currently lines 148-179)
- Modify: `src/satinfont.js` (`routeGlyph` and `layoutText`, as left by Task 2)
- Modify: `src/digitize.js` (`buildLetteringDesign`, as left by Task 3)
- Modify: `app/src/lib/generate.js`
- Modify: `app/src/lib/project.js`
- Modify: `app/src/ui/TextStep.svelte`
- Test (new): `test/satinplay.test.js`
- Test: `test/satinfont.test.js`
- Test: `test/digitize.test.js`
- Test: `app/src/lib/generate.spec.js`

**Interfaces:**
- Consumes: nothing new from Tasks 1-3.
- Produces: `satinplay.js`'s `emitZigzag`/`satinFromGeom`/`satinFromRails` accept `opts.slantDeg` (degrees, default 0). `routeGlyph`/`layoutText` thread it through. `buildLetteringDesign` accepts `opts.slantDeg` (-20 to +20, default 0). `element.slantDeg` (number, default 0) is the new project-model field.

**Pre-verified math (see conversation for the spike):** on a synthetic straight 40mm-wide column, this exact approach produces a cross-stitch angle of exactly `90 + slantDeg` degrees away from the column's clamped end stations, and is byte-identical to unslanted at `slantDeg=0`.

### Step 1: Create `test/satinplay.test.js` with the failing slant test

This module has no dedicated test file yet (its behavior has only been exercised indirectly via `test/satinfont.test.js`). Create `test/satinplay.test.js`:

```js
const assert = require("node:assert");
const { test } = require("node:test");
const satinplay = require("../src/satinplay.js");
const { correspond, columnGeom, satinFromGeom } = satinplay;

// A straight 40mm-wide (px units, pxPerMm=10 elsewhere in this codebase so
// 400 units == 40mm), 40mm-long synthetic column — same fixture shape used
// to verify this math before writing this test.
function straightColumn(lengthPx, widthPx, n) {
  const railA = [], railB = [];
  for (let i = 0; i <= n; i++) {
    const y = (i * lengthPx) / n;
    railA.push({ x: -widthPx / 2, y });
    railB.push({ x: widthPx / 2, y });
  }
  return { railA, railB };
}

function crossAngleDeg(pA, pB) {
  // Angle of the A->B cross vector from the column's own axis (+y here).
  return Math.atan2(pB.x - pA.x, pB.y - pA.y) * 180 / Math.PI;
}

test("satinFromGeom: slantDeg 0 (absent) is byte-identical to today's perpendicular cross output", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const { A, B } = correspond(railA, railB, [], 12);
  const geom = columnGeom(railA, railB, [], 12);
  const noField = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10 });
  const explicit0 = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, slantDeg: 0 });
  assert.deepStrictEqual(explicit0, noField);
});

test("satinFromGeom: slantDeg leans the cross-stitch by exactly that many degrees away from perpendicular, at interior stations", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const geom = columnGeom(railA, railB, [], 12);
  const opts = { spacingMm: 4, pxPerMm: 10 }; // coarse spacing -> few, easy-to-inspect stations
  const pts15 = satinFromGeom(geom, 0, 1, Object.assign({ slantDeg: 15 }, opts));
  const ptsM15 = satinFromGeom(geom, 0, 1, Object.assign({ slantDeg: -15 }, opts));
  // Interior cross pairs (skip the first/last, which taper toward
  // perpendicular as the shifted sample clamps against the column end).
  for (let i = 2; i + 1 < pts15.length - 2; i += 2) {
    const ang = Math.abs(crossAngleDeg(pts15[i], pts15[i + 1]));
    assert.ok(Math.abs(ang - 105) < 1, `slantDeg=15 interior cross should be ~105deg from column axis, got ${ang}`);
  }
  for (let i = 2; i + 1 < ptsM15.length - 2; i += 2) {
    const ang = Math.abs(crossAngleDeg(ptsM15[i], ptsM15[i + 1]));
    assert.ok(Math.abs(ang - 75) < 1, `slantDeg=-15 interior cross should be ~75deg from column axis, got ${ang}`);
  }
});
```

- [ ] Create `test/satinplay.test.js` exactly as shown.

### Step 2: Run tests to verify they fail

Run: `node --test test/satinplay.test.js`
Expected: first test PASSES trivially (nothing reads `slantDeg` yet, so both calls are already identical — a valid forward-looking pin). Second test FAILS (all cross angles come out at 90, not 105/75).

### Step 3: Implement `slantDeg` in `emitZigzag`

In `src/satinplay.js`, replace the entire `emitZigzag` function (lines 148-179):

```js
  // Turn corresponded pairs into zig-zag satin at the given density.
  // opts = { spacingMm, pxPerMm, pullCompMm=0 }.
  function emitZigzag(A, B, opts) {
    const denom = (opts.spacingMm || 0.4) * (opts.pxPerMm || 1);
    const offset = ((opts.pullCompMm || 0) * (opts.pxPerMm || 1)) / 2;
    const M = A.length;
    if (M < 2) return [];
    // Centerline cumulative arc length, to space stations evenly along the run.
    const C = []; for (let i = 0; i < M; i++) C.push({ x: (A[i].x + B[i].x) / 2, y: (A[i].y + B[i].y) / 2 });
    const cum = [0]; for (let i = 1; i < M; i++) cum.push(cum[i - 1] + Math.hypot(C[i].x - C[i - 1].x, C[i].y - C[i - 1].y));
    const total = cum[M - 1];
    if (!(total > EPS)) return [];
    const steps = Math.max(2, Math.ceil(total / (denom > 0 ? denom : 4)));
    const out = [];
    let seg = 0;
    for (let t = 0; t <= steps; t++) {
      const target = (t / steps) * total;
      while (seg < M - 2 && cum[seg + 1] < target) seg++;
      const segLen = cum[seg + 1] - cum[seg];
      const f = segLen > EPS ? (target - cum[seg]) / segLen : 0;
      let ax = A[seg].x + (A[seg + 1].x - A[seg].x) * f, ay = A[seg].y + (A[seg + 1].y - A[seg].y) * f;
      let bx = B[seg].x + (B[seg + 1].x - B[seg].x) * f, by = B[seg].y + (B[seg + 1].y - B[seg].y) * f;
      if (offset > 0) {
        let vx = ax - bx, vy = ay - by; const L = Math.hypot(vx, vy) || 1; vx /= L; vy /= L;
        ax += vx * offset; ay += vy * offset; bx -= vx * offset; by -= vy * offset;
      }
      const pA = { x: ax, y: ay }, pB = { x: bx, y: by };
      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < 0.3) continue;
      if (t % 2 === 0) { out.push(pA, pB); } else { out.push(pB, pA); }
    }
    return out;
  }
```

with:

```js
  // Interpolate a point on `arr` at arc-length position `s` along `cum`
  // (arr's own cumulative arc-length table, same length as arr). Used by
  // slantDeg below to sample rail A and rail B at DIFFERENT arc-length
  // positions (a lean) instead of always the same one (perpendicular).
  function interpAt(arr, cum, s) {
    const n = arr.length;
    if (s <= 0) return { x: arr[0].x, y: arr[0].y };
    const total = cum[n - 1];
    if (s >= total) return { x: arr[n - 1].x, y: arr[n - 1].y };
    let i = 0;
    while (i < n - 2 && cum[i + 1] < s) i++;
    const segLen = cum[i + 1] - cum[i] || 1;
    const f = (s - cum[i]) / segLen;
    return { x: arr[i].x + (arr[i + 1].x - arr[i].x) * f, y: arr[i].y + (arr[i + 1].y - arr[i].y) * f };
  }

  // Turn corresponded pairs into zig-zag satin at the given density.
  // opts = { spacingMm, pxPerMm, pullCompMm=0, slantDeg=0 }.
  //
  // slantDeg (Font editing abilities Round 1, italic-style lean): 0 keeps
  // the cross-stitch perpendicular to the column (today's behavior,
  // byte-identical). A nonzero value samples rail A AHEAD of the centerline
  // target and rail B BEHIND it (or vice versa) by halfWidth*tan(slantDeg) —
  // the same "shift the far-rail contact point along the column" trick a
  // real italic satin lean uses — verified analytically before this task was
  // written: on a synthetic straight column this produces a cross-stitch
  // angle of EXACTLY 90+slantDeg degrees away from the column's clamped end
  // stations (where the shifted target runs off the column and clamps back
  // toward perpendicular — an intentional, graceful taper, not a bug).
  function emitZigzag(A, B, opts) {
    const denom = (opts.spacingMm || 0.4) * (opts.pxPerMm || 1);
    const offset = ((opts.pullCompMm || 0) * (opts.pxPerMm || 1)) / 2;
    const slantRad = ((opts.slantDeg || 0) * Math.PI) / 180;
    const M = A.length;
    if (M < 2) return [];
    // Centerline cumulative arc length, to space stations evenly along the run.
    const C = []; for (let i = 0; i < M; i++) C.push({ x: (A[i].x + B[i].x) / 2, y: (A[i].y + B[i].y) / 2 });
    const cum = [0]; for (let i = 1; i < M; i++) cum.push(cum[i - 1] + Math.hypot(C[i].x - C[i - 1].x, C[i].y - C[i - 1].y));
    const total = cum[M - 1];
    if (!(total > EPS)) return [];
    const steps = Math.max(2, Math.ceil(total / (denom > 0 ? denom : 4)));
    const out = [];
    let seg = 0;
    for (let t = 0; t <= steps; t++) {
      const target = (t / steps) * total;
      while (seg < M - 2 && cum[seg + 1] < target) seg++;
      const segLen = cum[seg + 1] - cum[seg];
      const f = segLen > EPS ? (target - cum[seg]) / segLen : 0;
      let ax = A[seg].x + (A[seg + 1].x - A[seg].x) * f, ay = A[seg].y + (A[seg + 1].y - A[seg].y) * f;
      let bx = B[seg].x + (B[seg + 1].x - B[seg].x) * f, by = B[seg].y + (B[seg + 1].y - B[seg].y) * f;
      if (slantRad) {
        const halfW = Math.hypot(ax - bx, ay - by) / 2;
        const shift = halfW * Math.tan(slantRad);
        const clampS = (s) => Math.max(0, Math.min(total, s));
        const pA1 = interpAt(A, cum, clampS(target + shift));
        const pB1 = interpAt(B, cum, clampS(target - shift));
        ax = pA1.x; ay = pA1.y; bx = pB1.x; by = pB1.y;
      }
      if (offset > 0) {
        let vx = ax - bx, vy = ay - by; const L = Math.hypot(vx, vy) || 1; vx /= L; vy /= L;
        ax += vx * offset; ay += vy * offset; bx -= vx * offset; by -= vy * offset;
      }
      const pA = { x: ax, y: ay }, pB = { x: bx, y: by };
      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < 0.3) continue;
      if (t % 2 === 0) { out.push(pA, pB); } else { out.push(pB, pA); }
    }
    return out;
  }
```

- [ ] Apply this replacement to `src/satinplay.js`.

### Step 4: Run tests to verify they pass

Run: `node --test test/satinplay.test.js`
Expected: both PASS.

Run the full engine suite: `node --test 2>&1 | tail -10`
Expected: all pass (165 + 2 = 167).

### Step 5: Commit

```bash
git add src/satinplay.js test/satinplay.test.js
git commit -m "Add slantDeg to satinplay's emitZigzag"
```

### Step 6: Write the failing threading test in `satinfont.test.js`

Add to `test/satinfont.test.js`:

```js
test("layoutText: slantDeg absent/0 is byte-identical to today's straight output; a nonzero value visibly leans a satin run's cross-stitches", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false };
  const lay0 = SF.layoutText(font, "H", opts);
  const layExplicit0 = SF.layoutText(font, "H", Object.assign({ slantDeg: 0 }, opts));
  assert.deepStrictEqual(layExplicit0, lay0);
  const layShear = SF.layoutText(font, "H", Object.assign({ slantDeg: 15 }, opts));
  // Same run/point COUNT (slant re-samples the same stations, doesn't add/remove any).
  assert.strictEqual(layShear.runs.length, lay0.runs.length);
  const totalPts0 = lay0.runs.reduce((s, r) => s + r.pts.length, 0);
  const totalPtsShear = layShear.runs.reduce((s, r) => s + r.pts.length, 0);
  assert.strictEqual(totalPtsShear, totalPts0);
  // But the actual point positions differ (the lean visibly changed the geometry).
  const flat0 = lay0.runs.flatMap((r) => r.pts);
  const flatShear = layShear.runs.flatMap((r) => r.pts);
  const anyDiffer = flat0.some((p, i) => Math.abs(p.x - flatShear[i].x) > 0.5 || Math.abs(p.y - flatShear[i].y) > 0.5);
  assert.ok(anyDiffer, "slantDeg:15 must produce visibly different point positions than slantDeg:0");
});
```

- [ ] Add this test to `test/satinfont.test.js`.

### Step 7: Run test to verify it fails

Run: `node --test test/satinfont.test.js 2>&1 | grep -A10 "slantDeg absent"`
Expected: FAIL (`slantDeg` isn't threaded through yet, so `layShear` equals `lay0`).

### Step 8: Thread `slantDeg` through `routeGlyph` and `layoutText`

In `src/satinfont.js`, locate `routeGlyph`'s opts destructuring (around line 81):

```js
  function routeGlyph(cols, opts) {
    const pxPerMm = opts.pxPerMm, spacingMm = opts.spacingMm, pullCompMm = opts.pullCompMm || 0;
    const satinOpts = { spacingMm, pxPerMm, pullCompMm };
```

Replace with:

```js
  function routeGlyph(cols, opts) {
    const pxPerMm = opts.pxPerMm, spacingMm = opts.spacingMm, pullCompMm = opts.pullCompMm || 0, slantDeg = opts.slantDeg || 0;
    const satinOpts = { spacingMm, pxPerMm, pullCompMm, slantDeg };
```

Then locate `layoutText`'s opts reading (around lines 217-223):

```js
    const o = opts || {};
    const emMm = o.emMm || 18;
    const pxPerMm = o.pxPerMm || 10;
    const spacingMm = o.spacingMm || 0.4;
    const pullCompMm = o.pullCompMm || 0;
    const doUnderlay = o.underlay !== false;
    const arcDeg = o.arcDeg || 0;
```

Replace with:

```js
    const o = opts || {};
    const emMm = o.emMm || 18;
    const pxPerMm = o.pxPerMm || 10;
    const spacingMm = o.spacingMm || 0.4;
    const pullCompMm = o.pullCompMm || 0;
    const slantDeg = o.slantDeg || 0;
    const doUnderlay = o.underlay !== false;
    const arcDeg = o.arcDeg || 0;
```

Then locate the `routeGlyph` call inside the glyph loop (around line 282):

```js
        const gRuns = routeGlyph(cols, { pxPerMm, spacingMm, pullCompMm, underlay: doUnderlay });
```

Replace with:

```js
        const gRuns = routeGlyph(cols, { pxPerMm, spacingMm, pullCompMm, slantDeg, underlay: doUnderlay });
```

- [ ] Apply all three edits to `src/satinfont.js`.

### Step 9: Run tests to verify they pass

Run: `node --test test/satinfont.test.js 2>&1 | tail -15`
Expected: PASS.

Run the full engine suite: `node --test 2>&1 | tail -10`
Expected: all pass (167 + 1 = 168).

### Step 10: Commit

```bash
git add src/satinfont.js test/satinfont.test.js
git commit -m "Thread slantDeg through routeGlyph and layoutText"
```

### Step 11: Write the failing `buildLetteringDesign` test

Add to `test/digitize.test.js`:

```js
test("buildLetteringDesign: slantDeg absent/0 is byte-identical to today's output; a nonzero value changes the generated geometry", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../src/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "H", base);
  const dExplicit0 = DG.buildLetteringDesign(font, "H", Object.assign({ slantDeg: 0 }, base));
  assert.deepStrictEqual(dExplicit0, d0);
  const dSlant = DG.buildLetteringDesign(font, "H", Object.assign({ slantDeg: 15 }, base));
  assert.strictEqual(dSlant.stitches.length, d0.stitches.length, "slant re-samples the same stations, doesn't add/remove stitches");
  const anyDiffer = d0.stitches.some((s, i) => Math.abs(s.x - dSlant.stitches[i].x) > 1 || Math.abs(s.y - dSlant.stitches[i].y) > 1);
  assert.ok(anyDiffer, "slantDeg:15 must produce visibly different stitch positions");
});
```

- [ ] Add this test to `test/digitize.test.js`.

### Step 12: Run test to verify it fails, then implement

Run: `node --test test/digitize.test.js 2>&1 | grep -A6 "slantDeg absent"`
Expected: FAIL (`slantDeg` isn't read by `buildLetteringDesign` yet).

In `src/digitize.js`, locate BOTH `layoutText` calls (the probe pass and the final pass, as left by earlier tasks):

```js
    const probe = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: 2, pullCompMm: 0, letterSpacingMm: ls, underlay: false, arcDeg: o.arcDeg || 0 });
```

Replace with:

```js
    const probe = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: 2, pullCompMm: 0, letterSpacingMm: ls, underlay: false, arcDeg: o.arcDeg || 0, slantDeg: o.slantDeg || 0 });
```

And:

```js
    const lay = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: densityMm / sc, pullCompMm: pullCompMm / sc, letterSpacingMm: ls, underlay: o.underlay !== false, arcDeg: o.arcDeg || 0 });
```

Replace with:

```js
    const lay = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: densityMm / sc, pullCompMm: pullCompMm / sc, letterSpacingMm: ls, underlay: o.underlay !== false, arcDeg: o.arcDeg || 0, slantDeg: o.slantDeg || 0 });
```

(Threading `slantDeg` through the probe pass too matters for the same reason `arcDeg` already is — see the existing test `"digitize.buildLetteringDesign: arcDeg is threaded through both layoutText passes (probe + final)"` in this same file — slant changes the glyph bbox slightly, so the probe must reflect the same geometry the final pass will produce, keeping the fit-scale calculation consistent.)

- [ ] Apply both edits to `src/digitize.js`.

### Step 13: Run tests to verify they pass

Run: `node --test test/digitize.test.js 2>&1 | tail -15`
Expected: PASS.

Run the full engine suite: `node --test 2>&1 | tail -10`
Expected: all pass (168 + 1 = 169).

### Step 14: Commit

```bash
git add src/digitize.js test/digitize.test.js
git commit -m "Thread slantDeg through buildLetteringDesign"
```

### Step 15: Add `slantDeg` to the project model and thread it through `generate.js`

In `app/src/lib/project.js`'s `defaultTextElement` (as left by Task 3), add `slantDeg: 0,` right after `weightPreset: "normal"`:

```js
export function defaultTextElement(id) {
  return {
    id,
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    weightPreset: "normal",
    slantDeg: 0,
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}
```

In `app/src/lib/generate.js`'s text branch (as left by Task 3), add `slantDeg: element.slantDeg || 0,`.

Update the `defaultTextElement` shape assertion in `app/src/lib/project.spec.js` (as left by Task 3 Step 7) to match:

```js
test("defaultTextElement has sane beginner defaults", () => {
  const el = defaultTextElement("e1");
  expect(el).toEqual({
    id: "e1",
    type: "text",
    text: "",
    fontKey: "geneva_simple",
    colorRgb: [20, 20, 20],
    colorRanges: [],
    weightPreset: "normal",
    slantDeg: 0,
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  });
});
```

- [ ] Apply all three edits (`project.js`, `generate.js`, `project.spec.js`).
- [ ] Run `cd app && npx vitest run src/lib/project.spec.js` — expect PASS.

### Step 16: Write the failing app-level test

Add to `app/src/lib/generate.spec.js`:

```js
test("generateElement: slantDeg 15 produces different stitch geometry than slantDeg 0 for the same text", async () => {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  const straight = generateElement(textElement({ text: "H" }), garment, {});
  const slanted = generateElement(textElement({ text: "H", slantDeg: 15 }), garment, {});
  expect(slanted.stitches.length).toBe(straight.stitches.length);
  const anyDiffer = straight.stitches.some((s, i) => Math.abs(s.x - slanted.stitches[i].x) > 1 || Math.abs(s.y - slanted.stitches[i].y) > 1);
  expect(anyDiffer).toBe(true);
});
```

Update the `textElement()` helper to include `slantDeg: 0`.

- [ ] Apply both edits to `app/src/lib/generate.spec.js`.

### Step 17: Run app tests to verify pass

Run: `cd app && npx vitest run src/lib/generate.spec.js`
Expected: all pass.

### Step 18: Commit

```bash
git add app/src/lib/project.js app/src/lib/generate.js app/src/lib/generate.spec.js
git commit -m "Thread slantDeg through the text-element project model"
```

### Step 19: Add the slant UI to `TextStep.svelte`

Add a slider matching the Curve/Rotation pattern, after the Weight preset buttons added in Task 3:

```svelte
<label class="letterspacing">
  <span>Slant</span>
  <input
    type="range"
    min="-20"
    max="20"
    step="2"
    value={element.slantDeg || 0}
    on:input={(e) => patch({ slantDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.slantDeg || 0}°</span>
</label>
```

- [ ] Apply this edit to `app/src/ui/TextStep.svelte`.

### Step 20: Rebuild, restart, and live-verify

```bash
node tools/bundle.mjs
cd app && node scripts/copy-engine.mjs
```

- [ ] Run both commands.
- [ ] In the Studio app, confirm a "Slant" slider (-20 to 20) appears below the Weight buttons.
- [ ] Drag it to a positive value and confirm the letters visibly lean like italics in the Review field.
- [ ] Drag it to a negative value and confirm they lean the other way.
- [ ] Return it to 0 and confirm the text is upright again.
- [ ] Combine slant with rotation and bold on the same word and confirm nothing crashes or looks obviously broken (a basic combination smoke-check, not exhaustive).

### Step 21: Commit

```bash
git add app/src/ui/TextStep.svelte EMB-Bot-standalone.html
git commit -m "Add slant/italic slider to TextStep"
```

---

## Task 5: Final integration

**Files:** none new — verification and wrap-up only.

**Interfaces:** none.

- [ ] **Step 1:** Run the full engine suite: `node --test 2>&1 | tail -10`. Expected: all pass (169 total: 156 baseline + 13 new across the four tasks).
- [ ] **Step 2:** Run the full app suite: `cd app && npx vitest run 2>&1 | tail -10`. Expected: all pass (178 baseline + new tests added across the four tasks).
- [ ] **Step 3:** Rebuild the standalone bundle one final time to make sure it reflects every task's changes: `node tools/bundle.mjs`.
- [ ] **Step 4:** Re-copy the engine into the app's dev-server public folder: `cd app && node scripts/copy-engine.mjs`.
- [ ] **Step 5:** Do one final combined live-verification pass in the browser: create a single text element, set a color-range on part of it, rotate it 90°, set it Bold, and add a 10° slant — confirm the Review field renders something sensible (not a crash, not obviously mangled geometry) and the stats line shows a plausible stitch count and size.
- [ ] **Step 6:** Update project memory (`C:\Users\EE-LT-11030\.claude\projects\C--Users-EE-LT-11030\memory\emb-bot-digitizer.md`) with a summary of what shipped in this round, following the same style as the existing dated entries in that file (what was built, key architectural decisions — the pullCompMm-reuse insight for bold, the charIdx/native-textarea-selection insight for per-letter color, the arc-length-resample insight for slant — and the explicit Round 2 deferral of condensed/expanded width and mixed per-letter size).
- [ ] **Step 7:** Commit anything not yet committed (there shouldn't be much — each task already committed as it went):

```bash
git status --short
git add -A
git commit -m "Final integration pass: font editing abilities Round 1 complete" --allow-empty
```

(Use `--allow-empty` only if `git status` shows nothing to commit — don't force a commit with no real content otherwise.)
