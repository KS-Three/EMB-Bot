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

---

## The display layer, 2026-08-25 — four passes, and what they say about coverage

Four PRs (#239, #240, #242, #244) swept the wizard, both artwork panels, the
embroidery field and the design tokens. Numbers, PR-by-PR detail and the
session's process notes are in [`../scope-history.md`](../scope-history.md)
under its 2026-08-25 entry; what belongs here is what still governs a decision.

**The suite does not speak for the display layer, and the gap is not small.**
Every defect below was live on `main`, and none of them failed a test. Two were
functional rather than cosmetic:

- **The wizard's `Next` button rendered white-on-white on every step.** A
  neutral `background` on `.stepnav-controls button` matched `button.primary`
  at equal specificity (0,1,1) and won on source order ~490 lines later; the
  white `color` came from `button.primary` and was never overridden. The flow's
  primary CTA was a blank rounded rectangle.
  *(confirmed 2026-08-25 — computed style read off the live page)*
- **The field's right-click tool menu created invisible elements.** It is
  available on every step, but element editors live in the Content step's
  panel, so "Draw shapes" from the Garment step appended and persisted a real
  element with no visible change anywhere. Repeat it and you accumulate orphans
  you cannot see, edit or delete.
  *(confirmed 2026-08-25 — element read back out of localStorage)*

The standing lesson: **a Studio change is not verified until it has been looked
at in a browser.** Logic coverage is broad and did not help here.

`app/e2e/field-chrome.spec.js` (added #242) is the first spec covering the
field's own chrome — control-bar placement, canvas sizing, and the simulator.

**Writing a regression test is not the same as writing one that catches the
regression.** That spec's first version passed with the bug deliberately
re-introduced. The trigger turned out to be narrower than assumed: `.simbar`
merely being in flow does not reproduce it, because side by side the control
row's height is unchanged — only *stacking* the bars does. A regression spec
should be run against the real broken state before it is trusted.
*(confirmed 2026-08-25 — repro run both ways)*

**The paint effect is coupled to `simActive`, and it is a live trap.**
`paint()` opens with `stopSim()`, which reads `simActive`, so the effect's
dependency set reaches it. Any layout change that resizes the canvas while the
simulator is starting will re-enter `paint()` after `startSim()` set the flag
and switch the simulator off in the same tick. `.fieldbars` exists to keep the
control row's height independent of `simActive` for exactly this reason; the
e2e spec fails if a future change lets the bars stack again.
*(confirmed 2026-08-25 — stack trace captured from the running app)*

Related, observed but deliberately not changed: that same effect re-runs on a
simulator toggle with `project`, `runtime` and `canvas` all unchanged,
regenerating the whole design for nothing. It is harmless on `main` today
because it fires before `simActive` is set. It is render scheduling rather than
display, so it was left rather than folded into a UI pass.
*(suspected 2026-08-25 — observed, not root-caused)*

**The embroidery field sizes its bitmap to its pane.** It was a hardcoded
760×560 canvas centred in a much larger pane, using about half the available
area and never growing on a wider screen. A `ResizeObserver` on `.hoop` now
sets `canvas.width/height` to the measured box. This is a view change and
nothing more — `renderRealistic` derives its whole mm→px transform from
`canvas.width/height` via `hoopTransform(garment, cw, ch, pad)`, so a bigger
bitmap is the same hoop and the same design at more pixels, and no physical
constant is involved (ROADMAP gate 1 is untouched). Intrinsic size tracks
displayed size deliberately: stretching the bitmap with CSS instead would
render a blurry stitch preview. `canvasPointFromEvent` already rescales client
px to canvas px, so pointer math holds at any size.
*(confirmed 2026-08-25 — e2e/field-chrome.spec.js pins both properties)*

**Chrome does not sit on the sewable field.** The zoom bar, the drag hint and
the simulator bar were all absolutely positioned inside `.hoop`, painting over
canvas inside the hoop guide — and the two bars collided with each other at the
same offset. `.hoop` holds the canvas and nothing else that can paint over it;
the spec asserts zero overlap. *(confirmed 2026-08-25 — same spec)*

### Design tokens

**A `var(--x, fallback)` whose name is undefined is not a fallback — it is a
silent bespoke value.** Three names the code already consumed did not exist
(`--warn-text`, `--warn-bg`, `--fs-s`), so every call site took its hardcoded
literal and the app shipped two different warning colours, one of them
bypassing the token system entirely. Defining the names fixed every call site
without touching one of them. Worth re-running that check after any new
component lands. *(confirmed 2026-08-25 — theme.css `:root`)*

**Contrast must be checked against the ground a string actually sits on.**
`--muted` and `--warn` both passed on `--surface` and both failed WCAG AA on
`--field-bg` and `--tint`, which is where a good deal of the app's secondary
text lives. Both are retargeted with headroom rather than to the 4.5 line.
*(confirmed 2026-08-25 — sweep walking up for the first non-transparent
ancestor, zero failures after)*

The scale also gained a line-height system (`--lh-tight` / `--lh-snug` /
`--lh-body`, with `--lh-snug` managed on `body`), a density step `--fs-2xs`
that collapsed thirteen off-scale literals, and `--ring` for the selection ring
that was written longhand at three call sites.

**What the audit did not find is the more useful half.** The spacing scale is
respected — the bespoke px left in `theme.css` are borders, icon boxes and grid
gutters, not spacing. Elevation is applied consistently across two tokens plus
one deliberately directional drawer shadow. The card and tile treatments
already agree with each other; only `.fs-trigger` was out of step. **Do not
re-audit these three expecting to find something.**
*(confirmed 2026-08-25 — usage counts over theme.css and the components)*

### Still open

Two display defects were judged least-severe and deferred, not missed: the DST
provenance note on the Download step is a seven-line wall of prose, and `#0134`
repeats as the identity label on every digitize layer row where it
distinguishes nothing — the useful part (glyph, area) is set smaller than the
part that identifies nothing. *(confirmed 2026-08-25 — driven in browser)*

Typography was the third open item here and is **closed** — Kent gave the
direction on 2026-08-25 and it shipped. See "Typography — Kent's standing
direction" at the end of this file.

## Typography — Kent's standing direction (2026-08-25)

Asked for a direction and gave one: **"tighter and more editorial."** That is a
standing ruling, not a one-off approval — new UI is set to it rather than
re-deciding each time. It closed the three items the design-system pass had
left as taste, and MASTER_SCOPE's queue item 10 is resolved on it.

What it resolved to, and the reasoning worth keeping:

**The section label is an eyebrow, and it is keyed on ROLE.** `h3` used to
render at `--fs-md` semi-muted — the same size as the body text under it — so
it competed with its own content and the step's `h2` had nothing to rank
against. Now `--fs-xs`, semibold, uppercase, `--tracking-wide`. Critically the
rule also covers `.tp-label` and `.alignlabel`, which are spans inside
components rather than headings: an `h3`-only rule left "COLOR" and "Font" as
mismatched peers three lines apart on the Content step. **If you add a label
that heads a control GROUP, add it to that selector list.**
*(confirmed 2026-08-25 — driven in browser)*

**A FIELD label is deliberately NOT an eyebrow.** "Letter spacing", "Curve",
"Rotation", the "Chart" beside its select — these name one input, not a group,
and they stay sentence case one rank below. That distinction is the hierarchy;
flattening it undoes the point. Three voices: 25px display, 12px group label,
16px body, with field labels at 14px between the last two.

**The scale is two ramps and only one is modular.** `--fs-2xs/xs/sm`
(11/12/14) is a DENSITY ramp for dense UI — forcing a ratio there yields
8/10/13px, unusable in a tool. From `--fs-md` up is the DISPLAY ramp and it is
a clean 1.25: 16 → 20 → 25. Do not "regularise" the small end.
*(confirmed 2026-08-25 — theme.css `:root`)*

**Tracking has two opened steps because they are different jobs.**
`--tracking-slight` (0.02em) is a nudge for caps in a FIXED box or a label that
wants air; `--tracking-wide` (0.08em) is the eyebrow. Folding the first into
the second pushed the logomark's "EMB" past its own 28px tile — a real
overflow, caught by sweeping every text node for `scrollWidth > clientWidth`.
Run that sweep after any type change. *(confirmed 2026-08-25 — same sweep)*

Measured on the Garment step after the pass: distinct size/weight pairs
**16 → 11**, every size on the scale, every weight a token, zero overflows,
zero WCAG AA failures.

## Display-layer detail moved from MASTER_SCOPE (2026-08-27)

Moved verbatim under the 800-line budget rule; MASTER_SCOPE keeps every rule
in compressed form. Nothing here was edited in the move.

**The display layer is a distinct risk surface, and the suite does not speak
for it.** A 2026-08-25 browser sweep found defects a green suite never touched
— a primary CTA rendering white-on-white on every wizard step, and a canvas
menu creating elements with no visible feedback. Both were shipped. **A Studio
change is not verified until it has been *looked at* in a browser.** Two lesser
display defects are deferred, not missed. *(confirmed 2026-08-25 — area doc)*

**A `var(--x, fallback)` whose name is undefined is not a fallback — it is a
silent bespoke value.** Three such names shipped, so the app carried two
warning colours, one bypassing the token system; two more tokens failed WCAG AA
on the app's own non-white grounds while passing on white. Both closed; re-run
the check when a new component lands. *(confirmed 2026-08-25 — theme.css)*

**Preview thread width is PHYSICAL, and must not be widened.**
`preview.js`'s `THREAD_WIDTH_MM` (0.4, nominal 40wt) is coverage 1.0 against
the engine's 0.40 mm fill rows — rows that just touch — so a fill that is too
open looks too open. **Do not widen it to make fills look solid.** Row spacing
is an unresolved two-population question standing *pending sew-out* (area 1,
"Fill row spacing (law 19)"; `machine.py:45-49`), so widening thread would be
the display layer prejudging a question only cloth can settle — ROADMAP gate 1.
Display-only: it scales pixels, never stitch geometry.
**Caveat:** `lw` has a 1.2 px floor, so below ~3 px/mm the floor sets the drawn
width and coverage reads high. The property holds zoomed in, not on a
thumbnail. Guarded by a test pinning the literal 0.4.
*(confirmed 2026-08-25 — `preview.js`, `preview.spec.js`)*

**Correction (2026-08-25).** The paragraph above first read that widening
thread would "hide the open fill-density item … FILL_ROW_MM running ~2x
light." That overstated a hedge into a defect: the ~0.20 mm figure is a
satin-rail **artifact** for one file population (refuted) and a genuine denser
pitch on 43 commissioned cap logos (still alive) — unresolved, not open-and-
known. It also pointed at Cross-cutting issues, which has never carried such an
item. Imported from the 2026-08-09 Ember teardown without re-checking it was
still live. *(corrected 2026-08-25 — area 1 "Fill row spacing (law 19)")*

**The stitch simulator already exists — do not build a second one.**
`lib/simulate.js` plus EmbroideryField's `simbar`: play/pause, a scrub slider,
speed cycling, close. `renderRealistic`'s `limitStrands` is its drawing
contract. This was nearly rebuilt from scratch on the assumption it was a gap.
*(confirmed 2026-08-25 — driven in a browser)*

**Thread lighting is unverified against real thread.** The light direction,
sheen ceiling and shadow weight are eye-tuned judgement calls. No sew-out has
happened, so there is nothing to compare a render against — treat the look as
a preference setting, not a calibrated one. *(suspected 2026-08-25)*
