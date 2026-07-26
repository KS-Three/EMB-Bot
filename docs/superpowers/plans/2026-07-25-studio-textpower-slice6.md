# Studio Slice 6: Arc Text + Multi-line + PNG Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Text elements can curve along an arc (the classic hat arch) and span multiple lines; the download step gains a PNG preview export.

**Architecture:** Arc + multi-line live in the ENGINE's glyph layout (`src/satinfont.js layoutText`) as additive opts — a measure pass computes each line's total advance, then each glyph is rotated to the arc tangent and placed on the circle (straight text = the exact current path, untouched when `arcDeg` is 0/absent). `buildLetteringDesign` passes `arcDeg` through. The app adds a Curve slider + textarea per text element; PNG export renders the combined design to an offscreen canvas.

**Tech Stack:** unchanged. Branch `feat/studio-textpower`.

## Global Constraints

- Engine changes ADDITIVE & BACK-COMPAT: `arcDeg` absent/0 AND single-line text ⇒ behavior identical to today (existing 145 engine tests untouched and green; satinfont has no byte snapshots, but keep the straight path structurally the same code where practical).
- Arc semantics: `arcDeg` = TOTAL angle (degrees) the text spans; **positive arches UPWARD** (rainbow — first/last letters lower than the middle IN THE FINAL RENDERED/SEWN OUTPUT); negative = valley. Range the UI exposes: −180…180. Glyphs rotate to the local tangent; inter-glyph arc length preserves the straight-text advances (kerning/letter spacing still apply).
- Multi-line: `\n` splits lines; each line is CENTERED horizontally; vertical stacking = `font.leading` units per line (fallback `unitsPerEm`); first line on top IN THE RENDERED OUTPUT. Arc applies per-line (each line gets its own arc of the same arcDeg).
- App tests `.spec.js`; `src/` may be modified ONLY in `satinfont.js` + `digitize.js` (arcDeg pass-through) this slice.
- PNG export: offscreen canvas 1200px long side, `renderRealistic` design-fit (no hoop), white-ish fabric, `canvas.toBlob("image/png")` → download `design.png`.

---

### Task 1: Engine — arc + multi-line in layoutText (Sonnet, careful)

**Files:**
- Modify: `src/satinfont.js` (layoutText), `src/digitize.js` (buildLetteringDesign passes `arcDeg: o.arcDeg || 0` to both layoutText calls)
- Test: `test/satinfont.test.js` (NEW — node:assert style like the other engine tests; loads a real font JSON like test/digitize.test.js does)

**Implementation notes:**
- Refactor layoutText: FIRST tokenize `text.split("\n")` → lines. For each line, a MEASURE pass computes per-glyph pen offsets + the line's total advance (reusing the existing advance/kerning/letter-spacing logic, in font units). Then a PLACEMENT pass emits glyph runs:
  - Straight (arcDeg falsy): pen origin for the line = `-totalAdv/2` (CENTERED — NOTE: today's single-line output is left-anchored at 0; centering changes only the absolute origin, which is IRRELEVANT because buildLetteringDesign re-centers by bbox — verify the digitize tests still pass; do NOT center if it breaks anything, instead center only multi-line lines relative to each other).
  - Arc (arcDeg ≠ 0): `R = lineArcLenPx / |arcRad|` where lineArcLenPx = totalAdv*u2px; each glyph's pen-CENTER arc position `s` (from line center) → `θ = s / R` (radians, sign of arcDeg); glyph transform = rotate glyph-local px coords (x_local = (x+ox)*u2px − penCenterPx, y_local = y*u2px + lineYpx) by θ about the pen point, then translate onto the circle. Work out the y-sign empirically: font-space here is y-DOWN (SVG source), while the final render flips y — the CONTRACT is visual (positive = arch up in the render); Task 1 MUST include a rendered-PNG check (see verification) not just math assertions.
  - Multi-line: `lineYpx = lineIdx * (font.leading || font.unitsPerEm) * u2px` added to glyph y (y-down font space puts later lines below — verify against the render).
- `runs` keep the same shape (`{pts, kind, jump}`) — routing/underpath per glyph column is unchanged (routeGlyph operates on transformed rails; rails/rungs rotate rigidly, satin math is orientation-agnostic).

**Verification (this task):**
- New engine tests: (a) straight single-line output deep-equals the pre-change behavior for "AB" (capture invariants: run count, first/last stitch coords within ε of current values — compute the expected values by running the CURRENT code before editing and hard-coding them); (b) arcDeg 120 on "MMM": the middle glyph's bbox center y differs from the outer glyphs' by > 2mm in DST output via buildLetteringDesign, and outer glyphs are ROTATED (check stitch-direction spread); (c) two-line "AB\nCD": design heightMM ≈ 2× single-line height ± leading tolerance; widthMM ≈ single-line width.
- RENDERED check: harness `TEXT="CURVED" ARC=120` через a small node script → DST → `tools/render-dst.mjs` → PNG; the CONTROLLER views it (worker: generate the PNG and report its path; note in report).
- Full engine suite `node --test` green (145 + new); app suite untouched-green.
- Commit.

### Task 2: App — Curve slider + multi-line textarea (Haiku)

**Files:** `app/src/lib/project.js` (+spec: text element gains `arcDeg: 0`), `app/src/lib/generate.js` (+spec: passes `arcDeg`; arc'd design differs in heightMM), `app/src/ui/TextStep.svelte` (input → `<textarea rows=2>`; "Curve" slider −180…180 step 10, value label "°", dispatch elupdate patch)

- Verify: full app suite green; build clean. Commit.

### Task 3: PNG export (Haiku)

**Files:** `app/src/lib/exporters.js` (+spec), `app/src/ui/DownloadStep.svelte`

- `exportPNG(design) → Promise<{blob, filename:"design.png"}>`: offscreen canvas, long side 1200 scaled to design aspect (from widthMM/heightMM), `renderRealistic(canvas, design, { pad: 40 })` (design-fit), `canvas.toBlob`. Spec (node): assert it returns filename + calls renderRealistic — jsdom has no canvas2d: mock `renderRealistic` via vi.mock and stub `toBlob`; assert canvas dims aspect matches design.
- DownloadStep: "PNG" button → generate combined → exportPNG → triggerDownload({bytes: blob, ...}) (adapt triggerDownload if it needs Blob support — it already wraps bytes in a Blob; pass the blob directly with a small guard).
- Verify: suite green; build clean. Commit.

### Task 4: Browser acceptance + docs (controller)

- Live: curve slider bends "CURVED TEXT" on the field (arch up at +, valley at −, straight at 0); two-line textarea stacks lines; arc + multi-element (curved text over an image) renders; PNG downloads and is a real image; DST decodes with the arch visible. Regression single-line/straight.
- README, ledger, commit; final whole-branch review (opus); fix loop; merge to main + push.

## Notes for the implementer
- READ `src/satinfont.js` lines ~160-200 (the pen/TX/TY structure) before touching it.
- The glyph transform must rotate railA/railB/rungs coherently (they share the same affine) — routeGlyph after that is orientation-agnostic.
- DO NOT change `routeGlyph`, `satinplay`, or any satin math.
