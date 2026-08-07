# Ember Design competitive research (2026-08-07)

Three research passes against `emberdesign.net`, a browser-based embroidery
digitizing competitor, run the same day as the SEEDS boundary-contrast fix.
Outcome and prioritization decisions live in `MASTER_SCOPE.md`'s
cross-cutting section; this doc is the evidence trail behind them.

**Method note, stated plainly:** none of this required bypassing
authentication or accessing anything non-public. Pass 1 was a screenshot of
Kent's own session. Passes 2 and 3 read client-side JavaScript that Ember's
own servers already send to any visitor's browser during ordinary use of the
public product — the same thing "View Source" or browser devtools do, not a
security bypass. Nothing behind Ember's login was accessed by this session
directly (this session's own outbound network is policy-blocked from
reaching `emberdesign.net` at all — passes 2 and 3 were run by the user's own
local tooling and reported back).

---

## Pass 1 — screenshot walkthrough (Space Cat project)

A single screenshot of an in-progress design ("Space Cat," an astronaut-cat
patch) showing the editor's right-rail layers panel and canvas.

Observed, UI/UX only:
- Per-shape stitch-type label directly in the layers list ("Tatami",
  "Satin", "Satin blocks") under each shape name — not buried in a settings
  panel.
- Live-rendered per-shape thumbnails (actual stitch texture, not a generic
  icon).
- A "Clone" button alongside Export, suggesting a duplicate/remix workflow.
- Directional, fur-like fill on the cat's face — appears to follow a
  growth-direction field rather than one flat angle.
- Graduated satin-block shading within one object (the helmet), suggesting
  pseudo-3D shading via multiple tone-blocks.
- A play control implying animated stitch-order preview on canvas.
- Tabbed icon side-panel (layers/shapes/image/colors/settings/info) rather
  than one long scrolling panel.

## Pass 2 — Chrome-extension end-to-end exploration

The user's own browser tooling drove the live editor directly: the Space Cat
project, a fresh blank project, account/library pages, the marketing site,
and the manual. Canvas is loaded from a separate origin
(`v2.emberdesign.net/editor/{userId}/{projectId}`) in a full-viewport
iframe under the `emberdesign.net/editor-v2/...` shell — the outer document
exposes almost no DOM, so any inspection has to go through the iframe.

**Editor layout.** Canvas center, infinite grid, zoom + undo/redo
bottom-left. Top-left: project chip + app menu (Export file, Export image,
units toggle, New Project, My projects, Explore, Discord, Sign out).
Top-right: Export + Clone (existing/others' designs) or Export + Share (new
designs). Selection shows a dimensions bar (H/W in inches, aspect-lock,
flip) plus a floating toolbar (Edit shape: Reshape/Knife/Start-end, lock,
delete). Bottom toolbar: Select (S), Pan (space), Measure (M), open shape
(1), closed shape (2), Satin blocks (3), Pen (4), Text (T), a "Draw shape"
flyout (circle/rectangle/star/triangle/diamond/hexagon/heart), stitch
player, realistic-view toggle. Drawing tools show a contextual instruction
banner at canvas-top (e.g. circle: "click to set the center, click again to
set the radius") — flagged during the walkthrough as the single nicest UX
detail in the product.

**Right rail, six panels:** shape list (thumbnail, name, stitch-type label,
color chip, sew-order number, drag handle, per-shape gear opening a
draggable Properties popover with trim-after/tie-on/tie-off + 4 reorder
buttons); **Sequencer: Colors** (collapses N shapes into color blocks —
thread name, brand code, shape count, and the stitch-index range each block
covers, e.g. "1-2, 3, 4-6, 7-18" — described as exactly the view needed
before loading a machine); Sequencer: Images; Colors (15,809 threads, 78
brands, search, brand tabs, eyedropper); Visibility (units, grid, rulers,
overlays for jumps/trims/tie-ons/needle points); Project Info (on Space Cat:
3.72 x 3.72in, 121 shapes, 11 color changes, 6 total colors, 24,013
stitches).

**Stitch model.** Every shape is Outlined or Filled. Filled exposes a Fill
Pattern gallery (Tatami/Original/Triangle/Waves/Columns/Offset Columns
free; hearts/diamonds/zig-zag/circles/etc. Pro-gated) + Fill Settings
(stitch angle, row space, stitch length, Hand Stitch slider, Underpath, a
gated Gradient). Outlined exposes 7 run types (3 free, 4 Pro) + Run
Settings. Underlay is a repeatable list (center/contour/zigzag, each with
its own length, "+ Add Underlay") rather than one setting. Per-shape
Properties: name, hex color, visibility, transparency, Advanced
(tie-on/tie-off/trim-after/speed flag). The manual documents deeper satin
controls (split satin max width, stagger cycles/amount, contour/cap inset)
than were observed on inspected shapes — presumably gated behind specific
run types not exercised.

**Export dialog:** restates stitches/shapes/color-changes/dimensions,
filename field, searchable format chip (`.pes .dst .exp .jef .vp3 .u01
.pec .xxx .tbf .gcode`), and an origin-point 3x3 grid ("Sets this point as
(0, 0) in the exported file"). Not downloaded; Share/Clone not exercised
(both change what's public or create records).

**Live workflow exercised:** drew a 4-point closed shape (Enter to
complete), flipped Outlined -> Filled (instant Tatami regen), changed
stitch angle 135 -> 45 (instant re-stitch), inserted "Ember" as satin
lettering via Text, drew a heart from the primitives flyout, toggled
realistic view, undid back to empty. Stitch player: scrubbable timeline,
color-change markers, cycling speed multiplier, pause/close, a red needle
crosshair tracking the current stitch — real interaction depth, not a
static preview.

**Bugs / friction found, worth avoiding, not adopting:**
- Both explored projects show as "Untitled Embroidery" with blank grey
  thumbnails in the library grid, despite one being a named, finished
  24k-stitch design in the editor itself — name/thumbnail not syncing to
  the profile view. Related: layer-list shape thumbnails render blank on
  first load, fill in later.
- Properties popover anchors near its gear icon and overflows the bottom of
  the viewport, clipping Transparency and Advanced; it doesn't scroll, only
  dragging the popover by its handle reveals the rest.
- The Available Fills gallery shows a scrollbar thumb but neither wheel nor
  thumb-drag scrolls it (see pass 3 — at least one paid fill pattern may be
  hidden behind this).
- Clicking a layer row's stitch-type label does nothing; right-clicking a
  layer row or a canvas shape does nothing (the manual describes a context
  menu that didn't appear).
- A Satin-blocks shape's parameter panel is headed "Run Settings" with a
  Density field + Split Satin toggle — inconsistent with the Filled case's
  "Fill Settings" heading for the analogous area.
- Numeric inputs grow a small save-disk glyph on edit with no clear signal
  of whether Enter is required or the value is already live.
- **The manual has drifted from the shipped app**: it documents `3 =
  circle, 4 = rectangle, 5 = pen, 6 = satin blocks` and no Text tool at
  all; the shipped toolbar is `3 = satin blocks, 4 = pen`, circle/rectangle
  live in the primitives flyout instead, and Text is a real toolbar entry.
  Anyone following the manual presses the wrong keys. (This is the one
  finding worth treating as a direct lesson, not just color — see
  `MASTER_SCOPE.md`'s note on it.)
- Auto Digitize and Click-to-Stitch are both advertised as step one of the
  onboarding flow, but both are Pro-gated ($9.99/mo), along with autosave,
  version history, custom fonts, gradient fill, 24 of 30 fill patterns, and
  4 of 7 run types — so the actual free experience is manual digitizing
  with no visible save/dirty indicator and no autosave, a real
  silent-data-loss risk for a free user.

**Automation notes** (relevant to how Ember's own canvas is built, not
directly transferable): the drawing surface only registers control points
on a drag-style pointer sequence (mousedown + move + mouseup), not a plain
click — plain synthetic clicks were silently ignored and Enter alone
produced `Command failed — Error: Not enough control points to complete the
shape.` Image-drop onto the Sequencer: Images panel failed to verify at
all, almost certainly because the drop target sits inside the cross-origin
iframe — the image-to-stitch upload path could not be exercised this pass.

## Pass 3 — build-artifact fingerprinting

Fetched every shipped JS chunk (both the `emberdesign.net` marketing shell
and the `v2.emberdesign.net` editor iframe) and grepped for library
signatures, retained `node_modules` build paths, and API fingerprints.
Caveat stated by the source directly: minified bundles only prove a
library's *presence*; a few identifications (Radix vs. shadcn/ui
conventions) are inferred from coding conventions rather than an explicit
name string. The solid identifications below each left an explicit name or
unique API surface in the shipped code.

**Geometry core (the significant find).** Two editor chunks are
Emscripten/Embind WASM bundles with intact build paths:
- `node_modules/@matthewjacobson/str8/dist/str8.js` —
  [`github.com/matthewjacobson/str8`](https://github.com/matthewjacobson/str8),
  CGAL 6.1 straight-skeleton compiled to WASM, used for insets/offset
  contours. Described by its own repo as a from-scratch rebuild of
  `StrandedKitty/straight-skeleton`.
- `node_modules/voron8/dist/voron8.js` —
  [`github.com/matthewjacobson/voron8`](https://github.com/matthewjacobson/voron8),
  CGAL segment Voronoi / medial-axis extraction. The bundle calls
  `medialAxis` directly — almost certainly how satin columns get their
  centerlines.

The same author's toolbox also includes, per the same account: `bcd`
(boustrophedon cellular decomposition of a polygon-with-holes along an
arbitrary sweep angle), `ess` (evenly-spaced streamlines of a 2D vector
field), `str8-path` (central path-finding through a polygon via its
straight skeleton + JSTS), `svg2wkt`, `CDT.js`/`cdt2d` (constrained
Delaunay triangulation), and `ember-bridge` — a separate Tauri v2 desktop
app (Rust backend, React/TypeScript/Vite frontend) that terminates Brother
machines' own TLS 1.2 static-RSA "pedxml" protocol on a local loopback
port (`127.0.0.1:17831`), i.e. direct-to-machine design transfer bypassing
manual file export.

**`ess` confirmed live, not just present in the bundle**: chunk `3c1ca957`
calls a streamline generator with a `vectorField` and `boundingBox`; chunk
`1092` registers a fill pattern `{id: "streamlineFill", name:
"Streamlines", paid: true, separationMm: ...}` — a paid fill never observed
in the Available Fills gallery during pass 2's walkthrough, plausibly
hidden behind that gallery's non-scrolling scrollbar bug.

**Supporting stack:** JSTS ([`bjornharrtell/jsts`](https://github.com/bjornharrtell/jsts),
~530KB chunk, confirmed via `TopologyException`/`GeometryFactory`/
`ConformingDelaunayTriangulator` class fingerprints) for general polygon
operations — the JS-side analog of what EMB-Bot's Python side gets from
Shapely/GEOS. Rendering is PixiJS v8 ([`pixijs/pixijs`](https://github.com/pixijs/pixijs),
`~8.11.x`, WebGL-based). App shell: Next.js App Router + React, Radix UI
primitives (shadcn/ui conventions inferred), lucide-react icons, Sonner for
toasts (including the "Command failed" one hit in pass 2), AWS Amplify v6 +
Cognito for auth, Stripe for the Pro upgrade flow. App orchestration is
[XState](https://github.com/statelyai/xstate) (`appService.send({type:
...})`, state machine in chunk `6217`). Underneath both WASM modules:
CGAL and Emscripten.

**`/api/vectorize` — the auto-digitize entry point, reverse-engineered from
the caller side only** (the endpoint itself was not called — this session's
own outbound network is policy-blocked from reaching `emberdesign.net`, and
the report's author deliberately did not call it independently either, so
only the client-side caller is documented, not the server implementation):

- Single call: `fetch("/api/vectorize", {method: "POST", body: FormData
  with field "image"})`, response consumed via `.text()` — raw SVG, not
  JSON. Runs on the `v2.emberdesign.net` origin as a Next.js route handler.
  Everything after the response is client-side.
- Two commands sit on top, both calling the same trace:
  - `click-to-stitch` (`function na`): traces, defaults every resulting
    shape's stitch type to Filled unless a predicate overrides it, pushes
    into a candidate-shape store, dispatches `CLICK_TO_STICH` (sic — a
    genuine typo in the shipped event constant/dispatch, missing the
    second T, internally consistent so harmless in practice) to the
    XState app service so the user can pick regions.
  - `auto-digitize-all` (`function nd`): same trace with `groupColors:
    true`, completes all shapes at once via `completeShapes(x,
    {selectOnComplete: false, computeStitchesOnAdd: false})`, fires an
    analytics event (`stitches_generated`, `method: "auto_digitize_all"`,
    `project_object_count`).
- **Simplification heuristic, raster inputs only** (SVG input skips it):
  `tolerance = min(2.5, max(0.32, size > 0 ? 0.0028 * size : 0.65))`, where
  `size` is the larger of the traced shape's width/height, then
  `simplifyLines: true, simplifyCurveSmoothing: false, simplifyTolerance:
  tolerance`. Tolerance scales linearly with design size, clamped to
  [0.32, 2.5]. A neighboring hue helper (RGB -> 0-360) and an area helper
  (`bounds.width * bounds.height`) feed a color-grouping/ordering step that
  buckets shapes by `color.id` and exposes a `preserveAllHoles` option.
- **Gating:** one predicate returns true for `click-to-stitch`,
  `auto-digitize-all`, `convert-to-redwork`, and `edit-gradient` whenever
  `!hasActiveSubscription` — confirms and extends pass 2's Pro-wall
  finding to two more features. Availability additionally requires exactly
  one selected, unlocked image and shape.
- **Error handling:** failures log to console under `[vectorize]` with
  `phase, message, code, status, stack`; codes map to user copy —
  `MISSING_IMAGE, INVALID_IMAGE, IMAGE_PREP_FAILED, VECTORIZE_FAILED,
  FETCH_FAILED` — all surfaced under one consistent dialog title, "Image
  tracing failed."
- **On whether it's AI:** the client bundles were probed explicitly for
  ONNX, TensorFlow.js, transformers.js, WebGPU/WebNN inference, potrace,
  ImageTracer, vtracer, and any color-quantization library — none found.
  No OpenAI, Anthropic, Replicate, Bedrock, or SageMaker reference
  anywhere. The only `/api/` strings in the whole editor are
  `/api/vectorize` and the Ember Bridge loopback set (`/api/jobs/`,
  `/api/machines`, `/api/discover`, `/api/health`, `/api/pair`,
  `/api/status`), which are unrelated to vectorization. Whatever
  intelligence exists lives entirely behind `/api/vectorize`'s server
  implementation; from the browser it is indistinguishable from a classic
  raster-to-SVG tracer.

---

## What this changed, in one place

Full reasoning and the standing prioritization rule live in
`MASTER_SCOPE.md`'s cross-cutting section ("Ember Design competitive
research"). Summary: feature-parity ideas are real but backlogged behind
open trust/quality work by a standing rule, not a one-time gate. Two
findings were promoted within that backlog because a funded competitor
shipping them in production is independent validation, not just "they have
it": evenly-spaced streamline fill (EMB-Bot already has this built,
`digitizer_core/stage6_streamline.py`, scoped today to the photo-pipeline
only) and boustrophedon sweep-angle decomposition (relevant to existing
fill-angle research). One concrete, testable idea was adopted from the
`/api/vectorize` fingerprinting: EMB-Bot's `simplify_tol_mm` is a fixed
0.2mm constant regardless of design size and could plausibly benefit from
size-proportional scaling the way Ember's does. The color-block sequencer
UI idea is backlogged with independent justification (it addresses a real,
already-found gap in EMB-Bot's own cross-color sequencing). `ember-bridge`
(direct-to-machine transfer) is recorded as a distinct, much larger
"someday" idea, not comparable in scope to the above. Two of EMB-Bot's own
architectural choices were validated rather than changed: server-side
auto-digitizing, and depending on a mature format library (`pyembroidery`)
rather than hand-rolling format codecs the way Ember's own `/convert`
module does.
