# Border Chip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clicking a shape on the design canvas of a digitized element pops a small chip beside it carrying that shape's Border control.

**Architecture:** All new *logic* goes in `app/src/lib/shapeOverlay.js` (pure, already unit-tested, no browser needed) and a new `app/src/lib/shapeEdits.js` (the override read/write rules lifted out of DigitizePanel so both surfaces share one implementation). `EmbroideryField.svelte` gets markup and two new props. One read-only field is added to the service's review payload.

**Tech Stack:** Svelte 5, vitest + @testing-library/svelte (jsdom), Playwright (e2e), Python 3.12 + FastAPI (service), pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-border-chip-design.md`

## Global Constraints

- Base branch `claude/border-chip`, worktree `.claude/worktrees/border-chip`. **Rebase onto `origin/main` after PR #422 merges** — that PR fixes 7 Studio specs that are red on this base, and until then `npm test` cannot be read as a clean signal.
- Border vocabulary is the closed set `{"off", "auto", "bean"}` (`app/src/lib/digitizer.js:247`, `digitizer_service/app.py:143`). The no-override sentinel is `null`, spelled `"default"` in the UI. **`"auto"` is a real override value here, not the absence of one** — inverted from `tier`, where `"auto"` IS the absence.
- `updateElement` is a **shallow top-level merge** (`project.js:550`). Any shape write must rebuild the whole `shapeOverrides` map.
- Only CSS custom properties actually defined in `app/src/ui/theme.css`. `var(--x, fallback)` with an undefined name silently renders a bespoke value.
- `EmbroideryField.svelte` has **no `<style>` block**. All its classes live in `theme.css`.
- Never route a canvas resize through `paint()` — it calls `stopSim()` and kills a starting simulator. `repaintView()` is the view-only path.
- Every spec must be watched **red before green**.
- The digitizer venv does **not** exist in this worktree. Python tests run with the main checkout's interpreter from this worktree's `digitizer/` directory, so cwd shadows the installed package:
  `cd digitizer` then `"C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe" -m pytest -q tests/test_service.py`

---

### Task 1: Interior hit test

Today `hitOverlay` matches only within `NODE_GRAB_PX = 9` of a vertex or `EDGE_GRAB_PX = 6` of a segment. Clicking a shape's body hits nothing, falls through, and clears the selection (`EmbroideryField.svelte:1824-1827`).

**The design decision that matters:** interior hits are **opt-in via a fourth argument**, a Set of shape ids eligible for interior selection. Two things fall out of that for free:

1. `shapeOverlay.spec.js:948-952` asserts `hitOverlay(SQ, 150, 150)` is `null` — "dead centre, inside". With interior opt-in, that call has no fourth argument and **stays green**. The existing contract is not broken, it is extended.
2. `editableOutlinesPx()` does **not** filter hidden or deleted shapes — only the draw pass does (`EmbroideryField.svelte:798-812`). A shape's interior is a huge target compared to its outline, so without filtering, clicking anywhere inside a deleted shape would select it. Passing only visible ids into the Set is the filter.

**Files:**
- Modify: `app/src/lib/shapeOverlay.js:291-313`
- Test: `app/src/lib/shapeOverlay.spec.js` (extend the existing `describe("hitOverlay")` at :917)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `hitOverlay(outlinesPx, px, py, interiorIds = null)` → `{ shapeId, kind: "node" | "edge" | "interior", index, atPx } | null`. For an interior hit, `index` is `-1` and `atPx` is the pointer itself. Task 6 consumes `kind === "interior"`.

- [ ] **Step 1: Write the failing tests**

Add inside the existing `describe("hitOverlay", ...)` block in `app/src/lib/shapeOverlay.spec.js`:

```js
  // --- interior selection (opt-in) -----------------------------------------
  //
  // Interior hits are opt-in so the "misses cleanly" test above stays true:
  // a caller that does not pass an eligible-id set gets exactly today's
  // node/edge behaviour. The set is also the filter that keeps a hidden or
  // deleted shape unselectable — its interior is a far bigger target than its
  // outline, so without it, clicking empty-looking canvas inside a deleted
  // shape would select it.
  const ALL = new Set(["s1"]);

  test("without an eligible set, a dead-centre point is still a miss", () => {
    expect(hitOverlay(SQ, 150, 150)).toBe(null);
  });

  test("with an eligible set, a dead-centre point selects the shape", () => {
    const h = hitOverlay(SQ, 150, 150, ALL);
    expect(h).toMatchObject({ shapeId: "s1", kind: "interior", index: -1 });
    expect(h.atPx).toEqual([150, 150]);
  });

  test("a shape absent from the eligible set is not interior-selectable", () => {
    expect(hitOverlay(SQ, 150, 150, new Set())).toBe(null);
  });

  test("a node still beats an interior hit on the same shape", () => {
    // The vertex at (200,200) is inside no shape but on one; more to the
    // point, an interior test that ran inside the per-shape loop would
    // short-circuit before later shapes' nodes were considered.
    const h = hitOverlay(SQ, 200, 200, ALL);
    expect(h.kind).toBe("node");
  });

  test("an edge still beats an interior hit", () => {
    const h = hitOverlay(SQ, 150, 102, ALL);
    expect(h.kind).toBe("edge");
  });

  test("a point outside every shape is a miss even when everything is eligible", () => {
    expect(hitOverlay(SQ, 400, 400, ALL)).toBe(null);
  });

  test("the topmost shape wins when interiors overlap", () => {
    // Later in the array = drawn later = on top, matching the convention
    // manualShapes.js:149-151 already documents for the drawing canvas.
    const NESTED = [
      { id: "under", points: [[100, 100], [300, 100], [300, 300], [100, 300]] },
      { id: "over", points: [[150, 150], [250, 150], [250, 250], [150, 250]] },
    ];
    const h = hitOverlay(NESTED, 200, 200, new Set(["under", "over"]));
    expect(h.shapeId).toBe("over");
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd app && npx vitest run src/lib/shapeOverlay.spec.js -t "interior"`
Expected: FAIL. The dead-centre-with-set cases return `null` because `hitOverlay` ignores the fourth argument.

- [ ] **Step 3: Implement**

In `app/src/lib/shapeOverlay.js`, add above `hitOverlay`:

```js
// Even-odd ray cast on this module's [x, y] tuples.
//
// A third copy of this algorithm in the repo, deliberately: manualShapes.js's
// `pointInShape` is the same test on {x, y} OBJECTS and digitize.js's
// `pointInPoly` is the engine's own on tuples but behind browser globals.
// Adapting either would mean allocating a converted ring on every hit test,
// and hitOverlay runs on every pointermove for the hover cursor.
function pointInRingPx(pts, px, py) {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
    if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}
```

Then replace the body of `hitOverlay`. The existing node and edge loops are unchanged; the interior pass is a **third** pass, after both, and only consulted when neither matched:

```js
/**
 * What is under the pointer, in one pass over the drawn outlines.
 *
 * @param outlinesPx [{ id, points: [[xPx, yPx], ...] }] — already projected
 * @param interiorIds Set<string> | null — shapes whose INTERIOR may select.
 *   Null (the default) is exactly the historical behaviour: outlines only.
 *   The caller passes only shapes a user can actually see, which is what keeps
 *   a hidden or deleted shape — whose interior is a large target — unclickable.
 * @returns { shapeId, kind: "node" | "edge" | "interior", index, atPx } or null
 *
 * Nodes beat edges everywhere, not just when strictly nearer: a node sits ON
 * two edges, so a distance comparison would hand a dead-centre node hit to
 * whichever edge happened to round smaller, and dragging a node is both the
 * more common intent and the harder target. Interiors come last for the same
 * reason, one step further: an interior contains every one of its own nodes
 * and edges, so testing it first would make node and edge grabs unreachable.
 * Interiors must also be a SEPARATE pass rather than a branch inside the
 * per-shape loop — the node loop returns early, so an in-loop interior test on
 * shape 1 would shadow a node grab on shape 2.
 */
export function hitOverlay(outlinesPx, px, py, interiorIds = null) {
  let bestEdge = null;
  for (const o of outlinesPx) {
    const pts = o.points;
    for (let i = 0; i < pts.length; i++) {
      const d = Math.hypot(px - pts[i][0], py - pts[i][1]);
      if (d <= NODE_GRAB_PX) {
        return { shapeId: o.id, kind: "node", index: i, atPx: [pts[i][0], pts[i][1]] };
      }
    }
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i];
      const b = pts[(i + 1) % pts.length];
      const s = distToSegment(px, py, a[0], a[1], b[0], b[1]);
      if (s.dist <= EDGE_GRAB_PX && (!bestEdge || s.dist < bestEdge.dist)) {
        bestEdge = { shapeId: o.id, kind: "edge", index: i, atPx: [s.x, s.y], dist: s.dist };
      }
    }
  }
  if (bestEdge) {
    const { dist, ...hit } = bestEdge;
    return hit;
  }
  if (interiorIds && interiorIds.size) {
    // Back to front: later in the array is drawn later, so it is on top. The
    // drawing canvas already resolves overlap this way (manualShapes.js:149).
    for (let i = outlinesPx.length - 1; i >= 0; i--) {
      const o = outlinesPx[i];
      if (!interiorIds.has(o.id)) continue;
      if (pointInRingPx(o.points, px, py)) {
        return { shapeId: o.id, kind: "interior", index: -1, atPx: [px, py] };
      }
    }
  }
  return null;
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd app && npx vitest run src/lib/shapeOverlay.spec.js`
Expected: PASS, including every pre-existing `hitOverlay` test — especially "misses cleanly when the pointer is nowhere near", which must still pass **unchanged**.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/shapeOverlay.js app/src/lib/shapeOverlay.spec.js
git commit -m "feat(overlay): opt-in interior hit test for shape selection"
```

---

### Task 2: Chip anchor geometry

The chip is a DOM element positioned inside `.hoop`, which is `position: relative`. Its coordinates must be **CSS layout px**. Everything the overlay speaks is **drawing px** (`canvasPointFromEvent` divides by `dpr`; `canvas.width` is set to pane size × `devicePixelRatio` by `fitCanvasToPane`). Assuming 1:1 is right on a dpr-1 desktop and wrong on HiDPI, during the ResizeObserver catch-up frame, and in the narrow `.hoop { max-width: min(100%, 62vh) }` breakpoint.

**Files:**
- Modify: `app/src/lib/shapeOverlay.js` (append)
- Test: `app/src/lib/shapeOverlay.spec.js` (new describe block)

**Interfaces:**
- Consumes: nothing.
- Produces: `chipAnchorPx(pointsPx, box)` → `{ left, top, placement: "above" | "below" }`, all in CSS px relative to the positioned parent. `box` is `{ chipW, chipH, hostW, hostH, scale, gap }`. Task 6 consumes it.

- [ ] **Step 1: Write the failing tests**

Append to `app/src/lib/shapeOverlay.spec.js`:

```js
// --- chip anchor -------------------------------------------------------------

describe("chipAnchorPx", () => {
  // A 100x100 drawing-px square. scale 1 means CSS px == drawing px.
  const SQ = [[100, 100], [200, 100], [200, 200], [100, 200]];
  const BOX = { chipW: 160, chipH: 32, hostW: 800, hostH: 600, scale: 1, gap: 8 };

  test("centres the chip horizontally over the shape and sits above it", () => {
    const a = chipAnchorPx(SQ, BOX);
    expect(a.placement).toBe("above");
    expect(a.left).toBe(150 - 80);        // shape centre 150, half chip 80
    expect(a.top).toBe(100 - 32 - 8);     // shape top, minus chip, minus gap
  });

  test("flips below when there is no room above", () => {
    const high = [[100, 5], [200, 5], [200, 60], [100, 60]];
    const a = chipAnchorPx(high, BOX);
    expect(a.placement).toBe("below");
    expect(a.top).toBe(60 + 8);
  });

  test("clamps to the left edge instead of going negative", () => {
    const left = [[0, 100], [40, 100], [40, 200], [0, 200]];
    expect(chipAnchorPx(left, BOX).left).toBe(0);
  });

  test("clamps to the right edge instead of overflowing the host", () => {
    const right = [[760, 100], [800, 100], [800, 200], [760, 200]];
    expect(chipAnchorPx(right, BOX).left).toBe(800 - 160);
  });

  test("converts drawing px to CSS px with scale", () => {
    // scale 0.5 is a dpr-2 display: 200 drawing px is 100 CSS px.
    const a = chipAnchorPx(SQ, { ...BOX, scale: 0.5 });
    expect(a.left).toBe(75 - 80 < 0 ? 0 : 75 - 80);  // centre 75, clamped at 0
    expect(a.top).toBe(50 - 32 - 8);
  });

  test("a chip wider than the host clamps to 0 rather than a negative left", () => {
    const a = chipAnchorPx(SQ, { ...BOX, chipW: 900 });
    expect(a.left).toBe(0);
  });

  test("returns null for a degenerate ring", () => {
    expect(chipAnchorPx([], BOX)).toBe(null);
    expect(chipAnchorPx(null, BOX)).toBe(null);
  });
});
```

Add `chipAnchorPx` to the import list at the top of the spec.

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/lib/shapeOverlay.spec.js -t "chipAnchorPx"`
Expected: FAIL with `chipAnchorPx is not a function`.

- [ ] **Step 3: Implement**

Append to `app/src/lib/shapeOverlay.js`:

```js
/**
 * Where to put the selection chip, in CSS px relative to the canvas's own
 * positioned parent (`.hoop`, which is position:relative).
 *
 * `scale` converts DRAWING px — everything hitOverlay and toCanvas speak — into
 * CSS px. It is `canvas.getBoundingClientRect().width / canvas.width`, which is
 * 1/devicePixelRatio on a settled layout and something else entirely during the
 * ResizeObserver catch-up frame. Passing it in rather than reading dpr means the
 * one case that actually breaks — a resize in flight — is expressible in a test.
 *
 * Clamping is not decoration: `.fieldmenu`, the only other absolutely-positioned
 * child of `.hoop`, is positioned straight off a pointer event with no clamp,
 * and it can only get away with that because a pointer is by definition inside
 * the canvas. A chip anchored to a SHAPE has no such guarantee — a shape at the
 * top of the hoop puts the chip off the top edge.
 */
export function chipAnchorPx(pointsPx, box) {
  const pts = pointsPx || [];
  if (pts.length < MIN_RING_POINTS) return null;
  const { chipW, chipH, hostW, hostH, scale = 1, gap = 8 } = box || {};
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of pts) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  const cx = ((minX + maxX) / 2) * scale;
  const top = minY * scale;
  const bottom = maxY * scale;

  const above = top - chipH - gap;
  const placement = above >= 0 ? "above" : "below";
  const rawTop = placement === "above" ? above : bottom + gap;

  const clamp = (v, lo, hi) => (hi < lo ? lo : Math.max(lo, Math.min(hi, v)));
  return {
    left: clamp(cx - chipW / 2, 0, hostW - chipW),
    top: clamp(rawTop, 0, hostH - chipH),
    placement,
  };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd app && npx vitest run src/lib/shapeOverlay.spec.js`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/shapeOverlay.js app/src/lib/shapeOverlay.spec.js
git commit -m "feat(overlay): chipAnchorPx — clamped, dpr-aware chip placement"
```

---

### Task 3: Lift the override read/write rules into `lib/`

`setOverride` and `overrideBorder` are component-local to `DigitizePanel.svelte`. The chip needs both. A second copy would diverge on the prune rule — and the specific way it would diverge is nasty: `EmbroideryField`'s own existing merge idiom (`commitShapeEdit`, :603-608) spreads **without** pruning, so copying that would make every border option work except **"Design (…)"**, the one that removes an override.

**Files:**
- Create: `app/src/lib/shapeEdits.js`
- Create: `app/src/lib/shapeEdits.spec.js`
- Modify: `app/src/ui/DigitizePanel.svelte:803-818` and `:885-898`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `mergeShapeOverride(overrides, sid, fields)` → a **new** overrides map. Pure; does not dispatch.
  - `readShapeBorder(overrides, sid)` → `"default" | "off" | "auto" | "bean"`.
  - `BORDER_CHOICES` → `[{ value, label }]` for `off` / `auto` / `bean` (the "Design (…)" option's label is caller-built, because it interpolates the design-wide setting).

- [ ] **Step 1: Write the failing tests**

Create `app/src/lib/shapeEdits.spec.js`:

```js
// The per-shape override read/write rules, shared by the Layers list and the
// canvas chip. Lifted out of DigitizePanel so there is one prune rule rather
// than two — the failure mode of a second copy is specific and quiet: an
// override map that never drops a key makes "Design (…)" (the option that
// REMOVES an override) silently do nothing while every other option works.
import { expect, test } from "vitest";
import { mergeShapeOverride, readShapeBorder, BORDER_CHOICES } from "./shapeEdits.js";

test("merging a field onto a shape with no entry creates one", () => {
  expect(mergeShapeOverride({}, "s1", { border: "auto" })).toEqual({ s1: { border: "auto" } });
});

test("merging preserves the shape's other fields", () => {
  const cur = { s1: { tier: "fill", fill_angle_deg: 45 } };
  expect(mergeShapeOverride(cur, "s1", { border: "off" }))
    .toEqual({ s1: { tier: "fill", fill_angle_deg: 45, border: "off" } });
});

test("a null value deletes that field", () => {
  const cur = { s1: { tier: "fill", border: "auto" } };
  expect(mergeShapeOverride(cur, "s1", { border: null })).toEqual({ s1: { tier: "fill" } });
});

test("emptying an entry removes the shape from the map entirely", () => {
  expect(mergeShapeOverride({ s1: { border: "auto" } }, "s1", { border: null })).toEqual({});
});

test('tier "auto" is the no-override spelling and is pruned; border "auto" is NOT', () => {
  // The asymmetry is real and load-bearing — DigitizePanel.svelte:803-810 and
  // digitizer_service/app.py:348-355 both depend on it. For border, "auto"
  // FORCES a border on for one shape even when the design-wide setting is off.
  expect(mergeShapeOverride({}, "s1", { tier: "auto" })).toEqual({});
  expect(mergeShapeOverride({}, "s1", { border: "auto" })).toEqual({ s1: { border: "auto" } });
});

test("the input map is not mutated", () => {
  const cur = { s1: { border: "auto" } };
  mergeShapeOverride(cur, "s1", { border: "off" });
  expect(cur).toEqual({ s1: { border: "auto" } });
});

test("other shapes are carried through untouched", () => {
  const cur = { s1: { border: "auto" }, s2: { tier: "satin" } };
  expect(mergeShapeOverride(cur, "s1", { border: null })).toEqual({ s2: { tier: "satin" } });
});

test("readShapeBorder reports the sentinel for an absent override", () => {
  expect(readShapeBorder({}, "s1")).toBe("default");
  expect(readShapeBorder({ s1: {} }, "s1")).toBe("default");
  expect(readShapeBorder({ s1: { tier: "fill" } }, "s1")).toBe("default");
});

test("readShapeBorder reports a set override verbatim", () => {
  for (const v of ["off", "auto", "bean"]) {
    expect(readShapeBorder({ s1: { border: v } }, "s1")).toBe(v);
  }
});

test("BORDER_CHOICES is the wire vocabulary, in UI order, without the sentinel", () => {
  expect(BORDER_CHOICES.map((c) => c.value)).toEqual(["off", "auto", "bean"]);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/lib/shapeEdits.spec.js`
Expected: FAIL — cannot resolve `./shapeEdits.js`.

- [ ] **Step 3: Implement**

Create `app/src/lib/shapeEdits.js`:

```js
// Per-shape override read/write rules, shared by DigitizePanel's Layers list
// and EmbroideryField's canvas chip.
//
// These lived in DigitizePanel until the chip needed them. They are here rather
// than duplicated because the prune rule is the part that fails SILENTLY: an
// implementation that merges without deleting looks correct for every option
// except the one that removes an override, and EmbroideryField's own existing
// merge idiom (commitShapeEdit) is exactly such an implementation.

// The three real border values, in the order the UI offers them. The fourth
// option a UI shows — "Design (…)" — is not a value: it is the ABSENCE of an
// override, written as null, and its label interpolates the design-wide
// setting, so the caller builds that option itself.
export const BORDER_CHOICES = [
  { value: "off", label: "No border" },
  { value: "auto", label: "Auto border" },
  { value: "bean", label: "Bean border" },
];

/**
 * Merge fields into one shape's override entry and return a NEW map.
 *
 * null clears a field. `tier: "auto"` also clears, because for tier "auto" IS
 * the absence of an override — but `border: "auto"` does NOT clear, because
 * for border "auto" is a real value that forces a border on for one shape even
 * when the design-wide setting is off. That asymmetry is the wire contract
 * (digitizer_service/app.py pops tier=="auto" and keeps border=="auto"), not a
 * quirk of this function.
 *
 * An emptied entry disappears entirely, so an untoggled-then-retoggled edit
 * canonicalises back to "no edits" and the job cache key returns to its
 * original value.
 */
export function mergeShapeOverride(overrides, sid, fields) {
  const next = { ...(overrides || {}) };
  const entry = { ...(next[sid] || {}), ...fields };
  for (const k of Object.keys(entry)) {
    if (entry[k] == null || (k === "tier" && entry[k] === "auto")) delete entry[k];
  }
  if (Object.keys(entry).length) next[sid] = entry;
  else delete next[sid];
  return next;
}

/** The border override in effect for one shape, in UI spelling. */
export function readShapeBorder(overrides, sid) {
  const e = (overrides || {})[sid] || {};
  return e.border == null ? "default" : e.border;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd app && npx vitest run src/lib/shapeEdits.spec.js`
Expected: PASS (10 tests).

- [ ] **Step 5: Rewire DigitizePanel to the shared implementation**

In `app/src/ui/DigitizePanel.svelte`, add to the existing `lib/` imports:

```js
  import { mergeShapeOverride, readShapeBorder } from "../lib/shapeEdits.js";
```

Replace `setOverride` (:885-898) body:

```js
  // Merge fields into one shape's override entry; null (and tier "auto")
  // clears a field, an emptied entry disappears entirely. Every call is one
  // element patch = one undo step (App's 500 ms coalescing merges rapid
  // clicks, same as any slider). The rule itself lives in lib/shapeEdits.js
  // so the canvas chip applies the same one.
  function setOverride(sid, fields) {
    patch({ shapeOverrides: mergeShapeOverride(element.shapeOverrides, sid, fields) });
  }
```

Replace `overrideBorder` (:812-815) body, keeping its comment block above it:

```js
  function overrideBorder(row, ov) {
    return readShapeBorder(ov, row.id);
  }
```

- [ ] **Step 6: Run the panel specs to verify nothing regressed**

Run: `cd app && npx vitest run src/ui/DigitizePanel.spec.js src/lib/digitizer.spec.js`
Expected: PASS. The existing per-shape Border test at `DigitizePanel.spec.js:175-179` is the assertion that must stay green — it pins the exact patch shape a border change produces.

- [ ] **Step 7: Commit**

```bash
git add app/src/lib/shapeEdits.js app/src/lib/shapeEdits.spec.js app/src/ui/DigitizePanel.svelte
git commit -m "refactor(studio): lift per-shape override rules into lib/shapeEdits"
```

---

### Task 4: Report the border a shape actually sewed

**Scope note — this is narrower than the spec's decision 6, deliberately.** The spec says "the border it actually sewed … plus the reason when none". The reason is **not recoverable**: `stitch_one`'s per-shape report is consumed positionally at `stage7_sequence.py:2110-2122` and summed, and the three reasons a border can be absent live in three unrelated places. Threading a report out of stage 7 is a much larger change than a payload field. What *is* clean is the plan's own run kinds — `stitches.BORDER` is emitted at exactly one site in the entire core (`stage6_border.py:624`) and `run_outline` deliberately emits `RUN` not `BEAN`. So this task reports **what**, not **why**. The why is filed.

**Files:**
- Modify: `digitizer/digitizer_service/app.py:531-563` (`_sew_facts`) and `:664-723` (the per-shape dict in `_review_payload`)
- Modify: `app/src/lib/digitizer.js:1001-1052` (`reviewFromJob`)
- Test: `digitizer/tests/test_service.py`, `app/src/lib/digitizer.spec.js`

**Interfaces:**
- Consumes: nothing.
- Produces: wire field `border_sewn` ∈ `{"satin", "bean", "run", null}`; Studio field `row.borderSewn` with the same values. Task 6 consumes `borderSewn`.

- [ ] **Step 1: Write the failing Python test**

Add to `digitizer/tests/test_service.py`:

```python
def test_review_reports_the_border_each_shape_actually_sewed(client, whitebg):
    """border_sewn is read off the emitted plan, not predicted from config.

    The distinction matters because a border override is a TOTAL no-op on a
    satin-tier shape: stage7_sequence.stitch_one returns at :1634 roughly 330
    lines before the border block at :1972 ever reads meta["border"]. A field
    that echoed the REQUEST would report a border on a shape that sewed none.
    """
    body = _digitize(client, whitebg, {"border": "auto"})
    shapes = body["review"]["shapes"]
    assert shapes, "fixture produced no shapes"
    for s in shapes:
        assert "border_sewn" in s, f"{s['shape_id']} has no border_sewn"
        assert s["border_sewn"] in (None, "satin", "bean", "run")
    # A shape that sewed as satin can never have sewn a border.
    for s in shapes:
        if s["tier"] == "satin":
            assert s["border_sewn"] is None, (
                f"{s['shape_id']} sews satin yet claims a {s['border_sewn']} border")


def test_border_sewn_is_none_for_every_shape_when_borders_are_off(client, whitebg):
    body = _digitize(client, whitebg, {"border": "off"})
    assert all(s["border_sewn"] is None for s in body["review"]["shapes"])
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
cd digitizer && "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe" -m pytest -q tests/test_service.py -k border_sewn
```
Expected: FAIL with `KeyError` / `assert "border_sewn" in s`.

- [ ] **Step 3: Implement the service side**

In `digitizer/digitizer_service/app.py`, extend `_sew_facts`. Add the border-kind fold beside the existing tier-rank fold:

```python
# Which run kinds ARE a border. stage6_border.border_runs is the only emitter
# of BORDER in the core, and run_outline deliberately emits RUN rather than
# BEAN, so these three kinds mean "this shape got an outline" and nothing else
# does. Read off the plan, like tier, so it reports what stage 7 DID rather
# than what the config asked for — which matters because a border override is
# a total no-op on the satin tier.
_BORDER_KINDS = {"border": "satin", "bean": "bean", "run": "run"}
```

Inside `_sew_facts`'s run loop, after the `_rank` line:

```python
            b = _BORDER_KINDS.get(run.kind)
            if b:
                f["border_sewn"] = b
```

And in the finalising loop, default it:

```python
    for f in facts.values():
        f["tier"] = _RANK_TIER.get(f.pop("_rank"))
        f.setdefault("border_sewn", None)
```

Then in `_review_payload`, add `border_sewn` to the `none` default and to the fact spread:

```python
    none = {"sew_index": None, "sew_block": None, "tier": None, "border_sewn": None}
```

```python
                # The border this shape ACTUALLY sewed, read off the plan's run
                # kinds (server-computed, read-only — no `_OVERRIDE_KEYS` entry,
                # same category as `tier` above). "satin" | "bean" | "run" |
                # None. It is not a prediction: a per-shape `border` override is
                # ignored outright on the satin tier (stage7_sequence.stitch_one
                # returns ~330 lines before the border block reads it), so a
                # client that echoed the REQUEST would claim a border on shapes
                # that sewed none. This says nothing about WHY a border is
                # absent — the plan records what happened, not what was refused.
                **{k: facts.get(r.shape_id, none)[k]
                   for k in ("sew_index", "sew_block", "tier", "border_sewn")},
```

(Replace the existing three-key spread with this four-key one.)

- [ ] **Step 4: Run to verify the Python tests pass**

Run:
```bash
cd digitizer && "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe" -m pytest -q tests/test_service.py -k border_sewn
```
Expected: PASS, 2 tests.

- [ ] **Step 5: Write the failing Studio contract test**

Add to `app/src/lib/digitizer.spec.js`, beside the other `reviewFromJob` contract tests:

```js
test("reviewFromJob carries border_sewn through, and an absent key reads as null", () => {
  // Same "absent key = default" convention stitched/textCandidate follow: a
  // service that predates this field must not make every shape claim a border.
  const withField = reviewFromJob({
    palette: [], shapes: [{ shape_id: "s1", outline_mm: [[0, 0], [1, 0], [1, 1]], border_sewn: "satin" }],
  });
  expect(withField.shapes[0].borderSewn).toBe("satin");

  const without = reviewFromJob({
    palette: [], shapes: [{ shape_id: "s1", outline_mm: [[0, 0], [1, 0], [1, 1]] }],
  });
  expect(without.shapes[0].borderSewn).toBe(null);

  const junk = reviewFromJob({
    palette: [], shapes: [{ shape_id: "s1", outline_mm: [[0, 0], [1, 0], [1, 1]], border_sewn: "nonsense" }],
  });
  expect(junk.shapes[0].borderSewn).toBe(null);
});
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js -t "border_sewn"`
Expected: FAIL — `borderSewn` is `undefined`, because `reviewFromJob` drops every wire field it does not explicitly name.

- [ ] **Step 7: Implement the Studio side**

In `app/src/lib/digitizer.js`, add above `reviewFromJob`:

```js
// The border kinds the service reports having SEWN (app.py's _BORDER_KINDS).
// Closed set, validated here for the same reason SHAPE_BORDERS is: an
// unrecognised spelling must read as "no information", never render as a label.
const BORDER_SEWN_VALUES = new Set(["satin", "bean", "run"]);
```

And inside the `shapes.map` return object, beside `tier`:

```js
      // The border this shape ACTUALLY sewed (contract 2026-09-08,
      // server-computed, read-only — see app.py's _review_payload comment):
      // "satin" | "bean" | "run", or null for no border at all. Distinct from
      // the `border` OVERRIDE, which is what was asked for: the two differ
      // whenever the request could not be honoured, most commonly on a
      // satin-tier shape, where a border override is ignored outright. A
      // pre-contract service sends nothing; that reads as null, the same
      // "absent key = default" convention `stitched` and `textCandidate` use.
      borderSewn: BORDER_SEWN_VALUES.has(s.border_sewn) ? s.border_sewn : null,
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js`
Expected: PASS, whole file.

- [ ] **Step 9: Commit**

```bash
git add digitizer/digitizer_service/app.py digitizer/tests/test_service.py app/src/lib/digitizer.js app/src/lib/digitizer.spec.js
git commit -m "feat(service): report the border each shape actually sewed"
```

---

### Task 5: Plumbing — props, the timer fix, and the element-switch fix

Three small changes that the chip depends on, each independently testable.

`EmbroideryField` knows neither the wizard step nor the service health — both are plain `App.svelte` locals (`step` at `:91`, `digitizerHealth` at `:335`). The chip must not appear where nothing can restitch it, so both have to be threaded in.

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte:24-31` (props), `:618-621` (the reactive clear)
- Modify: `app/src/App.svelte:1175-1189` (the single usage site)
- Modify: `app/src/ui/DigitizePanel.svelte:416-450` (timer) and `:672-680` (stale comment)
- Test: `app/src/ui/DigitizePanel.spec.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `EmbroideryField` props `step: string` and `digitizerHealth: object | null`. Task 6 consumes both.

- [ ] **Step 1: Write the failing timer test**

Add to `app/src/ui/DigitizePanel.spec.js`, in the existing auto-restitch block (:880-945) which already sets up fake timers and a spied `digitize`:

```js
test("an edit made and then interrupted by a remount still restitches", async () => {
  // The bug: onDestroy(() => clearTimeout(restitchTimer)) kills an ARMED timer
  // when the panel unmounts — a step change, a Next click, entering
  // multi-select, or ContentStep's {#key el.id} on an element switch. On
  // remount, prevEditsKey re-seeds from the ALREADY-DIRTY element, so the
  // watcher sees no change and never fires again. Edit a border, click Next
  // inside 2 seconds, and that edit is permanently never sewn: the element
  // stays hatched stale and Download ships the old stitches.
  const el = { ...baseElement(), shapeOverrides: { s1: { border: "auto" } } };
  const { unmount } = renderPanel({ element: el });
  unmount();
  digitize.mockClear();

  // Remounting with the same dirty element is the "came back to the step" case.
  renderPanel({ element: el });
  vi.advanceTimersByTime(2100);
  await Promise.resolve();
  expect(digitize).toHaveBeenCalledTimes(1);
});

test("a clean element does not restitch on mount", async () => {
  // The guard on the fix: it must repair an interrupted edit, not turn
  // "open a design" into "digitize a design".
  const el = baseElement();
  renderPanel({ element: el });
  vi.advanceTimersByTime(2100);
  await Promise.resolve();
  expect(digitize).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/ui/DigitizePanel.spec.js -t "remount"`
Expected: FAIL — `digitize` called 0 times, because the remounted panel re-seeds `prevEditsKey` from the dirty element.

- [ ] **Step 3: Implement the timer fix**

In `app/src/ui/DigitizePanel.svelte`, replace the stale comment at `:416-427` and add the mount reconciliation. The whole block becomes:

```js
  // Shape edits restitch on their own, after a pause (Kent's call,
  // 2026-08-13). Before this, a hand edit on the canvas moved the outline and
  // left the stitches where they were until "Apply layer changes" was pressed
  // — correct, but it made the canvas editor feel like it was drawing on a
  // photograph rather than editing a design.
  //
  // Debounced rather than immediate because a restitch is a real service run.
  // It is NOT a cold stage 0-7 run, whatever this comment used to claim:
  // digitizer_service/jobs.py:81 strips shape_overrides out of the GENERATION
  // key, so stages 0-4 replay from the generation cache (LRU depth 4) and only
  // the edit-sensitive tail re-runs. The JOB cache does miss every time, which
  // is what the old "guaranteed miss" note was really about. Debouncing still
  // earns its keep: firing per drag would queue a run behind every nudge.
  const RESTITCH_IDLE_MS = 2000;
  let restitchTimer = 0;
  let prevEditsKey = editsKey(canonicalShapeEdits(element));
  $: {
    const k = editsKey(canonicalShapeEdits(element));
    if (k !== prevEditsKey) {
      prevEditsKey = k;
      // `health` gates it: with no service there is nothing to restitch to,
      // and the existing "saved with the design, applied next time you
      // digitize" branch already covers that honestly.
      if (element.result && health) scheduleRestitch();
    }
  }

  // An edit whose timer died with the panel. onDestroy below clears an ARMED
  // timer on every unmount — a step change, a Next click, multi-select, or
  // ContentStep's {#key el.id} — and `prevEditsKey` above then re-seeds from
  // the already-dirty element on remount, so the watcher never fires again and
  // the edit is silently never sewn. Reconciling on mount closes that: if what
  // the element holds differs from what was last stitched, schedule it.
  //
  // Gated on `element.result` so this repairs an INTERRUPTED edit rather than
  // turning "open a saved design" into "digitize a saved design" — a project
  // loaded from disk with unapplied edits has no result yet and is left alone.
  onMount(() => {
    if (element.result && health && prevEditsKey !== (element.appliedEdits || editsKey({}))) {
      scheduleRestitch();
    }
  });

  function scheduleRestitch() {
    clearTimeout(restitchTimer);
    restitchTimer = setTimeout(() => {
      restitchTimer = 0;
      runDigitize(element);
    }, RESTITCH_IDLE_MS);
  }

  onDestroy(() => clearTimeout(restitchTimer));
```

Add `onMount` to the existing `svelte` import.

Also fix the second stale comment at `:678` — replace "and only restitch on Apply" with "and restitch on their own after a pause, or at once on Apply".

- [ ] **Step 4: Run to verify it passes**

Run: `cd app && npx vitest run src/ui/DigitizePanel.spec.js`
Expected: PASS, whole file — both new tests and every pre-existing restitch test.

- [ ] **Step 5: Thread the two props and fix the element-switch leak**

In `app/src/ui/EmbroideryField.svelte`, after `export let showDragHint = false;`:

```js
  // The wizard step and the service health, both needed only by the shape
  // chip. They live in App.svelte and are passed down rather than read from a
  // store because this component has no store access and there is exactly one
  // usage site. The chip must not appear where nothing can restitch it: the
  // 2 s auto-restitch lives in DigitizePanel, which mounts only on the Content
  // step, so a border set anywhere else would persist, hatch the element stale
  // forever, and let Download ship the old stitches with no gate to catch it.
  export let step = "";
  export let digitizerHealth = null;
```

Replace the reactive clear at `:618-621`:

```js
  // Clearing the shape selection when the ELEMENT selection moves away keeps
  // Delete from acting on a shape whose element is no longer in front of the
  // user. Cheap to compute, and it also drops the highlight.
  //
  // Keyed on the element ID, not just on its type: the old test only cleared
  // when the new selection was absent or non-digitized, so moving between TWO
  // digitized elements kept element A's shape id selected while B was current.
  // Delete then wrote A's id into B's deletedShapeIds — a no-op that still
  // dirtied B and cost a restitch — and the chip would anchor to a shape that
  // is not in B at all.
  let selectedForElId = null;
  $: if (project && project.selectedId !== undefined) {
    const sel = selectedElement();
    if (!sel || sel.type !== "digitized") {
      selectedShapeId = null;
      selectedForElId = null;
    } else if (selectedForElId !== sel.id) {
      selectedShapeId = null;
      selectedForElId = sel.id;
    }
  }
```

In `app/src/App.svelte:1175-1189`, add the two props:

```svelte
    <EmbroideryField
      {project}
      {runtime}
      {step}
      {digitizerHealth}
      showDragHint={showDragFieldHint}
```

- [ ] **Step 6: Run the whole Studio suite**

Run: `cd app && npm test`
Expected: PASS, 53 files. (If PR #422 has not merged yet, expect its known 7 failures in `generate.spec.js` and `summary.spec.js` and nothing else.)

- [ ] **Step 7: Commit**

```bash
git add app/src/ui/EmbroideryField.svelte app/src/App.svelte app/src/ui/DigitizePanel.svelte app/src/ui/DigitizePanel.spec.js
git commit -m "fix(studio): restitch an interrupted edit; scope shape selection to its element"
```

---

### Task 6: The chip

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte` (imports, derived state, the pointerdown branch at `:1779-1828`, the `.hoop` markup at `:2140`)
- Modify: `app/src/ui/theme.css` (append `.shapechip` rules beside `.fieldmenu` at `:666-677`)
- Test: `app/src/ui/EmbroideryField.spec.js` (new), `app/src/ui/EmbroideryField.testHarness.svelte` (new)

**Interfaces:**
- Consumes: `hitOverlay(..., interiorIds)` and `chipAnchorPx` (Tasks 1–2); `mergeShapeOverride`, `readShapeBorder`, `BORDER_CHOICES` (Task 3); `row.borderSewn` (Task 4); `step` and `digitizerHealth` props (Task 5).
- Produces: nothing consumed downstream.

- [ ] **Step 1: Write the failing component test**

Create `app/src/ui/EmbroideryField.testHarness.svelte`:

```svelte
<script>
  import EmbroideryField from "./EmbroideryField.svelte";

  // Test-only wrapper (see EmbroideryField.spec.js) — never imported by the
  // app itself. Same reason DigitizePanel.testHarness.svelte exists: Svelte 5
  // gives a test no way to observe a mounted component's dispatched events, so
  // a real parent listens with on:elupdate and mirrors App.svelte's
  // { id, patch } shallow merge.
  export let project;
  export let runtime = {};
  export let step = "content";
  export let digitizerHealth = { status: "ok" };
  export let onPatch = () => {};

  function handle(e) {
    const i = project.elements.findIndex((x) => x.id === e.detail.id);
    if (i >= 0) {
      const els = [...project.elements];
      els[i] = { ...els[i], ...e.detail.patch };
      project = { ...project, elements: els };
    }
    onPatch(e.detail);
  }
</script>

<EmbroideryField {project} {runtime} {step} {digitizerHealth} on:elupdate={handle} />
```

Create `app/src/ui/EmbroideryField.spec.js`:

```js
// @vitest-environment jsdom
//
// The first component-level coverage EmbroideryField has ever had. Scope is
// deliberately narrow: the shape chip's GATING and its patch shape. The canvas
// itself is not exercised — jsdom has no 2D context worth driving, and the
// geometry that decides where the chip goes is unit-tested in
// shapeOverlay.spec.js where it needs no browser at all.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

let Harness;
beforeAll(async () => {
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  HTMLCanvasElement.prototype.getContext = () => null;
  ({ default: Harness } = await import("./EmbroideryField.testHarness.svelte"));
});

function digitizedProject(shapeOverrides = {}, shapes = null) {
  const rows = shapes || [
    { id: "s1", tier: "fill", stitched: true, borderSewn: null,
      outlineFull: [[-10, -5], [10, -5], [10, 5], [-10, 5]] },
  ];
  return {
    selectedId: "e1",
    elements: [{
      id: "e1", type: "digitized", shapeOverrides, deletedShapeIds: [],
      result: { design: {} }, review: { shapes: rows },
      sizeMm: 40, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0, params: { border: null },
    }],
  };
}

// The chip only exists once a shape is selected, and selection comes from a
// canvas hit. These tests drive the exported test hook rather than synthesising
// a pointer event against a canvas jsdom cannot lay out.
function selectShape(container, id) {
  const canvas = container.querySelector("canvas");
  canvas.__selectShapeForTest(id);
}

test("no chip until a shape is selected", () => {
  const { container } = render(Harness, { project: digitizedProject() });
  expect(container.querySelector(".shapechip")).toBeNull();
});

test("selecting a shape shows the chip with the design-default border", async () => {
  const { container } = render(Harness, { project: digitizedProject() });
  selectShape(container, "s1");
  await Promise.resolve();
  const sel = container.querySelector(".shapechip select");
  expect(sel).not.toBeNull();
  expect(sel.value).toBe("default");
});

test("choosing a border patches shapeOverrides for that shape only", async () => {
  const patches = [];
  const { container } = render(Harness, {
    project: digitizedProject({ s2: { tier: "satin" } }),
    onPatch: (d) => patches.push(d),
  });
  selectShape(container, "s1");
  await Promise.resolve();
  await fireEvent.change(container.querySelector(".shapechip select"), {
    target: { value: "auto" },
  });
  expect(patches).toHaveLength(1);
  expect(patches[0]).toEqual({
    id: "e1",
    patch: { shapeOverrides: { s2: { tier: "satin" }, s1: { border: "auto" } } },
  });
});

test('choosing "Design" REMOVES the override rather than storing a word', async () => {
  // The prune rule. A merge that spread without deleting would leave
  // { border: "default" }, which canonicalShapeEdits then drops silently —
  // so the chip would look like it worked and nothing would change.
  const patches = [];
  const { container } = render(Harness, {
    project: digitizedProject({ s1: { border: "auto" } }),
    onPatch: (d) => patches.push(d),
  });
  selectShape(container, "s1");
  await Promise.resolve();
  await fireEvent.change(container.querySelector(".shapechip select"), {
    target: { value: "default" },
  });
  expect(patches[0].patch.shapeOverrides).toEqual({});
});

test("a satin-tier shape is told why, and is offered no border options", async () => {
  // A border override is a total no-op on the satin tier — stage 7 returns
  // ~330 lines before it reads meta["border"]. Offering the options would
  // spend a full restitch to produce a byte-identical design.
  const { container } = render(Harness, {
    project: digitizedProject({}, [
      { id: "s1", tier: "satin", stitched: true, borderSewn: null,
        outlineFull: [[-10, -5], [10, -5], [10, 5], [-10, 5]] },
    ]),
  });
  selectShape(container, "s1");
  await Promise.resolve();
  expect(container.querySelector(".shapechip select")).toBeNull();
  expect(container.querySelector(".shapechip")).toHaveTextContent(/satin column already is an outline/i);
});

test("no chip off the Content step", async () => {
  const { container } = render(Harness, { project: digitizedProject(), step: "download" });
  selectShape(container, "s1");
  await Promise.resolve();
  expect(container.querySelector(".shapechip")).toBeNull();
});

test("no chip when the digitizer is offline", async () => {
  const { container } = render(Harness, { project: digitizedProject(), digitizerHealth: null });
  selectShape(container, "s1");
  await Promise.resolve();
  expect(container.querySelector(".shapechip")).toBeNull();
});

test("the chip reports what actually sewed when it differs from what was asked", async () => {
  const { container } = render(Harness, {
    project: digitizedProject({ s1: { border: "auto" } }, [
      { id: "s1", tier: "fill", stitched: true, borderSewn: "bean",
        outlineFull: [[-10, -5], [10, -5], [10, 5], [-10, 5]] },
    ]),
  });
  selectShape(container, "s1");
  await Promise.resolve();
  expect(container.querySelector(".shapechip")).toHaveTextContent(/sewed a bean/i);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/ui/EmbroideryField.spec.js`
Expected: FAIL — no `.shapechip` in the DOM, and `__selectShapeForTest` is not a function.

- [ ] **Step 3: Implement**

In `app/src/ui/EmbroideryField.svelte`:

Add imports:

```js
  import { chipAnchorPx } from "../lib/shapeOverlay.js";
  import { mergeShapeOverride, readShapeBorder, BORDER_CHOICES } from "../lib/shapeEdits.js";
```

Add derived state near the other shape-selection state:

```js
  // Which shapes may be selected by clicking their INTERIOR. Exactly the set
  // the draw pass shows (EmbroideryField.svelte's drawShapeOutlines filter) —
  // a hidden or deleted shape still has a large, invisible interior, and
  // without this a click on apparently empty canvas would select it.
  function interiorEligible(el, rows) {
    const dead = new Set(el.deletedShapeIds || []);
    const ov = el.shapeOverrides || {};
    const ids = new Set();
    for (const r of rows) {
      if (dead.has(r.id)) continue;
      const o = ov[r.id] || {};
      const stitched = typeof o.stitched === "boolean" ? o.stitched : r.stitched !== false;
      if (stitched) ids.add(r.id);
    }
    return ids;
  }

  // The chip renders only where its edit can actually be sewn. DigitizePanel
  // owns the 2 s auto-restitch and mounts only on the Content step, so a
  // border set anywhere else would persist, hatch the element stale forever,
  // and let Download ship the old stitches with nothing to catch it.
  $: chipRow = (() => {
    if (!selectedShapeId || simActive) return null;
    if (step !== "content" || !digitizerHealth) return null;
    const el = selectedElement();
    if (!el || el.type !== "digitized") return null;
    const rows = (el.review && el.review.shapes) || [];
    return rows.find((r) => r.id === selectedShapeId) || null;
  })();

  $: chipAnchor = (() => {
    if (!chipRow || !hoopEl || !canvas) return null;
    const edit = editableOutlinesPx();
    const o = edit && edit.outlines.find((x) => x.id === selectedShapeId);
    if (!o) return null;
    // canvas.width is DEVICE px; getBoundingClientRect().width is CSS px. The
    // ratio is 1/dpr on a settled layout and something else during the
    // ResizeObserver catch-up frame, which is exactly why it is measured
    // rather than derived from devicePixelRatio.
    const r = canvas.getBoundingClientRect();
    const scale = canvas.width ? r.width / canvas.width : 1;
    return chipAnchorPx(o.points, {
      chipW: 208, chipH: 34, hostW: r.width, hostH: r.height, scale, gap: 8,
    });
  })();

  // A border override is ignored outright on these tiers: stage 7's stitch_one
  // returns at the run, width-floor and satin branches long before it reads
  // meta["border"]. Offering the options would spend a full restitch to
  // produce a byte-identical design.
  const BORDER_INERT_TIERS = new Set(["satin", "run"]);
  $: chipBorderInert = !!chipRow && BORDER_INERT_TIERS.has(chipRow.tier);

  function setChipBorder(v) {
    const el = selectedElement();
    if (!el) return;
    dispatch("elupdate", {
      id: el.id,
      patch: {
        shapeOverrides: mergeShapeOverride(
          el.shapeOverrides, selectedShapeId, { border: v === "default" ? null : v }),
      },
    });
  }
```

In `onPointerDown`, change the hit test to opt into interior selection, and treat an interior hit as select-only:

```js
    const edit = editableOutlinesPx();
    if (edit) {
      const hit = hitOverlay(edit.outlines, p.x, p.y,
                             interiorEligible(edit.el, edit.rows));
      if (hit) {
        // First click on a shape selects it and stops there — no geometry
        // moves until you have said which shape you mean.
        if (hit.shapeId !== selectedShapeId) {
          selectedShapeId = hit.shapeId;
          shapeEditError = "";
          drawOverlay();
          return;
        }
        // An interior hit may only ever SELECT. Falling through would start a
        // rubber-sheet drag from a point that is not on the ring at all, and
        // the interior is where "move the whole element" has always lived.
        if (hit.kind === "interior") return;
        const ring = edit.mmById.get(hit.shapeId);
```

Add the test hook beside the canvas binding (it is the only way a jsdom spec can reach a selection that normally comes from canvas geometry):

```js
  // Test seam: jsdom cannot lay out a canvas, so a spec has no way to produce
  // a real hit. Exposed on the element rather than as a prop so nothing in the
  // app can reach it. See EmbroideryField.spec.js.
  $: if (canvas) canvas.__selectShapeForTest = (id) => { selectedShapeId = id; };
```

Add the markup inside `.hoop`, after the `fieldMenu` block:

```svelte
    {#if chipRow && chipAnchor}
      <!-- The per-shape border control, on the surface the shape is on.
           Mirrors .fieldmenu's structure (absolute inside .hoop, dismissed by
           the same handlers) but is CLAMPED — .fieldmenu can skip clamping
           because a pointer is by definition inside the canvas, and a chip
           anchored to a SHAPE has no such guarantee. -->
      <div
        class="shapechip"
        style="left: {chipAnchor.left}px; top: {chipAnchor.top}px"
        role="group"
        aria-label="Shape border"
      >
        {#if chipBorderInert}
          <span class="shapechip-note">
            {chipRow.tier === "satin"
              ? "Border n/a — a satin column already is an outline"
              : "Border n/a — this shape sews as a run"}
          </span>
        {:else}
          <label class="shapechip-lbl" for="shapechip-border">Border</label>
          <select
            id="shapechip-border"
            class="dgp-lsel"
            value={readShapeBorder((selectedElement() || {}).shapeOverrides, selectedShapeId)}
            on:change={(e) => setChipBorder(e.currentTarget.value)}
          >
            <option value="default">Design ({(selectedElement() || {}).params?.border ?? "automatic"})</option>
            {#each BORDER_CHOICES as c}
              <option value={c.value}>{c.label}</option>
            {/each}
          </select>
          {#if chipRow.borderSewn}
            <span class="shapechip-note">sewed a {chipRow.borderSewn}</span>
          {/if}
        {/if}
      </div>
    {/if}
```

Append to `app/src/ui/theme.css`, beside `.fieldmenu`:

```css
/* The per-shape border chip on the design canvas. Same layer and surface
   treatment as .fieldmenu — it is the same kind of thing, a transient control
   floating over the field — but it is positioned from SHAPE geometry rather
   than a pointer, so shapeOverlay.chipAnchorPx clamps it inside the hoop. */
.shapechip {
  position: absolute;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 8px;
  background: var(--panel);
  border: 1px solid var(--line);
  box-shadow: 0 6px 18px rgba(12, 20, 28, 0.22);
  font-size: 12px;
  white-space: nowrap;
}
.shapechip-lbl { color: var(--muted); }
.shapechip-note { color: var(--muted); font-style: italic; }
```

Before writing those, confirm `--panel`, `--line` and `--muted` are actually defined in `theme.css` — `var(--x)` with an undefined name is a silent bespoke value, and this repo already carries three such names at 24 call sites. If any is absent, use the exact tokens `.fieldmenu` itself uses.

- [ ] **Step 4: Run to verify it passes**

Run: `cd app && npx vitest run src/ui/EmbroideryField.spec.js`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add app/src/ui/EmbroideryField.svelte app/src/ui/EmbroideryField.spec.js app/src/ui/EmbroideryField.testHarness.svelte app/src/ui/theme.css
git commit -m "feat(studio): per-shape border chip on canvas selection"
```

---

### Task 7: Repair the panel's dropdown the same way

The Layers list's Border `<select>` (`DigitizePanel.svelte:2218-2228`) is gated only by `{#if !dead && !unstitched}` — unlike the fill-angle and underlay selects, which sit inside `{#if tier === "fill"}`. So it offers Auto and Bean on satin shapes today, where they are a guaranteed no-op. The spec's decision 2 applies to both surfaces.

**Files:**
- Modify: `app/src/ui/DigitizePanel.svelte:2218-2228`
- Test: `app/src/ui/DigitizePanel.spec.js`

**Interfaces:**
- Consumes: `effTier` (already in the component), `BORDER_CHOICES` (Task 3).
- Produces: nothing.

- [ ] **Step 1: Write the failing test**

```js
test("a satin-tier row offers no border options, and says why", async () => {
  const { container } = renderPanel({
    element: { ...baseElement(), review: { shapes: [shapeRow({ id: "s1", tier: "satin" })] } },
  });
  await openLayers(container);
  expect(perShapeSelect(container, "Border")).toBeNull();
  expect(container).toHaveTextContent(/satin column already is an outline/i);
});

test("a fill-tier row still offers every border option", async () => {
  const { container } = renderPanel({
    element: { ...baseElement(), review: { shapes: [shapeRow({ id: "s1", tier: "fill" })] } },
  });
  await openLayers(container);
  const sel = perShapeSelect(container, "Border");
  expect([...sel.options].map((o) => o.value)).toEqual(["default", "off", "auto", "bean"]);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/ui/DigitizePanel.spec.js -t "satin-tier row"`
Expected: FAIL — the Border select renders regardless of tier.

- [ ] **Step 3: Implement**

Wrap the existing Border `<select>` at `:2218-2228`:

```svelte
                      {#if BORDER_INERT_TIERS.has(tier)}
                        <span class="dgp-lnote">
                          {tier === "satin"
                            ? "Border n/a — a satin column already is an outline"
                            : "Border n/a — this shape sews as a run"}
                        </span>
                      {:else}
                        <select
                          class="dgp-lsel"
                          value={overrideBorder(row, overrides)}
                          on:change={(e) => setShapeBorder(row.id, e.currentTarget.value)}
                          aria-label={"Border — " + rowAria}
                        >
                          <option value="default">Design ({borderLabel(element.params.border)})</option>
                          {#each BORDER_CHOICES as c}
                            <option value={c.value}>{c.label}</option>
                          {/each}
                        </select>
                      {/if}
```

Add near the other constants in the component:

```js
  // Mirrors EmbroideryField's set, and for the same reason: stage 7's
  // stitch_one returns on these tiers long before it reads meta["border"], so
  // the options would spend a full restitch to produce an identical design.
  const BORDER_INERT_TIERS = new Set(["satin", "run"]);
```

Import `BORDER_CHOICES` from `../lib/shapeEdits.js` (already imported in Task 3).

- [ ] **Step 4: Run to verify it passes**

Run: `cd app && npx vitest run src/ui/DigitizePanel.spec.js`
Expected: PASS, whole file.

- [ ] **Step 5: Commit**

```bash
git add app/src/ui/DigitizePanel.svelte app/src/ui/DigitizePanel.spec.js
git commit -m "fix(studio): stop offering border options where a border cannot happen"
```

---

### Task 8: Verify in a real browser, and check the e2e constraints

Green specs are not the bar here. The last four UI defects in this app were invisible in the source and only showed in the cascade — including a primary CTA rendering white-on-white on every wizard step.

**Files:**
- Possibly modify: `app/e2e/field-chrome.spec.js:59-67`, `app/e2e/field-outlines.spec.js:153-200`

- [ ] **Step 1: Check the two e2e specs that constrain this area**

`field-chrome.spec.js` asserts `.hoop > *` has **exactly one** child. The chip is a conditional child, and that spec selects no shape, so it should stay green — but confirm rather than assume. `field-outlines.spec.js:160-165` states the old contract in a comment: *"Shape picking targets the outline itself — a node or an edge, not the interior."* That comment is now false and must be updated even if the test passes.

Run:
```bash
cd digitizer && .venv/Scripts/python -m digitizer_service
```
then in another shell:
```bash
cd app && npx playwright test e2e/field-chrome.spec.js e2e/field-outlines.spec.js
```
Expected: PASS. If `field-chrome` fails on the child count, change the assertion to express its real intent — that nothing overlays the sewable field when no shape is selected — rather than loosening the number.

- [ ] **Step 2: Drive the real app**

```bash
node .claude/skills/run-emb-bot/driver.mjs repl <<'EOF'
btn Logo patch
upload input[type=file] scratch_kent/Instagram_icon.png
eval new Promise(r=>{const t=setInterval(()=>{const m=document.body.innerText.match(/[\d,]+ stitches[^\n]*/);if(m){clearInterval(t);r(m[0])}},1000);setTimeout(()=>{clearInterval(t);r('TIMEOUT')},180000)})
ss before-chip
EOF
```

Then click a shape's interior on the canvas and screenshot the chip. **Read computed styles, not the rule you wrote** — `getComputedStyle(document.querySelector('.shapechip')).backgroundColor` and `.color`, on both a pale and a dark fabric, and confirm the chip is not white-on-white against either.

- [ ] **Step 3: Confirm the chip actually changes the sewn output**

Select one of the three white shapes, set **Auto border**, wait for the restitch, and confirm the stitch count moves. The spec's own measurement is the reference: design `border` off with the three white shapes on Auto gives **12,650 stitches / 2,819 border / 5 rings**, against 17,890 for blanket `auto`. A chip that changes nothing is the exact failure mode this repo has shipped before — `satin_shape(angle_deg=…)` was built, wired, green, and inert.

- [ ] **Step 4: Full suites**

```bash
node --test
cd app && npm test
cd app && npx playwright test
cd digitizer && "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe" -m pytest -q -n auto
```

Expected: engine 505 pass; Studio 53 files pass; e2e pass with the service up; digitizer red **only** on the three known golden tests (`test_pushcomp`, `test_flat_lane_byte_identical`, `test_stage2_photo_segment`). A fourth failure is a regression. Judge by the named tests, not the total.

- [ ] **Step 5: Open the PR ready for review, and arm auto-merge**

Not a draft — auto-merge cannot be armed on a draft. Arm it while `mergeStateStatus` is `BLOCKED` (required checks pending); once everything is green there is nothing left to arm.

```bash
gh pr create --title "feat(studio): per-shape border control on the canvas" --body-file <path>
gh pr merge <n> --auto --squash
```

---

## Self-Review

**Spec coverage.** Decision 1 (inherit the 2 s debounce) — Task 5 leaves `RESTITCH_IDLE_MS` untouched and the chip writes through the same `shapeOverrides` field the watcher already keys on, so it inherits it by construction. Decision 2 (hide inert options, state why) — Tasks 6 and 7. Decision 3 (interior hit test) — Task 1. Decision 4 (Content step only) — Task 5 props, Task 6 gating. Decision 5 (timer-death fix) — Task 5. Decision 6 (per-shape echo) — Task 4, **narrowed**: what, not why, with the reason filed. Every "Out of scope, filed" item in the spec remains untouched.

**Type consistency.** `hitOverlay`'s fourth parameter is `interiorIds` in Tasks 1 and 6. `chipAnchorPx(pointsPx, box)` returns `{left, top, placement}` in Tasks 2 and 6. `mergeShapeOverride(overrides, sid, fields)` and `readShapeBorder(overrides, sid)` keep their signatures across Tasks 3, 6 and 7. `border_sewn` (wire) maps to `borderSewn` (Studio) in Task 4 and is read as `chipRow.borderSewn` in Task 6. `BORDER_INERT_TIERS` is defined separately in both components — deliberate, and commented as mirroring, because the two files share no other constant and importing a two-element Set across a UI boundary would be the only such import in either.

**Known gap.** Task 6's `__selectShapeForTest` hook is a test seam on a DOM element. It is the only way a jsdom spec can reach a selection that normally originates in canvas geometry, and the alternative — no component coverage at all for the chip — is what left `EmbroideryField` untested in the first place. Flagged for review rather than hidden.
