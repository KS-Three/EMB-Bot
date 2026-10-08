# Area 3 — Studio app / configurator (file name keeps "wizard" for link stability)

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

**2026-10-01 — the theme pass (PR 4 of 4, PR #588).** Landed before PR 3 (progressive disclosure) by Kent's call 2026-10-01, so the panel is restyled but still long; PR 3 is the one remaining. Spec §6; plan `docs/superpowers/plans/2026-10-01-studio-configurator-pr4-theme.md`.
*Palette:* `--ink #171a20`, `--bg #ffffff` (the page is white like the panel; only `body` uses it now), `--border #e6e6e6`, NEW `--fill #f4f4f4` — the neutral ground for pills, segmented controls, hovers and read-only inputs (what `--bg` used to be for controls; on a white page a white hover is no hover). `--muted`, `--accent`, `--tint`, `--danger`, `--warn` and the dark stage's `--surround*` are unchanged *(built 2026-10-01 — `theme.css`)*.
*Type:* body and controls 13 px (`--fs-md`), small 12, caption 11, label 10, drawer/dialog heading 16, panel title 22. Two weights chrome-wide (400/500); 600 only on the summary bar's figures and the wordmark; base headings and `b`/`strong` are 500; `--fw-bold` deleted. Section headings (`.cfg-body h3, .sheet h3, .tp-label, .alignlabel`) are sentence case at body size, medium weight, full ink — no longer a 12 px uppercase muted eyebrow *(built 2026-10-01 — `theme.css`)*.
*Accent discipline:* plain hovers no longer use accent or tint — they are ink borders or `--fill` grounds; at rest accent/tint remain on the Download CTA, selection, links, focus, the in-flow hint banner, the font-licence badge, the quality grade, and the digitize/manual panels' control borders (`--tint-border`). Spec §6's "sheet slide" transition was not built (the sheet appears without one). Transitions are 150 ms, all behind `prefers-reduced-motion: no-preference`; shadows only on floating surfaces (drawer, sheet, menus, popovers, tooltips) — in-flow shadows removed from the zoom bar, simulator bar, slider thumbs, canvas and thread panel *(built 2026-10-01 — `theme.css`)*.
*Top bar:* 44 px, no bottom border, `EMB·BOT` wordmark replaces the tile + "Bot Studio"; Font credits is a round `?` button (accessible name still "Font credits"). At ≤ 820 px the `?` hides (credits stay reachable from the Download sheet's footer link); at ≤ 480 px the wordmark hides so the project name has room (31 → 145 px at 375 wide, measured) *(built 2026-10-01 — `theme.css`, `App.svelte`)*.
*Phone guard:* under 820 px `input, textarea, select` are 16 px `!important` — iOS Safari zooms the page into any focused field under 16 px, and the plain rule lost the cascade to every class-styled field *(built 2026-10-01 — `theme.css`)*.
*Contrast spec:* `e2e/theme-contrast.spec.js` (new) reads COMPUTED colours, walks to the first opaque ground, and holds every TEXT NODE in `.topbar`, `.panel` (empty and text-design states), `.gmenu`, `.sheet`, `.drawer` to WCAG AA (4.5:1; 3:1 large); disabled/inert exempt. It does not measure field values/placeholders, hover/focus states, the stage, the digitize/image/manual panels, tooltips or popovers. First run on the new theme: 0 failures across ~130 elements (top bar 4, panel 61–64, garment menu 10, sheet 35, drawer 20). Mutation-proved: `--muted: #9aa0a6` fails at 2.64:1 *(measured 2026-10-01 — `theme-contrast.spec.js`)*.
*Found by looking at screenshots, fixed:* the offline note collided with the text box; the sheet's save-location line was off-scale and the "Your machine" select was a bare native control; the drawer showed two headings in a row (`TemplateRow`'s own "Quick start" removed) and grey-flanked template thumbnails; the phone top bar squeezed the project name.
*Found by review, fixed:* a `var(--bg, #f6f7fb)` fallback form in `DigitizePanel` left the layer-list hover (and the canvas↔list cross-highlight) white on white; five plain hovers still sat on accent/tint.
*Known, not fixed (open):* at 375 px the zoom/view bar under the canvas is clipped at both ends; the Color select and Font card still carry 2 px borders; the machine select is narrower than the Chart select; the top bar meets the white panel with no separation (the spec's "no border").

---

**2026-09-30 — garment pill row and the Original view (PR 2 of 4, PR #586).**
*Garments:* the ten tiles are gone. `ui/GarmentPicker.svelte` shows pills `Polo` (left_chest), `Hat` (hat_front), `Tee` (full_back), a fourth pill for any other garment in force, and `More ›`, a `role="menu"` of all ten garments by the engine's labels with the `garmentArt` icons; the pure logic is `lib/garmentPills.js`, and `GarmentStep` still dispatches the same `update {garmentId}` *(built 2026-09-30 — `garmentPills.spec.js` 5, `GarmentPicker.spec.js` 6)*. e2e `pickGarment` (`e2e/helpers.js`) now goes through the More menu; 12 bare tile clicks in 10 specs were migrated *(measured 2026-09-30 — no-service group 29/29, sampled service-backed 5/5)*.
*Original view:* a fourth segment in the field's View group (Stitches · Realistic · Simulate · Original). It is painted ON the canvas: the render runs with zero strands (fabric + hoop) and the uploaded artwork is drawn. View-only (never saved, not in undo), dropped by any regeneration, disabled when no element has an uploaded original; pure maths in `lib/originalImage.js` *(built 2026-09-30 — `originalImage.spec.js`, smoke + field-chrome e2e 24/24)*.
*Registration, by lane:* **browser `image` lane** — the artwork's content box (the flat's non-transparent pixels, the ones actually stitched) is mapped onto the element's stitch rect; measured within 2 px of the stitches on the red-square fixture (stitches x426–461 y226–261; original x428–461 y228–261), pinned by an e2e registration assertion that fails (9 px) when the mapping is swapped for a plain frame fit *(measured 2026-09-30 — field e2e)*. **Service `digitized` lane — NOT registered, and this is the lane most customers use when the service is up:** the service returns only `px_per_mm` and the design size, not where the art sits inside its working image, so the whole image is fitted to the hoop's placement box, and the tip text does not claim "same spot and size". **Open:** the service would have to return the content box *(confirmed 2026-09-30 — code read)*.
*Two departures from spec §4, both approved by Kent with the plan:* no thumbnail chip over the stage (DOCTRINE: no chrome on the sewable field; `field-chrome.spec.js` pins `.hoop > *` at 1), so Original is a text segment under the canvas; and the artwork is placed on its own stitches (image lane) rather than fitted to the placement box.

---

**2026-09-30 — the four-step wizard became a configurator (PR 1 of 4, PR #585).**
*What changed:* one scrolling panel (`ui/Configurator.svelte`: "Your design" title, `Garment · Hoop` subtitle, an Add text | Upload file start control ("Upload logo" until 2026-10-05; it now opens the file browser directly), the Design section = `ContentStep`, the Garment section = the existing `GarmentStep` tiles/hoop/fabric) replaces the steps; a sticky `ui/SummaryBar.svelte` (size · stitches · colours, plus the one Download button, disabled with `title="Add text or a logo first"` until something sews); `ui/DownloadSheet.svelte`, a `role=dialog` over the panel holding the old recap `dl.summary`, `QualityReport` and `DownloadStep` unchanged. The panel moved to the right of the field; templates moved into the My designs drawer ("Start from a template"). Removed: `lib/flow.js` `STEPS`/`canAdvance`/`nextStep`/`prevStep` (`isSewable` stays), `lib/stepHistory.js`, `ui/StepNav.svelte`, the "create" review step, the topbar Download shortcut, the "What are you putting this on?"/"What are you making?" headings *(built and driven 2026-09-30 — `e2e/configurator-smoke.spec.js` 16/16; three step specs deleted, three component specs added — Configurator, DownloadSheet, SummaryBar — so 71 spec files before and after; unit suite measured 69/71 files green on a loaded machine, the two hook-timeout files (ManualPanel, TraceImportPanel — pre-existing 10 s `beforeAll` hooks, untouched here) pass alone 61/61)*.
*History:* the Download sheet is the ONLY history entry the Studio pushes — Escape, Close and browser Back close it, and a reload with it open is normalised on mount. The mechanism lives in `App.svelte` (`openSheet`/`closeSheet`/`onPopState`), not in `DownloadSheet.svelte` *(built 2026-09-30 — commit d3be1328; pinned by `configurator-smoke.spec.js` "the Download sheet's history entry")*. This supersedes the 2026-09-12 step-history rule.
*What stayed:* `EmbroideryField`, `DownloadStep`, and every export lane — no engine or service file moved *(confirmed 2026-09-30 — diff touches `app/` UI and docs only)*.
*What the e2e migration cost:* `wizard-smoke.spec.js` became `configurator-smoke.spec.js`, and the other 23 specs came off the Next-walk onto `e2e/helpers.js` (`startStudio`, `typeText`, `pickGarment`, `pickTemplate`, `openDownload`, `closeDownload`) *(migrated 2026-09-30 — Task 10 of the plan, `docs/superpowers/plans/2026-09-30-studio-configurator-pr1-structure.md`)*.
*Known, deliberate:* the "Nothing to stitch yet" screen is unreachable from the UI now (Download is disabled instead) and is unit-tested only; the bar's colour figure is distinct spools while `DownloadStep`'s thread list counts colour blocks, so the two can differ *(confirmed 2026-09-30 — code read)*.
*Next:* PRs 2–4 follow — garment pill row + Original chip, progressive disclosure, theme pass (spec `docs/superpowers/specs/2026-09-30-studio-configurator-design.md`). Everything below predates this and still says "wizard"/"step" — read it as history.

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

**The project lifecycle holds — driven end to end, not assumed (2026-09-07).**
The registry had never been exercised by hand, only read. Every step checked in
a real browser: a design survives a reload (caption identical either side);
switching between two projects keeps each one's text and stitch count; an
`.embproj` export → delete → re-import round-trips to the identical caption; a
garbage file is refused with *"That doesn't look like a design file
(.embproj)."*; the two-tap delete arms and confirms. Zero console errors
throughout. *(driven 2026-09-07 — `app/e2e/design-naming.spec.js` pins the
naming half; `storage-full.spec.js` the failure half)*

**Every design used to be called "Untitled design" — FIXED (2026-09-07).**
The drawer listed `Untitled design / today` twice for two designs, and both
exported as `untitled-design.embproj`, so a customer backing up three designs
got three files they could only tell apart by importing each one. A design now
takes its name from its content while it is still unnamed — the first non-blank
line of text, else the uploaded artwork's filename minus its extension, clipped
to 40 characters — and the guess follows the content in both directions,
falling back to the placeholder when the text is deleted. A name the customer
types is sticky and is never overwritten; clearing the field is how they ask
for the guess back. Projects saved before the flag existed are caught up on
open and at boot, which is the whole existing population.
*(`deriveProjectName` in `app/src/lib/project.js`, `isAutoNamed`/
`autoNameProject` in `app/src/lib/projects.js`)*

**Two storage-write failures that reported success — FIXED (2026-09-07).**
`renameProject` and `deleteProject` both ended `writeIndex(idx); return true;`,
and a name and a project's membership of the registry live ONLY in that index.
On a blocked store a rename repainted the topbar and the drawer and was gone at
the next reload with nothing said. `deleteProject` additionally removed the
project record BEFORE writing the index, so a failed write left an unopenable
row behind. Both now propagate, the delete writes the index first, and the App
routes the failure to the storage banner that already existed. `saveProject`
deliberately still reports success when only the index write fails — the design
itself is in its own record and did land. *(DOCTRINE "Where the index IS the
data, a swallowed write is a lie")*

**Undo/redo goes through the same write path as an edit (2026-09-07).**
`applyHistorySnapshot()` used to call `saveProject` directly, which meant undo
skipped everything else in `persist()`'s tail — the storage-failure banner, and
(from the same day) the auto-name. Undoing a text change left the design
reading HELLO with every name surface still reading GOODBYE. It now calls
`persist(false)`; the `false` skips the history record, which was the only
reason it had its own path. *(pinned by `app/e2e/design-naming.spec.js`)*

**The production bundle is verified, and now works below the domain root
(2026-09-07).** Every test here runs against `vite dev`; `npm run build` output
had never been driven. At the domain root it is sound — full lane, 1,356
stitches, zero failed requests, zero console errors, and the auto-naming above
survives minification. Served from `/studio/` it produced no stitches at all
(7x 404 on `/fonts/manifest.json`), because five hand-written asset paths were
absolute while `vite.config.js` sets `base: "./"` precisely so the bundle is
path-independent. All five are document-relative now; at the root the two forms
resolve identically, so nothing about today's deployment changes. Font licence
links — a compliance surface — were among the five and are verified 200 in both
deployments. `file://` cannot work at all (browsers block ES modules from a
`null` origin), so the only deployments in play are root and sub-path.
*(guard: `app/src/lib/assetPaths.spec.js`)*

**The printed worksheet, looked at for the first time (2026-09-07).** Three
tiers of test covered it and none had rendered a page. On a one-colour design
the thread row was drawn at y = 11.09 on an 11.00 in page — off the paper — and
page two was blank; the page break ran after each row instead of before it. The
render is now capped at 5.5 in so an ordinary design prints on ONE page, and
the break happens before a row is drawn, so a page is only added when there is a
row to put on it. The sheet also now states whether the design fits the hoop it
names: the Download step already refuses an oversize STITCH export until the
customer confirms, but the worksheet said nothing, and its picture shows the
design inside the GARMENT placement box, not the hoop — so a 305 mm design under
"Hoop: 8x8 in (200 mm x 200 mm)" looked like it fitted. Same sentence as the
screen, passed in rather than re-derived. *(guards: `pdfsheet.spec.js` sweeps
1-45 colours for off-page draws and blank pages; `worksheet-numbers.spec.js`
pins the hoop verdict end to end)*

**The lettering lane on a phone: sound, and the gap is narrower than
"desktop-only" suggests (2026-09-07).** Driven at iPhone 13 size (390 x 664),
by tap: no horizontal overflow on either step, the garment tiles and the text
field are usable, the design sews identically (1,336 stitches, 102 x 15 mm),
every one of the 38 visible controls carries an accessible name, and the
console is clean. The layout stacks properly — canvas, view toolbar, caption,
text field, step nav — with no cramping.

What a phone genuinely cannot reach is the DRAWING tools (Draw shapes, Trace
image), which live behind the canvas's right-click menu; the toolbar visible
under the canvas is view-only (zoom, fit, auto-snap, outline/jump/trim
toggles, realistic view, simulator). The empty-canvas hint already says
exactly that — "the drawing tools need a mouse" — and this drive confirms the
claim rather than contradicting it.

The artwork lane works there too: a logo uploaded at phone size digitizes to
2,187 stitches, 80 x 17 mm, 2 colours, with no overflow and a clean console.

One caution recorded because it cost a detour: a probe that reads
`aria-label || innerText` off a control is NOT reading its accessible name, and
it reported the digitize panel's file input as unnamed on both phone and
desktop. The real accessibility tree calls it `button "Replace artwork…"` — the
input is wrapped in a `<label>` and hidden with CSS, which is the intended
pattern, and `unnamedControls()` in `wizard-smoke.spec.js` (which reads
`ariaSnapshot()`) had it right all along: zero unnamed controls, before and
after digitizing, at both sizes. The app was correct; the probe was not.

So PRODUCT.md's "Desktop-only, stated on the site" (still stated nowhere)
covers a narrower gap than it sounds: lettering and artwork work on a phone,
two launch-scope tools do not, and the app already says so at the point it
matters. Kent's call what, if anything, the site should say.

## The phone measurement above was taken with the service UP (2026-09-08)

Re-driven that day with the digitizer deliberately unreachable, which is not a
scenario — it is **every real phone**. `DEFAULT_DIGITIZER_URL` is
`http://127.0.0.1:8721` and `digitizer.js` says the localStorage override is
"never a way to leave the machine", so on a phone that loopback is the phone's
own, and nothing is listening on it.

The conclusion above survives — **artwork does work on a phone** — but by a
different route than the numbers suggest, and the numbers change with it:

| | lane | measured |
|---|---|---|
| service reachable (the run above) | auto-digitize | 2,187 stitches · 80 × 17 mm · 2 colours |
| service unreachable (a real phone) | browser flatten-and-sew | **3,011 stitches · 90 × 18 mm** |

Same fixture, same 390×844 viewport with touch. `ContentStep`'s own comment has
this right — the tile stopped disappearing when the service is down because
"Artwork still works, it just falls back to the browser engine's own
flatten-and-sew lane" — and the note it shows is honest: *"Artwork will be
placed but not auto-digitized."* This entry exists because the earlier
measurement, taken on a desktop at phone SIZE, reads as though the phone gets
the auto-digitizer. **A phone-sized viewport on a machine running the service
is not a phone**, and only the unreachable-service run separates them.

Two things fell out of that run, one fixed and one recorded:

- **Fixed here:** the `Colors` count was the slider, not the sewn count, on
  **two** screens — the review card (`Colors 4` beside `Thread changes 1`) and
  the content step's element chip (`Image · 4 colors` above a two-swatch
  strip). Both are browser-flatten-lane surfaces, so the phone is where they
  always show. The chip half surfaced only when the production bundle was
  re-driven to confirm the first fix — worth remembering, because the obvious
  move after a fix verifies the screen the report named and stops.
  MASTER_SCOPE defect 42(e).
- **Recorded, not fixed, Kent's call because it is wording on a lane that
  works:** the offline note's remedy is *"Start it, then check again"*, and
  `DigitizePanel` adds *"Start it: `python -m digitizer_service` in the
  digitizer folder."* Neither is followable on a phone. This is the same shape
  as the `emptyFieldHint` defect already fixed for this device class — advice
  naming something the device cannot do — but milder: there the customer was
  sent to a gesture with no alternative, whereas here the lane completes anyway
  and the note is about quality, not access. Worth a sentence that varies on
  `(any-pointer: fine)` the way `emptyFieldHint` already does; not worth
  inventing a phone story PRODUCT.md has not decided on (launch posture is
  still "Desktop-only, stated on the site", still stated nowhere).

## Moved from MASTER_SCOPE (2026-09-18) — the "Make it bigger" chips

Lifted verbatim from the area-3 summary on 2026-09-18 to bring `MASTER_SCOPE.md` back under its 27,000-word budget (the offload mechanism it documents); the summary keeps the one-line claim and the dated pointer. Snapshot as of 2026-09-06, not re-verified since.

**Both "Make it bigger" chips offer a PARTIAL remedy, and the comment justifying them misquoted the finding it cited** — it read `LETTERING_TOO_SMALL`'s message as ending *"Enlarging helps"* when on that same commit it already ended *"...but does not fully clear it ... Remove or simplify the smallest lettering"*. Corrected in place with the history; the buttons are LEFT for Kent, since whether a partial remedy earns one is his call. `STITCHES_TOO_SHORT` no longer recommends enlarging at all and now names the shapes carrying the short steps — it and `LETTERING_TOO_SMALL` measure the same quantity at the same threshold (`MIN_COLUMN_MM` **is** `machine.MIN_STITCH_MM`) and it never fired alone over the corpus at 80 mm (the only width swept), but only **66%** of its short steps sit in a shape lettering named: the rest are sewable columns (1.1–3.2 mm median) with a narrow waist. **And the button itself is now measured: ONE PRESS CLEARS THE FINDING ON 1 OF 10** corpus fixtures (two presses on 4 of 10) and makes it **worse on 3** — `photo_dof_meadow` 0.36 → 0.58 → 0.71 — while the satin shape count rises on every fixture (2 → 9, 42 → 71), which is "the smallest shapes regenerate at any size" from the other side. No grade claim is drawn from that sweep: several checks move with size and 5 of the 10 are on the clamped floor. *(measured 2026-09-06 — `tools/short_satin_overlap.py`, `tools/enlarge_cure.py`, `tests/test_short_satin_shapes.py` (14); DOCTRINE)*

**A third size chip, and this one jumps (2026-09-30, Kent's pick).** Preflight's
`SATIN_GAPS_TIGHT` (a satin shape whose own gaps are narrower than the fabric's
pull compensation plus the thread) names the design width at which its
headline shape's tightest tenth of gap clears — arithmetic on that polygon —
so its "Make it bigger" sets `target_width_mm` to that width (capped at
400 mm) instead of stepping 25%. `offeredFixes` now keeps ONE button per
parameter and lets the larger target win, so the jump and a 25% step from
`LETTERING_TOO_SMALL` on the same run never show twice; a payload with no
named width takes the 25% step. The finding's own words are on the tooltip.
The finding is `info` since 2026-10-05 (Kent's call, issue #630) — the chip
keys on the code, not the severity, so it still offers the jump; only the
12-point deduction is gone.
What the jump promises is exactly what the finding does: that shape clears;
the design can segment new small shapes at the larger size (bridge at
140 mm cleared its script and fired on nothing with the 6 mm floor). Spec:
`DigitizePanel.spec.js` (the named width, the one-button rule both orders,
the 400 cap, the fallback). *(2026-09-30)*

## Moved from MASTER_SCOPE (2026-09-20) — three fixed Studio entries

Lifted verbatim from the area-3 summary on 2026-09-20 to buy budget space for
the machine-physics backlog pointer (see
[`machine-physics-backlog.md`](machine-physics-backlog.md)); the summary keeps
the one-line claim and the dated pointer, as the 2026-09-18 and 2026-09-19
moves above did. All three are FIXED entries — the verdict is current, the
mechanism detail below is what no longer needed to sit in the dashboard.

**Typographic punctuation folds to its ASCII twin where a font lacks it.**
`satinfont.js TYPOGRAPHIC_FOLD` stitches the twin ONLY where the fancy form is
missing — 367 font x character combinations rescued, and all 85 fonts hash
identically on text that never needed it. Not NFKD: accented letters are
different letters and stay unfolded. What it cost before the fix (a phone's
U+2019 sewing "Fritschs Stitches", under a note naming a character that looks
identical to the one typed): DOCTRINE; scope-history 09-07. *(fixed
2026-09-07)*

**Lettering under the cap floor now names a way out.** The "cannot be sewn"
verdict was the only one with no fix while the milder branch named two. Levers
were measured before being named, so line breaks lead and "fewer characters"
is second; "Size up" is withheld at the width cap, the rule the hairline
branch already followed. The measured ladder (74 chars at default left chest =
1.3 mm against a 4 mm floor, and what each lever buys): scope-history 09-07.
*(fixed 2026-09-07)*

**A design is named after what is in it, and the registry stops swallowing
failed writes.** Every project was "Untitled design", so "My designs" listed
rows a customer could only tell apart by opening each, and every backup
downloaded as `untitled-design.embproj`. A still-unnamed design now takes its
name from its content; a name typed by hand is sticky. Separately,
`renameProject` and `deleteProject` reported success for an index write that
never landed — a name and a project's membership of the registry live ONLY in
that index — and `deleteProject` removed the record before writing it. Both
propagate now, index first. *(fixed 2026-09-07 — area 3; DOCTRINE)*

**"My designs" filters by what a design is.** Each index entry carries `facts`
(`{st, col, w, h}`: needle-down stitches, spools, size in mm —
`lib/libraryFacts.js`), and the drawer filters on name text plus three upper
bounds: stitches, colors, and "fits hoop" (rotation allowed, derived from w/h
against `EMB.HOOPS` on read, so it is not stored). Things worth knowing before
touching it:

- **Facts are recorded reactively in `App.svelte`, not in `persist()`.**
  `persist()` runs before the flush that regenerates `combinedDesign`, and a
  text or uploaded-image design cannot be generated from its record alone
  (font fetch, PNG decode). The same reactive write is the backfill: an entry
  saved before facts existed is measured the first time it is opened. There is
  no migration pass.
- **A missing `facts` means "not measured", never zero.** Under a
  stitch/color/hoop filter those entries are left out and counted in a line
  below the list. A blank design is also unmeasured.
- **`setProjectFacts` keeps the registry's invariants**: no-op for an id not
  in the index (a late measurement cannot resurrect a deleted project), never
  bumps `updatedAt` (measuring on open must not reorder the drawer), no write
  when unchanged (the trigger fires per drag frame).
- **A null design clears facts only when nothing in the project could sew** —
  otherwise it is a design still loading, and a good measurement stays.
- **Not built:** content search ("dogs" — needs tagging or image
  understanding), exact-colour match (the bound is "up to"), an e2e spec.
- **The drawer lists saved designs first, templates after** (Kent, 2026-10-01).
  With the template cards on top the filter sat ~700 px down the list.
- **The filter applies only while its controls are on screen.** They show with
  two or more saved designs, and the drawer's `criteria` outlives them, so
  deleting down to one used to leave that design hidden behind a filter with
  nothing to clear it. *(fixed 2026-10-01 — `ProjectsDrawer.spec.js`)*

*(built and driven in a browser 2026-10-01: three seeded pre-facts designs
measured on open, row figures matched the canvas caption, `updatedAt`
unchanged)*
## Moved from MASTER_SCOPE (2026-09-19) — the two engines' wire tests

Lifted verbatim from the area-3 summary on 2026-09-19 to bring
`MASTER_SCOPE.md` back under its 27,000-word budget, the same way the "Make it
bigger" chips moved on 2026-09-18. `MASTER_SCOPE.md` keeps a one-line pointer;
this is the full entry.

**The two engines' fabric tables agree, and `test_fabric_wire.py` keeps them so**
— field-for-field, asserting AGREEMENT only; the numbers stay gate 1. Its sibling
`test_machine_wire.py` does the same for the 21 shared individual constants
(2026-09-14). What law 26's month of silent browser drift cost: DOCTRINE.
*(2026-09-07; 2026-09-14)*
## The `.embproj` carries the original artwork (2026-09-20)

Since 2026-09-20 a digitize sends the customer's FILE, not the panel's
1,200-px preview (DOCTRINE 2026-09-19/20), and the file's bytes live in
IndexedDB under their SHA-256 (`lib/sourceStore.js`). IndexedDB is this
browser's, so a design opened on another machine, or after cleared site data,
had only the preview and re-digitized from it with the panel's note. Kent's
pick the same day: the `.embproj` now carries every stored original its
elements point at — `sources` in the envelope, base64 under the same key,
BESIDE the project and never inside it, so the registry record in
localStorage stays preview-sized (`lib/projectFile.js`). Import puts them back
in the store before the project is registered, under the key the bytes hash
to here (`lib/projectSources.js`). Driven end to end in
`app/e2e/design-originals.spec.js`: export byte for byte, wipe both stores,
import, and a re-digitize whose `/digitize` POST carries the file under its
own name. A file saved before that day carries no originals; a preview-path
upload (SVG, GIF, oversize, a rotated JPEG) has none to carry. *(built and
verified 2026-09-20 — scope-history, the originals addendum)*

## Moved from MASTER_SCOPE (2026-09-20) — the built bundle's asset paths

Lifted verbatim from the area-3 summary to buy MASTER_SCOPE.md headroom: on
2026-09-20 both `main` and this lane sat at exactly 27,000 of 27,000 words, so
any lane adding a line overflowed the merge even when each side was legal on
its own. `MASTER_SCOPE.md` keeps a one-line pointer; this is the full entry.

**The built bundle works wherever it is served.** `vite.config.js` sets
`base: "./"` and five hand-written `/fonts/…` paths ignored it, so below the
domain root the lettering lane produced nothing; font LICENCE links were among
the five. Document-relative now, identical at the root. *(fixed 2026-09-07 —
`assetPaths.spec.js`)*

## Moved from MASTER_SCOPE (2026-09-20) — typographic punctuation folding

Lifted verbatim from the area-3 summary to buy MASTER_SCOPE.md headroom for
the operator-sheet entry. `MASTER_SCOPE.md` keeps a one-line pointer; this is
the full entry.

**Typographic punctuation folds to its ASCII twin where a font lacks it.**
`satinfont.js TYPOGRAPHIC_FOLD` stitches the twin ONLY where the fancy form is
missing — 367 font x character combinations rescued, and all 85 fonts hash
identically on text that never needed it. Not NFKD: accented letters are
different letters and stay unfolded. What it cost before the fix (a phone's
U+2019 sewing "Fritschs Stitches", under a note naming a character that looks
identical to the one typed): DOCTRINE; scope-history 09-07.
*(fixed 2026-09-07)*

## The surround, the flat panel, and the scale bar (2026-09-30)

Kent's brief, in his words: the Studio "feels a little un-professional",
the main preview is "hard to navigate", and he wants it to "look professional
like SpaceX or a Tesla website". Reviewed by driving both lanes at 1440×900
and reading `theme.css` against the screenshots; the review's full finding
list (tooltips, panel↔canvas selection sync, the toolbar, the Download step,
the panel split) is in the session and this entry records only what SHIPPED,
which is the first of those PRs. Two things were found NOT to be wrong on the
way: Inter IS loaded (`main.js` imports `@fontsource-variable/inter`;
`document.fonts.check` → true), and the token system is real. What made it
read as a template was elevation and grounds, not type.

**The canvas outside the hoop is a dark neutral surround.** `--surround`
(#22252c) with four on-surround text tokens, contrast measured in the token
comment (ink 12.75, muted 6.51, warn 8.35, danger 7.65). `renderRealistic`
takes `surround` and, with a hoop, fills the canvas with it and clips the
fabric and weave to the hoop's rounded rect (`hoopRectPx`, the one place the
ring's rectangle and radius are computed, so the fill's edge and the stroke
agree to the pixel). Without the option, or without a hoop, the path is
byte-for-byte what it was — thumbnails and PNG export never see it
(`preview.spec.js`, four new). The panel stays LIGHT on purpose: workbench
beside a viewport, not a page-wide dark mode. **What this cost:**
`e2e/field-chrome.spec.js`'s HiDPI ink test counted any dark pixel as
thread, which on a dark surround is the whole canvas; it now finds the fabric
first (the bounding box of the pale pixels, pulled in 3% a side for the
corners) and counts ink inside that. Its target — an unscaled context, which
paints everything in the top-left quadrant — still reads ~0.25 because the
fabric moves with the ink. Dry-run on the live canvas before the suite:
centre 0.501 / 0.499, ink bbox the text and not the hoop.

**The garment step is flat.** Radii 8/12/18 → 4/6/10; the 2px borders on
tiles, cards, rows, the font trigger and the topbar buttons are 1px; the
elevation-pass shadows on `.tile`, `.tcard`, `.hooptile`, `.elrow`,
`.fs-trigger`, `.drawer-row` and the topbar are gone, and so is the hover
lift. Selection is the accent border plus `--ring-inset` (2px of accent, no
layout change). The four hoops are one segmented strip, the picked segment
ink-filled; the fabric swatches are round with an inset hairline so White
still has an edge. Same DOM, same class names, so `GarmentStep.spec.js` and
every e2e locator are untouched. *(This supersedes the 2026-08-25 audit line
above that elevation "is applied consistently across two tokens" — cards no
longer carry it; popovers, menus and the drawer still do.)*

**A scale bar in the zoom bar.** `lib/scalebar.js` picks the longest round
length (1 … 200 mm) that fits 120 px at the render's px-per-mm, which already
has the view's zoom in it, so it follows wheel and button zoom for free. HTML
in the zoom bar, not paint on the canvas: it never covers sewable field
(DOCTRINE; `field-chrome.spec.js` pins that no chrome lands on the canvas),
it does not disturb the pixel counts three specs read off the bitmap, and it
needs no dpr of its own. `scalebar.spec.js`, five.

Two defects of the change itself, both seen in the screenshots and fixed
before the PR: the drag-field hint bubble inherited `.field`'s light
on-surround ink and its copy went near-invisible on the tint (colour now
stated on `.hintbubble`); the custom fabric `<input type=color>` stayed square
beside eight round swatches (its `::-webkit-color-swatch` is rounded; Firefox
keeps a square, not a broken control).

*(built and looked at 2026-09-30 — both lanes driven at 1440×900, the logo
lane against the live service; Studio unit suite 1,322 passed; e2e suite run
in full before the push)*

## The Layers list and the canvas point at the same shape (2026-09-30)

Second PR of the design review. The finding: `EmbroideryField`'s
`selectedShapeId` was set from a canvas hit only — its own comment said so —
so a row in the 31-row Edit shapes list had no way to say which outline it
was, and a shape on the canvas no way to say which row. "Hard to navigate
what a digitized image is up" was mostly this.

**One state, owned by App.** `hoverShape` and `selectedShape`, each
`{ elId, shapeId }` or null. The panel's rows send `shapehover` on
mouseenter/leave and the sewing rows' name (now a button, "Show #0134 on the
canvas") sends `shapeselect`; the field sends the same two from its pointer
(outline hit OR interior hit — the right-click menu's two tests) and from
every path that changes its selection (`setSelectedShape`: click, right-click,
Delete, the clear on element change). Each side draws the other's: the field
outlines the hovered shape in white whether or not the outlines toggle is on
(the signpost the toggle's comment said was lost), applies a row click as its
own amber selection (`applyFocusShape`, so Delete and a boundary drag act on
it); the panel takes a hover ground on the hovered row and the tint plus an
accent edge on the selected one, and a canvas selection opens the closed list
and scrolls its row into view (`revealRow`, `block: "nearest"`). Hidden and
deleted rows keep a plain name: they have no outline to show, and a Delete
armed on one would be a surprise. The panel only ever sees ids for the element
it is showing (App narrows by `elId`), and nothing echoes: `setSelectedShape`
is silent when unchanged, `applyFocusShape` never dispatches.

*(built and looked at 2026-09-30 — `e2e/field-panel-sync.spec.js`, 3, against
the live service, each reading the outline colour off the canvas; the panel's
half in `DigitizePanel.spec.js`, 3; Studio unit 1,325, e2e full suite run
before the push)*

## Every setting explains itself on hover (2026-09-30)

Third PR of the design review, and Kent's own idea from it: "when you hover
over a setting or feature, it provides a brief description that pops up with
what it does and how it changes the digitizing." The state before: 31
native `title=` attributes in DigitizePanel, ONE of them on a design setting
(Even out lettering widths); a browser tooltip waits about a second, cannot
be styled, never shows for keyboard users and does not exist on touch.

**The copy is data, in one file.** `lib/settingHelp.js` — 24 entries, each
the same three sentences in the same order: *what* it is in embroidery terms,
what *changes* in the stitch-out, *when* to touch it (and when to leave it).
Kent edits wording there without touching a component; `settingHelp.spec.js`
holds every entry to the shape (three non-empty sentences, none over 320
characters, the three under 700, each ending as a sentence). Covered: the 8
design settings (Design width, Colors, Satin for thin shapes, Even out
lettering widths, Fill angle, Border, Design edge, the artwork-reading row),
the 6 per-shape controls (Stitch type, Fill angle, Underlay, Border, Stitch
width, whole word), the 7 canvas toolbar buttons, and the Text step's three
sliders.

**The popover is one Svelte action.** `use:tip={"fillAngle"}` (`lib/tip.js`)
on a label, select, input or button: pointerenter shows after 150 ms (a
pass-over does not flash), focusin shows at once, pointerleave / focusout /
Escape hide, touchstart toggles. One `role="tooltip"` element for the whole
app, appended to `<body>` so no scrolling panel clips it, positioned under
the host and flipped above when there is no room, kept inside the viewport;
the host carries `aria-describedby` while it is open, so a screen reader
hears the same three sentences. Built with textContent, never innerHTML.
`tip.spec.js`, six. A "?" ring beside each label is generated content on an
empty aria-hidden element, so every label's accessible name — and every e2e
locator that reads one — is unchanged.

*(built and looked at 2026-09-30 — a hovered setting and a focused toolbar
button screenshotted against the live service; Studio unit 1,336; e2e full
suite before the push)*

## Settings / Shapes / Threads (2026-09-30)

The last item of the design review. The digitize panel's result section had
grown to a 1,738px single column at 1440×900 — settings, the run's
sentences, the warnings, four layer accordions, the spool list, rotation —
and the customer's question ("what do I change?") sat under the expert's
list. Three tabs once there is a result, with the stats line, "Since last run"
and the run's warnings above them as the part every tab shares: **Settings**
(the fixes, notes, re-digitize-at-size, rotation), **Shapes** (the enclosed
banner and the whole Layers block with its editors), **Threads** (the spool
list). A shape picked on the canvas switches to Shapes before scrolling to
its row (`revealRow`). Counts on the tabs are aria-hidden so the names stay
the plain words every locator uses. The eight e2e helpers that open the
shape list click the tab first; the unit spec's `openLayers` does the same.

**"Thread per color" lists spools, not sew blocks.** The design edge re-loads
a cone, so a two-spool logo sews three blocks and the list read "1720 Not
Quite Red" twice — the same defect MASTER_SCOPE 42(e)'s rule caught twice
already on the summary and the review's shopping list, now on the third
display. Grouped by the cone's name and colour ("loaded 2 times"); a pick
recolours every block of that spool, since on the machine they are one.
`DigitizePanel.spec.js` +4.

*(built and looked at 2026-09-30 — the three tabs screenshotted on the logo
lane against the live service; Studio unit 1,377; e2e full suite before the
push)*


## Moved from MASTER_SCOPE (2026-09-30) — two Studio entries

Lifted verbatim from the area-3 summary to buy MASTER_SCOPE.md headroom for the 2026-09-30 design-review entry: the file stood at 27,273 words against its 27,000 budget with all four review parts written in. `MASTER_SCOPE.md` keeps a one-line pointer for each; these are the full entries.
## Moved from MASTER_SCOPE (2026-09-30) — five Studio entries, verbatim

The 27,000-word budget tripped on 2026-09-30 (27,070 after two lanes landed in one evening) and its own failure message named this area as the reclaim: 80 lines in the dashboard against 638 here. Each paragraph below is the full text that used to sit under the verdict; MASTER_SCOPE keeps a one-line verdict with a pointer for each. Nothing is deleted.

### Uploading artwork is the whole interaction

**Uploading artwork is the whole interaction — the panel asks NOTHING about
what the art is.** The run starts on upload and the panel STATES what the art
was read as ("Read as flat art" / "as a photo" / "as shaded artwork" /
"couldn't tell" / "A face was found, so it's sewing as flat art"). **The
per-design override is GONE (Kent's call 2026-09-30):** the "It's flat art" /
"It's a photo" / "Use automatic detection" buttons that had sat on that row
since 2026-08-30 are removed, the Studio no longer sends `forced_class` or
`is_photographic` at all, and a project saved with either digitizes as a fresh
upload would. In their place the Studio sends `detect_photographic=true` on
every job, so the engine's own EXIF-or-face detection (area 1, built
2026-09-11, engine default still OFF) answers "is this a photograph" — **and a
found face routes the design FLAT (`faces_route_flat`, Kent's ruling later
that day from two stand-in portraits rendered down both lanes; DOCTRINE
2026-09-30 "A face sews FLAT")**. `detail_layer` still sits on the row and
appears only where the art is photographic or shaded by the engine's reading
(`PHOTO_DETECTED` and `FACE_ROUTED_FLAT` count). **The cost is real and
named:** stage 0 still misroutes most real logos (ROADMAP phase 2), and a
misrouted design now has no in-product correction — the routing is the fix,
not a button; a detection false positive (camera EXIF on a scanned flat logo)
is likewise unmitigated in the product. Before 2026-09-30 this entry read
"with the override recast as a one-click correction to that sentence" and
"phase-4 v1 works around it with exactly this override"; both are history.
*(confirmed 2026-09-30 — `digitizer.spec.js` legacy-override tests, `DigitizePanel.spec.js` reading-row block, e2e `digitize-auto-start.spec.js` reads the POSTed config; the 08-30 browser drive and its numbers in scope-history 08-30)*

### The hoop you picked is drawn, and the export gate uses it

**The hoop you picked is DRAWN, and the export gate uses it.** `hoopTransform`
returns the hoop and the placement box and fits to the larger (before 2026-09-04
`preview.js` had only the placement box and called it the hoop, so picking one
changed nothing on screen); `DownloadStep` warns before a stitch export that will not fit (confirm,
not block; PNG and PDF worksheet ungated — not machine files). **Live: the stock
Tote / Full Back preset is 203.2 mm against a 200 mm max hoop**, so it fires on a
shipped preset — whether auto-fit should CAP is open, and it is now measured: **four of ten garments (full_back, jacket_back, blanket, tote) have placement boxes larger than the 200 mm biggest hoop**, so 40% of the picker is oversize on every design (defect 39). *(2026-09-02 — PR #317;
`preview.spec.js`, `DownloadStep.spec.js`, e2e)* **What that gate is fed changed 2026-09-07**: it used the box the design was fit to, which 65.6% of designs sew outside of (defect 34), so it now reads the thread's own extent.

### The digitize panel states what changed and offers the fix

**The digitize panel states what CHANGED and offers the fix.** Shape list behind
an "Edit shapes (N)" disclosure, closed by default; a re-digitize reads as a
delta against `priorRun`; `COLOR_STOPS_HEAVY`, `LETTERING_TOO_SMALL` and
`STITCHES_TOO_SHORT` render as one-click adjustment chips offered AFTER the run
(Kent's call — an adjustment, not a pre-run form). `QualityReport` surfaces
trims. *(2026-09-02 — PRs #317/#318)* **Both "Make it bigger" chips offer a PARTIAL remedy** — one press clears the finding on 1 of 10 corpus fixtures, two presses on 4, and it worsens 3; the buttons are LEFT for Kent. The measurement, the misquoted comment it corrected and `STITCHES_TOO_SHORT`'s 66% moved to the area file, "Moved from MASTER_SCOPE (2026-09-18)". *(measured 2026-09-06 — `tools/enlarge_cure.py`, `tests/test_short_satin_shapes.py`)*

### `cfg.border` reaches its own default

**`cfg.border` reaches its own default now** — `null` = unset, key omitted when
unset, panel says "automatic", `fill_angle_deg`'s sentinel shape. Until
2026-09-02 the Studio seeded `"off"` and always sent it, so the service-side
default was unreachable. *(PR #318)*

### Preview thread width is physical

**Preview thread width is PHYSICAL — neither widened nor narrowed.**
`preview.js`'s `THREAD_WIDTH_MM` (0.4, nominal 40wt) is coverage 2.67 against the
ruled 0.15 mm fill row (rows overlap, as the professional's do) and 1.0 against
the 0.4 mm satin spacing; a fill at the ruled row looks solid because it IS. The
PDF sheet (`src/render.js`) and the SVG export draw the same width since
2026-09-04 — the sheet had drawn 1 px hairlines at any scale. Caveat: `lw` has a
1.2 px floor (1 px on the sheet), so the property holds zoomed in, not on a
thumbnail. Pinned on the literal 0.4 and both ratios. *(2026-09-04 — `preview.spec.js`)*

### Thread lighting is unverified against real thread

**Thread lighting is unverified against real thread** — eye-tuned, and the one physical out (2026-09-01) cannot settle it: its colours were random operator threading, so DOCTRINE bars grading colour from it at all. Treat the look as a preference, not a calibration. *(suspected 2026-08-25; sharpened 2026-09-14)*


### A corner drag on a digitized design is a Design width change (2026-10-08)

**The defect, measured in the running Studio on `logo_golden_tee.jpg`:** the
field's corner handles SCALE a digitized design's baked stitches
(`generate.js` hands `sizeMm` to `buildImportedDesign`, the `.dst` import
path). Dragged 80 → 62 mm, the caption read **8,764 stitches · 62×52 mm** —
every stitch of the 80 mm run on 0.6× the area, **1.66× the thread per mm²**,
which is what makes a patch stiff and breaks needles. The Auto Digitize button
stayed solid, Design width still read 80, and the one sentence about it
("Resized to 77% …") sat in the Settings tab below the fold at 1440×960. Its
button, **"Re-digitize at 62 mm", put the design back at 80 mm and ran
nothing**: it cleared `sizeMm`, set the width, and waited for the automatic
re-run that Kent's 2026-10-05 ruling ("nothing re-runs on its own") had
removed, so its own comment had been false for three days.

**The fix (Kent's two rules kept: resize honesty, and the button as the only
run):** `resizedTargetWidth` (`lib/digitizer.js`) reads a drag beyond the
panel's existing 2% threshold as the Design width it asks for (the ratio
applied to the width the result was DIGITIZED at, so pull-comp margin does
not compound). The panel compares THAT config against the applied one, so the
button goes transparent, the stale line says "Resized to 62 mm — the stitches
are only scaled until you press Auto Digitize Image", and Design width shows
61.9. A run sends the dragged width and its landing patch drops the scale in
the same step: **6,246 stitches · 62×52 mm**, button solid. "Re-digitize at
N mm" is now that same run. A typed width replaces a dragged one.
Renders: `docs/renders/field-resize-2026-10-08/`.
*(fixed 2026-10-08 — `DigitizePanel.spec.js` "a resize on the field" (4 of 5
fail on the old panel), `digitizer.spec.js` "resizedTargetWidth")*
