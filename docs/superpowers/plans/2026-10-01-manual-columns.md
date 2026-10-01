# Satin columns in the manual lane — Implementation Plan (plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hand-drawn satin column: draw an open spine, it gets a width, and it sews as satin between the two rails that width implies.

**Architecture:** A column is a shape record `{ id, kind: "column", points, curves, widthPx, colorRgb }` — an OPEN spine plus a drawn width stored as geometry in authored canvas px. One pure module turns spine + width into two rails and a closed ring; one function, `shapeRing(shape)`, is the only place that says what ring a shape presents to the engine, the bbox, hit-testing and the placement box. The engine sews a region carrying `sewAs: { kind: "column", railA, railB }` with `satinFromRails` instead of deriving rails from the polygon.

**Tech Stack:** `src/digitize.js` + `src/satinplay.js` (browser-global engine, `node --test`), Svelte 5 in legacy syntax, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-30-manual-digitizing-gaps-design.md` — §2, §4, **§6 including its 2026-10-01 amendment block (it overrides the older §6 text)**, §10 rulings 2, 5, 9, 12. Evidence for ruling 12: `docs/satin-column-width-on-resize-2026-10-01.md`.

**Survey of every closed-ring assumption a column trips** (file:line, read 2026-10-01 at `5396251a`; line numbers drift — re-read): `.superpowers/sdd/2026-10-01-manual-columns/survey-notes.md`.

## Global Constraints

- **Byte-identical for every design with no column.** A region with no `sewAs` sews exactly as today; `shapesToRegions` on shapes with no `kind: "column"` emits exactly what it emits today. Engine `node --test` stays green with no stored hash or golden changed. If a pre-existing engine test moves, STOP and report.
- **Do not bump `PROJECT_FILE_VERSION`.** `kind` absent means a closed shape.
- **Width is `widthPx`** — the full drawn width in authored canvas px. Never store a width in mm. Drawn mm = `widthPx × fit.mmPerPx`; sewn mm = drawn + `fabric.pullCompMm`.
- **No new physical constants.** Default drawn width 4.0 mm and the 6.5 mm warn line are Kent's rulings 9 and 5; 6.5 already exists as `STITCH_WIDTH_MAX_MM` in `app/src/lib/digitizer.js` — import it, do not retype it. No clamp, no auto-split (`splitAboveMm` is NOT passed).
- **Exact user-facing strings:**
  - name: `Shape N · Column`
  - `A column needs at least 2 points.`
  - `This column is too short to sew.`
  - `This column folds over itself — widen the bend or narrow the column.`
  - width note: `Sews X.X mm on <fabric label>.` (one decimal)
  - wide warning: `Over 6.5 mm sewn — long satin stitches can snag. Consider a fill, or two columns.`
  - mode hint: `Click along the middle of the stroke, then double-click to finish.`
- A column cannot be a cut-out and cannot be a cut-out's parent.
- Engine edits in `src/` only; run `node app/scripts/copy-engine.mjs` before any Studio/e2e run after one.
- Svelte: legacy syntax only (`export let`, `on:`, `$:`). A `$:` tracks only what it reads lexically. `EmbroideryField.svelte` has no mount test: `cd app && npx vite build` is its compile gate.
- Edit tool only for source edits. Never pipe a test run to `tail`/`head`; log to a file with `echo "EXIT=$?"` appended and read the log.
- **This machine is short on CPU.** One heavy job at a time. Studio suite: `cd app && npx vitest run --maxWorkers=2`. Never run the Python digitizer suite. Playwright: only the spec files a task names.
- Work only in `C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\.claude\worktrees\manual-columns`. Scratch files only under `.superpowers/sdd/2026-10-01-manual-columns/` (a repo hook refuses shell deletes under the worktree). Never start, stop or restart anything on port 8721.
- Before each commit: `git status --porcelain`; STOP if a tracked file you did not touch is modified. Stage only your files. Do not push.
- Commit trailers:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01WQy2mffhR9ExF1c8PGKmM7
  ```
- Public repo: no client artwork or names in fixtures.

---

### Task 1: Engine — sew a region from authored rails

**Files:** Modify `src/digitize.js`; Test `test/digitize.test.js`.

**Interfaces:**
- Consumes: `satinplay.satinFromRails(railA, railB, rungs, opts)` and `satinplay.centerRun(railA, railB, rungs, opts)` from `src/satinplay.js` (read their signatures and what `centerRun` returns before use).
- Produces: a region shape may carry `sewAs: { kind: "column", railA: [{x,y}...], railB: [{x,y}...] }` (region px, both rails running the same direction). With `tierOverride: "satin"` and no holes, its top stitch is `satinplaymod.satinFromRails(railA, railB, [], { spacingMm: satinSpacingMm, pxPerMm: pxPerFinalMm, pullCompMm, slantDeg })`, and when the underlay style in force is `center_run` its underlay is `satinplaymod.centerRun(railA, railB, [], …)` instead of `underlayRuns`' straight PCA line. Every other underlay style and everything else (outline, bbox, spans, `shapeOutlines`, trims) reads `outer` as today.

- [ ] **Step 1: failing tests** (rails for a straight column: `railA` = (0,0)→(300,0), `railB` = (0,24)→(300,24); `outer` = railA + reversed railB; `pxPerMm: 6`, `targetWidthMm: 50`, garment 8×8 in):
  1. With `sewAs`, the design's satin stitches for the shape equal — point for point after the engine's own `T()` rounding — a direct `satinFromRails` call on the same rails with the same options (build the expectation with the engine's exported `fit` to get `pxPerFinalMm`; read how an existing test derives it).
  2. Without `sewAs`, the same `outer` with `tierOverride: "satin"` produces today's stitches — assert it is NOT equal to (1) only if they genuinely differ; the binding assertion is that removing `sewAs` reproduces the pre-change output (hash it before your change and pin the hash).
  3. A CURVED column (rails along a quarter circle, radius 200 px, width 24 px), `underlay: true`, fabric with `satinUnderlay: "center_run"`: every underlay stitch lies inside `outer` (even-odd point-in-polygon, 0.5 px tolerance). Show it FAILS before the underlay change.
  4. `sewAs` with a hole present or `tierOverride: "fill"` is ignored (sews as fill, as today).
  5. The module works under Node: `satinFromRails` is reached through a real binding (this test fails with a TypeError/ReferenceError before Step 2).
- [ ] **Step 2: implement.** Add `const satinplaymod = _node ? dep("./satinplay.js") : root.EMB;` beside the other bindings. In the `if (thin)` top-stitch branch use the rails when `shape.sewAs && shape.sewAs.kind === "column"`. In the fabric-mode underlay branch, when `thin`, the column has rails and the style is `center_run`, push `satinplaymod.centerRun(...)`'s run(s) in the same form `underlayRuns` returns. Comment both sites with the spec section.
- [ ] **Step 3:** `node --test` from the repo root to a log; baseline count + your tests, zero failures. `node app/scripts/copy-engine.mjs`.
- [ ] **Step 4: commit** — `Engine: a region with authored rails sews satin between them, and its centre run follows them`.

---

### Task 2: Rails from a spine, and one function for a shape's ring

**Files:** Create `app/src/lib/spineRails.js`, `app/src/lib/spineRails.spec.js`; Modify `app/src/lib/manualShapes.js`, `app/src/lib/flow.js`; Test `app/src/lib/manualShapes.spec.js`, `app/src/lib/flow.spec.js`, `app/src/lib/projectFile.spec.js`.

**Interfaces — produces:**
- `spineRails.js`: `railsFromSpine(spineFlat, widthPx) → { railA, railB, ring } | null` — `spineFlat` is a flattened open polyline (≥2 distinct points); rails are offset ±`widthPx/2` along per-vertex normals (averaged adjacent tangents, miter length clamped to 2× the half-width), SAME point count and direction; `ring = railA.concat(railB.slice().reverse())`. `null` when the spine has under two distinct points or `widthPx` is not > 0.
- `manualShapes.js`:
  - `export const COLUMN_DEFAULT_MM = 4.0;`
  - `isColumn(shape) → boolean` (`shape.kind === "column"`).
  - `columnIssues(shape) → string[]` — `A column needs at least 2 points.`; `This column is too short to sew.` (flattened spine length ≤ `MIN_COLUMN_LEN_PX = 4`); `This column folds over itself — widen the bend or narrow the column.` (the rail ring self-crosses, tested with the module's ring self-intersection check on `ring`). Too many points uses the existing message.
  - `shapeRing(shape) → [{x,y}...]` — the ring the engine sees: closed shape → `flattenShape(points, curves, true)`; column → `railsFromSpine(flattenShape(points, curves, false), widthPx).ring` (or `[]`).
  - `shapeProblems(shape) → string[]` — `columnIssues` for a column, else `shapeIssues(shapeRing(shape))`. `isSewableShape(shape)` = no problems and not a cut-out.
  - `columnRails(shape) → { railA, railB } | null`.
  - `manualShapeName` → `Shape N · Column` for a column.
  - `resolveCutOuts`: a column is never a solid (cannot be a parent); a column with `cutOut` is treated as not a cut-out. `withCutOut` on a column returns it unchanged.
  - `shapesToRegions`: a valid column emits `{ id, outer: ring, holes: [], tierOverride: "satin", angleOverride: null, sewAs: { kind: "column", railA, railB } }`; an invalid one is skipped like an invalid shape.
- `flow.js` `isSewable`: uses `isSewableShape`.

- [ ] **Step 1: failing tests.** `spineRails.spec.js`: a straight horizontal spine of length 300, width 24 → rails exactly 24 apart, ring area 7,200, both rails 2 points, same direction; a right-angle spine → the corner's miter is clamped (no rail point further than 2× half-width from its spine vertex); a curved (flattened quadratic) spine → rails have the spine's point count; zero width / one point → `null`. `manualShapes.spec.js`: `shapeRing` for both kinds; `columnIssues` for each message (a hairpin spine wider than its bend radius folds); `shapesToRegions` emits the `sewAs` region and, for shapes with no column, output deep-equal to before (pin with the existing no-cut-out fixtures); `resolveCutOuts` never picks a column as parent even when its ring contains a cut-out; `manualShapeName`; a 2-point column `isSewableShape`. `flow.spec.js`: an element holding only a valid column is sewable. `projectFile.spec.js`: a column round-trips with `kind` and `widthPx` intact, version unchanged.
- [ ] **Step 2: implement.**
- [ ] **Step 3:** full Studio suite (`--maxWorkers=2`) to a log; zero failures.
- [ ] **Step 4: commit** — `manualShapes: a column is an open spine plus a width, and shapeRing says what ring any shape presents`.

---

### Task 3: Node editing an open spine, and width in millimetres

**Files:** Modify `app/src/lib/fieldNodeEdit.js`; Test `app/src/lib/fieldNodeEdit.spec.js`.

**Interfaces — produces:**
- `authoredInFieldMm(shape, fit)`: for a column, `n − 1` handles (no closing segment) and an extra `rails: { a: [[x,y]...], b: [[x,y]...] }` in field mm.
- `hitAuthored(authoredPx, px, py, closed = true)`: with `closed === false` no phantom closing handle or edge.
- `applyHandleDrag`, `insertAnchor`: unchanged for valid segment indices; never called with the closing index on a column.
- `removeAnchor(shape, index)`: floor is 2 for a column (3 otherwise); for a column, removing an end anchor drops that end's own segment curve (index 0 → `curves[0]`; last → `curves[n−2]`) and shifts the rest; interior removal merges the two neighbours into one straight segment.
- `editedElementPatch`: validity via `shapeProblems(edited)` (first string as `{ error }`).
- `flatBBox`, `ringInsideBox`: via `shapeRing(shape)` — so the bbox equals the engine's (the rail ring) and the placement-box guard sees the rails.
- `columnWidthMm(shape, fit) → number` (`widthPx × fit.mmPerPx`); `withColumnWidthMm(shape, fit, mm) → shape` (sets `widthPx = mm / fit.mmPerPx`, floor 0.1 mm); `columnSewnMm(shape, fit, pullCompMm) → number`.

- [ ] **Step 1: failing tests**, including, through the REAL engine like the file's invariance tests: (a) an element with a rectangle and a column; drag one spine anchor; `editedElementPatch`; regenerate — the rectangle's outline moves by no more than the existing tolerance and `fit.mmPerPx` holds to 1e-12; (b) the same after `withColumnWidthMm` doubles the width via `refitShapesPatch` — proves the bbox uses the rail ring; (c) **ruling 12**: generate the element at `sizeMm` S and at 2S — `columnWidthMm` doubles (±0.05 mm), and the measured sewn width (max cross length among the column's satin stitches, in mm) grows by `2 × drawn + pullComp` over `drawn + pullComp`, i.e. LESS than 2×; assert the ratio is within 0.03 of that prediction for the fabric in force.
  Unit: `removeAnchor` bookkeeping for first / last / interior anchors with curves on every segment; floor 2 returns `null`; `hitAuthored(..., false)` never returns index n−1 for an edge or handle.
- [ ] **Step 2: implement.**
- [ ] **Step 3:** suite to a log; zero failures; the pre-existing invariance tests unmodified.
- [ ] **Step 4: commit** — `fieldNodeEdit: an open spine edits like a shape, and a column's width reads and writes in mm through the fit`.

---

### Task 4: The popover for a column

**Files:** Modify `app/src/lib/shapePopover.js`, `app/src/ui/ShapePopover.svelte`, `app/src/ui/theme.css`; Test both specs.

**Interfaces:**
- `popoverModel({ element, shapeId, fit, fabric })` — `fit` and `fabric` are new optional context (`fabric = { label, pullCompMm }`). For a column: name `Shape N · Column`; rows `[ color, { key: "widthMm", kind: "number", label: "Width", value: <drawn mm, 1 decimal> | null when no fit, hint: "mm", step: 0.1, min: 0.5, note, warn }, editPoints, delete ]`. `note` = `Sews X.X mm on <label>.`; when sewn > `STITCH_WIDTH_MAX_MM` the note is the wide warning and `warn: true`. No stitch-type, angle or Cut out rows.
- `popoverPatch(ctx, "widthMm", value)` with `ctx.fit` → `{ shapes }` using `withColumnWidthMm`; `null` when `fit` is missing or the value is not a positive number. (The field re-fits it — Task 5.)
- `ShapePopover.svelte`: a `number` row honours `row.step` / `row.min` (default step 1 as today) and commits on `change` (blur/Enter), not on every keystroke, when `row.key === "widthMm"`.

- [ ] Steps: failing tests → implement → both specs + suite to a log → commit `Popover: a column shows its width in mm, what it sews at, and warns past 6.5`.

---

### Task 5: The hoop canvas

**Files:** Modify `app/src/ui/EmbroideryField.svelte`.

Behaviour:
1. `popModel` passes `fit: manualFit(el)` and the fabric in force (`{ label, pullCompMm }` — find how the field or its parent knows the garment's fabric; if only `App.svelte` does, add a prop and thread it) to `popoverModel` / `popoverPatch`.
2. `onPopChange` for `widthMm` on a manual element commits through `refitShapesPatch` (like `cutOut`), refusing with `shapeProblems`' first string when the wider column is invalid.
3. `drawAuthoredNodes`: a column draws its spine OPEN (no `closePath`), `n − 1` handles, anchors from 2 points up, and its two rails as thin lines so the width is visible while editing.
4. Every `hitAuthored` call passes `closed = !isColumn(shape)`; edge-insert never targets the closing index.
5. Remove point: floor message for a column is `A column needs at least 2 points.`; the right-click item's at-floor test uses the per-kind floor.
6. The drag guards use the functions Task 3 changed — no code change expected; verify the box guard now stops a column's RAIL at the placement box.

- [ ] Verify: `npx vite build` (EXIT=0, no new warnings), suite, then drive it once in a browser with a throwaway script under the workspace (model on `.superpowers/sdd/2026-10-01-manual-holes/task6-drive.mjs` if that directory still exists in the sibling worktree `../manual-holes`; else on `app/e2e/manual-cutout.spec.js`'s helpers). Because Task 6 (drawing) is not built yet, seed a column by loading a project/element whose `shapes` already contains one — find how the e2e specs seed state, or use the app's own import. Check: the column sews as satin; click it → popover `Shape 1 · Column` with a width and the sews-note; set width 6.0 → caption changes, nothing else moves; drag a spine anchor; right-click an anchor → Remove point. Screenshot to the workspace; open it and say what you see.
- [ ] Commit — `Field: a column's spine edits open, its width sets from the popover, and nothing else moves`.

---

### Task 6: Drawing a column on the side canvas

**Files:** Modify `app/src/ui/ManualPanel.svelte`, `app/src/ui/TraceImportPanel.svelte`; Test `ManualPanel.spec.js`.

Behaviour:
1. Mode strip gains `Column` (`Shape | Hole | Column`). In Column mode: the mode hint is the Global Constraints string; a click always places a point (never selects, like Hole mode); a click near the start does NOT finish (a spine may end near where it began); **double-click, Enter, or the Finish button finishes** with ≥2 points. `canFinish` and the issues banner use an open-spine check in this mode.
2. `finishShape` in Column mode creates `{ id, kind: "column", points, curves, widthPx, colorRgb }` — no `stitchType`/`angleDeg`. `widthPx = COLUMN_DEFAULT_MM / mmPerPx`, where `mmPerPx` comes from a new optional prop `fit` (the element's `design.fit`, passed by the parent — find where ManualPanel is mounted and what it can reach; if the fit is not reachable there, thread it from `App.svelte`), else the nominal `1 / PX_PER_MM`.
3. Render: a column draws as its rail ring filled in its colour (Dim applies) with the spine as a thin line and the label `COLUMN`; validity via `shapeProblems`; hit-test via `pointInShape(shapeRing(s))`.
4. List row `Shape N · Column`; assign box for a column: Dim, Color, and a Width row (number, mm, step 0.1, with the same note as the popover via the same lib functions) — no Stitch type, Fill angle or Cut out rows. With no fit the width row shows the nominal mm.
5. `TraceImportPanel`'s preview of existing shapes uses `shapeRing`.

- [ ] Steps: failing spec tests (mode strip has three entries; 2 clicks + double-click in Column mode emits a `kind: "column"` shape with `widthPx` > 0 and no `stitchType`; near-start click adds a point; list row text; assign box rows; Shape and Hole modes' existing tests unmodified) → implement → suite + `vite build` → browser drive (draw a curved column across the canvas; see satin on the hoop; screenshot at 1440×900, open it) → commit `ManualPanel: Column mode — draw a spine, get a satin column`.

---

### Task 7: End to end, and the docs

**Files:** Create `app/e2e/manual-column.spec.js`; Modify `docs/scope/5-review-manual-editing.md`, `MASTER_SCOPE.md`, `COOKBOOK.md` (the manual-lane entry), `.claude/memory/` (one note + its index line, < 260 chars).

e2e (copy helpers from `app/e2e/manual-cutout.spec.js`; wait-for-change-then-settle on the caption; spend the hint-banner press before reading hoop coordinates):
- (a) Column mode: draw a 3-point spine, double-click → list row `Shape 1 · Column`, the caption shows stitches, and a pixel on the spine inside the fabric is thread.
- (b) Click it on the hoop → popover `Shape 1 · Column`, Width reads a number, the note starts `Sews `. Set Width to 6.0 → stitch count changes; the note still reads `Sews`; set 7.0 → the wide warning text shows and it still sews.
- (c) **Ruling 12**: read Width (W1) at the current size; resize the design (the size field in the panel) to 2× its width; Width reads 2×W1 (±0.1) — the drawn width scaled — and the note's sewn figure is drawn + the same fixed amount as before (sewn − drawn unchanged ±0.05).
- (d) Drag a spine anchor on the hoop → the count changes and a second shape drawn beforehand has not moved (2 px).
- (e) A closed shape drawn in Shape mode in the same design is unaffected by any of the above (its popover still offers Fill/Satin).
- Prove (a) by making `shapesToRegions` skip columns → red → restore (confirm `git diff --stat` clean).
- Run only: `npx playwright test e2e/manual-column.spec.js e2e/manual-cutout.spec.js e2e/field-node-edit.spec.js`.

Docs: a dated section in the area doc (what shipped; ruling 12 with the three measured pairs and the note's path; the three spec corrections; what is not built — taper, runs, run↔column conversion, auto-split; the pull-comp attribution is unconfirmed); MASTER_SCOPE area-5 paragraph with `(verb date — source)` pointers (word budget 27,000 — check with `/c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/digitizer/.venv/Scripts/python.exe -m pytest -q tests/test_scope_budget.py` from `digitizer/`, the one Python command allowed); COOKBOOK manual-lane entry gains the column bullets (`shapeRing` is the one ring; width is `widthPx`); memory note: the width-on-resize finding (k ≈ 0.80–0.85; outline scales, a fixed ~0.3–0.55 mm does not; no clamp 0.67–11.8 mm; one digitizer; where the note is).

- [ ] Commit — `e2e + docs: columns proven end to end, and ruling 12 on the record`.

---

## Done means

- Engine and Studio suites green; `manual-column.spec.js` green; browser screenshots at 1440×900 and 1024×768.
- PR ready for review, auto-merge armed while `BLOCKED`; body names rulings 2, 5, 9, 12, the three spec corrections, and what CI is the first run of.

## Not in this plan

Open runs (plan 3); run ↔ column conversion; taper; auto-split of wide columns (needs a sew-out — gate 1); drawn two-rail columns; the side panel's re-fit leftovers from plan 1.
