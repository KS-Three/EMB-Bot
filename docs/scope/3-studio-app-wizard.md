# Area 3 — Studio app / guided wizard

**Part of [`MASTER_SCOPE.md`](../../MASTER_SCOPE.md)** — this is the detail
for one capability area. The live one-line verdict (Status / Confidence /
what is next) is in MASTER_SCOPE; this file is the supporting record.

**Claim discipline:** a claim here should carry a `(verb date — source)`
pointer — `confirmed` = checked against code or a passing test, `measured` =
a number was produced, `suspected` = neither. Much of this file predates that
rule and is **not yet annotated**; anything unannotated is unverified until
someone checks it. Test counts, stitch counts and corpus grades written here
were snapshots when written — do not quote one as a current baseline.
Dated narrative belongs in [`../scope-history.md`](../scope-history.md).

---

The Svelte guided flow (garment → content → review → download), saved
projects, the Layers panel entry point — plus fabric & garment presets
(`src/fabrics.js`, `src/garments.js`), folded in here since they're wizard
inputs, not a separate product surface.

**Status:** Implemented. 8 studio slices built and merged, plus two later
feature commits (the auto-digitize review flow, the Layers panel). README
calls it "the primary product."

**Confidence: Medium**, with the one gap that was holding it there now
closed. **615/615** Studio (vitest) tests pass (33 files, verified
2026-08-11), and nearly every `app/src/lib/*.js` logic module has a paired spec
— that coverage is still mostly **logic-only**, not UI-behavior, but the
live-browser e2e side grew real breadth this pass: `app/e2e/wizard-smoke
.spec.js` (merged, PR #6) drives the full garment→content→review→download
path in a real browser and asserts real cross-step state, and the
broadening this doc used to list as the open next step — **merged, PR #29**
— covers all three named axes: two more garment types (Hat Front, Full
Back, each confirmed the review recap reflects the actual pick), the
image-content path (`ImagePanel`'s client-side canvas flatten, previously
untested — confirms the review step's image branch and a real download),
and two more export formats beyond DST (PES verified by its `#PES0001`
magic header, EXP by real stitch-record byte size, plus the PDF worksheet
as a fourth format via a distinct code path). A second live e2e spec exists
alongside it — `app/e2e/digitize-stale-edits.spec.js` (merged, PR #21) —
covering the stale-edit-recovery path; see area 5 below, since that's the
gap it was built to close. The previously-documented rotation/hoop-fit bug
is **FIXED** (`8e668d3`, merged): text auto-fit's scale/clamp now computes
against the exact rotated-bbox footprint instead of the unrotated glyph
bbox, with two regression tests reproducing the original overflow on a
non-square hoop across several non-180° angles (267/267 engine, 321/321 app
at that historical commit — not today's totals, which have since grown
further).

**Manual shape drawing gained curved edges, 2026-08-07** (`ManualPanel
.svelte`, the "Shapes" content type's hand-drawn-outline tool): dragging the
small handle at any edge's midpoint bows it into a quadratic curve — live
while drafting, and retroactively on a finished shape via "Edit points."
Prompted by directly observing Ember Design's own manual digitizing tool
(draw curved/straight lines, satin-fill the closed shape); confirmed via
code reading, not assumed, that EMB-Bot's satin/fill machinery already
derives rails/caps from any closed polygon via medial-axis skeletonization
— the missing piece was purely the curve-drawing UI, not new stitch-
generation capability. Curves live in their own sparse per-shape field
(`shape.curves`, segment-index → quadratic-control-point) and are only ever
flattened to plain points at the `shapesToRegions` hand-off boundary — the
Python pipeline and both stitch engines never need to know a curve exists,
and a shape with no curved segments flattens byte-identical to before this
feature. 30 new tests (22 pure-geometry, 8 component drag-gesture), plus
live-browser verification: drew a curved shape, generated real fill
stitches from it, satin-stitched it, and re-curved a different edge after
finishing — all client-side, no backend needed. Branch
`manual-shape-curve-tool`. Doesn't move this area's Status/Confidence
verdict (additive UI on an already-shipped content type).

**Manual shape tool gained an image-trace starting point, then real UX
fixes, 2026-08-09** (`ManualPanel.svelte`, `app/src/lib/manualTrace.js`,
`app/src/lib/manualShapes.js`) — three real, user-reported problems fixed
in sequence, not a single planned feature:

1. **Trace image → shapes** (PRs #98–100): a "Trace image…" button runs
   the engine's existing marching-squares contour tracer
   (`EMB.traceRegions`) + RDP simplification on an uploaded raster, then
   fits ONE quadratic-Bezier control point per segment
   (`fitCurvesForRing`) to produce editable shapes directly instead of
   requiring hand-tracing from scratch. Holes are detected and warned,
   never silently emitted as a shape. `app/e2e/manual-trace-import.spec.js`
   drives it against a real browser.
2. **Editor was cluttered, selection/cursor gave no feedback** (direct
   user feedback) — fixed in PR #104: non-selected shapes de-emphasize
   (fill-opacity 0.18, label dropped — reuses `DigitizePanel.svelte`'s own
   established dimming value rather than a new number), clicking a
   shape's body selects it (`pointInShape`, even-odd ray-cast), and the
   canvas cursor now changes contextually (`grab`/`copy`/`pointer`/
   `grabbing`/`crosshair`) instead of one static cursor throughout.
3. **Step-nav tabs read as messy, hover looked identical to active,
   content forced scrolling** (direct user feedback) — fixed in PR #105:
   active vs. hover are now visually distinct (mirrors the `.elrow.sel`
   tint pattern used elsewhere in the app), disabled steps read as
   "grayed out" not "gone," numbered/checkmark progress badges added, and
   the element list is capped at a scrollable 220px so a selected editor
   no longer gets pushed below the fold. **Found but explicitly NOT
   fixed** during this PR's own visual QA pass: at ≤375px width the top
   bar has no narrow-width handling and overlaps ("Bot Studio" collides
   with "My designs"), causing horizontal page overflow — pre-existing,
   out of scope, flagged here since nothing before this pass had driven
   the app narrow enough to notice it.

Also removed the old frozen standalone `EMB-Bot.html`/`src/app.js` tool
(PR #101) — confirmed via `app/scripts/copy-engine.mjs`'s `ENGINE_FILES`
list that nothing it used is still shared with the Studio build before
deleting it; it had been reading as a second, competing app to Kent.

**Curve-smoothing approach reconsidered against a comparable tool, not
changed.** A hands-on evaluation of `kent746/shape-tracer`
(`docs/shape-tracer-evaluation.md`, PR #103) found its tracer core solid,
but it smooths via a Catmull-Rom spline through points, not
`fitCurvesForRing`'s per-segment independent quadratic fit. Tested
numerically against the real `smoothPathD` source (not a guess) on a
square, an L-shape, and a 5-point star: wholesale Catmull-Rom reintroduces
real corner overshoot (12.5px on the square, 10px on the L-shape) that
`fitCurvesForRing` avoids entirely (0px on all three) — the exact defect
`fitCurvesForRing` was built to avoid. A narrow tangent-continuity upside
exists on rounded sections but rarely triggers at production's default
tolerances and doesn't clear the bar for a hybrid given the schema
constraints. Verdict: no change made.

**UI icon system foundation landed, 2026-08-09** (`app/src/ui/Icon.svelte`,
branch `ui-icon-system-foundation`) — a live Playwright audit of the running
app found 13 component files rendering UI affordances (undo/redo, hint
lightbulb/dismiss, canvas-toolbar zoom/fit/snap/jumps/trims/play, dropdown
chevrons, etc.) as raw Unicode/emoji characters instead of real icons —
inconsistent across OS/browser font stacks, and auto-snap literally showed
as the 🧲 emoji. This PR is the narrow foundation only: one reusable
`Icon.svelte` (24x24 inline SVG, 1.75px stroke, `currentColor`, no new
npm dependency) hand-drawn for 15 icons covering the full inventory found,
wired into the two highest-leverage shared spots (`App.svelte`'s topbar
undo/redo, `Hint.svelte`'s lightbulb + dismiss — the latter fixes every
hint banner app-wide at once since every hint routes through it). Also a
conservative elevation/shadow pass in `theme.css` (topbar, `.tile`,
`.tcard`, `.elrow`, `.drawer-row` gained `--shadow-1`, reusing existing
tokens — no new palette). The other 11 files the audit found are
deliberately untouched, left for follow-up PRs that depend on this one
merging first (ThreadPicker, ContentStep, DesignPanel, DigitizePanel,
EmbroideryField, FontBrowser, FontCredits, ImagePanel, ManualPanel,
ProjectsDrawer, StepNav). Doesn't move this area's Status/Confidence
verdict — visual/consistency polish, not a capability change.

**All 11 follow-up files done, 2026-08-10** (PRs #111-115, a parallel
4-way fan-out plus a small `Icon.spec.js` coverage reconciliation) — every
file the original audit found is now wired to `Icon.svelte`, zero raw
Unicode/emoji affordances left anywhere in the app. `EmbroideryField.svelte`'s
canvas toolbar (the most visible cluster — zoom/fit/magnet/jumps/trims/
play), `DigitizePanel.svelte`'s Layers panel (5 new icons added to the
shared registry: `arrowUp`, `arrowDown`, `exclude`, `revert`, `edit`),
`ManualPanel.svelte`/`ContentStep.svelte` (including the "+ Text/Image/..."
add-tiles, which used a literal `+` character prefix, not just a missing
icon), and the 7 remaining smaller panels (`ThreadPicker`, `DesignPanel`,
`ImagePanel`, `FontBrowser`, `FontCredits`, `ProjectsDrawer`, `StepNav` —
`StepNav`'s own `✓` and `DesignPanel`'s `⚠` now route through `Icon.svelte`
too). One real gap the parallel structure created and then closed: each of
the 4 PRs deliberately left `Icon.spec.js`'s inventory test untouched to
avoid guaranteed conflicts with sibling PRs editing the same file — PR #115
reconciled that afterward, adding the 6 icon names (`arrowUp`, `arrowDown`,
`exclude`, `revert`, `edit`, `reset`) the fan-out added but hadn't covered.
Visually verified end-to-end via live Playwright against the real merged
app (not just unit tests) — confirmed clean SVG rendering, no fallback
placeholders, no accessible-name regressions. Doesn't move this area's
Status/Confidence verdict, same reasoning as the foundation entry above.

**Fabric-preset accuracy: pending sew-out** — kept as an explicit separate
note, not blended into the wizard's own score. README says it outright:
"Presets are starting points — stitch a test on your machine and tell me if
a fabric needs tuning." No physical validation has happened yet.

**Next step:** with the three-axis e2e broadening landed, the wizard-flow
gap this doc tracked longest is closed; whether that alone earns a bump to
High or Medium stays right pending real UI-behavior (not just logic) specs
is Kent's call, not this pass's to decide unilaterally — left at Medium
here. Fabric-preset accuracy remains sew-out-gated, unchanged.
