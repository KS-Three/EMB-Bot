<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { generateAll, charList, letteringNote, emptyFieldHint, splitIntoTwoLines, columnNoteFabric } from "../lib/generate.js";
  import { ensureFonts, loadCoverage, loadManifest } from "../lib/fontLoader.js";
  import { isOutlineKey } from "../lib/outlineFonts.js";
  import { unsupportedMessage } from "../lib/fontCoverage.js";
  import { renderRealistic, isDark } from "../lib/preview.js";
  import { hasOriginal, loadOriginal, fitRect, placeByContent, flatContentBox, digitizedContentBox } from "../lib/originalImage.js";
  import { pickScaleBar } from "../lib/scalebar.js";
  import { tip } from "../lib/tip.js";
  import { designToStrands, strandStitchOrdinals } from "../lib/strands.js";
  import { sewnPullFor, hasSatinSpans } from "../lib/sewnWidth.js";
  import { advanceIndex, clampIndex, nextSpeed, simTimeline, colorStopBetween, stepBlock, blockAt, blockThreadNames, underlayRuns, phaseAt, blockStart, sewClock, sewTimeAt } from "../lib/simulate.js";
  import { drawSimOverlay, drawIsolate, threadPx } from "../lib/simOverlay.js";
  import SimBar from "./SimBar.svelte";
  import StitchInspector from "./StitchInspector.svelte";
  import { buildStitchIndex, inspectAt, canvasPxToMm } from "../lib/stitchInspect.js";
  import { chartIdForProject } from "../lib/designChart.js";
  import { getCachedPalette, loadPalette, loadPreferredPaletteId, STUDIO_PALETTE } from "../lib/threads.js";
  import { EMB } from "../lib/emb.js";
  import { designRectPx, hitTest, pickElement, dragResize, clampOffsets, clampPan, MIN_ZOOM, MAX_ZOOM, clampZoom, buildSnapLines, snapMove, snapResizeWidth, rotateHandlePx, dragRotate, unionBBox, clampGroupDelta, groupResizePatches } from "../lib/interact.js";
  import { selectedIdsOf } from "../lib/project.js";
  import { effectiveHoop, hoopFitNote } from "../lib/hoop.js";
  import { garmentOf, placementBoxOf } from "../lib/placement.js";
  import { resizeBadgeText, runSpm } from "../lib/estimate.js";
  import { fabricContrastNote } from "../lib/colorMatch.js";
  import { shapeOutlinesInFieldMm, designOutlinesInFieldMm, pulseAt, pulseFadeAt, createPulseTracker, hitOverlay, hitShapeInterior, moveNode, moveNodes, moveEdge, ringNodesInBox, fieldMmToOutlineMm, simplifyRing, ringKey, splitRingKey, NODE_GRAB_PX } from "../lib/shapeOverlay.js";
  import { editModeBar, MODE_SAYS, holePointPhrase, ringCentre, stepHoleCursor, sameNode, stepNodeCursor, nodeCursorPhrase } from "../lib/editModeA11y.js";
  import EditModeBar from "./EditModeBar.svelte";
  import { withNodes, nodeMarker, spanOfEdge, pastClickDeadZone, ringEditOverrides as ringEditOverridesLib, discardPatch, moveShapeOverrides } from "../lib/shapeNodes.js";
  import { rebuildSpans, moveNodesExact, insertNodeOnPath, toggleNode, deleteNodes } from "../lib/sparseNodes.js";
  import {
    appliedBorders,
    borderMenuItems,
    borderRequestPending,
    indexRuns,
    shapeBorderState } from "../lib/borderMenu.js";
  import { boundaryIssues } from "../lib/digitizer.js";
  import { isElementStale } from "../lib/staleness.js";
  import { popoverModel, popoverPatch, recolorPatch, SIMPLIFY_TOLS_MM } from "../lib/shapePopover.js";
  import { similarShapeIds, similarOverridesPatch } from "../lib/similarShapes.js";
  import { capOutlinesMm, isCapPieceId } from "../lib/capPieces.js";
  import { resolveCutOuts, isColumn, isRun, isOpenShape, shapeProblems } from "../lib/manualShapes.js";
  import { authoredInFieldMm, hitAuthored, applyAnchorDrag, applyAnchorsDrag, applyHandleDrag, insertAnchor, removeAnchor, removeAnchors, editedElementPatch, editedShapesPatch, refitShapesPatch, ANCHOR_GRAB_PX, fieldMmToPx, pxToFieldMm, clampMmToBox, cutOutOutlinesInFieldMm, breaksContainment, ringInsideBox, CUTOUT_HOLD_HINT, convertOpenShape } from "../lib/fieldNodeEdit.js";
  import Hint from "./Hint.svelte";
  import DigitizeRing from "./DigitizeRing.svelte";
  import CompareSplit from "./CompareSplit.svelte";
  import { SPLIT_DEFAULT } from "../lib/compareSplit.js";
  import { digitizeBusy } from "../lib/digitizeBusy.js";
  import Icon from "./Icon.svelte";
  import { prefersReducedMotion } from "../lib/reducedMotion.js";
  import ShapePopover from "./ShapePopover.svelte";

  // Task 4 (Slice 5): the field now renders every element in the project
  // (generateAll's combined design) instead of a single design, and drag/
  // resize/selection are scoped to whichever element is currently selected
  // (project.selectedId). `runtime` carries the per-element flattened image
  // state (see generate.js's generateAll) -- it replaces the old singleton
  // `flat` prop.
  export let project;
  export let runtime;
  // Whether the floating "drag-field" onboarding hint should render right
  // now -- App.svelte computes this from hints.js's shouldShow("drag-field")
  // + the A8 eligibility condition (the combined design has stitchCount > 0,
  // reported via this component's own "stats" event below) + the A7
  // cross-hint priority rule.
  export let showDragHint = false;
  // The shape the Layers list is pointing at (2026-09-30). Both are
  // { elId, shapeId } or null, owned by App so the list and the canvas share
  // one idea of "the shape in question": `hoverShape` is drawn as a white
  // outline whether or not the outlines toggle is on; `focusShape` is
  // applied as this component's own selection (the amber one) exactly as a
  // canvas click would. Before this, selectedShapeId was set from a canvas
  // hit only, and a row in a thirty-row list had no way to say which
  // outline it was.
  export let hoverShape = null;
  export let focusShape = null;
  // The operator's Quote settings (App's `quote`, quote.js), read only for
  // the simulator bar's sew-time rate: runSpm() picks the same speed for it as
  // Download's "Run time" row, so the two agree. Not named in any `$: if
  // (canvas)` block, so a quote change never repaints the field.
  export let quote = null;
  $: simRate = runSpm(quote);

  const dispatch = createEventDispatcher();
  const MM_PER_INCH = 25.4;
  const MIN_SIZE_MM = 5;
  const HANDLE_R = 8;
  // Auto-snap: screen-space radius, converted to mm through the current
  // render scale on every use — zooming in naturally shrinks the mm radius,
  // which is the fine-control escape hatch alongside Alt/the magnet toggle.
  const SNAP_PX = 7;
  const GUIDE_COLOR = "#e0308c";
  const ROTATE_STALK_PX = 22;
  const ROTATE_GRIP_R = 7;

  let canvas;
  let error = "";
  let stats = "";
  let warn = false;
  let hasDesign = false;
  let hint = "";
  // Does this device have a mouse? `emptyFieldHint` picks its sentence from
  // this, because the drawing tools are only reachable by right-click and a
  // touch customer cannot perform that gesture (generate.js carries the
  // measurement). Not a viewport question — a phone-sized window on a laptop
  // still has a mouse, and a tablet with a trackpad attached mid-session
  // gains one, which is what the listener below is for.
  //
  // Read EAGERLY here, not in onMount: the first paint() can run before
  // onMount's callbacks do, and a phone that saw the desktop sentence on
  // first paint would keep it — which is the whole defect. onMount only adds
  // the listener. `true` when there is no matchMedia at all (jsdom, SSR):
  // the mouse sentence is the one that was shipping, so an environment that
  // cannot answer keeps the old behaviour rather than inventing a new one.
  let hasFinePointer = readFinePointer();
  let pointerMq = null;
  function readFinePointer() {
    if (typeof window === "undefined" || !window.matchMedia) return true;
    return window.matchMedia("(any-pointer: fine)").matches;
  }
  // Spoken to a screen reader after a keyboard nudge (see nudgeSelected). It
  // is the position readout a sighted user gets from the moveBadge and from
  // simply watching the design move, so it carries the same two facts: where
  // the design now sits, or that the hoop edge refused the move.
  let liveMsg = "";
  // Hoop ceiling check (launch item 2): the COMBINED design's dims against
  // the project's chosen hoop (lib/hoop.js). "" = fits, else the user-facing
  // note ("Exceeds your 4×4 in hoop…"). Set alongside `stats` in paint() —
  // it's a CHECK on the generated result, never a clamp (the clamp math
  // stays keyed to the garment placement box).
  let hoopNote = "";
  // Characters the element's font has no glyph for. The lettering path skips
  // them silently, which was obscure while the library was all-Latin and became
  // a one-click dead end when Hebrew fonts arrived: pick one, type "Emb", and
  // the field just stays empty. generate.js reports them; this turns them into
  // something a person can act on.
  let unsupportedNote = "";
  // The selected TEXT element's width-guard note (cap under the floor,
  // hairline strokes sewn as run, columns under 1 mm) — per element like the
  // 5 mm warn, because the fix is that element's size or font.
  let letterNote = "";
  // The one-click line break offered beside a thin-lettering note: the
  // element to patch and its text over two lines, or null.
  let twoLinesFix = null;
  // Thread vs garment colour. The canvas shows a neutral work bed, not the
  // fabric (#648), so this caption note is the only place a design that will
  // vanish into its garment says so. Reactive on the cached result so picking
  // a fabric swatch updates it without a regenerate.
  $: contrastNote = lastGenerateResult
    ? fabricContrastNote(lastGenerateResult.combined && lastGenerateResult.combined.colors, project && project.fabricRgb)
    : "";

  // Result of the last renderRealistic() call — { toCanvas, scale, designBBoxMm } —
  // kept around so pointer handlers and the selection overlay can hit-test /
  // draw against the exact transform that was just used to paint the canvas.
  let renderResult = null;
  // Count of completed paints of a real design (paint() and repaintView()).
  // Surfaced as data-paint-seq so a test waits on state, not on a timer.
  let paintSeq = 0;

  // Per-element canvas rects computed from the last paint(), one per ready
  // element (see generate.js's generateAll perElement), each shaped
  // { id, x, y, w, h } — exactly what interact.js's pickElement/hitTest
  // expect. Array order matches project.elements order (paint order), which
  // is also the "topmost" order pickElement resolves overlaps with.
  let perElementRects = [];
  // The last paint()'s perElement entries, keyed by id, so drag handlers can
  // look up a specific element's design/bboxMm without re-running generateAll.
  let peById = {};

  // B2: the last successful generateAll() result ({ combined, perElement }),
  // kept so a view-only change (wheel/pan/zoom buttons) can re-paint against
  // the SAME stitches without paying for another full generateAll — only
  // renderRealistic + perElementRects need to redo work when just the camera
  // moved. null whenever there's no design (paint()'s error/empty branches).
  let lastGenerateResult = null;

  // Zoom/pan view state (Slice 8 Task 2). Not part of `project` -- it's
  // ephemeral field-viewport UI state, not project data, and never persisted.
  // Fed to renderRealistic's `view` opt (B1: POST-VIEW contract -- see
  // preview.js) on every paint, full or view-only.
  // Range is MIN_ZOOM..MAX_ZOOM (100%-800%), from lib/interact.js.
  let view = { zoom: 1, panX: 0, panY: 0 };
  let rafViewScheduled = false;

  // Diagnostic overlays (view-only, ephemeral — same lifecycle as zoom/pan):
  // dashed needle-up travel lines and X markers at trims.
  let showJumps = false;
  let showTrims = false;
  // Sewn width (2026-10-06): satin columns drawn with the fabric's pull
  // compensation taken back off, the width the cloth shows rather than the
  // width the file carries. A view toggle like jumps/trims — nothing in the
  // design moves. The pull is the project's garment preset with its profile,
  // the same number the service compensated with (lib/sewnWidth.js). Only a
  // design with satin spans has anything for it to act on, so the toggle is
  // disabled otherwise rather than silently doing nothing.
  let sewnWidthView = false;
  function toggleSewnWidth() { sewnWidthView = !sewnWidthView; scheduleViewRepaint(); }
  $: sewnPullMm = sewnWidthView ? sewnPullFor(project) : 0;
  $: canSewnWidth = !!(lastGenerateResult && lastGenerateResult.combined && hasSatinSpans(lastGenerateResult.combined)) && sewnPullFor(project) > 0;
  function toggleJumps() { showJumps = !showJumps; scheduleViewRepaint(); }
  function toggleTrims() { showTrims = !showTrims; scheduleViewRepaint(); }

  // ---- the stitch inspector (2026-11-08) ------------------------------------
  //
  // Inspect on: hovering the field names the stitch nearest the pointer
  // (lib/stitchInspect.js, StitchInspector.svelte). Off by default; the bar
  // toggles it, Escape turns it off.
  //
  // A hover here must never repaint the field (#1334 pins 0 renders per
  // hover): nothing below writes `canvas`, `view` or anything a paint
  // statement names, and none of it draws. The tooltip is a DOM element
  // outside `.hoop`, so `inspectHit` is the only thing a move changes.
  //
  // The index is built on the first hover after a generation, from the very
  // `combined` design the field drew, and kept until the next one; the
  // thread names are the simulator's (nameSimThreads' chart lookup).
  let inspectOn = false;
  let inspectHit = null;   // { info, x, y } (client px), or null
  let inspectIx = null;
  let inspectFor = null;   // the combined design inspectIx indexes
  let inspectNames = [];
  function toggleInspect() {
    inspectOn = !inspectOn;
    inspectHit = null;
    inspectFor = null; // re-read the chart's names when it comes back on
  }
  function inspectHover(e, p) {
    if (!inspectOn) return;
    const c = lastGenerateResult && lastGenerateResult.combined;
    if (!c || !renderResult || !renderResult.toCanvas) { inspectHit = null; return; }
    if (inspectFor !== c) {
      inspectIx = buildStitchIndex(c);
      inspectFor = c;
      nameInspectThreads(inspectIx);
    }
    const mm = canvasPxToMm(renderResult.toCanvas, p.x, p.y);
    const info = mm ? inspectAt(inspectIx, mm.x, mm.y, inspectNames) : null;
    inspectHit = info ? { info, x: e.clientX, y: e.clientY } : null;
  }
  function nameInspectThreads(ix) {
    inspectNames = [];
    if (!ix) return;
    const id = loadPreferredPaletteId(chartIdForProject(project));
    const hit = getCachedPalette(id);
    inspectNames = blockThreadNames(ix.tl, (hit || STUDIO_PALETTE).threads);
    if (hit) return;
    loadPalette(id).then((pal) => {
      if (inspectIx === ix && pal) inspectNames = blockThreadNames(ix.tl, pal.threads);
    }, () => {});
  }
  // A new generation or a new view moves the stitches under a resting
  // pointer; the next move reads them again.
  $: { lastGenerateResult; view; inspectHit = null; }
  // Every shape of a digitized element used to be outlined in cyan, with a
  // node on every vertex, permanently — not tied to selection, not tied to an
  // edit mode, and unaffected by the Realistic view toggle. On a two-colour
  // logo that is 31 outlines over the artwork, so the one screen meant to
  // answer "what will this look like sewn?" answered "here is a wireframe".
  //
  // Off by default, like the other two diagnostic overlays it now sits
  // beside. The SELECTED shape is always outlined regardless (see
  // drawShapeOutlines) — that highlight is what tells you which shape a
  // Delete or a drag is about to act on, so hiding it would break editing
  // rather than declutter it.
  let showOutlines = false;
  function toggleOutlines() { showOutlines = !showOutlines; scheduleViewRepaint(); }

  // Realistic vs flat thread. Ember ships this as a toggle and it earns its
  // place for the same reason: with the lighting off, coverage and stitch
  // structure read as flat areas of colour, which is the better view while
  // judging whether a shape is actually filled. Physical thread width is the
  // same in both, so the coverage answer never changes with the view.
  let realisticView = true;
  function toggleRealistic() { realisticView = !realisticView; scheduleViewRepaint(); }
  // The view segments (2026-09-30): each picks its view rather than toggling,
  // so clicking the one already lit does nothing, which is what a segmented
  // control promises. Leaving the simulator to pick a view stops it first.
  function showFlat() {
    if (originalView) { originalView = false; originalToken++; scheduleViewRepaint(); }
    if (simActive) stopSim();
    if (realisticView) toggleRealistic();
  }
  function showRealistic() {
    if (originalView) { originalView = false; originalToken++; scheduleViewRepaint(); }
    if (simActive) stopSim();
    if (!realisticView) toggleRealistic();
  }
  // Original view (spec §4): the uploaded artwork in place of the thread.
  // View-only, like zoom — never saved, and any regeneration drops it,
  // because a regenerated design is the thing the customer now wants to see.
  let originalView = false;
  $: anyOriginal = !!(project && project.elements && project.elements.some(hasOriginal));
  $: if (!anyOriginal && originalView) { originalView = false; originalToken++; }
  function showOriginal() {
    if (simActive) stopSim();
    originalView = true;
    compareView = false;
    scheduleViewRepaint();
  }
  // Compare view (2026-11-07): Original view with a split — the artwork LEFT
  // of a draggable handle, the realistic stitches RIGHT, at the same
  // registration. It IS Original view underneath (originalView stays true),
  // so every rule that keeps edits and chrome off the artwork — and every
  // way out of Original view (another view, the simulator, a regeneration) —
  // applies to it unchanged; `compareView` alone means nothing.
  //
  // The artwork side is painted from repaintView onto an OFFSCREEN canvas
  // (never in the DOM: .hoop holds exactly one <canvas>, which e2e locators
  // and the field's own code assume) and shown in CompareSplit as an <img>
  // of that bitmap, once drawOriginals has put the artwork on it.
  let compareView = false;
  let compareSplit = SPLIT_DEFAULT;
  let compareCanvas = null;
  let compareSrc = "";
  $: compareOn = originalView && compareView;
  // Leaving Compare (by any way out of Original view) drops the bitmap.
  $: if (!compareOn && compareSrc) setCompareSrc("");
  function setCompareSrc(url) {
    if (compareSrc && typeof URL !== "undefined" && URL.revokeObjectURL) URL.revokeObjectURL(compareSrc);
    compareSrc = url;
  }
  // The offscreen bitmap -> an object URL for the <img>. Only the latest
  // drawOriginals pass publishes (`my`), and only while Compare is still lit.
  function publishCompare(my) {
    const c = compareCanvas;
    if (!c || !c.toBlob) return;
    c.toBlob((blob) => {
      if (!blob || my !== originalToken || !(originalView && compareView)) return;
      setCompareSrc(URL.createObjectURL(blob));
    }, "image/png");
  }
  function showCompare() {
    if (simActive) stopSim();
    originalView = true;
    compareView = true;
    scheduleViewRepaint();
  }

  // ---- stitch simulator state (see lib/simulate.js for the pure math) ----
  // simIndex is a FLOAT while playing (fractional progress carries across
  // frames); everything that renders/display floors it. The simulator is a
  // view of the CURRENT generated design only — any project/runtime change
  // regenerates stitches, so paint() force-stops it (stopSim) rather than
  // trying to keep a stale strand count alive.
  let simActive = false;
  let simPlaying = false;
  let simIndex = 0;
  let simTotal = 0;
  // Stitch number per strand — see startSim. The DISPLAY total is the last
  // entry, not `combined.stitchCount`: a run of a single stitch paints no
  // segment, so the simulator must not claim to have drawn it.
  let simOrdinals = [];
  let simSpeed = 1;
  let simRafId = 0;
  let simLastTs = 0;
  // The machine's events on the strand timeline (lib/simulate.js
  // simTimeline): thread blocks, trims, travel. Built once per run, with the
  // strands the needle marker reads its position from.
  let simTl = null;
  let simStrands = [];
  let simNames = [];
  // Stop at each thread change, as the machine does (on by default; the
  // bar's "Stops" toggle). simStopped: paused AT a change by that stop, so
  // the bar names the thread to load next.
  let simStopAtChanges = true;
  let simStopped = false;
  // Underlay sewn and not yet covered, drawn lighter (lib/simulate.js
  // underlayRuns); built once per run from the strands' own kind tags.
  let simUnderlay = null;
  // Isolate (the bar's toggle): dim everything but the thread on the needle.
  let simIsolate = false;
  // Where the stitches and stops sit on the strand timeline, for the bar's
  // sew-time estimate (lib/simulate.js sewClock); built once per run.
  let simClock = null;

  // Drag state (module-local to this component instance, not reactive —
  // none of it needs to trigger a re-render on its own).
  let dragMode = null; // null | "resize" | "move" | "rotate" | "pan"
  let dragHandle = null; // "nw"|"ne"|"sw"|"se" when dragMode === "resize"
  let dragTargetId = null; // element id the current drag applies to
  let dragStartPx = null; // {x,y} canvas-space pointer start
  let dragStartWidthMm = 0;
  let dragStartHeightMm = 0;
  let dragStartOffXMm = 0;
  let dragStartOffYMm = 0;
  let dragStartPanX = 0; // view.panX at the start of a "pan" drag
  let dragStartPanY = 0; // view.panY at the start of a "pan" drag
  let rafScheduled = false;
  let pendingPatch = null; // { id, patch }

  // Auto-snap + rotate state. `snapEnabled` is an app-wide UI preference
  // (like zoom, it's not project data — but unlike zoom it survives reloads
  // via localStorage; holding Alt suspends it for the current drag events).
  // The rest is per-drag overlay chrome, cleared by endDrag.
  let snapEnabled = (() => {
    try { return localStorage.getItem("embbot-snap") !== "0"; } catch { return true; }
  })();
  let activeGuides = null; // { vXMm, hYMm } while a move-snap is live (null members = axis not snapped)
  let sizeMatch = null; // "width" | "height" while a resize is size-matched to another element
  let moveBadge = null; // { xMm, yMm } center-offset readout during a move drag
  let sizeBadge = null; // { wMm, hMm, xMm, yMm } live W × H (+ centre offset) during a resize drag
  let rotateBadgeDeg = null; // live degrees during a rotate drag
  let dragStartBBoxMm = null; // dragged element's absolute mm bbox at pointerdown
  let dragStartTargetMm = 0; // element's sizeMm at pointerdown (see size-match note below)
  let dragStartRotationDeg = 0;
  let dragRotateCenterPx = null; // element center (canvas px), fixed at rotate-grab

  // Multi-select (Ctrl+click) group-drag state. dragMembers snapshots each
  // selected member's offsets/size at pointerdown; dragGroupBBoxMm is the
  // union mm bbox the group moves/resizes as.
  let dragMembers = null; // [{ id, offX, offY, widthMm, targetMm }]
  let dragGroupBBoxMm = null;

  $: selIds = selectedIdsOf(project);
  // Starts the "we found these shapes" pulse when a digitize result is new.
  // Safe to run on every project change: `noteOutlineResults` only restarts a
  // cue when an element's `review` identity actually changed, so editing an
  // unrelated element (or panning) never re-triggers it.
  $: project, noteOutlineResults();
  $: multiSel = selIds.length > 1;
  // The scale bar follows the render's px-per-mm, which already has the
  // view's zoom in it (B1), so wheel/button zoom moves it without any
  // second calculation. `renderResult` is reassigned on every render, view
  // repaint and clear, which is exactly the set of events that change it.
  $: scaleBar = pickScaleBar(renderResult && renderResult.scale);

  // Union canvas-px rect of every selected member — the group's visible box.
  function groupRectPx() {
    const rects = perElementRects.filter((r) => selIds.includes(r.id));
    if (!rects.length) return null;
    const x = Math.min(...rects.map((r) => r.x));
    const y = Math.min(...rects.map((r) => r.y));
    const x1 = Math.max(...rects.map((r) => r.x + r.w));
    const y1 = Math.max(...rects.map((r) => r.y + r.h));
    return { x, y, w: x1 - x, h: y1 - y };
  }

  function toggleSnap() {
    snapEnabled = !snapEnabled;
    try { localStorage.setItem("embbot-snap", snapEnabled ? "1" : "0"); } catch {}
  }

  // The garment AS PLACED (lib/placement.js): the placement's box and label.
  function garmentFor(p) {
    return garmentOf(p);
  }

  // Returns the GARMENT PLACEMENT BOX, not the hoop, despite the name — the
  // same historical naming `SizePanel.hoopWidthMm` documents ("it is not the
  // physical hoop, which is a separate ceiling check"). Kept for the same
  // reason: every clamp site below reads it. Written down here too because the
  // name cost real time on 2026-09-08 — a starter template sized to the full
  // placement box became un-nudgeable, and the arrow keys blamed the hoop,
  // which had 14 mm of room on each side.
  //
  // The four clamp sites (nudgeSelected, reclampAll, group drag, single
  // drag/resize) all clamp to the PLACEMENT, which is the intended behaviour —
  // a left-chest design should not wander onto the shoulder. What was wrong
  // was only what the app SAID about it; see the two live-region strings below.
  //
  // The PLACEMENT's box since 2026-10-27 (lib/placement.js placementBoxOf):
  // the pro's where he measured one, the picked placement's otherwise. Until
  // then the clamps read the garment's round-inch pair, so a hat front let a
  // drag run to 127 mm while auto-fit stopped at the pro's 113.5.
  function hoopSizeMm(p) {
    const box = placementBoxOf(p);
    return box ? { wMm: box.w, hMm: box.h } : { wMm: 0, hMm: 0 };
  }

  const EMPTY_DESIGN = { stitches: [] };

  // B4: the empty state shares the SAME renderRealistic() call the populated
  // state uses below (fabricRgb fill, luminance-aware hoop outline, weave,
  // view) -- no separate hardcoded-color fill path. An empty design just
  // means designToStrands() inside renderRealistic contributes zero strands;
  // the background/hoop-outline/weave painting is identical either way.
  // The two rectangles the canvas draws, together, because they are different
  // objects and the picture used to show only one of them: `garment` is the
  // placement box (where on the shirt the design sits), `hoop` is the frame the
  // machine actually clamps. Before this, changing the hoop in step 1 left the
  // canvas BYTE-IDENTICAL -- the only signal was a line of caption text --
  // because every paint passed the garment and the renderer called it a hoop.
  function hoopOpt(p) {
    const garment = garmentFor(p);
    if (!garment) return undefined;
    return { garment, hoop: effectiveHoop(p).hoop || undefined };
  }

  // Every field render starts from a DEFAULT 2D context state. renderRealistic
  // sets only some of it (the dpr transform, its own strokes' styles), so state
  // a previous render left behind leaked into the next one: the stitches end
  // with lineCap/lineJoin "round", and the hoop's dashed safe-area line drawn
  // next was then drawn with round dash ends. Same design, same size, different
  // pixels, depending only on whether the canvas had been resized (a width
  // write resets the context) since the last render. Measured 2026-11-07:
  // 1,191 px differed, all on the dashed lines, between a render on a fresh
  // context and the same design re-rendered after an undo
  // (keyboard-a11y.spec.js "Ctrl+Z / Ctrl+Shift+Z ..."). Before #1341 a resize
  // ALSO re-ran paint(), whose render then landed on a used context, so the
  // first frame happened to match later ones. reset() also clears the bitmap,
  // which renderRealistic fills edge to edge anyway.
  function freshContext(el) {
    const ctx = el && el.getContext && el.getContext("2d");
    if (!ctx) return;
    if (typeof ctx.reset === "function") { ctx.reset(); return; }
    if (ctx.setTransform) ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (ctx.setLineDash) ctx.setLineDash([]);
    ctx.lineDashOffset = 0;
    ctx.lineCap = "butt";
    ctx.lineJoin = "miter";
    ctx.lineWidth = 1;
    ctx.miterLimit = 10;
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }

  function clearToFabric() {
    if (!canvas) return;
    freshContext(canvas);
    renderResult = renderRealistic(canvas, EMPTY_DESIGN, {
      dpr,
      hoop: hoopOpt(project),
      fabricRgb: project && project.fabricRgb,
      weave: true,
      surround: surroundColor(),
      grid: gridColors(),
      view,
    });
  }

  // The canvas outside the hoop paints the same --surround the field pane
  // is, read off the token so the two can never drift (the old contract
  // between .field and the canvas fill, kept — just dark now). The fallback
  // is the token's own value, for a render before styles are attached.
  function surroundColor() {
    if (typeof document === "undefined") return "#22252c";
    const v = getComputedStyle(document.documentElement).getPropertyValue("--surround").trim();
    return v || "#22252c";
  }

  // Work bed + measuring grid, read off theme tokens (fallbacks are the token
  // values) so the canvas and the CSS can never drift.
  function gridColors() {
    const cs = typeof document === "undefined" ? null : getComputedStyle(document.documentElement);
    const tok = (name, fb) => (cs && cs.getPropertyValue(name).trim()) || fb;
    return {
      bed: tok("--field-bed", "#7b8190"),
      minor: tok("--field-grid-minor", "rgba(255,255,255,0.10)"),
      major: tok("--field-grid-major", "rgba(255,255,255,0.22)"),
      label: tok("--surround-muted", "#a3a9b6"),
    };
  }

  function accentColor() {
    if (typeof document === "undefined") return "#2f6fed";
    const v = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    return v || "#2f6fed";
  }

  // B7: on dark fabric the plain accent color reads poorly (indigo-on-navy is
  // low contrast), so the selection chrome switches to a light accent-tinted
  // variant -- same isDark() luminance helper drawHoopOutline uses in
  // preview.js, so "what counts as dark" never drifts between the two.
  function selectionColor() {
    const rgb = project && project.fabricRgb;
    if (rgb && isDark(rgb)) {
      if (typeof document === "undefined") return "#ccd6fb";
      const v = getComputedStyle(document.documentElement).getPropertyValue("--tint-border").trim();
      return v || "#ccd6fb";
    }
    return accentColor();
  }

  function selectedElement() {
    return (project && project.elements && project.elements.find((el) => el.id === project.selectedId)) || null;
  }

  // Text elements rotate via the lettering engine's rotationDeg path;
  // imported design elements via buildImportedDesign's (rotate-before-
  // scale/clamp, 2026-07-29), and digitized elements ride that same
  // buildImportedDesign path. Image elements have no rotation support
  // (yet), so they alone show no dead handle.
  function rotatable() {
    const el = selectedElement();
    return !!el && (el.type === "text" || el.type === "design" || el.type === "digitized");
  }

  // Full-canvas smart-guide lines at the mm positions a live move-snap
  // locked onto. Drawn under the selection chrome.
  function drawGuides(ctx) {
    if (!activeGuides || !renderResult || !renderResult.toCanvas) return;
    ctx.save();
    ctx.strokeStyle = GUIDE_COLOR;
    ctx.lineWidth = 1;
    if (activeGuides.vXMm != null) {
      const x = Math.round(renderResult.toCanvas(activeGuides.vXMm, 0).x) + 0.5;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, cssH());
      ctx.stroke();
    }
    if (activeGuides.hYMm != null) {
      const y = Math.round(renderResult.toCanvas(0, activeGuides.hYMm).y) + 0.5;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(cssW(), y);
      ctx.stroke();
    }
    ctx.restore();
  }

  // Grip placement, shared by drawing and hit-testing so the two can never
  // disagree: the lollipop flips BELOW the box when its normal above-the-top
  // position would land off-canvas (top edge panned/zoomed above y=0) —
  // an off-canvas grip can't be pointed at, making rotation unreachable.
  function rotateGripPos(rect) {
    const flip = rect.y - ROTATE_STALK_PX - ROTATE_GRIP_R < 0;
    return { ...rotateHandlePx(rect, ROTATE_STALK_PX, { flip }), flip };
  }

  function drawRotateHandle(ctx, rect, color) {
    const grip = rotateGripPos(rect);
    const stalkAnchorY = grip.flip ? rect.y + rect.h : rect.y;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(Math.round(rect.x + rect.w / 2) + 0.5, Math.round(stalkAnchorY) + 0.5);
    ctx.lineTo(Math.round(grip.x) + 0.5, Math.round(grip.y) + 0.5);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(grip.x, grip.y, ROTATE_GRIP_R, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  }

  // Small dark pill with white text — shared by the move-offset readout,
  // the "same width/height" resize indicator, and the rotate degree badge.
  // Position is clamped so it never renders off-canvas.
  function drawBadge(ctx, cx, cy, text) {
    ctx.save();
    ctx.font = "11px system-ui, sans-serif";
    const w = ctx.measureText(text).width + 12;
    const h = 18;
    const x = Math.round(Math.min(Math.max(cx - w / 2, 4), cssW() - w - 4));
    const y = Math.round(Math.min(Math.max(cy - h / 2, 4), cssH() - h - 4));
    ctx.fillStyle = "rgba(24, 26, 38, 0.85)";
    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(x, y, w, h, 4);
      ctx.fill();
    } else {
      ctx.fillRect(x, y, w, h);
    }
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, x + w / 2, y + h / 2 + 0.5);
    ctx.restore();
  }

  const fmtMm = (v) => (v >= 0 ? "+" : "") + v.toFixed(1);

  function drawDragBadges(ctx, rect) {
    if (moveBadge) {
      // Center offset from hoop center in mm (+y up) — the number an
      // embroiderer would transfer to a hooping aid.
      drawBadge(ctx, rect.x + rect.w / 2, rect.y + rect.h + 14, `x ${fmtMm(moveBadge.xMm)} · y ${fmtMm(moveBadge.yMm)} mm`);
    } else if (sizeBadge) {
      // Live W × H (mm, inches in brackets, the summary bar's sizeLabel) with
      // the centre offset, under a resize drag — single element or group.
      // Kent, 2026-10-27: "resize the design on the canvas with live X and Y
      // mm readouts". The size-match word rides on the end when it applies.
      drawBadge(ctx, rect.x + rect.w / 2, rect.y + rect.h + 14, resizeBadgeText(sizeBadge, sizeMatch));
    } else if (sizeMatch) {
      drawBadge(ctx, rect.x + rect.w / 2, rect.y + rect.h + 14, sizeMatch === "width" ? "same width" : "same height");
    } else if (rotateBadgeDeg != null) {
      // Badge sits on the grip's outward side (above normally, below when
      // the lollipop is flipped under the box) so it never covers the box.
      const grip = rotateGripPos(rect);
      drawBadge(ctx, grip.x, grip.y + (grip.flip ? 16 : -16), `${rotateBadgeDeg}°`);
    }
  }

  // Draws the selection box + 4 corner handles ONLY around the SELECTED
  // element's rect — every other element renders plain (no overlay), even
  // if it's also "ready" this paint. Snap guides go underneath, the rotate
  // lollipop (text elements) and any live drag badge on top.
  function drawBoxWithHandles(ctx, rect, color) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.strokeRect(Math.round(rect.x) + 0.5, Math.round(rect.y) + 0.5, rect.w, rect.h);
    const s = HANDLE_R;
    ctx.fillStyle = color;
    const corners = [
      [rect.x, rect.y],
      [rect.x + rect.w, rect.y],
      [rect.x, rect.y + rect.h],
      [rect.x + rect.w, rect.y + rect.h],
    ];
    for (const [cx, cy] of corners) ctx.fillRect(cx - s / 2, cy - s / 2, s, s);
    ctx.restore();
  }

  // ---- auto-digitize shape outlines (Kent's 2026-08-12 request, reqs 1-3, 7)
  //
  // Every shape the digitizer recognised, drawn over the stitches as its own
  // outline with its own nodes — so the result reads as a set of editable
  // FEATURES rather than one opaque blob of stitching. The geometry (and the
  // reason it fits a bbox instead of recomputing buildImportedDesign's
  // transform) lives in lib/shapeOverlay.js.
  //
  // Draws under the selection chrome and above the stitches. Deliberately for
  // EVERY digitized element, not just the selected one: the point of the cue
  // is "here is what I found", which is not a per-selection question.
  const NODE_R = 2.6;
  const OUTLINE_RGB = "0, 200, 255";

  // Fires the cue once per DIGITIZE — not per repaint, and not on load. See
  // createPulseTracker for why the "not on load" half matters.
  const pulses = createPulseTracker();
  let pulseRafId = 0;

  // Hand edits that have been saved but not yet re-digitized, keyed by shape.
  // Both the draw pass and the hit-test read through this so what is shown and
  // what is grabbable are the same geometry.
  function pendingBoundaries(el) {
    const ov = (el && el.shapeOverrides) || null;
    if (!ov) return null;
    const m = new Map();
    for (const [sid, entry] of Object.entries(ov)) {
      if (entry && Array.isArray(entry.boundary_override)) m.set(sid, entry.boundary_override);
    }
    return m.size ? m : null;
  }

  // The same for interior rings: a pending `holes_override` (v1.9) is drawn in
  // place of the review's own `holesFull`.
  function pendingHoles(el) {
    const ov = (el && el.shapeOverrides) || null;
    if (!ov) return null;
    const m = new Map();
    for (const [sid, entry] of Object.entries(ov)) {
      if (entry && Array.isArray(entry.holes_override)) m.set(sid, entry.holes_override);
    }
    return m.size ? m : null;
  }

  function digitizedRows(el) {
    const rows = el && el.review && el.review.shapes;
    if (!Array.isArray(rows) || !rows.length) return null;
    // A shape the user hid or deleted in review is not something the app
    // "found" any more — but it still counts toward the shared transform (see
    // shapeOverlay.outlineBBoxMm), so filter for DRAWING only.
    return rows;
  }

  function outlinePulseKey(el) {
    // `review` is replaced wholesale by each digitize, so its identity is the
    // cheapest honest "this is a new result" signal available.
    return el && el.review ? el.review : null;
  }

  function noteOutlineResults() {
    if (!project || !Array.isArray(project.elements)) return;
    const now = performance.now();
    for (const el of project.elements) {
      if (el.type !== "digitized") continue;
      // An upload that has not been digitized yet is seen too, with a null
      // key: that baseline is what makes its FIRST result a change, and so a
      // pulse. Skipping it made the first result a silent first sighting.
      pulses.seen(el.id, digitizedRows(el) ? outlinePulseKey(el) : null, now);
    }
    if (pulses.active(now)) schedulePulseFrame();
  }

  // The pulse is the only thing on this canvas that animates without user
  // input, so it drives its own rAF loop and stops itself the moment every
  // element's cue has finished — no idle timer left running behind a design
  // the user is just looking at.
  function schedulePulseFrame() {
    if (pulseRafId) return;
    pulseRafId = requestAnimationFrame(() => {
      pulseRafId = 0;
      if (simActive) return;      // the simulator owns the canvas while playing
      repaintView();
    });
  }

  // ---- shape editing (Kent's requirements 4 and 4b) -------------------------
  //
  // Drag a node, drag a whole line, double-click an edge to add a node. Writes
  // through `boundary_override` (contract v1.4) — the same key DigitizePanel's
  // per-shape editor already round-trips, so nothing new had to be invented on
  // the wire.
  //
  // SELECT FIRST, THEN EDIT (Kent's call, 2026-08-13). The first click on an
  // outline SELECTS that shape; only the selected shape's nodes and lines are
  // grabbable. The alternative — every outline live the moment it is drawn —
  // was built first and rejected: on a photo design the outlines cover most of
  // the artwork, so positioning a design would constantly reshape it by
  // accident. One extra click buys back "I can still move this thing".
  //
  // Precedence: tested AFTER the rotate grip and multi-select chrome but
  // BEFORE the element rect. Clicking an unselected outline selects it and
  // does nothing else; clicking the SELECTED shape's outline starts an edit;
  // everywhere else still moves the element.
  let selectedShapeId = null;
  // The element `selectedShapeId` belongs to. A shape id alone does not name
  // a shape: every preset element's one shape is "shape", and hand-drawn ids
  // restart at s1 in each element, so an untagged id highlighted (and armed
  // Delete on) the same-id shape of EVERY element. Every assignment to
  // selectedShapeId sets this beside it. Invariant, kept by the `$:` block
  // below: whenever selectedShapeId is set, selectedShapeElId ===
  // project.selectedId — the selected shape lives on the selected element.
  let selectedShapeElId = null;
  let shapeEdit = null;     // { elId, shapeId, kind, index, startPx, ring }
  let liveRing = null;      // { shapeId, points } — the drag's working geometry
  let shapeEditError = "";

  // The click-to-edit popover (2026-09-29 spec §5). Open when a CLICK — a
  // press and release that travelled under CLICK_PX — lands on or inside a
  // shape; the shape is selected first so the amber highlight shows what the
  // controls act on. {x, y} are offsets inside .hoop, like fieldMenu's.
  const CLICK_PX = 4;
  let shapePop = null;
  let pressClient = null;   // { x, y, px } — the press, for the click test in endDrag
  // The press landed on an outline and only SELECTED its shape: the popover
  // opens on the release, and only if the pointer did not travel. Opening on
  // the press let a drag open it, and the browser's mousedown default then
  // took focus back from the dialog.
  let pressOutline = false;
  // The press landed on an EDGE of the selected hand-drawn shape: a click
  // there inserts an anchor on the release (endDrag); a drag does nothing.
  let pressEdge = null;     // { elId, shapeId, index }
  let hoopBounds = { w: 0, h: 0 };

  // Node editing of a HAND-DRAWN shape (2026-09-29 field-node-edit spec):
  // the authored anchors/controls, mapped through the engine's fit, drawn and
  // grabbable once the shape is selected. `basis` is frozen at press so a
  // regenerate landing mid-drag cannot skew the inverse; `live` is the shape
  // as the drag has it. The drag is RELATIVE — `grab` is the node's offset
  // from the press point (authored px), so the node keeps that offset rather
  // than snapping to the pointer — and `moving` flips only once the pointer
  // has travelled CLICK_PX, so a click on a node never changes it.
  // `focusedAnchor` is the anchor a Delete would remove.
  let nodeEdit = null;      // { elId, shapeId, kind: "anchor"|"handle", index, basis: { fit, shape }, live, grab: { dx, dy }, moving }
  let focusedAnchor = null; // { elId, shapeId, index }

  // ---- Reshape mode (2026-11-03 spec, section 4) -----------------------------
  //
  // "Edit points" in the shape popover turns it on for the selected ELEMENT, on
  // either lane. Outside it nothing here applies: a selected shape drags one
  // node, a bare drag moves the element, arrows nudge the element. Inside it a
  // bare drag is a MARQUEE over the points of EVERY shape of the element — a
  // seam is two shapes' coincident edges, and stage 5 clips or hides the edge
  // of whichever one moved alone, so both have to move in one gesture — a drag
  // on a selected point moves them all, the arrows nudge them 0.1 mm (Shift
  // 1 mm), Delete removes them. One gesture is ONE elupdate (`discrete`, so
  // its own undo step) however many shapes it touched.
  //
  // sel: Map<shapeId, Map<ring, Set<index>>>. `ring` is "exterior" (a digitized
  // shape's outline) or "anchors" (a hand-drawn shape's authored points); the
  // holes work (spec section 6) adds further ring keys, one per hole.
  const RING_EXTERIOR = "exterior";
  const RING_ANCHORS = "anchors";
  let reshape = null;       // { elId, sel }
  let reshapeDrag = null;   // { kind: "ring"|"anchors", elId, startPx, startClient, sel, basis, moving, live: Map|null }
  let marquee = null;       // { startPx, curPx, startClient, add }
  let dragReadout = null;   // { x, y, text } — the dx, dy mm beside the pointer mid-drag

  // The keyboard node cursor (Tab or [ / ] step it, Space toggles that point in
  // the same selection the marquee builds): { shapeId, ring, index } | null.
  let nodeCursor = null;

  function reshapeOn() {
    return !!reshape && !!project && !multiSel && !simActive && project.selectedId === reshape.elId;
  }
  function reshapeSelHas(elId, sid, ring, i) {
    if (!reshape || reshape.elId !== elId) return false;
    const rings = reshape.sel.get(sid);
    const set = rings && rings.get(ring);
    return !!set && set.has(i);
  }
  function reshapeSelCount(rs) {
    let n = 0;
    if (rs) for (const rings of rs.sel.values()) for (const set of rings.values()) n += set.size;
    return n;
  }
  function cloneSel(sel) {
    const out = new Map();
    for (const [sid, rings] of sel) {
      const m = new Map();
      for (const [ring, set] of rings) m.set(ring, new Set(set));
      out.set(sid, m);
    }
    return out;
  }
  function selAdd(sel, sid, ring, i) {
    if (!sel.has(sid)) sel.set(sid, new Map());
    const rings = sel.get(sid);
    if (!rings.has(ring)) rings.set(ring, new Set());
    rings.get(ring).add(i);
  }
  function selRemove(sel, sid, ring, i) {
    const rings = sel.get(sid);
    const set = rings && rings.get(ring);
    if (!set) return;
    set.delete(i);
    if (!set.size) rings.delete(ring);
    if (!rings.size) sel.delete(sid);
  }
  function setReshapeSel(sel) {
    reshape = { ...reshape, sel };
    repaintNodeChrome();
  }
  // The fields a point edit writes (ring overrides; hand-drawn shapes + re-fit).
  // Discard restores exactly these, from the element as it was on entry.
  const RESHAPE_KEYS = ["shapeOverrides", "shapes", "sizeMm", "offsetXMm", "offsetYMm"];
  // Node counts per ring of the Reshape element, as shown. An undo or redo that
  // adds or removes a node changes it, and the point selection (node-list
  // indices) would then name the wrong nodes: it is dropped.
  let reshapeNodeSig = "";
  function nodeSigOf(el) {
    const src = el ? outlinesMmFor(el) : null;
    return src ? src.mm.map((o) => `${o.key || o.id}=${o.nodes ? o.nodes.length : 0}`).join(",") : "";
  }
  function enterReshape(el) {
    if (shapeMove) commitShapeMove();
    reshapeNodeSig = el.type === "digitized" ? nodeSigOf(el) : "";
    const start = {};
    for (const k of RESHAPE_KEYS) start[k] = el[k];
    reshape = { elId: el.id, sel: new Map(), start };
    nodeCursor = null;
    liveMsg = MODE_SAYS.reshapeEnter;
    shapeEditError = "";
    repaintNodeChrome();
  }
  function endReshape() {
    if (!reshape && !reshapeDrag && !marquee) return;
    if (reshape) liveMsg = MODE_SAYS.reshapeDone;
    reshape = null;
    nodeCursor = null;
    reshapeDrag = null;
    marquee = null;
    dragReadout = null;
    if (shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
    repaintNodeChrome();
  }
  // Discard: put the entry-time fields back in ONE patch (one undo step, and the
  // stitches regenerate once), then leave the mode. Nothing changed: just leave.
  function discardReshape() {
    const el = reshape && project ? project.elements.find((x) => x.id === reshape.elId) : null;
    if (el) {
      const patch = discardPatch(el, reshape.start, RESHAPE_KEYS);
      if (Object.keys(patch).length) dispatch("elupdate", { id: el.id, patch, discrete: true });
    }
    endReshape();
    liveMsg = MODE_SAYS.reshapeDiscard;
  }
  // ---- Add hole (2026-11-05, PR 3 of the node-editing work) -----------------
  // "Add hole" (popover row, or the right-click menu inside a digitized shape)
  // enters a draw mode for ONE shape: each click places a vertex, a click on
  // the first vertex (or Enter) closes the ring once it has three, and the
  // closed ring is appended to the shape's holes through the same commit path
  // as every other ring edit (`ringEditOverrides`' `added`). A refusal from
  // boundaryIssues keeps the draft open so Backspace can take a vertex back.
  // Escape, the cross, another element, or another shape ends it with no patch.
  // The vertices are kept in FIELD mm, so a zoom or pan mid-draw cannot move them.
  const HOLE_DRAFT_HINT = "Click to place hole points · click the first point to close · Esc to cancel";
  let holeDraft = null;     // { elId, shapeId, pointsMm: [[x, y], ...] }

  function holeDraftOn() {
    return !!holeDraft && !!project && !multiSel && !simActive && project.selectedId === holeDraft.elId;
  }
  function enterHoleDraft(el, shapeId) {
    if (!el || el.type !== "digitized" || !shapeId || isCapPieceId(shapeId)) return;
    if (shapeMove) commitShapeMove();
    selectedShapeId = shapeId;
    selectedShapeElId = el.id;
    shapeEditError = "";
    holeDraft = { elId: el.id, shapeId, pointsMm: [], cursorMm: null };
    liveMsg = MODE_SAYS.holeEnter;
    if (canvas) canvas.focus({ preventScroll: true });
    repaintNodeChrome();
  }
  function cancelHoleDraft() {
    if (!holeDraft) return;
    holeDraft = null;
    liveMsg = MODE_SAYS.holeCancel;
    if (shapeEditError) shapeEditError = "";
    repaintNodeChrome();
  }
  function fieldPxOfMm(pt) {
    const c = renderResult.toCanvas(pt[0], pt[1]);
    return { x: c.x, y: c.y };
  }
  function mmOfFieldPx(p) {
    const o = renderResult.toCanvas(0, 0), ex = renderResult.toCanvas(1, 0), ey = renderResult.toCanvas(0, 1);
    return [(p.x - o.x) / (ex.x - o.x), (p.y - o.y) / (ey.y - o.y)];
  }
  // The strip: the instruction line in a pill, the cross to its right.
  function holeDraftStrip(ctx) {
    ctx.save();
    ctx.font = "11px system-ui, sans-serif";
    const w = ctx.measureText(HOLE_DRAFT_HINT).width + 12;
    ctx.restore();
    const bx = Math.round(Math.min(Math.max(cssW() / 2 - 20, w / 2 + 4), cssW() - w / 2 - 4 - 26));
    return { bx, w, cross: { x: Math.round(bx + w / 2 + 6), y: 7, w: 18, h: 18 } };
  }
  function holeDraftCrossHit(p) {
    const ctx = canvas && canvas.getContext("2d");
    if (!ctx) return false;
    const b = holeDraftStrip(ctx).cross;
    return p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h;
  }
  function drawHoleDraftChrome(ctx) {
    if (!holeDraftOn() || !renderResult) return;
    const strip = holeDraftStrip(ctx);
    drawBadge(ctx, strip.bx, 16, HOLE_DRAFT_HINT);
    const b = strip.cross;
    ctx.save();
    ctx.fillStyle = "rgba(24, 26, 38, 0.85)";
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(b.x, b.y, b.w, b.h, 4); else ctx.rect(b.x, b.y, b.w, b.h);
    ctx.fill();
    ctx.fillStyle = "#ff8a8a";
    ctx.font = "13px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("✕", b.x + b.w / 2, b.y + b.h / 2 + 0.5);
    ctx.restore();
    if (holeDraft.cursorMm) {
      const c = fieldPxOfMm(holeDraft.cursorMm);
      ctx.save();
      ctx.strokeStyle = "rgba(255, 214, 64, 0.95)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(c.x - 8, c.y); ctx.lineTo(c.x + 8, c.y);
      ctx.moveTo(c.x, c.y - 8); ctx.lineTo(c.x, c.y + 8);
      ctx.stroke();
      ctx.restore();
    }
    const pts = holeDraft.pointsMm.map(fieldPxOfMm);
    if (!pts.length) return;
    ctx.save();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(255, 214, 64, 0.95)";
    ctx.beginPath();
    pts.forEach((q, i) => (i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y)));
    ctx.stroke();
    if (pts.length >= 3) {
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
      ctx.lineTo(pts[0].x, pts[0].y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    for (const q of pts) {
      ctx.fillStyle = "rgba(255, 214, 64, 1)";
      ctx.strokeStyle = "rgba(24, 26, 38, 0.9)";
      ctx.fillRect(q.x - 3.5, q.y - 3.5, 7, 7);
      ctx.strokeRect(q.x - 3.5, q.y - 3.5, 7, 7);
    }
    ctx.restore();
  }
  // Close the ring: needs three vertices. -> true when it committed.
  function closeHoleDraft() {
    const d = holeDraft;
    if (!d || d.pointsMm.length < 3) return false;
    const edit = editableOutlinesPx();
    const el = edit && edit.el;
    if (!el || el.id !== d.elId || el.type !== "digitized") return false;
    const ring = d.pointsMm.map(([x, y]) => [x, y]);
    const ok = commitRingEdits(el, editBasis(edit), new Map(), null, new Map(), new Map([[d.shapeId, [ring]]]));
    if (ok) {
      holeDraft = null;
      liveMsg = MODE_SAYS.holeClosed;
      repaintNodeChrome();
    } else repaintNodeChrome();
    return ok;
  }
  // A press while drawing. -> true when the draft took it.
  function holeDraftPress(p) {
    if (holeDraftCrossHit(p)) { cancelHoleDraft(); return true; }
    const other = pickElement(perElementRects, p.x, p.y);
    if (other && other !== holeDraft.elId) { cancelHoleDraft(); return false; }   // the press selects it as usual
    const pts = holeDraft.pointsMm;
    if (pts.length >= 3) {
      const f = fieldPxOfMm(pts[0]);
      if (Math.hypot(f.x - p.x, f.y - p.y) <= NODE_GRAB_PX) { closeHoleDraft(); return true; }
    }
    // A press on any placed vertex adds nothing (a double-click's second press,
    // or a stray click back on the first point before the ring can close).
    for (const q of pts) {
      const l = fieldPxOfMm(q);
      if (Math.hypot(l.x - p.x, l.y - p.y) < 3) return true;
    }
    shapeEditError = "";
    holeDraft = { ...holeDraft, pointsMm: [...pts, mmOfFieldPx(p)] };
    repaintNodeChrome();
    return true;
  }

  // ---- Move shape (2026-11-05 spec) ------------------------------------------
  // "Move shape" (popover row after Edit points, or the right-click menu inside a
  // digitized shape) translates ONE shape (shell, holes, nodes) as a unit. A
  // left press anywhere on the canvas drags it (outline live, stitches follow on
  // commit through the normal restitch); the arrows move it 0.1 mm (Shift 1 mm).
  // Enter / Done / a selection change commits ONE discrete elupdate; Esc /
  // Discard restore and dispatch nothing. The "edit all similar shapes" tick is
  // ignored: only the grabbed shape moves.
  const MOVE_HINT = "Moving shape · drag or arrow keys · Enter to finish · Esc to cancel";
  let shapeMove = null;     // { elId, shapeId, eb, shell, holes, dx, dy, drag: null | { startClient, startPx, dx0, dy0, armed } }

  // The arguments are unused: a template expression only re-renders for the
  // variables it NAMES, so the markup passes the ones this reads.
  // eslint-disable-next-line no-unused-vars
  function shapeMoveOn(_sm, _project, _multi, _sim) {
    return !!shapeMove && !!project && !multiSel && !simActive && project.selectedId === shapeMove.elId;
  }
  function enterShapeMove(el, shapeId) {
    if (!el || el.type !== "digitized" || !shapeId || isCapPieceId(shapeId)) return;
    const edit = outlinesPxFor(el);
    const shell = edit && edit.mmById.get(shapeId);
    if (!shell) return;
    if (shapeMove) commitShapeMove();
    if (reshape || reshapeDrag || marquee) endReshape();
    cancelHoleDraft();
    selectedShapeId = shapeId;
    selectedShapeElId = el.id;
    shapeEditError = "";
    shapeMove = {
      elId: el.id, shapeId, eb: editBasis(edit),
      ovAtEntry: (el.shapeOverrides || {})[shapeId] || null,
      rowAtEntry: ((el.review && el.review.shapes) || []).find((r) => r && r.id === shapeId) || null,
      shell: shell.map(([x, y]) => [x, y]),
      holes: (edit.holesById.get(shapeId) || []).map((h) => h.map(([x, y]) => [x, y])),
      dx: 0, dy: 0, drag: null,
    };
    liveMsg = MODE_SAYS.moveEnter;
    if (canvas) canvas.focus({ preventScroll: true });
    repaintNodeChrome();
  }
  // True when the shape's override entry or review row is no longer the object
  // the move was entered on.
  function shapeMoveStale(proj) {
    const sm = shapeMove;
    const el = sm && proj && (proj.elements || []).find((x) => x.id === sm.elId);
    if (!el) return false;
    if (((el.shapeOverrides || {})[sm.shapeId] || null) !== sm.ovAtEntry) return true;
    const row = ((el.review && el.review.shapes) || []).find((r) => r && r.id === sm.shapeId) || null;
    return row !== sm.rowAtEntry;
  }
  function endShapeMove() {
    if (!shapeMove) return;
    shapeMove = null;
    liveMsg = MODE_SAYS.moveCancel;
    dragReadout = null;
    setCanvasCursor("default");
    repaintNodeChrome();
  }
  // Commit the pending move as ONE patch (nothing at all on a zero net move).
  function commitShapeMove() {
    const sm = shapeMove;
    if (!sm) return;
    shapeMove = null;
    liveMsg = MODE_SAYS.moveDone;
    dragReadout = null;
    const el = project && (project.elements || []).find((x) => x.id === sm.elId);
    if (el && (Math.abs(sm.dx) > 1e-9 || Math.abs(sm.dy) > 1e-9)) {
      const res = moveShapeOverrides(el, sm.eb, sm.shapeId, sm.shell, sm.holes, sm.dx, sm.dy);
      if (res && res.error) {
        const row = sm.eb.rows.find((r) => r && r.id === sm.shapeId);
        shapeEditError = (row ? shapeMenuName(row) + ": " : "") + res.error;
      } else if (res && res.cur) {
        shapeEditError = "";
        dispatch("elupdate", { id: el.id, patch: { shapeOverrides: res.cur }, discrete: true });
      }
    }
    setCanvasCursor("default");
    repaintNodeChrome();
  }
  function moveShapeBy(dxMm, dyMm) {
    if (!shapeMoveOn() || shapeMove.drag) return;
    shapeMove = { ...shapeMove, dx: shapeMove.dx + dxMm, dy: shapeMove.dy + dyMm };
    repaintNodeChrome();
  }
  // The strip: label pill with Done / Discard to its right.
  function shapeMoveStrip(ctx) {
    ctx.save();
    ctx.font = "11px system-ui, sans-serif";
    const w = ctx.measureText(MOVE_HINT).width + 12;
    ctx.restore();
    const bx = Math.round(Math.min(Math.max(cssW() / 2 - 30, w / 2 + 4), cssW() - w / 2 - 4 - 52));
    const x0 = Math.round(bx + w / 2 + 6);
    return { bx, w, done: { x: x0, y: 7, w: 18, h: 18 }, discard: { x: x0 + 22, y: 7, w: 18, h: 18 } };
  }
  function shapeMoveBtnAt(p) {
    const ctx = canvas && canvas.getContext("2d");
    if (!ctx) return null;
    const s = shapeMoveStrip(ctx);
    for (const k of ["done", "discard"]) {
      const b = s[k];
      if (p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) return k;
    }
    return null;
  }
  function drawShapeMoveChrome(ctx) {
    // setAttribute, not a binding (see the note on data-stale-ids). The centres of
    // Done / Discard in canvas CSS px, so a test can aim at the drawn buttons.
    if (!shapeMoveOn()) {
      if (canvas && canvas.hasAttribute("data-shape-move-btns")) canvas.removeAttribute("data-shape-move-btns");
      return;
    }
    const s = shapeMoveStrip(ctx);
    if (canvas) {
      const btns = JSON.stringify({ done: [s.done.x + s.done.w / 2, s.done.y + s.done.h / 2], discard: [s.discard.x + s.discard.w / 2, s.discard.y + s.discard.h / 2] });
      if (canvas.getAttribute("data-shape-move-btns") !== btns) canvas.setAttribute("data-shape-move-btns", btns);
    }
    drawBadge(ctx, s.bx, 16, MOVE_HINT);
    for (const [k, glyph] of [["done", "✓"], ["discard", "✕"]]) {
      const b = s[k];
      ctx.save();
      ctx.fillStyle = "rgba(24, 26, 38, 0.85)";
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(b.x, b.y, b.w, b.h, 4); else ctx.rect(b.x, b.y, b.w, b.h);
      ctx.fill();
      ctx.fillStyle = k === "done" ? "#7fe08a" : "#ff8a8a";
      ctx.font = "13px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(glyph, b.x + b.w / 2, b.y + b.h / 2 + 0.5);
      ctx.restore();
    }
    if (dragReadout) drawBadge(ctx, dragReadout.x, dragReadout.y, dragReadout.text);
  }
  // The shift a ring of shape `sid` of element `elId` is drawn at (field mm).
  function moveShiftFor(elId, sid) {
    return shapeMove && shapeMove.elId === elId && shapeMove.shapeId === sid ? shapeMove : null;
  }
  function shapeMovePress(e, p) {
    const btn = shapeMoveBtnAt(p);
    if (btn) {
      if (btn === "done") commitShapeMove(); else endShapeMove();
      drawOverlay();
      return;
    }
    canvas.setPointerCapture(e.pointerId);
    shapeMove = { ...shapeMove, drag: { startClient: { x: e.clientX, y: e.clientY }, startPx: p, dx0: shapeMove.dx, dy0: shapeMove.dy, armed: false } };
    setCanvasCursor("grabbing");
  }
  function shapeMoveDrag(e, p) {
    const d = shapeMove.drag;
    if (!d.armed) {
      if (!pastClickDeadZone(d.startClient, { x: e.clientX, y: e.clientY }, CLICK_PX)) return;
      d.armed = true;
    }
    const mm = pxToMmDelta(p.x - d.startPx.x, p.y - d.startPx.y);
    shapeMove = { ...shapeMove, dx: d.dx0 + mm.dx, dy: d.dy0 + mm.dy };
    dragReadout = { x: p.x + 18, y: p.y - 18, text: `${fmtMm(shapeMove.dx)}, ${fmtMm(shapeMove.dy)} mm` };
    repaintNodeChrome();
  }

  // The DOM twin of the canvas strips (keyboard + screen reader): the same
  // actions as real buttons. The arguments feed the reactive statement below.
  $: modeBar = editModeBar({
    move: !!shapeMove && !!project && !multiSel && !simActive && project.selectedId === shapeMove.elId,
    reshape: !!reshape && !!project && !multiSel && !simActive && project.selectedId === reshape.elId,
    holePoints: !!holeDraft && !!project && !multiSel && !simActive && project.selectedId === holeDraft.elId ? holeDraft.pointsMm.length : null,
  });
  function onModeBarAction(e) {
    const id = e.detail.id;
    if (id === "moveDone") commitShapeMove();
    else if (id === "moveCancel") endShapeMove();
    else if (id === "reshapeDone") endReshape();
    else if (id === "reshapeDiscard") discardReshape();
    else if (id === "holeClose") { if (!closeHoleDraft()) liveMsg = MODE_SAYS.holeNeedThree; }
    else if (id === "holeCancel") cancelHoleDraft();
    else if (id === "holeUndo") {
      if (holeDraft && holeDraft.pointsMm.length) {
        shapeEditError = "";
        holeDraft = { ...holeDraft, pointsMm: holeDraft.pointsMm.slice(0, -1) };
        repaintNodeChrome();
      }
    }
    // The bar unmounts with the mode; hand focus back to the field.
    if (canvas) canvas.focus({ preventScroll: true });
    drawOverlay();
  }

  // Strip buttons: Done (tick) and Discard (cross), right of the label.
  function reshapeBtnRects() {
    const cx = cssW() / 2;
    return { done: { x: cx + 30, y: 7, w: 18, h: 18 }, discard: { x: cx + 52, y: 7, w: 18, h: 18 } };
  }
  function reshapeBtnAt(p) {
    const r = reshapeBtnRects();
    for (const k of ["done", "discard"]) {
      const b = r[k];
      if (p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) return k;
    }
    return null;
  }
  // A hand-drawn shape whose anchors the running reshape drag is holding in a
  // working position — drawn from the drag, not from the (stale) element.
  function anchorsLive(el, shapeId) {
    return !!(reshapeDrag && reshapeDrag.kind === "anchors" && reshapeDrag.elId === el.id
      && reshapeDrag.live && reshapeDrag.live.has(shapeId));
  }

  // The point under the pointer, on whichever shape of the element has one
  // there: the NEAREST within the grab radius (hitOverlay's rule on the
  // digitized lane, the same on the hand-drawn one). -> { shapeId, ring, index }
  function reshapeNodeAt(edit, p) {
    const el = edit.el;
    if (el.type === "manual") {
      let best = null;
      for (const s of el.shapes || []) {
        if (!s || s.id == null) continue;
        const ap = authoredPxFor(el, s.id);
        if (!ap) continue;
        ap.anchors.forEach(([x, y], i) => {
          const d = Math.hypot(p.x - x, p.y - y);
          if (d <= ANCHOR_GRAB_PX && (!best || d < best.d)) best = { d, shapeId: s.id, ring: RING_ANCHORS, index: i };
        });
      }
      return best;
    }
    const hit = hitOverlay(liveOutlinesPx(edit), p.x, p.y);
    return hit && hit.kind === "node" ? { shapeId: hit.shapeId, ring: hit.ring == null ? RING_EXTERIOR : hit.ring, index: hit.index } : null;
  }

  // Every point of every shape of the element inside the box (canvas px).
  function reshapeNodesInBox(edit, a, b) {
    const el = edit.el;
    const out = new Map();
    if (el.type === "manual") {
      const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x);
      const y0 = Math.min(a.y, b.y), y1 = Math.max(a.y, b.y);
      for (const s of el.shapes || []) {
        if (!s || s.id == null) continue;
        const ap = authoredPxFor(el, s.id);
        if (!ap) continue;
        ap.anchors.forEach(([x, y], i) => {
          if (x >= x0 && x <= x1 && y >= y0 && y <= y1) selAdd(out, s.id, RING_ANCHORS, i);
        });
      }
      return out;
    }
    // Shells AND hole rings: a box over a seam takes both sides, hole edges too.
    return ringNodesInBox(liveOutlinesPx(edit), a.x, a.y, b.x, b.y);
  }

  // Every point the mode draws, in ring order across rings (the cursor's walk).
  function reshapeNodeList() {
    const edit = reshapeOn() && renderResult ? editableOutlinesPx() : null;
    if (!edit || edit.el.id !== reshape.elId) return [];
    const out = [];
    if (edit.el.type === "manual") {
      for (const s of edit.el.shapes || []) {
        if (!s || s.id == null) continue;
        const ap = authoredPxFor(edit.el, s.id);
        if (ap) ap.anchors.forEach((_, i) => out.push({ shapeId: s.id, ring: RING_ANCHORS, index: i }));
      }
      return out;
    }
    for (const o of liveOutlinesPx(edit)) {
      if (o.open) continue;
      const ring = o.ring == null ? RING_EXTERIOR : o.ring;
      const count = o.nodes ? o.nodes.length : o.points.length;
      for (let k = 0; k < count; k++) out.push({ shapeId: o.id, ring, index: k });
    }
    return out;
  }
  function saidNodeCursor(list) {
    const sel = nodeCursor && reshapeSelHas(reshape.elId, nodeCursor.shapeId, nodeCursor.ring, nodeCursor.index);
    liveMsg = nodeCursorPhrase(list, nodeCursor, !!sel) || "";
    repaintNodeChrome();
  }
  // Tab / [ / ] / Space in the mode. true when the key was taken.
  function reshapeCursorKey(e) {
    if (!reshapeOn() || reshapeDrag || marquee || shapeEdit || nodeEdit) return false;
    if (e.target !== canvas && e.target !== document.body) return false;
    const isTab = e.key === "Tab";
    if (!isTab && e.key !== "[" && e.key !== "]" && e.key !== " ") return false;
    const list = reshapeNodeList();
    if (nodeCursor && !list.some((n) => sameNode(n, nodeCursor))) nodeCursor = null;
    if (e.key === " ") {
      if (!nodeCursor) return false;
      const sel = cloneSel(reshape.sel);
      const c = nodeCursor;
      if (reshapeSelHas(reshape.elId, c.shapeId, c.ring, c.index)) selRemove(sel, c.shapeId, c.ring, c.index);
      else selAdd(sel, c.shapeId, c.ring, c.index);
      setReshapeSel(sel);
      saidNodeCursor(list);
      return true;
    }
    if (!list.length) return false;
    const dir = e.key === "]" || (isTab && !e.shiftKey) ? 1 : -1;
    // Tab with no cursor yet only starts one going forward; going past either
    // end lets focus leave the field rather than trapping it.
    if (isTab && !nodeCursor && dir < 0) return false;
    const next = stepNodeCursor(list, nodeCursor, dir, !isTab);
    if (!next) { nodeCursor = null; repaintNodeChrome(); return false; }
    nodeCursor = next;
    saidNodeCursor(list);
    return true;
  }
  // The cursor's ring, drawn over the point at (x, y): dark casing under cyan.
  function drawNodeCursorRing(ctx, x, y, r) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r + 4, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(10, 22, 30, 0.9)";
    ctx.lineWidth = 4;
    ctx.stroke();
    ctx.strokeStyle = "rgba(60, 220, 255, 1)";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
  }
  function isCursorNode(elId, sid, ring, i) {
    return !!nodeCursor && !!reshape && reshape.elId === elId && nodeCursor.shapeId === sid && nodeCursor.ring === ring && nodeCursor.index === i;
  }

  // The press, in the mode. true when it was handled here; false hands the
  // press to the ordinary branch below (a hand-drawn shape's curve handle or
  // edge keeps its single-drag meaning).
  function reshapePress(e, p, edit) {
    const el = edit.el;
    const node = reshapeNodeAt(edit, p);
    if (node) {
      shapeEditError = "";
      const sel = cloneSel(reshape.sel);
      const has = reshapeSelHas(el.id, node.shapeId, node.ring, node.index);
      if (e.shiftKey) {
        // Shift-click toggles one point; it starts no drag.
        if (has) selRemove(sel, node.shapeId, node.ring, node.index);
        else selAdd(sel, node.shapeId, node.ring, node.index);
        setReshapeSel(sel);
        return true;
      }
      // Double-click a node: corner <-> smooth (digitized lane). The press that
      // inserted this very node a moment ago is not the first half of one.
      if (isDoublePress() && el.type === "digitized" && !recentInsert(node)) {
        toggleNodeAt(edit, node);
        return true;
      }
      // Dragging a point that is not selected first makes it THE selection.
      if (!has) {
        const only = new Map();
        selAdd(only, node.shapeId, node.ring, node.index);
        setReshapeSel(only);
      }
      startReshapeDrag(e, p, edit);
      return true;
    }
    if (el.type === "manual" && selectedShapeId && selectedShapeElId === el.id) {
      const ap = authoredPxFor(el, selectedShapeId);
      const ah = ap ? hitAuthored(ap, p.x, p.y, !isOpenShape(ap.shape)) : null;
      if (ah && ah.kind !== "anchor") return false;
    }
    // Anywhere else: the marquee. (A press on the path that never travels is a
    // click on the path, which inserts a node: see `insertNodeFromClick`, run
    // from the release.)
    canvas.setPointerCapture(e.pointerId);
    marquee = { startPx: p, curPx: p, startClient: { x: e.clientX, y: e.clientY }, add: !!e.shiftKey };
    shapeEditError = "";
    return true;
  }

  // ---- sparse nodes: toggle / insert on the path (2026-11-05) -----------------

  // The node just inserted by a click on the path: a second press on it inside
  // this window is the second half of that same double-click, not a toggle.
  const INSERT_DBLCLICK_MS = 350;
  const INSERT_CLICK_PX = 3;
  let lastInsert = null;   // { key, nodeIndex, t }
  function recentInsert(node) {
    return !!lastInsert && lastInsert.key === ringKey(node.shapeId, node.ring)
      && lastInsert.nodeIndex === node.index && performance.now() - lastInsert.t < INSERT_DBLCLICK_MS;
  }

  // Double-click a node: corner <-> smooth, its two spans rebuilt, one commit.
  // `node` is { shapeId, ring, index } with `index` in the node list.
  function toggleNodeAt(edit, node) {
    const key = ringKey(node.shapeId, node.ring);
    const ring = edit.mmById.get(key);
    const nodes = edit.nodesById.get(key);
    if (!ring || !nodes) return false;
    const t = toggleNode(nodes, node.index);
    const rebuilt = rebuildSpans(ring, t.nodes, t.dirty);
    shapeEditError = "";
    return commitNodeRing(edit.el, edit, key, rebuilt.ring, rebuilt.nodes);
  }

  // Click on the path (pointer-up within INSERT_CLICK_PX of the press, on an
  // edge, no node under it): a CORNER node where the pointer projects onto the
  // edge. The polygon gains one collinear vertex; nothing rebuilds (spec I6).
  // true when it inserted.
  function insertNodeFromClick(edit, p) {
    if (edit.el.type !== "digitized") return false;
    const hit = hitOverlay(liveOutlinesPx(edit), p.x, p.y);
    if (!hit || hit.kind !== "edge") return false;
    const key = ringKey(hit.shapeId, hit.ring);
    const ring = edit.mmById.get(key);
    const nodes = edit.nodesById.get(key);
    if (!ring || !nodes) return false;
    const o = renderResult.toCanvas(0, 0);
    const d = pxToMmDelta(hit.atPx[0] - o.x, hit.atPx[1] - o.y);
    const grown = insertNodeOnPath(ring, nodes, [d.dx, d.dy]);
    shapeEditError = "";
    if (!commitNodeRing(edit.el, edit, key, grown.ring, grown.nodes)) return false;
    lastInsert = { key, nodeIndex: grown.nodeIndex, t: performance.now() };
    return true;
  }

  function startReshapeDrag(e, p, edit) {
    const el = edit.el;
    const sel = reshape.sel;
    let basis;
    if (el.type === "manual") {
      const fit = manualFit(el);
      if (!fit) return;
      // Frozen at press, like nodeEdit's: the fit, the shapes, and which of
      // them started inside the placement box (one already past keeps the old
      // behaviour — nothing is held to a box it was never in).
      const boxOk = new Map();
      for (const sid of sel.keys()) {
        const sh = manualShapeOf(el, sid);
        if (sh) boxOk.set(sid, ringInsideBox(sh, fit, hoopSizeMm(project)));
      }
      basis = { fit, shapes: (el.shapes || []).slice(), boxOk };
    } else {
      // keyed by ring (`ringKey`): the shell is its shape id, a hole `<id>#h<k>`
      const rings = new Map();
      for (const [sid, byRing] of sel) {
        for (const ring of byRing.keys()) {
          const k = ringKey(sid, ring);
          const r = edit.mmById.get(k);
          if (r) rings.set(k, r);
        }
      }
      basis = { ...editBasis(edit), rings };
    }
    canvas.setPointerCapture(e.pointerId);
    reshapeDrag = { kind: el.type === "manual" ? "anchors" : "ring", elId: el.id, startPx: p,
                    startClient: { x: e.clientX, y: e.clientY }, sel, basis, moving: false, live: null, liveNodes: null };
    setCanvasCursor("grabbing");
    repaintNodeChrome();
  }

  // Move the nodes `idx` (indices into the node list) of one ring by (dx, dy)
  // field mm. Bare: EXACTLY those vertices, then the spans at each rebuilt
  // (spec section 5). Alt: the soft pull on the polygon's vertices at those
  // nodes' indices, no rebuild; the nodes keep their indices. -> { ring, nodes }
  function moveNodeSet(ring, nodes, idx, dx, dy, soft) {
    if (soft) {
      const polyIdx = [...idx].filter((k) => nodes[k]).map((k) => nodes[k].i);
      return { ring: moveNodes(ring, polyIdx, dx, dy, { soft: true }), nodes };
    }
    const m = moveNodesExact(ring, nodes, [...idx], dx, dy);
    return rebuildSpans(m.ring, m.nodes, m.dirty);
  }

  function reshapeDragMove(e, p) {
    const d = reshapeDrag;
    // Under CLICK_PX the press is still a click: nothing moves (trackpad jitter).
    if (!d.moving) {
      if (Math.hypot(e.clientX - d.startClient.x, e.clientY - d.startClient.y) < CLICK_PX) return;
      d.moving = true;
    }
    const mm = pxToMmDelta(p.x - d.startPx.x, p.y - d.startPx.y);
    if (d.kind === "ring") {
      const live = new Map();
      const liveNodes = new Map();
      for (const [sid, byRing] of d.sel) {
        for (const [ring, seeds] of byRing) {
          const k = ringKey(sid, ring);
          const base = d.basis.rings.get(k);
          if (!seeds || !seeds.size || !base) continue;
          const moved = moveNodeSet(base, d.basis.nodesById.get(k), seeds, mm.dx, mm.dy, !!e.altKey);
          live.set(k, moved.ring);
          liveNodes.set(k, moved.nodes);
        }
      }
      d.live = live;
      d.liveNodes = liveNodes;
    } else {
      const b = d.basis;
      const q0 = fieldPxToAuthored(b.fit, d.startPx);
      const q1 = fieldPxToAuthored(b.fit, p);
      const delta = { dx: q1.x - q0.x, dy: q1.y - q0.y };
      const clamp = (at) => clampAuthoredToBox(b.fit, at);
      const cand = new Map();
      for (const [sid, rings] of d.sel) {
        const idx = rings.get(RING_ANCHORS);
        const base = b.shapes.find((s) => s && s.id === sid);
        if (!idx || !idx.size || !base) continue;
        cand.set(sid, applyAnchorsDrag(base, idx, delta, clamp));
      }
      // Hold last good, for the WHOLE gesture: one shape bulging past the
      // placement box, or any cut-out leaving the shape it cuts, drops the
      // frame and every shape stays where it last was.
      const box = hoopSizeMm(project);
      let boxHeld = false;
      for (const [sid, c] of cand) if (b.boxOk.get(sid) && !ringInsideBox(c, b.fit, box)) boxHeld = true;
      const cutHeld = !boxHeld && breaksContainment(b.shapes, b.shapes.map((s) => (s && cand.has(s.id) ? cand.get(s.id) : s)));
      if (cutHeld) shapeEditError = CUTOUT_HOLD_HINT;
      if (boxHeld && shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
      if (!boxHeld && !cutHeld) {
        d.live = cand;
        if (shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
      }
    }
    dragReadout = { x: p.x + 18, y: p.y - 18, text: `${fmtMm(mm.dx)}, ${fmtMm(mm.dy)} mm` };
    reshapeDrag = d;
    repaintNodeChrome();
  }

  // Digitized commit: `live` is Map<shapeId, ring in field mm>. Every touched
  // ring goes back to the service's space and through boundaryIssues FIRST; one
  // refusal drops the whole gesture (named by shape) and the shapes snap back.
  // Otherwise ONE elupdate carries a boundary_override per touched shape.
  function commitRingEdits(el, basis, live, removed = null, liveNodes = null, added = null) {
    const res = ringEditOverrides(el, basis, live, removed, liveNodes, added);
    if (res.error) {
      const row = res.sid != null && basis.rows ? basis.rows.find((r) => r && r.id === res.sid) : null;
      shapeEditError = (row ? shapeMenuName(row) + ": " : "") + res.error;
      return false;
    }
    if (!res.cur) return false;
    shapeEditError = "";
    dispatch("elupdate", { id: el.id, patch: { shapeOverrides: res.cur }, discrete: true });
    return true;
  }

  // The overrides a set of edited rings turns into. `live` is Map<ringKey,
  // ring in field mm> (a shell is its shape id, a hole `<id>#h<k>`); `removed`
  // is Map<shapeId, Set<holeIndex>> of holes deleted outright. Per touched
  // shape: `boundary_override` from the shell when the SHELL moved, and
  // `holes_override` from ALL of the shape's current holes when a hole did
  // (this gesture, or an earlier one: once a shape carries a pending
  // `holes_override` every later edit keeps sending the full set). An
  // exterior-only edit on a shape with no pending holes_override therefore
  // stays byte-identical on the wire to before v1.9. Untouched holes go back
  // out as they came (the pending override, else the review's `holesFull`),
  // not through the field round trip. boundaryIssues runs on every touched
  // shape with its holes; one refusal drops the whole gesture.
  //
  // `liveNodes` (2026-11-05): Map<ringKey, node list> for the rings the NODE
  // editor rewrote. When given, every touched shape also gets `nodes`
  // ({ shell, holes }): the live list for a ring that has one, else the list
  // the ring was shown with (`basis.nodesById`), which is how seeds are
  // committed alongside the polygon on the first node edit. When null, the
  // writer is not the node editor (Simplify) and `nodes` is DELETED from the
  // entry: its indices would mean nothing against the new polygon (spec 2).
  // -> { cur } | { error, sid }
  function ringEditOverrides(el, basis, live, removed = null, liveNodes = null, added = null) {
    return ringEditOverridesLib(el, basis, live, removed, liveNodes, added);
  }

  // Hand-drawn commit: the shapes as they now stand, through the re-fit rule in
  // ONE patch. A refusal (an invalid shape, a cut-out out of its shape) drops
  // the whole gesture and names the shape.
  function commitAnchorEdits(el, fit, shapes) {
    if (!shapes.length || !fit) return false;
    const patch = editedShapesPatch(el, fit, shapes);
    if (patch.error) {
      shapeEditError = shapes.length > 1 && patch.shapeId != null
        ? `Shape ${String(patch.shapeId).replace(/^s/, "")}: ${patch.error}` : patch.error;
      return false;
    }
    shapeEditError = "";
    dispatch("elupdate", { id: el.id, patch, discrete: true });
    return true;
  }

  // Arrow keys: the selected points move 0.1 mm (Shift 1 mm) in field mm, each
  // press its own committed undo step. EXACTLY the chosen points on a digitized
  // ring — a nudge is the precision tool, and a falloff around 0.1 mm would
  // only blur it (a drag keeps the 3 mm neighbourhood).
  function nudgeReshape(dxMm, dyMm) {
    const edit = editableOutlinesPx();
    const el = edit && edit.el;
    if (!el || !reshape || el.id !== reshape.elId) return;
    shapeEditError = "";
    if (el.type === "manual") {
      const fit = manualFit(el);
      if (!fit) return;
      const delta = { dx: dxMm / fit.mmPerPx, dy: -dyMm / fit.mmPerPx };
      const clamp = (at) => clampAuthoredToBox(fit, at);
      const out = [];
      for (const [sid, rings] of reshape.sel) {
        const sh = manualShapeOf(el, sid);
        const idx = rings.get(RING_ANCHORS);
        if (!sh || !idx || !idx.size) continue;
        const moved = applyAnchorsDrag(sh, idx, delta, clamp);
        if (moved !== sh) out.push(moved);
      }
      if (out.length && commitAnchorEdits(el, fit, out)) liveMsg = reshapeMovedPhrase();
      return;
    }
    const live = new Map();
    const liveNodes = new Map();
    for (const [sid, rings] of reshape.sel) {
      for (const [ring, seeds] of rings) {
        const k = ringKey(sid, ring);
        const base = edit.mmById.get(k);
        if (!seeds || !seeds.size || !base) continue;
        const moved = moveNodeSet(base, edit.nodesById.get(k), seeds, dxMm, dyMm, false);
        live.set(k, moved.ring);
        liveNodes.set(k, moved.nodes);
      }
    }
    if (live.size && commitRingEdits(el, editBasis(edit), live, null, liveNodes)) liveMsg = reshapeMovedPhrase();
  }
  function reshapeMovedPhrase() {
    const n = reshapeSelCount(reshape);
    return `${n} point${n === 1 ? "" : "s"} moved`;
  }

  // Delete / Backspace on the selection: per ring, never below the floor. A
  // ring at the floor refuses with the hand-drawn lane's wording and loses
  // nothing; the others go in ONE patch.
  function deleteReshapeSelection() {
    const edit = editableOutlinesPx();
    const el = edit && edit.el;
    if (!el || !reshape || el.id !== reshape.elId || !reshapeSelCount(reshape)) return false;
    let refused = "";
    const done = [];
    if (el.type === "manual") {
      const fit = manualFit(el);
      if (!fit) return false;
      const out = [];
      for (const [sid, rings] of reshape.sel) {
        const sh = manualShapeOf(el, sid);
        const idx = rings.get(RING_ANCHORS);
        if (!sh || !idx || !idx.size) continue;
        const smaller = removeAnchors(sh, idx);
        if (!smaller) refused = anchorFloorMessage(sh);
        else { out.push(smaller); done.push(sid); }
      }
      if (out.length && !commitAnchorEdits(el, fit, out)) return true;
    } else {
      const live = new Map();
      const liveNodes = new Map();
      const removed = new Map();   // sid -> holes deleted outright
      for (const [sid, rings] of reshape.sel) {
        for (const [ring, idx] of rings) {
          const k = ringKey(sid, ring);
          const base = edit.mmById.get(k);
          const nodes = edit.nodesById.get(k);
          if (!idx || !idx.size || !base || !nodes) continue;
          // Every node of one hole ring selected: the hole itself goes (the
          // shape is solid there). The exterior never does this; at the floor
          // it refuses like any ring.
          if (ring !== RING_EXTERIOR && idx.size >= nodes.length) {
            if (!removed.has(sid)) removed.set(sid, new Set());
            removed.get(sid).add(ring);
            done.push(sid);
            continue;
          }
          // Spec section 4: the removed nodes go, each merged span rebuilds; a
          // ring at the 3-node floor refuses and loses nothing.
          const del = deleteNodes(base, nodes, idx);
          if (!del) refused = "A shape needs at least 3 points.";
          else {
            const rebuilt = rebuildSpans(del.ring, del.nodes, del.dirty);
            live.set(k, rebuilt.ring);
            liveNodes.set(k, rebuilt.nodes);
            done.push(sid);
          }
        }
      }
      if ((live.size || removed.size) && !commitRingEdits(el, editBasis(edit), live, removed, liveNodes)) return true;
    }
    if (done.length) {
      // The removed indices are gone: those shapes' selections go with them.
      const sel = cloneSel(reshape.sel);
      for (const sid of done) sel.delete(sid);
      setReshapeSel(sel);
    }
    if (refused) shapeEditError = refused;
    return true;
  }

  function drawReshapeChrome(ctx) {
    if (!reshapeOn() || holeDraftOn()) return;
    // The strip: an instrument, drawn like the rotate badge, never a warning.
    const rb = reshapeBtnRects();
    drawBadge(ctx, cssW() / 2 - 24, 16, "Editing points");
    for (const [k, glyph] of [["done", "✓"], ["discard", "✕"]]) {
      const b = rb[k];
      ctx.save();
      ctx.fillStyle = "rgba(24, 26, 38, 0.85)";
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(b.x, b.y, b.w, b.h, 4); else ctx.rect(b.x, b.y, b.w, b.h);
      ctx.fill();
      ctx.fillStyle = k === "done" ? "#7fe08a" : "#ff8a8a";
      ctx.font = "13px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(glyph, b.x + b.w / 2, b.y + b.h / 2 + 0.5);
      ctx.restore();
    }
    if (marquee) {
      const x = Math.min(marquee.startPx.x, marquee.curPx.x), y = Math.min(marquee.startPx.y, marquee.curPx.y);
      const w = Math.abs(marquee.curPx.x - marquee.startPx.x), h = Math.abs(marquee.curPx.y - marquee.startPx.y);
      ctx.save();
      ctx.fillStyle = "rgba(255, 214, 64, 0.08)";
      ctx.fillRect(x, y, w, h);
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(255, 214, 64, 0.95)";
      ctx.strokeRect(Math.round(x) + 0.5, Math.round(y) + 0.5, w, h);
      ctx.restore();
    }
    if (dragReadout) drawBadge(ctx, dragReadout.x, dragReadout.y, dragReadout.text);
  }

  function manualFit(el) {
    const pe = peById[el.id];
    return pe && pe.design && pe.design.fit ? pe.design.fit : null;
  }
  function manualShapeOf(el, shapeId) {
    return (el.shapes || []).find((s) => s && s.id === shapeId) || null;
  }
  // The selected hand-drawn shape's authored geometry in CANVAS px, from the
  // live drag if one is running, else from the element.
  function authoredPxFor(el, shapeId) {
    if (!el || el.type !== "manual") return null;
    const fit = manualFit(el);
    const dragged = reshapeDrag && reshapeDrag.kind === "anchors" && reshapeDrag.elId === el.id && reshapeDrag.live
      ? reshapeDrag.live.get(shapeId) : null;
    const shape = dragged || (nodeEdit && nodeEdit.shapeId === shapeId && nodeEdit.elId === el.id ? nodeEdit.live : manualShapeOf(el, shapeId));
    if (!fit || !shape || !renderResult || !renderResult.toCanvas) return null;
    const mm = authoredInFieldMm(shape, fit);
    const toPx = ([x, y]) => { const c = renderResult.toCanvas(x, y); return [c.x, c.y]; };
    const controls = {};
    for (const k of Object.keys(mm.controls)) controls[k] = toPx(mm.controls[k]);
    const ap = { anchors: mm.anchors.map(toPx), controls, handles: mm.handles.map(toPx), fit, shape };
    // A column's two rails (the width the spine alone does not show). Built
    // from the same `shape` as the anchors, so mid-drag they follow the drag.
    if (mm.rails) ap.rails = { a: mm.rails.a.map(toPx), b: mm.rails.b.map(toPx) };
    return ap;
  }
  // Canvas px -> authored canvas px, through the frozen fit. The canvas
  // basis is read off toCanvas for the same reason pxToMmDelta does.
  function fieldPxToAuthored(fit, p) {
    const o = renderResult.toCanvas(0, 0), ex = renderResult.toCanvas(1, 0), ey = renderResult.toCanvas(0, 1);
    const xMm = (p.x - o.x) / (ex.x - o.x), yMm = (p.y - o.y) / (ey.y - o.y);
    return fieldMmToPx(fit, [xMm, yMm]);
  }
  // An authored point held inside the garment placement box (hoopSizeMm IS the
  // box, centred on the origin) — see clampMmToBox for the ruling.
  function clampAuthoredToBox(fit, at) {
    const box = hoopSizeMm(project);
    if (!(box.wMm > 0 && box.hMm > 0)) return at; // no garment: nothing to clamp to
    return fieldMmToPx(fit, clampMmToBox(pxToFieldMm(fit, at), box));
  }
  // Commits an edited hand-drawn shape through the re-fit rule, so nothing
  // that was not edited moves. An invalid shape is refused with the reason
  // and the element is left as it was (the live drag is simply dropped).
  function commitNodeEdit(el, edited) {
    const fit = nodeEdit ? nodeEdit.basis.fit : manualFit(el);
    if (!fit) return false;
    const patch = editedElementPatch(el, fit, edited.id, edited);
    if (patch.error) { shapeEditError = patch.error; return false; }
    shapeEditError = "";
    dispatch("elupdate", { id: el.id, patch });
    return true;
  }
  // drawOverlay paints ON TOP of the last render without clearing it, so
  // node chrome that MOVES or DISAPPEARS (a node drag's live outline, a
  // focus ring dropped) needs the preview re-rendered underneath, or every
  // frame stays on the canvas — measured: a node drag left a smear of amber
  // outlines. One rAF-coalesced view repaint (the zoom/pan path), which ends
  // in drawOverlay.
  function repaintNodeChrome() {
    scheduleViewRepaint();
  }
  // The anchor a Delete would remove — only while its shape is still the
  // selected one (a stale focus must never delete a point on another shape).
  function liveFocusedAnchor() {
    if (!focusedAnchor) return null;
    if (focusedAnchor.elId !== selectedShapeElId || focusedAnchor.shapeId !== selectedShapeId) return null;
    return focusedAnchor;
  }
  // The fewest anchors a hand-drawn shape can have, and what to say there: a
  // closed shape needs three to enclose anything, a column's open spine two.
  function anchorFloor(shape) {
    return isOpenShape(shape) ? 2 : 3;
  }
  function anchorFloorMessage(shape) {
    if (isRun(shape)) return "A line needs at least 2 points.";
    return isColumn(shape) ? "A column needs at least 2 points." : "A shape needs at least 3 points.";
  }
  // Removes one anchor of a hand-drawn shape: the floor message at the floor
  // (per kind), else the re-fit patch. Shared by Delete and the menu item.
  function removeAnchorOf(elId, shapeId, index) {
    const el = project && (project.elements || []).find((x) => x.id === elId);
    const shape = el && manualShapeOf(el, shapeId);
    if (!shape) return false;
    // A stale index (an undo of an insert shrank the shape under the focus)
    // removes nothing and drops the focus rather than removing some other point.
    if (!(index >= 0 && index < (shape.points || []).length)) {
      focusedAnchor = null;
      repaintNodeChrome();
      return false;
    }
    const smaller = removeAnchor(shape, index);
    if (!smaller) { shapeEditError = anchorFloorMessage(shape); return false; }
    return commitNodeEdit(el, smaller);
  }
  // The fabric a column's width note is quoted on (generate.js).
  $: popFabric = columnNoteFabric(project && project.garmentId, project && project.fabricProfile);
  // `peById` is named here on purpose: a column's width row reads the fit, and
  // a `$:` only tracks what the statement itself reads — through manualFit()
  // alone the width would stay stale after the regenerate that follows an edit.
  $: popModel = shapePop && selectedShapeId && project && selectedShapeElId === project.selectedId
    ? popoverModel({
        element: selectedShapeElement(), shapeId: selectedShapeId,
        fit: (peById[project.selectedId] && peById[project.selectedId].design && peById[project.selectedId].design.fit) || null,
        fabric: popFabric,
        similar: similarFor(selectedShapeElement(), selectedShapeId),
        reshaping: !!reshape && reshape.elId === project.selectedId,
        pointsWas: simplifiedFrom && simplifiedFrom.shapeId === selectedShapeId ? simplifiedFrom.from : null,
      })
    : null;
  // "Apply to all similar shapes": the shapes like the selected one (see
  // lib/similarShapes.js), only on a digitized element — the other lanes have
  // no such thing as a near-identical sibling to sweep up.
  function similarFor(el, shapeId) {
    return el && el.type === "digitized" && !isCapPieceId(shapeId) ? similarShapeIds(el, shapeId) : null;
  }
  // The box is per selection: it clears when the shape changes or the popover
  // closes, so a tick made for the stars cannot reach the next shape picked.
  let applyToSimilar = false;
  let similarKey = null;
  $: syncSimilar(shapePop ? selectedShapeId : null);
  function syncSimilar(key) {
    if (key === similarKey) return;
    similarKey = key;
    applyToSimilar = false;
    simplifiedFrom = null;
  }
  // `Points: 500 -> 87` after a Simplify: the count before the pick, for the
  // shape it ran on, until the popover closes or another shape is picked.
  let simplifiedFrom = null;
  $: if (canvas) { applyToSimilar; scheduleViewRepaint(); }
  // What the group edit keys act on: the popover's per-shape overrides. Delete
  // and Edit points are actions, not changes, and never go to the group.
  const GROUP_KEYS = new Set(["stitchType", "color", "border", "angle", "underlay"]);
  // A shape that stopped existing (deleted, or gone in a new result) closes
  // it. Deliberately NOT closeShapePop(): nobody pressed anything here, and
  // the change may have come from the side panel, whose focus must not be
  // pulled back to the canvas. The assignment sits in a function on purpose:
  // written inline, `shapePop = null` makes this statement a writer of
  // `shapePop`, which `popModel` reads, and Svelte refuses to compile the
  // pair (reactive_declaration_cycle).
  $: if (shapePop && !popModel) dropStalePop();
  function dropStalePop() {
    shapePop = null;
  }

  // The element the selected shape belongs to — which, by the invariant on
  // selectedShapeElId, is the selected element. Null when no shape is
  // selected, or when the invariant does not hold (a selection change the
  // `$:` block has not caught up with yet): nothing acts on a shape then.
  function selectedShapeElement() {
    if (!selectedShapeId || !selectedShapeElId || !project) return null;
    if (project.selectedId !== selectedShapeElId) return null;
    return (project.elements || []).find((x) => x.id === selectedShapeElId) || null;
  }

  function openShapePop(e) {
    if (!canvas || !hoopEl) return;
    const r = canvas.getBoundingClientRect();
    const hb = hoopEl.getBoundingClientRect();
    hoopBounds = { w: hb.width, h: hb.height };
    const el = selectedElement();
    // `elementId` pins the dialog to the element it was opened on: a
    // selection change closes it rather than re-aiming it (the preset model
    // ignores shapeId, so a re-aimed colour pick would land on another element).
    shapePop = { x: e.clientX - r.left, y: e.clientY - r.top, elementId: el ? el.id : null };
    // A spot the user dragged the dialog to holds for later shapes of the SAME
    // element (that is the point of moving it); another element opens at the
    // click again. Session only — never saved with the project.
    if (popPosition && popPosition.elementId !== shapePop.elementId) popPosition = null;
  }
  let popPosition = null;   // null | { x, y, elementId } in .hoop px

  // Every user-driven close (Escape, an outside press, Delete, Edit points, a
  // click off every shape) hands keyboard focus back to the canvas, so the
  // arrow-key nudge and Delete keep working without a click to re-focus it.
  function closeShapePop() {
    shapePop = null;
    if (canvas) canvas.focus({ preventScroll: true });
  }

  // Which shape of `el` a canvas point is on or inside — the outline the
  // point is ON wins, else the smallest ring it is INSIDE (a counter beats
  // its surround). Hidden and deleted shapes are not offered.
  function shapeAtPoint(el, p) {
    const edit = outlinesPxFor(el);
    if (!edit) return null;
    const live = liveOutlinesPx(edit);
    return hitOverlay(live, p.x, p.y) || hitShapeInterior(live, p.x, p.y);
  }

  // The outlines of an `outlinesPxFor` result that a pointer may hit: hidden
  // (stitched:false) and deleted shapes stay in `edit.outlines` for transform
  // stability, but they are not drawn, so they must not be grabbable either.
  function liveOutlinesPx(edit) {
    const hidden = hiddenShapeIds(edit.el, edit.rows);
    return edit.outlines.filter((o) => !hidden.has(o.id));
  }

  async function onPopChange(e) {
    const el = selectedShapeElement();
    if (!el) return;
    const { key, value } = e.detail;
    const shapeId = selectedShapeId;
    const elFit = el.type === "manual" ? manualFit(el) : null;
    // Ticked: the same edit on every shape like this one, as ONE patch (one
    // undo step). Worked out against the element as it is now.
    const group = applyToSimilar && popModel && popModel.similar && el.type === "digitized" && GROUP_KEYS.has(key)
      ? similarShapeIds(el, shapeId) : [];
    let patch = group.length > 1
      ? similarOverridesPatch(el, group, key, value)
      : popoverPatch({ element: el, shapeId, fit: elFit }, key, value);
    if (!patch && key === "color" && el.type === "digitized") {
      // A getter bound to THIS element's id, not to "whatever is selected":
      // the patch is rebuilt against the element as it stands once the thread
      // chart has loaded (so an edit made during the load is not reverted),
      // and a selection change during the load cannot aim it at another one.
      const live = () => (project && (project.elements || []).find((x) => x.id === el.id)) || null;
      patch = await recolorPatch({ element: live, shapeId }, value);
      if (!live()) return; // the element went away while the chart loaded
      if (patch && group.length > 1) {
        // The chart lookup answered for this shape; the group gets the same
        // thread, over the shapes like it in the element as it stands now.
        const one = patch.shapeOverrides[shapeId] || {};
        const now = live();
        patch = similarOverridesPatch(now, similarShapeIds(now, shapeId), "recolor",
          { thread_index: one.thread_index, rgb: one.rgb });
      }
    }
    if (!patch) {
      if (key === "color") shapeEditError = "Couldn't match that color to the job's thread chart.";
      return;
    }
    if (key === "widthMm" && el.type === "manual" && patch.shapes) {
      // A column's rail ring is what the engine fits, so a new width changes
      // the bbox: commit through the re-fit rule, like a node edit, so nothing
      // else moves. A width the spine cannot carry (the rails fold over at a
      // bend) is refused with the reason and the element is left as it was.
      // shapeProblems is O(n^2) on a column — fine here, once per commit.
      const wide = patch.shapes.find((sh) => sh && sh.id === shapeId);
      const issues = wide ? shapeProblems(wide) : ["Nothing to fit."];
      if (issues.length) { shapeEditError = issues[0]; return; }
      const held = refitShapesPatch(el, elFit, patch.shapes);
      if (held.error) { shapeEditError = held.error; return; }
      shapeEditError = "";
      patch = held;
    }
    if (key === "cutOut" && el.type === "manual" && patch.shapes) {
      // A cut-out emits no region, so the switch can change the bbox the engine
      // fits — a stray shape marked Cut out used to make the rest re-fit and
      // jump. The hoop's rule (an edit never moves what was not edited) covers
      // the switch too: hold the scale and the position, as a node edit does.
      const fit = manualFit(el);
      if (fit) {
        const held = refitShapesPatch(el, fit, patch.shapes);
        if (!held.error) patch = held;
      }
    }
    dispatch("elupdate", { id: el.id, patch });
  }

  function onPopAction(e) {
    const el = selectedShapeElement();
    if (!el) return;
    const { key } = e.detail;
    if (key === "simplify" && el.type === "digitized") {
      // Ticked: every similar shape on its OWN ring, one patch, one undo step.
      const group = applyToSimilar && popModel && popModel.similar ? similarShapeIds(el, selectedShapeId) : [];
      const res = simplifyShapes(el, group.length > 1 ? group : [selectedShapeId], e.detail.tol);
      if (res && res.changed && res.from.has(selectedShapeId)) {
        simplifiedFrom = { shapeId: selectedShapeId, from: res.from.get(selectedShapeId) };
      }
      return;
    }
    if (key === "delete") {
      const patch = popoverPatch({ element: el, shapeId: selectedShapeId }, "delete");
      closeShapePop();
      if (patch) dispatch("elupdate", { id: el.id, patch });
      selectedShapeId = null;
      selectedShapeElId = null;
      focusedAnchor = null;
      drawOverlay();
      return;
    }
    if ((key === "toColumn" || key === "toRun") && el.type === "manual") {
      // Run <-> column (ruling 8): the spine stays as drawn; a new column is
      // 4.0 mm at the fit it is in, and the re-fit rule holds everything else
      // still (the rails widen the bbox the engine fits). The popover stays
      // open on the same shape, now the other kind.
      const patch = convertOpenShape(el, manualFit(el), selectedShapeId, key === "toColumn" ? "column" : "run", null);
      if (patch.error) { shapeEditError = patch.error; return; }
      shapeEditError = "";
      dispatch("elupdate", { id: el.id, patch });
      return;
    }
    if (key === "addHole" && el.type === "digitized") {
      closeShapePop();
      enterHoleDraft(el, selectedShapeId);
      drawOverlay();
      return;
    }
    if (key === "moveShape" && el.type === "digitized") {
      closeShapePop();
      enterShapeMove(el, selectedShapeId);
      drawOverlay();
      return;
    }
    if (key === "editPoints") {
      // Every lane: enters Reshape mode for this element (or leaves it, when
      // the action reads "Done"). The shape stays selected, so a single node
      // still drags straight away outside the mode.
      closeShapePop();
      if (reshape && reshape.elId === el.id) endReshape();
      else enterReshape(el);
      drawOverlay();
    }
  }

  // The canvas transform is an axis-aligned scale+translate, but the y axis
  // flips (field mm are +y up, canvas px are +y down). Rather than hard-code
  // that sign — and re-derive it wrongly the first time preview.js changes —
  // read the basis straight off `toCanvas`.
  function pxToMmDelta(dxPx, dyPx) {
    const o = renderResult.toCanvas(0, 0);
    const ex = renderResult.toCanvas(1, 0);
    const ey = renderResult.toCanvas(0, 1);
    const sx = ex.x - o.x;
    const sy = ey.y - o.y;
    if (Math.abs(sx) < 1e-9 || Math.abs(sy) < 1e-9) return { dx: 0, dy: 0 };
    return { dx: dxPx / sx, dy: dyPx / sy };
  }

  // The three element types that carry per-shape geometry the field can
  // outline and address (2026-09-29 spec §4). `digitized` shapes come from
  // the service's review payload and need shapeOverlay's bbox fit;
  // `manual` and `shape` (preset) elements come from the browser engine's own
  // `shapeOutlines`, already in field mm.
  const SHAPE_LANES = new Set(["digitized", "manual", "shape"]);

  // Field-mm outlines + review rows for one element, whatever its lane.
  // `rows` is [] on the manual lanes: they have no review payload, no hidden
  // shapes and no pending boundary edits.
  function outlinesMmFor(el) {
    if (!el || !SHAPE_LANES.has(el.type)) return null;
    const pe = peById[el.id];
    if (!pe) return null;
    if (el.type === "digitized") {
      const rows = digitizedRows(el);
      if (!rows || !pe.bboxMm) return null;
      return {
        rows,
        // Sparse nodes (2026-11-05): every ring carries its node list, the stored
        // one when valid, else seeds (never written until a node edit commits).
        mm: withNodes(shapeOutlinesInFieldMm(rows, pe.bboxMm, el.rotationDeg || 0, pendingBoundaries(el), pendingHoles(el)), el.shapeOverrides),
        // The silhouette cap, one open polyline per stretch: selectable like a
        // shape (see lib/capPieces.js), never editable as one.
        caps: capOutlinesMm(el, pe.design),
      };
    }
    const mm = designOutlinesInFieldMm(pe.design);
    // A cut-out emits no region, so the engine has no outline for it: the
    // field builds one from the authored ring through the same fit, after the
    // engine's, so hitShapeInterior's smallest-ring rule picks the cut-out
    // over the shape it sits in. One that cuts nothing is listed too — it has
    // to stay clickable to be fixed or deleted (2026-09-30 spec §5).
    const fit = el.type === "manual" ? manualFit(el) : null;
    return { rows: [], mm: fit ? mm.concat(cutOutOutlinesInFieldMm(el.shapes, fit)) : mm };
  }

  function holesByShape(mm) {
    const out = new Map();
    for (const o of mm) {
      if (o.ring == null) continue;
      if (!out.has(o.id)) out.set(o.id, []);
      out.get(o.id)[o.ring] = o.points;
    }
    return out;
  }

  // The outlines of ONE shape-bearing element, in canvas px — what the pointer
  // hit-tests against. The left-click editor only ever asks for the selected
  // element's (`editableOutlinesPx`: the others' outlines are there to show
  // what was found, not to be grabbed); the right-click menu asks for the
  // element under the pointer, selected or not, because a per-shape command
  // starts by saying which shape it means.
  function outlinesPxFor(el) {
    if (!renderResult || !renderResult.toCanvas) return null;
    const src = outlinesMmFor(el);
    if (!src) return null;
    const pe = peById[el.id];
    return {
      el,
      rows: src.rows,
      pe,
      outlines: src.mm.map((o) => {
        const key = o.key || o.id;
        const out = {
          id: o.id,
          key,
          points: ((reshapeDrag && reshapeDrag.kind === "ring" && reshapeDrag.elId === el.id && reshapeDrag.live && reshapeDrag.live.get(key))
            || (liveRing && liveRing.key === key ? liveRing.points : o.points))
            .map(([x, y]) => {
              const mv = moveShiftFor(el.id, o.id);
              const c = renderResult.toCanvas(x + (mv ? mv.dx : 0), y + (mv ? mv.dy : 0));
              return [c.x, c.y];
            }),
          cutOut: !!o.cutOut,
        };
        if (o.ring != null) out.ring = o.ring;
        if (o.nodes) out.nodes = liveNodesOf(el, key, o);
        return out;
      }),
      // Keyed by ring (`ringKey`): a shell is its shape id, a hole `<id>#h<k>`.
      mmById: new Map(src.mm.map((o) => [o.key || o.id, o.points])),
      // The base node lists, same keys (indices into `mmById`'s rings).
      nodesById: new Map(src.mm.filter((o) => o.nodes).map((o) => [o.key || o.id, o.nodes])),
      // Each digitized shape's interior rings, in field mm, in index order.
      holesById: holesByShape(src.mm),
      caps: (src.caps || []).map((o) => ({
        id: o.id,
        open: true,
        points: o.points.map(([x, y]) => {
          const c = renderResult.toCanvas(x, y);
          return [c.x, c.y];
        }),
      })),
    };
  }

  // The cap stretch under the pointer, if any (see the press handler for how
  // it shares an edge with the outer shape's own outline).
  function capHitAt(edit, p) {
    const hidden = hiddenShapeIds(edit.el, edit.rows);
    const live = (edit.caps || []).filter((o) => !hidden.has(o.id));
    return live.length ? hitOverlay(live, p.x, p.y) : null;
  }

  function editableOutlinesPx() {
    return outlinesPxFor(selectedElement());
  }

  // Shapes that are not drawn and not addressable: the ones the user turned
  // off in review, and the ones deleted there (a deleted shape stays in
  // `review.shapes` so it is restorable from the Layers list).
  function hiddenShapeIds(el, rows) {
    return new Set([
      ...(rows || []).filter((r) => r && r.stitched === false).map((r) => r.id),
      ...(el.deletedShapeIds || []),
    ]);
  }

  // Commits the working ring through the SAME shapeOverrides path
  // DigitizePanel's own editor uses, so an edit made here is indistinguishable
  // downstream from one made there — including re-digitize carry-forward.
  // The exact inputs the FORWARD fit used, frozen at drag start.
  //
  // `commitShapeEdit` has to invert that fit. If it re-read `rows`/`bboxMm`
  // at commit time instead, an auto-restitch landing mid-drag would replace
  // `review` underneath and the inverse would run against a different source
  // bbox than the forward pass did — the edit would land somewhere other than
  // the pointer, silently. Freezing the basis makes a drag self-consistent no
  // matter what changes beneath it; a stale basis at worst produces an edit
  // against the geometry the user was actually looking at, which is the
  // correct answer anyway.
  function editBasis(edit) {
    return {
      rows: edit.rows,
      bboxMm: edit.pe.bboxMm,
      rotationDeg: edit.el.rotationDeg || 0,
      // The node lists the rings were shown with (frozen with them: a node's
      // index only means something against the ring it was read from).
      nodesById: edit.nodesById,
    };
  }

  // The node list to draw / hit for ring `key`: the running gesture's, when it
  // has one, else the list the ring was shown with.
  function liveNodesOf(el, key, o) {
    if (reshapeDrag && reshapeDrag.kind === "ring" && reshapeDrag.elId === el.id
        && reshapeDrag.liveNodes && reshapeDrag.liveNodes.has(key)) return reshapeDrag.liveNodes.get(key);
    if (liveRing && liveRing.key === key && liveRing.nodes) return liveRing.nodes;
    return o.nodes;
  }

  // One ring's edit as a patch: the ring and its node list (already rebuilt)
  // through the same commit path as every other point edit. -> true if committed.
  function commitNodeRing(el, edit, key, ring, nodes) {
    return commitRingEdits(el, editBasis(edit), new Map([[key, ring]]), null, new Map([[key, nodes]]));
  }

  function commitShapeEdit() {
    if (!shapeEdit || !liveRing) return;
    const el = project.elements.find((x) => x.id === shapeEdit.elId);
    const basis = shapeEdit.basis;
    if (!el || !basis || !basis.rows || !basis.bboxMm) return;
    // A drag that ended where it began (zero net delta) is not an edit.
    const was = shapeEdit.ring;
    if (was && was.length === liveRing.points.length
        && liveRing.points.every((q, i) => q[0] === was[i][0] && q[1] === was[i][1])) return;

    // Same validation the panel editor runs before it will save: a
    // self-intersecting or pinched ring, or a hole poking out of the shell, is
    // rejected here rather than sent for the service to 400 on.
    const nodes = liveRing.nodes || (basis.nodesById && basis.nodesById.get(liveRing.key)) || null;
    const res = ringEditOverrides(el, basis, new Map([[liveRing.key, liveRing.points]]), null,
      nodes ? new Map([[liveRing.key, nodes]]) : null);
    if (res.error) {
      shapeEditError = res.error;
      return;
    }
    if (!res.cur) return;
    shapeEditError = "";
    dispatch("elupdate", { id: el.id, patch: { shapeOverrides: res.cur } });
  }

  // Simplify points (spec 2026-11-03 section 5): each shape in `ids` is thinned
  // on its OWN current ring (its pending boundary_override, else outlineFull) at
  // `tolMm`, through commitShapeEdit's rules: field mm -> service mm per ring,
  // boundaryIssues first, one refused ring drops the whole gesture and names
  // the shape, ONE elupdate patch for all. A ring already at or under the
  // tolerance commits nothing. -> { changed, from: Map<id, countBefore> } or
  // null when it did not run.
  function simplifyShapes(el, ids, tolMm) {
    const edit = outlinesPxFor(el);
    if (!edit || !edit.pe || !edit.pe.bboxMm || !(tolMm > 0)) return null;
    const from = new Map();
    const live = new Map();
    for (const id of ids) {
      const ring = edit.mmById.get(id);
      if (!ring) continue;
      // The shell and every hole ring simplify at the same tolerance
      // (`simplifyRing` is ring-agnostic); a ring already at tolerance is left.
      let any = false;
      const next = simplifyRing(ring, tolMm);
      if (next.length < ring.length) { live.set(id, next); any = true; }
      (edit.holesById.get(id) || []).forEach((h, k) => {
        const hn = simplifyRing(h, tolMm);
        if (hn.length < h.length) { live.set(ringKey(id, k), hn); any = true; }
      });
      if (any) from.set(id, ring.length);
    }
    if (!from.size) return { changed: false, from };
    const res = ringEditOverrides(el, editBasis(edit), live);
    if (res.error || !res.cur) {
      if (res.error) {
        const row = (edit.rows || []).find((x) => x && x.id === res.sid);
        shapeEditError = `${row ? shapeMenuName(row) : "Shape"}: ${res.error}`;
      }
      return null;
    }
    shapeEditError = "";
    dispatch("elupdate", { id: el.id, patch: { shapeOverrides: res.cur } });
    // Point indices no longer mean what they did.
    if (reshapeOn()) setReshapeSel(new Map());
    return { changed: true, from };
  }

  // Requirement 6: delete the selected shape. Rides `deletedShapeIds`, the
  // same list DigitizePanel's own delete uses — so a shape removed here is
  // struck through and RESTORABLE from the Layers list exactly as before,
  // rather than being a second, one-way kind of deletion.
  // Clearing the shape selection when the ELEMENT selection moves away keeps
  // Delete from acting on a shape whose element is no longer in front of the
  // user. Cheap to compute, and it also drops the highlight.
  //
  // The shape selection is TAGGED with its element (selectedShapeElId) and
  // dropped the moment the selected element is any other one — including a
  // switch between two shape-lane elements, where an untagged id survived
  // and armed Delete on the new element's same-id shape. Tagged rather than
  // "clear on any selection change" because shapeUnderPointer dispatches
  // `select` and sets the shape in the same tick: the tag already names the
  // new element when this block sees it, so that selection survives.
  $: if (project && project.selectedId !== undefined) {
    const sel = selectedElement();
    // Reshape mode belongs to the element it was entered on: another element
    // selected, or none, ends it.
    if (reshape && reshape.elId !== project.selectedId) endReshape();
    if (holeDraft && (holeDraft.elId !== project.selectedId || multiSel)) cancelHoleDraft();
    // Selecting another shape ends a draft too.
    if (holeDraft && selectedShapeId !== holeDraft.shapeId) cancelHoleDraft();
    // Move shape: another element, none, or another shape commits the pending move.
    if (shapeMove && (shapeMove.elId !== project.selectedId || multiSel || selectedShapeId !== shapeMove.shapeId)) commitShapeMove();
    // The frozen rings are stale once an Undo or a landing restitch replaced the
    // shape's override entry or its review row: leave the move, commit nothing.
    if (shapeMove && shapeMoveStale(project)) endShapeMove();
    if (reshape && sel && sel.type === "digitized" && !reshapeDrag) {
      const sig = nodeSigOf(sel);
      if (sig !== reshapeNodeSig) {
        reshapeNodeSig = sig;
        if (reshape.sel.size) reshape = { ...reshape, sel: new Map() };
        nodeCursor = null;
      }
    }
    if (!sel || !SHAPE_LANES.has(sel.type)) {
      selectedShapeId = null;
      selectedShapeElId = null;
      focusedAnchor = null;
    }
    if (selectedShapeId && project.selectedId !== selectedShapeElId) {
      selectedShapeId = null;
      selectedShapeElId = null;
      focusedAnchor = null;
      dropStalePop();
    }
    // An open popover belongs to the element it was opened on. A different
    // selection (the Layers chips, a press on another element) closes it and
    // drops its shape rather than re-aiming it at the new element.
    if (shapePop && project.selectedId !== shapePop.elementId) {
      selectedShapeId = null;
      selectedShapeElId = null;
      focusedAnchor = null;
      dropStalePop();
    }
  }

  // Sets the selection AND its tag together, so the invariant above holds
  // whichever path picks a shape.
  function setSelectedShape(id) {
    if (selectedShapeId === id) return;
    selectedShapeId = id;
    const el = id ? selectedElement() : null;
    selectedShapeElId = el ? el.id : null;
  }

  // Canvas -> Layers list. The selection is set on several paths (a click,
  // a right-click, the popover's Delete, the clears above, a row click from
  // the list), so the list is told by WATCHING the ids rather than by
  // instrumenting each assignment — a watcher cannot be bypassed by the
  // next path that lands. Silent when nothing changed, which is also what
  // stops a list-originated selection echoing back and forth. The event is
  // `shapefocus`, not `shapeselect`: that name carries the manual lane's
  // { elementId, shapeId, edit } request to ManualPanel, a different
  // payload for a different listener.
  let focusNotified = "";
  function notifyShapeFocus(id, elId) {
    const key = id && elId ? elId + "\u0000" + id : "";
    if (key === focusNotified) return;
    focusNotified = key;
    dispatch("shapefocus", key ? { elId, shapeId: id } : null);
  }
  $: notifyShapeFocus(selectedShapeId, selectedShapeElId);

  // Panel -> canvas: a click on a row selects that shape here, the same
  // state a canvas click sets, so Delete and a boundary drag act on it and
  // the amber highlight shows which one. Only for the element in front of
  // the user; a stale focus for some other element is ignored.
  function applyFocusShape(f) {
    const sel = selectedElement();
    if (!sel || sel.type !== "digitized" || sel.id !== f.elId) return;
    if (selectedShapeId === f.shapeId) return;
    selectedShapeId = f.shapeId;
    selectedShapeElId = sel.id;
    shapeEditError = "";
    scheduleViewRepaint();
  }
  $: if (focusShape) applyFocusShape(focusShape);
  // A hover is drawn over the render, so a change to it (on or off) needs
  // the base repainted underneath, not just the overlay redrawn on top.
  $: if (canvas) { hoverShape; scheduleViewRepaint(); }

  // Canvas -> panel: the shape under the pointer, on its outline or inside
  // it (the same two tests the right-click menu uses), for the row to
  // highlight. Dispatched only on change; null when the pointer is on none.
  let hoverEmitted = null;
  function emitCanvasHover(p) {
    let id = null;
    let elId = null;
    const edit = p ? editableOutlinesPx() : null;
    if (edit) {
      const hidden = hiddenShapeIds(edit.el, edit.rows);
      const live = edit.outlines.filter((o) => !hidden.has(o.id));
      const hit = hitOverlay(live, p.x, p.y) || hitShapeInterior(live, p.x, p.y);
      if (hit) { id = hit.shapeId; elId = edit.el.id; }
    }
    if (id === hoverEmitted) return;
    hoverEmitted = id;
    dispatch("shapehover", id ? { elId, shapeId: id } : null);
  }

  function deleteSelectedShape() {
    // The selected shape's element, and only while it is the selected one.
    const el = selectedShapeElement();
    if (!el) return false;
    if (el.type === "manual") {
      // Same patch ManualPanel.deleteShape sends: the shape leaves
      // element.shapes, and the panel's own list drops the row.
      const shapes = el.shapes || [];
      if (!shapes.some((s) => s && s.id === selectedShapeId)) return false;
      dispatch("elupdate", { id: el.id, patch: { shapes: shapes.filter((s) => s.id !== selectedShapeId) } });
      selectedShapeId = null;
      selectedShapeElId = null;
      focusedAnchor = null;
      shapeEditError = "";
      return true;
    }
    if (el.type !== "digitized") return false; // a preset element IS its one shape; its chip removes it
    const cur = el.deletedShapeIds || [];
    if (cur.includes(selectedShapeId)) return false;
    dispatch("elupdate", { id: el.id, patch: { deletedShapeIds: [...cur, selectedShapeId] } });
    setSelectedShape(null);
    focusedAnchor = null;
    shapeEditError = "";
    return true;
  }

  // ---- keyboard placement ---------------------------------------------------
  //
  // The field was mouse-only: nothing here could be moved without a pointer,
  // and the canvas carried no name, so a screen reader walked the whole
  // four-step wizard to a surface that announced nothing at all.
  //
  // Arrow keys drive the SAME clamp-and-patch path a drag uses
  // (clampOffsets -> "elupdate"), so hoop containment and the undo history
  // behave identically whichever way the design was moved — including the
  // 500 ms coalesce in lib/history.js, which collapses a held arrow's
  // auto-repeat into one undo step exactly as it does a drag.
  //
  // 1 mm a press, 10 mm with Shift: the step pairing every design tool
  // shares. 1 mm is already finer than a 0.4 mm thread holds a placement to,
  // so a smaller default would be precision the fabric cannot keep.
  const NUDGE_MM = 1;
  const NUDGE_MM_COARSE = 10;
  // Reshape mode's point nudge: finer than the element's, in field mm.
  const RESHAPE_NUDGE_MM = 0.1;
  const RESHAPE_NUDGE_MM_COARSE = 1;

  function nudgeSelected(dxMm, dyMm) {
    // The simulator is a watch-mode (pointer editing is disabled there too),
    // and mid-boundary-edit the arrows belong to the ring being dragged.
    if (!project || simActive || shapeEdit || nodeEdit || reshapeDrag || marquee) return;
    const id = project.selectedId;
    if (!id) return;
    const el = (project.elements || []).find((e) => e.id === id);
    const pe = peById[id];
    if (!el || !pe || !pe.bboxMm) return;
    const { wMm: hoopWmm, hMm: hoopHmm } = hoopSizeMm(project);
    if (!hoopWmm || !hoopHmm) return;
    const curX = el.offsetXMm || 0;
    const curY = el.offsetYMm || 0;
    const clamped = clampOffsets(
      curX + dxMm, curY + dyMm,
      pe.bboxMm.x1 - pe.bboxMm.x0, pe.bboxMm.y1 - pe.bboxMm.y0,
      hoopWmm, hoopHmm,
    );
    if (Math.abs(clamped.offsetXMm - curX) < 0.001 &&
        Math.abs(clamped.offsetYMm - curY) < 0.001) {
      // The clamp refused the move — the design is already against the edge of
      // the PLACEMENT on that axis. Saying so is the only feedback a non-sighted
      // user gets that the key did anything at all, which is exactly why it has
      // to be true: this said "At the edge of the hoop" until 2026-09-08, and
      // the hoop is not what refused. A sighted user can see the hoop outline
      // still has room and shrug; a screen-reader user has only this sentence,
      // and it sent them to pick a bigger hoop, which changes nothing.
      const placement = garmentFor(project);
      liveMsg = placement && placement.label
        ? `At the edge of the ${placement.label} area`
        : "At the edge of the placement area";
      return;
    }
    dispatch("elupdate", { id, patch: clamped });
    liveMsg = offsetPhrase(clamped.offsetXMm, clamped.offsetYMm);
  }

  // "3 mm right and 1 mm up from center". Only the axes that are actually
  // off-center are named — a readout that says "centered" about one axis
  // while the other has moved is a sentence nobody can parse — and the
  // direction is a word, because a signed number read aloud as "minus three"
  // says nothing about which way the design went.
  function offsetPhrase(xMm, yMm) {
    const parts = [];
    if (Math.abs(xMm) >= 0.05) parts.push(`${Math.abs(xMm).toFixed(1)} mm ${xMm > 0 ? "right" : "left"}`);
    if (Math.abs(yMm) >= 0.05) parts.push(`${Math.abs(yMm).toFixed(1)} mm ${yMm > 0 ? "up" : "down"}`);
    if (parts.length) return `${parts.join(" and ")} from center`;
    // Same correction as the refusal message above: centred in the PLACEMENT,
    // which is what the offset is measured from, not in the hoop.
    const placement = garmentFor(project);
    return placement && placement.label
      ? `Centered in the ${placement.label} area`
      : "Centered in the placement area";
  }

  // Add hole without a pointer: a cursor (starts at the shape's centre) moves
  // 1 mm per arrow (Shift 5), Space drops a vertex on it. Same draft, same
  // close / refusal path as a click.
  function holeKeyboard(key, shift) {
    if (!holeDraftOn()) return;
    let cur = holeDraft.cursorMm;
    if (!cur) {
      const edit = renderResult ? outlinesPxFor(selectedElement()) : null;
      const shell = edit && edit.mmById.get(holeDraft.shapeId);
      cur = holeDraft.pointsMm.length ? holeDraft.pointsMm[holeDraft.pointsMm.length - 1] : ringCentre(shell);
    }
    if (key === " ") {
      const pts = holeDraft.pointsMm;
      const last = pts[pts.length - 1];
      if (last && Math.hypot(last[0] - cur[0], last[1] - cur[1]) < 1e-6) return;
      shapeEditError = "";
      holeDraft = { ...holeDraft, cursorMm: cur, pointsMm: [...pts, [cur[0], cur[1]]] };
      liveMsg = holePointPhrase(holeDraft.pointsMm.length, cur[0], cur[1]);
    } else {
      const next = stepHoleCursor(cur, key, shift);
      if (!next) return;
      holeDraft = { ...holeDraft, cursorMm: next };
      liveMsg = `Cursor at ${next[0].toFixed(1)}, ${next[1].toFixed(1)} mm`;
    }
    repaintNodeChrome();
  }

  function onCanvasKey(e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser/OS shortcuts alone
    if (reshapeCursorKey(e)) { e.preventDefault(); return; }
    // Drawing a hole: the arrows must not slide the element under the draft.
    // The arrows move a keyboard cursor instead; Space places a vertex there.
    if (holeDraftOn() && (e.key.startsWith("Arrow") || e.key === " ")) {
      e.preventDefault();
      holeKeyboard(e.key, e.shiftKey);
      return;
    }
    // Move shape: the arrows move the SHAPE, 0.1 mm (Shift 1 mm), accumulated
    // live; nothing commits until Enter / Done.
    if (shapeMoveOn() && e.key.startsWith("Arrow")) {
      const ms = e.shiftKey ? RESHAPE_NUDGE_MM_COARSE : RESHAPE_NUDGE_MM;
      if (e.key === "ArrowLeft") moveShapeBy(-ms, 0);
      else if (e.key === "ArrowRight") moveShapeBy(ms, 0);
      else if (e.key === "ArrowUp") moveShapeBy(0, ms);
      else if (e.key === "ArrowDown") moveShapeBy(0, -ms);
      e.preventDefault();
      return;
    }
    // Reshape mode with points selected: the arrows move THOSE points, 0.1 mm
    // (Shift 1 mm). With none selected they still nudge the element.
    if (reshapeOn() && reshapeSelCount(reshape) > 0 && !reshapeDrag && !marquee && !shapeEdit && !nodeEdit
        && (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === "ArrowUp" || e.key === "ArrowDown")) {
      const rs = e.shiftKey ? RESHAPE_NUDGE_MM_COARSE : RESHAPE_NUDGE_MM;
      if (e.key === "ArrowLeft") nudgeReshape(-rs, 0);
      else if (e.key === "ArrowRight") nudgeReshape(rs, 0);
      else if (e.key === "ArrowUp") nudgeReshape(0, rs);
      else nudgeReshape(0, -rs);
      e.preventDefault();
      return;
    }
    const step = e.shiftKey ? NUDGE_MM_COARSE : NUDGE_MM;
    if (e.key === "ArrowLeft") nudgeSelected(-step, 0);
    else if (e.key === "ArrowRight") nudgeSelected(step, 0);
    // +y is UP in offset space (clampOffsets' contract), so ArrowUp adds.
    else if (e.key === "ArrowUp") nudgeSelected(0, step);
    else if (e.key === "ArrowDown") nudgeSelected(0, -step);
    else return;
    // Swallowed whether or not anything moved: the canvas fills its pane, and
    // an arrow that scrolls the page out from under a focused field reads as
    // a bug even when the design was simply already at the edge.
    e.preventDefault();
  }

  function onWindowKey(e) {
    // The simulator's own keys (see simKey) -- only while it runs, and none
    // of them is a key any edit mode below listens for.
    if (simKey(e)) { e.preventDefault(); return; }
    // Move shape comes first: Escape restores and dispatches nothing, Enter
    // (from the field) commits the move.
    if (shapeMoveOn()) {
      // Escape cancels from anywhere (it is always safe); Enter needs the field.
      if (e.key === "Escape") { endShapeMove(); e.preventDefault(); return; }
      // A move session owns Delete / Backspace: nothing is deleted mid-move (a
      // delete would clear the selection and the move would then commit onto a
      // shape that is gone).
      if ((e.key === "Delete" || e.key === "Backspace") && (e.target === canvas || e.target === document.body)) {
        e.preventDefault();
        return;
      }
      if (e.key === "Enter" && !shapePop && !fieldMenu && (e.target === canvas || e.target === document.body)) {
        commitShapeMove();
        e.preventDefault();
        return;
      }
    }
    // Drawing a hole comes first: Escape cancels the draft (and nothing else —
    // Reshape and the popover are left for the next press), Backspace takes
    // the last vertex back, Enter closes the ring.
    if (holeDraftOn()) {
      const fromField = e.target === canvas || e.target === document.body;
      if (e.key === "Escape") { cancelHoleDraft(); e.preventDefault(); return; }
      if (fromField && (e.key === "Backspace" || e.key === "Delete")) {
        if (holeDraft.pointsMm.length) {
          shapeEditError = "";
          holeDraft = { ...holeDraft, pointsMm: holeDraft.pointsMm.slice(0, -1) };
          repaintNodeChrome();
        }
        e.preventDefault();
        return;
      }
      if (fromField && e.key === "Enter") {
        if (!closeHoleDraft() && holeDraft && holeDraft.pointsMm.length < 3) liveMsg = MODE_SAYS.holeNeedThree;
        e.preventDefault();
        return;
      }
    }
    // Reshape mode is the first thing Escape leaves, ahead of the focused
    // anchor, the popover and the tool menu (a drag in flight is dropped).
    // Enter is Done too (not while the popover or tool menu holds the keys).
    if ((e.key === "Escape" || (e.key === "Enter" && !shapePop && !fieldMenu && (e.target === canvas || e.target === document.body))) && reshape) {
      endReshape();
      e.preventDefault();
      return;
    }
    // Escape closes the shape popover, then the tool menu, before anything
    // else looks at the key.
    if (e.key === "Escape" && shapePop) {
      closeShapePop();
      e.preventDefault();
      return;
    }
    if (e.key === "Escape" && fieldMenu) {
      fieldMenu = null;
      e.preventDefault();
      return;
    }
    // Then a focused anchor: Escape drops the focus (the shape stays
    // selected), so the next Delete removes the shape rather than the point.
    if (e.key === "Escape" && focusedAnchor) {
      focusedAnchor = null;
      repaintNodeChrome();
      e.preventDefault();
      return;
    }
    // Then the stitch inspector, the least modal thing on the field: from the
    // field, the page, or the bar its toggle sits in.
    if (e.key === "Escape" && inspectOn) {
      const t = e.target;
      if (t === canvas || t === document.body || (t && t.closest && t.closest(".fieldbars"))) {
        inspectOn = false;
        inspectHit = null;
        e.preventDefault();
        return;
      }
    }
    if (e.key !== "Delete" && e.key !== "Backspace") return;
    // Reshape mode with points selected: Delete removes THOSE points (same
    // from-the-field rule as below). With none selected it does what it did.
    if (reshapeOn() && reshapeSelCount(reshape) > 0) {
      const rt = e.target;
      if (rt !== canvas && rt !== document.body) return;
      if (reshapeDrag || marquee || nodeEdit || pressEdge) return;
      deleteReshapeSelection();
      repaintNodeChrome();
      e.preventDefault();
      return;
    }
    if (!selectedShapeId || simActive) return;
    // Only a key that came FROM THE FIELD deletes: the canvas itself (a press
    // on it focuses it, and closeShapePop hands focus back to it), or nothing
    // focused at all. This listener is on the window, so an inputs-only guard
    // let a Delete aimed at ManualPanel's list — or the Backspace that takes
    // back a draft node on ManualPanel's own canvas — delete the field's
    // selected shape as well, a shape the user was not looking at. It also
    // covers every text field, and the popover's own controls (SELECT,
    // INPUT, BUTTON): the popover's Delete button is how you delete from it.
    const t = e.target;
    if (t !== canvas && t !== document.body) return;
    // Mid-drag (two-handed), the key belongs to nothing: a commit now would
    // run against the bbox the drag is about to change. nudgeSelected's rule.
    if (nodeEdit || pressEdge) return;
    // A focused anchor of the selected hand-drawn shape: Delete removes that
    // POINT (its two edges become one), not the shape. At the three-point
    // floor it refuses with the message and removes nothing.
    const fa = liveFocusedAnchor();
    if (fa) {
      if (removeAnchorOf(fa.elId, fa.shapeId, fa.index)) focusedAnchor = null;
      repaintNodeChrome();
      e.preventDefault();
      return;
    }
    if (deleteSelectedShape()) {
      if (shapePop) closeShapePop();
      e.preventDefault();
    }
  }

  // An element whose stitches are behind its settings: edits not stitched yet,
  // but also a resize or a garment switched since the run (lib/staleness.js,
  // the one rule the Digitize panel and Download read too). Whole-element
  // rather than per-shape on purpose: stage 5 resolves overlap BETWEEN shapes,
  // so editing one boundary genuinely moves its neighbours' stitches too.
  // Marking only the edited shape would be a more precise-looking half-truth.
  function isStale(el) {
    return isElementStale(el, project);
  }

  // Hatching over the stitches of an element that is behind its settings.
  // Drawn UNDER the outlines so the thing being edited stays crisp. The ids it
  // hatched are mirrored on the canvas (`data-stale-ids`) because a hatch is
  // pixels, and a spec cannot ask pixels which element they belong to.
  function drawStaleWash(ctx) {
    if (!renderResult || !renderResult.toCanvas || !project) return;
    const behind = [];
    for (const el of project.elements || []) {
      if (!isStale(el)) continue;
      behind.push(el.id);
      const rect = perElementRects.find((r) => r.id === el.id);
      if (!rect) continue;
      ctx.save();
      ctx.beginPath();
      ctx.rect(rect.x, rect.y, rect.w, rect.h);
      ctx.clip();
      // Diagonal hatch rather than a flat wash: a flat tint over stitches
      // reads as a colour change, which is the one thing it must not imply.
      ctx.strokeStyle = "rgba(120, 130, 145, 0.28)";
      ctx.lineWidth = 1;
      const step = 7;
      const span = rect.w + rect.h;
      ctx.beginPath();
      for (let d = -rect.h; d < span; d += step) {
        ctx.moveTo(rect.x + d, rect.y);
        ctx.lineTo(rect.x + d - rect.h, rect.y + rect.h);
      }
      ctx.stroke();
      ctx.restore();
    }
    // setAttribute, never `canvas.dataset.x = …`: in this legacy-mode
    // component a member assignment on a component-level variable invalidates
    // it, and paint() reads `canvas`, so the assignment re-ran the paint that
    // made it -- a loop that froze the page the moment a digitize landed.
    const ids = behind.join(",");
    if (canvas && canvas.getAttribute("data-stale-ids") !== ids) canvas.setAttribute("data-stale-ids", ids);
  }

  function drawShapeOutlines(ctx) {
    if (!renderResult || !renderResult.toCanvas || !project) return;
    const now = performance.now();
    let stillPulsing = false;
    let selNodes = 0;   // nodes drawn on the selected shape's rings (data-reshape-nodes)
    const selNodePx = [];   // the same nodes' canvas px, in Reshape mode only (data-reshape-node-px, for e2e aiming)

    for (const el of project.elements || []) {
      const src = outlinesMmFor(el);
      if (!src) continue;
      const rows = src.rows;
      const outlines = src.mm;
      if (!outlines.length) continue;

      const started = pulses.startedAt(el.id);
      // Reduced motion: the outline pulse is pure animation, so it never plays.
      const reduced = prefersReducedMotion();
      const pulse = started == null || reduced ? 0 : pulseAt(now - started);
      // The wave touches 0 between beats, so "still in the window" is read
      // off the fade, not the beat.
      const fade = started == null || reduced ? 0 : pulseFadeAt(now - started);
      if (fade > 0) stillPulsing = true;

      // Hidden shapes stay out of the drawing but stayed IN the transform, so
      // toggling one off does not shift the others.
      // Not drawn: shapes the user turned off, and shapes deleted in review.
      // A deleted shape stays in `review.shapes` on purpose (that is what
      // makes it restorable from the Layers list), so it has to be filtered
      // here or the canvas would keep outlining artwork that no longer sews.
      const hidden = hiddenShapeIds(el, rows);
      // A cut-out that cuts NOTHING sews nothing and, idle, had no outline:
      // it was invisible on the hoop until hovered. While its element is the
      // selected one its dashed outline is drawn whatever the toggle says.
      // Resolved once per element per draw, and only when there is one to find.
      const orphanCut = el.type === "manual" && project.selectedId === el.id && outlines.some((o) => o.cutOut)
        ? resolveCutOuts(el.shapes).parentOf
        : null;

      // Reshape mode: every shape of this element is drawn with its points,
      // selected or not, whatever the Outlines toggle says.
      const inMode = !!reshape && reshape.elId === el.id && project.selectedId === el.id && !multiSel;
      const similarSet = applyToSimilar && popModel && popModel.similar && el.id === selectedShapeElId
        ? new Set(popModel.similar.ids) : null;

      ctx.save();
      ctx.lineJoin = "round";
      for (const o of outlines) {
        if (hidden.has(o.id)) continue;
        // Mid-drag, the shape being edited renders from the working ring
        // rather than from the last committed review — otherwise the outline
        // would sit still until the pointer came up.
        const dragLive = reshapeDrag && reshapeDrag.kind === "ring" && reshapeDrag.elId === el.id && reshapeDrag.live
          ? reshapeDrag.live.get(o.key || o.id) : null;
        const src = dragLive || (liveRing && liveRing.key === (o.key || o.id) ? liveRing.points : o.points);
        const mv = moveShiftFor(el.id, o.id);
        const pts = src.map(([x, y]) => renderResult.toCanvas(x + (mv ? mv.dx : 0), y + (mv ? mv.dy : 0)));
        if (pts.length < 3) continue;
        // Highlighted when SELECTED, not only while dragging: the highlight
        // is what tells you which shape a Delete or a drag will act on.
        // Tagged by element: shape ids repeat across elements ("shape" on
        // every preset, s1… on every hand-drawn one).
        const editing = (el.id === selectedShapeElId && o.id === selectedShapeId) || inMode;
        // Under the pointer — on the canvas or on its row in the Layers
        // list (App routes both here as `hoverShape`). Drawn white so it
        // reads as a spotlight beside the amber selection.
        const hovered = !editing && !!hoverShape && hoverShape.elId === el.id && hoverShape.shapeId === o.id;
        // Ticked "Apply to all similar shapes": every other shape the edit
        // will touch, outlined blue so the reach is visible BEFORE the pick.
        const similar = !editing && !!similarSet && similarSet.has(o.id);
        // The default view is the stitch-out, so only the shape being acted
        // on, or pointed at, is outlined until the user asks for all of them.
        //
        // Clicking still selects with the outlines hidden: hit-testing runs
        // off the geometry (hitOverlay), never off what was drawn, and the
        // shape highlights the moment it is picked. The hover outline is the
        // signpost that the shapes are individually clickable; the toggle
        // remains for seeing all of them at once, which is why it sits with
        // the other two diagnostic overlays. (Since 2026-09-30 the Layers
        // list drives this too, through App: a row's hover and click land
        // in `hoverShape` / `focusShape` above.)
        const orphan = !!(orphanCut && o.cutOut && orphanCut[o.id] == null);
        // A fresh result pulses whatever the toggle says, fading out as it
        // goes: hiding the outlines by default (2026-09-01) silently hid the
        // "we found these shapes" cue with them, and Kent asked for it back
        // (2026-10-08).
        const ghost = !showOutlines && !editing && !hovered && !orphan && !similar;
        if (ghost && fade <= 0) continue;
        ctx.globalAlpha = ghost ? fade : 1;
        // Mid node-drag the flattened ring is the STALE geometry: drawing it
        // beside the live authored outline showed two amber outlines. Idle,
        // the flattened ring stays underneath the authored one (spec §5) —
        // except under a selected CUT-OUT, whose dashes the second stroke
        // would fill in: drawAuthoredNodes strokes that one alone.
        if (el.type === "manual" && editing && (o.cutOut || anchorsLive(el, o.id) || (nodeEdit && nodeEdit.elId === el.id && nodeEdit.shapeId === o.id))) {
          drawAuthoredNodes(ctx, el, o.id);
          continue;
        }

        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.closePath();
        // A cut-out reads as a hole, not as a shape: dashed, same casing and
        // colours. The canvas keeps dash state, so it is reset right after.
        if (o.cutOut) ctx.setLineDash([4, 3]);

        // Cased line: a dark casing under a bright core. An outline traces the
        // EDGE of the artwork it describes, so it is always sitting on the
        // boundary between the stitches and the fabric — a single-colour line
        // disappears into whichever of the two it happens to match. Verified
        // in a real browser first (2026-08-12): the uncased version was
        // legible on pale fabric and vanished against dark fill.
        ctx.strokeStyle = `rgba(10, 22, 30, ${0.5 + 0.3 * pulse})`;
        ctx.lineWidth = 3.4 + 1.8 * pulse;
        ctx.stroke();
        // The pulse rides on opacity and width together — brightening alone
        // reads as a highlight, widening alone as a wobble; both together read
        // as a heartbeat.
        ctx.strokeStyle = editing
          ? "rgba(255, 214, 64, 0.95)"     // the selected shape
          : hovered
            ? "rgba(255, 255, 255, 0.95)"  // the shape under the pointer, here or in the list
            : similar
              ? "rgba(70, 170, 255, 0.98)" // a shape the ticked group edit will touch
              : `rgba(${OUTLINE_RGB}, ${0.85 + 0.15 * pulse})`;
        ctx.lineWidth = (editing || hovered || similar ? 1.9 : 1.4) + 1.4 * pulse;
        ctx.stroke();
        if (o.cutOut) ctx.setLineDash([]);
        // A group member is a highlight, not something to drag: no node dots.
        if (similar) continue;

        // Node dots say "drag me". On the digitized lane every vertex of the
        // dense ring is one; a hand-drawn shape's nodes are its AUTHORED
        // anchors and curve handles (drawn by drawAuthoredNodes once the shape
        // is selected); a preset has none to move — its geometry is a recipe.
        if (el.type === "manual" && editing) {
          drawAuthoredNodes(ctx, el, o.id);
          continue;
        }
        if (el.type !== "digitized") continue;
        const r = NODE_R + 1.7 * pulse + (editing ? 0.6 : 0);
        // Sparse nodes (2026-11-05): only the NODES draw, never the dense
        // polygon's vertices. A smooth node is the disc, a corner a square of
        // the same size. The path above stays the dense polygon.
        const nodeList = liveNodesOf(el, o.key || o.id, o);
        if (el.id === selectedShapeElId && o.id === selectedShapeId && nodeList) {
          selNodes += nodeList.length;
          if (inMode) nodeList.forEach((nd, ni) => { const q = pts[nd.i]; if (q) selNodePx.push([ni, o.ring == null ? -1 : o.ring, Math.round(q.x * 10) / 10, Math.round(q.y * 10) / 10, nd.kind === "corner" ? 1 : 0]); });
        }
        const squareAt = (cx, cy, h) => ctx.rect(cx - h, cy - h, 2 * h, 2 * h);
        for (let pi = 0; pi < (nodeList ? nodeList.length : 0); pi++) {
          const p = pts[nodeList[pi].i];
          if (!p) continue;
          const square = nodeMarker(nodeList[pi].kind) === "square";
          // A selected point (Reshape mode) is a white marker inside an amber ring.
          if (inMode && reshapeSelHas(el.id, o.id, o.ring == null ? RING_EXTERIOR : o.ring, pi)) {
            ctx.beginPath();
            if (square) squareAt(p.x, p.y, r + 1.4); else ctx.arc(p.x, p.y, r + 1.4, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(255, 255, 255, 1)";
            ctx.fill();
            ctx.strokeStyle = "rgba(255, 214, 64, 1)";
            ctx.lineWidth = 2;
            ctx.stroke();
            if (inMode && isCursorNode(el.id, o.id, o.ring == null ? RING_EXTERIOR : o.ring, pi)) drawNodeCursorRing(ctx, p.x, p.y, r + 1.4);
            continue;
          }
          ctx.beginPath();
          if (square) squareAt(p.x, p.y, r); else ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
          // Same casing logic as the line: a node lands on the edge too, and
          // an unringed dot is invisible against matching stitches.
          ctx.fillStyle = editing
            ? "rgba(255, 214, 64, 0.95)"
            : `rgba(${OUTLINE_RGB}, ${0.85 + 0.15 * pulse})`;
          ctx.fill();
          ctx.strokeStyle = `rgba(10, 22, 30, ${0.75 + 0.25 * pulse})`;
          ctx.lineWidth = 1;
          ctx.stroke();
          if (inMode && isCursorNode(el.id, o.id, o.ring == null ? RING_EXTERIOR : o.ring, pi)) drawNodeCursorRing(ctx, p.x, p.y, r);
        }
      }
      ctx.restore();
      drawCapOutline(ctx, el, src.caps || [], hidden);
    }

    // setAttribute, not a template binding: see the note on data-stale-ids.
    if (canvas && canvas.getAttribute("data-reshape-nodes") !== String(selNodes)) canvas.setAttribute("data-reshape-nodes", String(selNodes));
    const nodePxJson = selNodePx.length ? JSON.stringify(selNodePx) : "";
    if (canvas && (canvas.getAttribute("data-reshape-node-px") || "") !== nodePxJson) canvas.setAttribute("data-reshape-node-px", nodePxJson);
    if (stillPulsing) schedulePulseFrame();
  }

  // The selected cap stretch (and the one under a Layers hover) — a cased
  // open line, amber when selected, like a shape's outline but with no ring
  // and no nodes. Idle stretches stay undrawn; the stitching is its own cue.
  function drawCapOutline(ctx, el, caps, hidden) {
    for (const o of caps) {
      if (hidden.has(o.id)) continue;
      const editing = el.id === selectedShapeElId && o.id === selectedShapeId;
      if (!editing) continue;
      const pts = o.points.map(([x, y]) => renderResult.toCanvas(x, y));
      if (pts.length < 2) continue;
      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.strokeStyle = "rgba(10, 22, 30, 0.6)";
      ctx.lineWidth = 5.2;
      ctx.stroke();
      ctx.strokeStyle = "rgba(255, 214, 64, 0.95)";
      ctx.lineWidth = 2.4;
      ctx.stroke();
      ctx.restore();
    }
  }

  // The selected hand-drawn shape's AUTHORED geometry: the quadratic outline
  // through its mapped controls, an amber dot per anchor, a green dot per
  // segment handle. Amber is the selected ring's colour; green is the side
  // canvas's curve-handle colour — the side canvas's vocabulary, so nothing
  // has to be relearned. Every dot is cased like the outline, because a node
  // sits on the edge between stitches and fabric. Mid-drag this draws the
  // live shape, so the outline follows the pointer before the regenerate.
  function drawAuthoredNodes(ctx, el, shapeId) {
    const ap = authoredPxFor(el, shapeId);
    // A column is an OPEN spine: two anchors are enough, there is no closing
    // segment (n - 1 segments, n - 1 handles), and its two rails are drawn as
    // thin lines so the width shows while the spine is edited.
    // A line (run) is open the same way and has no rails to draw.
    const open = !!ap && isOpenShape(ap.shape);
    if (!ap || ap.anchors.length < (open ? 2 : 3)) return;
    const n = ap.anchors.length;
    if (open && ap.rails) {
      for (const rail of [ap.rails.a, ap.rails.b]) {
        if (rail.length < 2) continue;
        ctx.beginPath();
        ctx.moveTo(rail[0][0], rail[0][1]);
        for (let i = 1; i < rail.length; i++) ctx.lineTo(rail[i][0], rail[i][1]);
        ctx.strokeStyle = "rgba(10, 22, 30, 0.45)";
        ctx.lineWidth = 2.2;
        ctx.stroke();
        ctx.strokeStyle = "rgba(255, 214, 64, 0.8)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }
    ctx.beginPath();
    ctx.moveTo(ap.anchors[0][0], ap.anchors[0][1]);
    for (let i = 0; i < (open ? n - 1 : n); i++) {
      const next = ap.anchors[(i + 1) % n];
      const c = ap.controls[i];
      if (c) ctx.quadraticCurveTo(c[0], c[1], next[0], next[1]);
      else ctx.lineTo(next[0], next[1]);
    }
    if (!open) ctx.closePath();
    // A cut-out's authored outline is dashed like its idle one, including
    // mid-drag (`ap.shape` is the live drag's shape then). Dots stay solid.
    const dashed = !!(ap.shape && ap.shape.cutOut);
    if (dashed) ctx.setLineDash([4, 3]);
    ctx.strokeStyle = "rgba(10, 22, 30, 0.5)";
    ctx.lineWidth = 3.4;
    ctx.stroke();
    ctx.strokeStyle = "rgba(255, 214, 64, 0.95)";
    ctx.lineWidth = 1.9;
    ctx.stroke();
    if (dashed) ctx.setLineDash([]);

    const dot = (x, y, r, fill) => {
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = "rgba(10, 22, 30, 0.75)";
      ctx.lineWidth = 1;
      ctx.stroke();
    };
    // NODE_R + 0.4 (3.0 px): at NODE_R - 1 the handles were near-invisible
    // at 100% zoom (controller ruling 2026-09-29); still smaller than an anchor.
    for (const [x, y] of ap.handles) dot(x, y, NODE_R + 0.4, "rgba(64, 200, 120, 0.95)");
    const fa = liveFocusedAnchor();
    for (let i = 0; i < n; i++) {
      const [x, y] = ap.anchors[i];
      if (reshapeSelHas(el.id, shapeId, RING_ANCHORS, i)) {
        // Selected in Reshape mode: white inside an amber ring.
        dot(x, y, NODE_R + 1.6, "rgba(255, 255, 255, 1)");
        ctx.beginPath();
        ctx.arc(x, y, NODE_R + 1.6, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 214, 64, 1)";
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        dot(x, y, NODE_R + 0.6, "rgba(255, 214, 64, 0.95)");
      }
      if (isCursorNode(el.id, shapeId, RING_ANCHORS, i)) drawNodeCursorRing(ctx, x, y, NODE_R + 1.6);
      if (fa && fa.elId === el.id && fa.index === i) {
        // The anchor a Delete would remove: ringed, cased like everything else.
        ctx.beginPath();
        ctx.arc(x, y, NODE_R + 0.6 + 3, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(10, 22, 30, 0.75)";
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.strokeStyle = "rgba(255, 214, 64, 0.95)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }

  // Draws each element's uploaded artwork into the rect its stitches occupy.
  // Same CSS-px coordinate space drawOverlay uses — it sets the same dpr
  // transform for itself, for the same reason: it can run without a render
  // having just left one. A token guards the awaits: a view change or a
  // regeneration during a decode must not paint over the new frame.
  //
  // Registration differs by lane, and only one lane can register exactly:
  //  - `image` (browser flatten): the stitches were traced from the flat's
  //    non-transparent pixels (imageRegions.js flatToRegions), so that pixel
  //    bbox — the CONTENT box — is mapped onto the stitch rect. It can run
  //    slightly larger than the sewn extent on noisy art, because the trace
  //    then drops specks and caps shapes per colour. Fitting
  //    the whole frame instead shrank and shifted the art (measured
  //    2026-09-30: a 23x20 px stitched square drawn back at 12x12).
  //  - `digitized` (service): the review carries `artBox`, the pipeline's
  //    art_bbox as fractions of its (cropped) working image; with the crop
  //    that gives the content box in source px. A review saved before the
  //    service sent it has none, and falls back to fitting the whole image
  //    into the placement box.
  // Either way the draw is clipped to the hoop, so a frame larger than its
  // content cannot spill onto the surround.
  let originalToken = 0;
  async function drawOriginals() {
    const my = ++originalToken;
    const rr = renderResult;
    if (!rr || !rr.toCanvas) return;
    // Compare view draws the same placement onto its offscreen canvas
    // (fabric already painted there by repaintView), leaving the stitches on
    // the field canvas; both bitmaps share one size, so one transform.
    const comparing = originalView && compareView;
    const target = comparing ? compareCanvas : canvas;
    if (!target) return;
    const centre = rr.toCanvas(0, 0);
    const box = hoopSizeMm(project);
    const placement = { x: centre.x - (box.wMm * rr.scale) / 2, y: centre.y - (box.hMm * rr.scale) / 2,
                        w: box.wMm * rr.scale, h: box.hMm * rr.scale };
    const realHoop = effectiveHoop(project).hoop;
    const clip = realHoop && realHoop.widthMm > 0 && realHoop.heightMm > 0
      ? { x: centre.x - (realHoop.widthMm * rr.scale) / 2, y: centre.y - (realHoop.heightMm * rr.scale) / 2,
          w: realHoop.widthMm * rr.scale, h: realHoop.heightMm * rr.scale }
      : placement;
    const flats = (runtime && runtime.flats) || {};
    const jobs = (project.elements || []).filter(hasOriginal).map(async (el) => {
      const rect = perElementRects.find((r) => r.id === el.id);
      if (!rect) return;
      let im;
      try { im = await loadOriginal(el.sourcePng); } catch (e) { return; }
      if (my !== originalToken || !originalView || !canvas) return;
      if ((originalView && compareView) !== comparing) return;
      const iw = im.naturalWidth, ih = im.naturalHeight;
      let at = null;
      if (el.type === "image") {
        const flat = flats[el.id];
        const cb = flat && flatContentBox(flat.indices, flat.w, flat.h);
        if (cb) {
          // The flat is the prepped copy of sourcePng (same WORK_MAX_PX size);
          // scaled anyway, so a grid that ever differs still registers.
          const sx = iw / flat.w, sy = ih / flat.h;
          at = placeByContent(iw, ih, { x: cb.x * sx, y: cb.y * sy, w: cb.w * sx, h: cb.h * sy }, rect);
        }
        if (!at) at = fitRect(iw, ih, rect);
      } else {
        // Digitized: the service's art box (fractions of the cropped upload)
        // registers the picture on its stitches; without it (a result saved
        // before the box existed) the whole image fits the placement box.
        const cb = digitizedContentBox(iw, ih, el.review && el.review.artBox, el.crop);
        at = (cb && placeByContent(iw, ih, cb, rect)) || fitRect(iw, ih, placement);
      }
      if (!at) return;
      const ctx = target.getContext("2d");
      ctx.save();
      if (dpr !== 1) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.beginPath();
      ctx.rect(clip.x, clip.y, clip.w, clip.h);
      ctx.clip();
      ctx.drawImage(im, at.x, at.y, at.w, at.h);
      ctx.restore();
    });
    await Promise.all(jobs);
    if (comparing && my === originalToken) publishCompare(my);
  }

  function drawOverlay() {
    if (!canvas) return;
    // Original view shows the artwork bare: a click or a shape pick while it
    // is lit must not paint selection chrome over the customer's image.
    if (originalView) return;
    const ctx = canvas.getContext("2d");
    // The overlay's px constants (node radius, handle size, line widths) are
    // CSS px like everything else, so it needs the same scale renderRealistic
    // uses. It sets its own rather than inheriting because drawOverlay also
    // runs WITHOUT a preceding render — endDrag calls it to erase drag chrome
    // — and on those paths there is no render to have left one.
    //
    // Note the two calls mask each other: after any full paint the context
    // already carries this transform, so deleting EITHER line alone still
    // looks right in steady state (deleting preview.js's shows up only on the
    // first frame after a resize, which clears the transform). That is why
    // preview.spec.js asserts renderRealistic makes the call itself, rather
    // than leaving the library side to the end-to-end check.
    if (dpr !== 1) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawStaleWash(ctx);
    drawShapeOutlines(ctx);
    drawReshapeChrome(ctx);
    drawHoleDraftChrome(ctx);
    drawShapeMoveChrome(ctx);
    drawGuides(ctx);
    const color = selectionColor();
    if (multiSel) {
      // Group mode: a thin dashed outline per member, then ONE group box
      // with corner handles (group resize). No rotate grip — group rotation
      // isn't a thing yet, so no dead control.
      const memberRects = perElementRects.filter((r) => selIds.includes(r.id));
      if (!memberRects.length) return;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      for (const r of memberRects) ctx.strokeRect(Math.round(r.x) + 0.5, Math.round(r.y) + 0.5, r.w, r.h);
      ctx.restore();
      const g = groupRectPx();
      drawBoxWithHandles(ctx, g, color);
      drawDragBadges(ctx, g);
      return;
    }
    const rect = perElementRects.find((r) => r.id === project.selectedId);
    if (!rect) return;
    drawBoxWithHandles(ctx, rect, color);
    if (rotatable()) drawRotateHandle(ctx, rect, color);
    drawDragBadges(ctx, rect);
  }

  // Emits the SELECTED element's bbox dims (not the combined design's) —
  // SizePanel binds to whatever's selected, so its W/H display and the
  // sub-5mm warning both need to track selection, not the whole project.
  function emitSelectedDims(perElement) {
    const pe = perElement.find((p) => p.id === project.selectedId);
    if (!pe) {
      warn = false;
      letterNote = "";
      twoLinesFix = null;
      dispatch("dims", null);
      return;
    }
    const widthMM = pe.bboxMm.x1 - pe.bboxMm.x0;
    const heightMM = pe.bboxMm.y1 - pe.bboxMm.y0;
    // Text elements carry the engine's own width-guard report; image and
    // shape elements have no `lettering` and get an empty note.
    //
    // `atWidthCap` decides which advice is TRUE. Lettering is fit by width, so
    // for a fixed character count the letters can only get bigger if the
    // design does — and an auto-fit design (sizeMm null, the default) is
    // already as wide as the garment's placement box allows. Telling that
    // customer to "size up" is telling them to do the one thing they cannot.
    // Read off the REQUEST, not the sewn width: the sewn extent is slightly
    // past the box by construction (pull compensation — defect 34), so
    // comparing it to the box would read "capped" for every design.
    const el = project.elements.find((e) => e.id === pe.id);
    // Auto-fit is capped to the largest hoop (EMB.autoFitBoxMm), so on the four
    // garments whose placement is bigger than every hoop it sits BELOW the box
    // and the letters can still grow by typing a width. The box is the one
    // auto-fit aims at: the pro's on a hat, left chest or beanie (proSized,
    // default since 2026-10-26), else the garment's inch box.
    const g = garmentFor(project); // as placed
    const boxWmm = g ? (EMB.placementBoxMm ? EMB.placementBoxMm(g).w : g.widthIn * 25.4) : Infinity;
    const reqWmm = el && el.sizeMm == null ? (g ? EMB.autoFitBoxMm(g).w : Infinity) : el && el.sizeMm;
    const atWidthCap = !!el && reqWmm >= boxWmm - 0.05;
    // `lines` only picks the wording of the cap-floor fix ("break it across
    // lines" vs "use more lines"); read off the element's own text, which is
    // what the customer would be editing.
    const lines = el && typeof el.text === "string" ? el.text.split("\n").length : 1;
    letterNote = letteringNote(pe.design && pe.design.lettering, { atWidthCap, lines });
    // Only where breaking the line is the advice that helps: the design is
    // already at the placement's width, so the letters can grow only if the
    // line gets shorter.
    const split = letterNote && atWidthCap && el && el.type === "text" ? splitIntoTwoLines(el.text) : null;
    twoLinesFix = split ? { id: el.id, text: split } : null;
    // "Smaller than 5 mm" is advice about a design that IS there and is too
    // small to sew cleanly. On an element with no stitches at all it is not
    // advice, it is noise — and it sat directly in front of the message that
    // actually explains the problem ("this font can't stitch E, m and b"),
    // reading as two unrelated faults instead of one cause.
    warn = pe.design.stitchCount > 0 &&
      (widthMM < MIN_SIZE_MM || heightMM < MIN_SIZE_MM);
    dispatch("dims", { widthMM, heightMM });
  }

  // Each hand-drawn element's fit ({ id: { mmPerPx } }), for the side panel:
  // a new column is 4.0 mm wide THROUGH this fit, and its Width row reads and
  // writes mm through it. Only on a change, so a repaint that moved nothing
  // re-renders nothing upstream.
  let lastManualFits = "";
  function emitManualFits(perElement) {
    const fits = {};
    const manual = new Set(((project && project.elements) || []).filter((x) => x && x.type === "manual").map((x) => x.id));
    for (const pe of perElement || []) {
      if (manual.has(pe.id) && pe.design && pe.design.fit && pe.design.fit.mmPerPx > 0) fits[pe.id] = { mmPerPx: pe.design.fit.mmPerPx };
    }
    const key = JSON.stringify(fits);
    if (key === lastManualFits) return;
    lastManualFits = key;
    dispatch("manualfits", fits);
  }

  // ---- "which font CAN stitch this" ---------------------------------------
  //
  // "This font can’t stitch «Р», «у», «с». Try a different font, or different
  // text." is true and unactionable: three shipped fonts cover Cyrillic, three
  // cover Greek, two cover Hebrew, and finding them meant opening up to 85
  // fonts by hand. Naming the fix is the same convention the preflight
  // findings already follow five times over.
  //
  // Async, so it cannot be part of the synchronous paint: `paint()` sets the
  // generic sentence, then this replaces it once the (lazily fetched, 16 KB)
  // index arrives. The token drops a stale answer when the text changes while
  // a fetch is in flight — the same guard App uses for its health probe.
  //
  // Asked about the WHOLE text, not the characters that failed: a font
  // covering exactly the failures and none of the rest (hebrew_font_large has
  // 29 glyphs and no ASCII) would move the dead end, not clear it.
  let suggestToken = 0;
  function textOfProject(p) {
    return (p.elements || [])
      .filter((el) => el.type === "text" && el.text)
      .map((el) => el.text)
      .join("");
  }
  async function suggestFonts(unsupported) {
    const token = ++suggestToken;
    const text = textOfProject(project);
    if (!unsupported || !unsupported.length || !text) return;
    const [coverage, man] = await Promise.all([
      loadCoverage(),
      loadManifest().catch(() => null),
    ]);
    if (token !== suggestToken || !coverage) return;
    const nameOf = new Map(((man && man.fonts) || []).map((f) => [f.key, f.name || f.key]));
    const msg = unsupportedMessage(charList(unsupported), text, coverage, (k) => nameOf.get(k) || k);
    // Whichever of the two the paint() that scheduled this had set — they are
    // mutually exclusive (an empty design shows `hint`, a partial one shows
    // `unsupportedNote`), and paint() clears both at the top of every run.
    if (hint) hint = msg;
    else if (unsupportedNote) unsupportedNote = msg;
  }

  // Invariant: every element's persisted offset must keep ITS bbox inside
  // the hoop. dragMove enforces this live for whichever element is being
  // dragged, but a stale offset (garment switched to a smaller hoop, size
  // changed elsewhere, or a reload) is never re-validated on its own for
  // elements that AREN'T being dragged right now — so this re-clamps EVERY
  // ready element after every generation, regardless of *why* it changed.
  //
  // Loop safety: same as the single-element version this replaces — a
  // dispatched correction changes `project`, which re-triggers paint() (via
  // the `$: if (canvas) { project; runtime; paint(); }` reactive block
  // below), which calls this again, but that second pass clamps an
  // already-clamped offset (clampOffsets is a pure min/max clamp, idempotent
  // on an in-range value) — diff is ~0, nothing dispatched, settles after
  // one correction per element.
  function reclampAll(perElement) {
    const { wMm: hoopWmm, hMm: hoopHmm } = hoopSizeMm(project);
    if (!hoopWmm || !hoopHmm) return; // unknown garment -- nothing to clamp against
    for (const pe of perElement) {
      const el = project.elements.find((e) => e.id === pe.id);
      if (!el) continue;
      const designWmm = pe.bboxMm.x1 - pe.bboxMm.x0;
      const designHmm = pe.bboxMm.y1 - pe.bboxMm.y0;
      const curOffX = el.offsetXMm || 0;
      const curOffY = el.offsetYMm || 0;
      const clamped = clampOffsets(curOffX, curOffY, designWmm, designHmm, hoopWmm, hoopHmm);
      if (Math.abs(clamped.offsetXMm - curOffX) > 0.01 || Math.abs(clamped.offsetYMm - curOffY) > 0.01) {
        // quiet: a programmatic correction, not a user edit — it must never
        // seed an undo step (a boot-time reclamp would otherwise light up
        // the Undo button before the user has touched anything).
        dispatch("elupdate", { id: pe.id, patch: clamped, quiet: true });
      }
    }
  }

  // Text elements' fontKeys must be resolved (see lib/fontLoader.js) BEFORE
  // generateAll runs -- fonts are now lazy-loaded (Slice 10A), so
  // EMB.SATIN_FONTS can be missing an entry the very first time a font is
  // used. `genToken` guards against overlap: paint() is async (it awaits
  // ensureFonts), and the reactive block below fires it again, uncoordinated,
  // on every project/runtime change -- if a second paint() starts before the
  // first one's await resolves, only the LAST one (the one matching the
  // current token when its await returns) is allowed to touch canvas/state,
  // so a slow-to-resolve stale call can never clobber a newer paint's result.
  let genToken = 0;

  function fontKeysOf(proj) {
    // Outline fonts (lib/outlineFonts.js) have no binary to ensure: the
    // service sews them and the element carries the result.
    return (proj.elements || [])
      .filter((el) => el.type === "text" && el.fontKey && !isOutlineKey(el.fontKey))
      .map((el) => el.fontKey);
  }

  async function paint() {
    if (!canvas) return;
    // Any regeneration invalidates the simulator's strand count -- stop it
    // (harmless no-op when it isn't running).
    stopSim();
    // A regeneration drops the Original view too: the new design is what
    // the customer now wants to see.
    originalView = false;
    originalToken++;
    const myToken = ++genToken;
    const fontKeys = fontKeysOf(project);
    let fontErr = null;
    try {
      await ensureFonts(fontKeys);
    } catch (e) {
      fontErr = e;
    }
    // Superseded by a later paint() while we were awaiting, or the component
    // unmounted -- neither should touch shared UI state at this point.
    if (myToken !== genToken || !canvas) return;

    error = "";
    stats = "";
    warn = false;
    hint = "";
    hoopNote = "";
    unsupportedNote = "";
    letterNote = "";
    twoLinesFix = null;
    renderResult = null;
    perElementRects = [];
    peById = {};

    if (fontErr) {
      // Font load failure surfaces through the existing element-error UI
      // (same treatment as a generateAll() throw below), never an unhandled
      // rejection.
      // A dead connection said "Failed to fetch" and nothing else — `fetch`'s
      // own TypeError message, rendered verbatim. No cause, no action, no
      // retry control anywhere on the page. Measured 2026-09-07 by aborting
      // the font requests in a real browser.
      //
      // "Try again" is an honest lever here, measured the same way: the
      // loader clears its cached promise on failure on purpose, so once the
      // connection is back ANY edit re-runs the load. Restored the network,
      // typed one more character, and the design came straight back —
      // 1,336 stitches, error gone, no reload. And the work really is safe:
      // the project is written to storage on every change.
      //
      // Only for a transport failure (fontLoader marks it). An HTTP status is
      // a bad deploy or a missing file, which "check your connection" would
      // send the customer chasing the wrong thing, so that keeps the message
      // the loader gave it.
      error = fontErr && fontErr.offline
        ? "Couldn\u2019t load the font \u2014 check your connection, then edit anything to try again. Your design is saved."
        : String(fontErr.message || fontErr);
      hasDesign = false;
      lastGenerateResult = null;
      clearToFabric();
      dispatch("dims", null);
      dispatch("stats", { stitchCount: 0 });
      return;
    }

    let result;
    try {
      result = generateAll(project, runtime);
    } catch (e) {
      error = e.message;
      hasDesign = false;
      lastGenerateResult = null;
      clearToFabric();
      dispatch("dims", null);
      // No design generated at all -- report zero stitches so App's
      // "drag-field" hint eligibility (A8) drops out too.
      dispatch("stats", { stitchCount: 0 });
      return;
    }

    if (!result.combined) {
      hasDesign = false;
      // A design can be empty because nothing has been typed yet, or because
      // the chosen font cannot render ANY of what was typed. Those need
      // different answers, and the second one used to get the first one's.
      hint = result.unsupported && result.unsupported.length
        ? `This font can\u2019t stitch ${charList(result.unsupported)}. Try a different font, or different text.`
        // Said HERE rather than in the drag hint because the drag hint is
        // gated on `stitchCount > 0` (hints.js, condition A8) — it appears
        // only once there is already a design, which is exactly when the
        // question has stopped being asked. This line is what a customer is
        // looking at while wondering what to do. Which sentence, and why it
        // depends on the pointer, is `emptyFieldHint` in generate.js.
        : emptyFieldHint(hasFinePointer);
      // paint() clears hint/unsupportedNote/… at the top of every run, so
      // exactly one of the two is set here and suggestFonts can tell which
      // message it is amending.
      suggestFonts(result.unsupported);
      lastGenerateResult = null;
      clearToFabric();
      dispatch("dims", null);
      dispatch("stats", { stitchCount: 0 });
      return;
    }

    const c = result.combined;
    // The chosen hoop rides the review stats line, and the ceiling check
    // runs against the combined design (not just the selected element) —
    // the whole design has to fit the physical hoop.
    const { hoop } = effectiveHoop(project);
    // toLocaleString like every other stitch count in the app (QualityReport,
    // DigitizePanel, DesignPanel, and the review summary this line sits above)
    // — it was the one place printing a bare 1289 where the rest say 1,289.
    stats = `${c.stitchCount.toLocaleString()} stitches · ${c.widthMM.toFixed(0)}×${c.heightMM.toFixed(0)} mm · ${hoop.label} hoop`;
    hoopNote = hoopFitNote(c.widthMM, c.heightMM, hoop) || "";
    // Something DID stitch, but not all of it — e.g. Latin mixed into Hebrew.
    // Rides the stats line next to the other warnings rather than blocking.
    unsupportedNote = (result.unsupported && result.unsupported.length)
      ? `This font can\u2019t stitch ${charList(result.unsupported)}` : "";
    suggestFonts(result.unsupported);
    // Reports the COMBINED design's stitch count (not just the selected
    // element's) -- App uses this for the "drag-field" hint's A8 eligibility
    // condition, which is about whether there's anything on the field to
    // drag at all, regardless of which element happens to be selected.
    dispatch("stats", { stitchCount: c.stitchCount });
    // colorOverride is gone — each element now bakes its own color into its
    // stitches at generation time (see generate.js's generateElement), so
    // the combined design already carries the right colors per-part.
    lastGenerateResult = result; // B2: cached for view-only repaints below
    freshContext(canvas);
    renderResult = renderRealistic(canvas, c, {
      dpr,
      hoop: hoopOpt(project),
      fabricRgb: project.fabricRgb,
      weave: true,
      surround: surroundColor(),
      grid: gridColors(),
      view,
      showJumps,
      showTrims,
      threadStyle: realisticView ? "realistic" : "flat",
      sewnPullMm,
    });
    hasDesign = true;

    if (renderResult && renderResult.toCanvas) {
      for (const pe of result.perElement) {
        peById[pe.id] = pe;
        const rect = designRectPx(pe.bboxMm, renderResult.toCanvas);
        if (rect) perElementRects.push({ id: pe.id, ...rect });
      }
    }

    drawOverlay();
    paintSeq++;
    emitManualFits(result.perElement);
    emitSelectedDims(result.perElement);
    reclampAll(result.perElement);
  }

  // B2: view-only repaint -- wheel/pan/zoom-button changes call THIS (via
  // scheduleViewRepaint's rAF throttle), never paint(). Re-runs ONLY
  // renderRealistic (against the cached lastGenerateResult, no generateAll)
  // + recomputes perElementRects (they're canvas-px, so they go stale on
  // every view change) and redraws the selection overlay. Stats/dims/warn/
  // reclamp are all mm-space and unaffected by the view, so none of them
  // re-run here -- exactly what B2 asks for.
  function repaintView() {
    if (!canvas) return;
    if (lastGenerateResult && lastGenerateResult.combined) {
      const comparing = originalView && compareView;
      const opts = {
        dpr,
        hoop: hoopOpt(project),
        fabricRgb: project.fabricRgb,
        weave: true,
        surround: surroundColor(),
        grid: gridColors(),
        view,
        // While simulating, the overlays show only what has HAPPENED, so the
        // simulator draws them itself (drawSimOverlay, below); these draw
        // the whole design, which during playback showed the future.
        showJumps: showJumps && !simActive,
        showTrims: showTrims && !simActive,
        // Compare view's stitch side is the realistic render, whichever of
        // the two thread styles was lit before it.
        threadStyle: realisticView || comparing ? "realistic" : "flat",
        sewnPullMm,
        // While simulating, every repaint (zoom/pan included) draws only the
        // sewn-so-far prefix -- otherwise a mid-playback wheel event would
        // flash the finished design.
        // Original view draws fabric + hoop only (zero strands); the
        // artwork goes on top in drawOriginals. Compare view keeps every
        // strand here and puts the fabric + artwork on its own canvas.
        limitStrands: originalView && !comparing ? 0 : simActive ? Math.floor(simIndex) : undefined,
      };
      freshContext(canvas);
      renderResult = renderRealistic(canvas, lastGenerateResult.combined, opts);
      if (comparing) {
        // The artwork side renders OFFSCREEN (e2e locators, and the field's
        // own code, assume .hoop holds exactly one <canvas>), at the same
        // bitmap size and options as the field canvas, so the same mm->px
        // transform: the artwork lands where Original view puts it.
        // drawOriginals then publishes it to CompareSplit's <img>.
        if (!compareCanvas && typeof document !== "undefined") compareCanvas = document.createElement("canvas");
        if (compareCanvas) {
          if (compareCanvas.width !== canvas.width) compareCanvas.width = canvas.width;
          if (compareCanvas.height !== canvas.height) compareCanvas.height = canvas.height;
          freshContext(compareCanvas);
          renderRealistic(compareCanvas, lastGenerateResult.combined, { ...opts, showJumps: false, showTrims: false, limitStrands: 0 });
        }
      }
      perElementRects = [];
      if (renderResult && renderResult.toCanvas) {
        for (const pe of lastGenerateResult.perElement) {
          const rect = designRectPx(pe.bboxMm, renderResult.toCanvas);
          if (rect) perElementRects.push({ id: pe.id, ...rect });
        }
      }
      // Original view: the artwork, and no selection chrome over it.
      if (originalView) { drawOriginals(); return; }
      // Selection chrome is hidden during playback -- the simulator is a
      // watch-mode, not an edit-mode (pointer editing is disabled below too).
      // In its place: the needle, the travel in flight, the trims so far.
      if (!simActive) drawOverlay();
      else if (simTl && renderResult && renderResult.toCanvas) {
        const idx = Math.floor(simIndex);
        const blk = simTl.blocks[blockAt(simTl, idx)];
        const ctx2 = canvas.getContext("2d");
        const lw = threadPx(renderResult.scale);
        if (simIsolate && blk) {
          drawIsolate(ctx2, {
            strands: simStrands,
            idx,
            from: blk.start,
            toCanvas: renderResult.toCanvas,
            lw,
            flat: !realisticView,
            sewnPullMm,
            wash: gridColors().bed,
            bboxMm: renderResult.designBBoxMm,
            cw: cssW(),
            ch: cssH(),
          });
        }
        drawSimOverlay(ctx2, {
          strands: simStrands,
          timeline: simTl,
          idx,
          toCanvas: renderResult.toCanvas,
          showJumps,
          rgb: blk ? blk.rgb : null,
          underlay: simUnderlay,
          lw,
        });
      }
      paintSeq++;
    } else {
      clearToFabric();
    }
  }

  function scheduleViewRepaint() {
    if (rafViewScheduled) return;
    rafViewScheduled = true;
    requestAnimationFrame(() => {
      rafViewScheduled = false;
      repaintView();
    });
  }

  // ---- stitch simulator ----------------------------------------------------

  function simFrame(ts) {
    simRafId = 0;
    if (!simActive || !simPlaying) return;
    const dt = simLastTs ? ts - simLastTs : 0;
    simLastTs = ts;
    const from = simIndex;
    simIndex = advanceIndex(simIndex, dt, simSpeed, simTotal);
    // A thread change inside this frame's step: land ON it and stop, as the
    // machine does, with the bar naming the thread to load next. Play
    // carries on from there (the change is then behind `from`, not ahead).
    const stop = simStopAtChanges ? colorStopBetween(simTl, Math.floor(from), Math.floor(simIndex)) : null;
    if (stop != null) {
      simIndex = stop;
      simPause();
      simStopped = true;
      liveMsg = simThreadPhrase("Thread change. Next:", stop + 1);
      repaintView();
      return;
    }
    repaintView();
    if (simIndex >= simTotal) {
      simPlaying = false; // finished -- leave the completed design showing
      return;
    }
    simRafId = requestAnimationFrame(simFrame);
  }

  function simPlay() {
    if (!simActive) return;
    if (simIndex >= simTotal) simIndex = 0; // replay from the start
    simStopped = false;
    simPlaying = true;
    simLastTs = 0;
    if (!simRafId) simRafId = requestAnimationFrame(simFrame);
  }

  function simPause() {
    simPlaying = false;
    if (simRafId) { cancelAnimationFrame(simRafId); simRafId = 0; }
  }

  function startSim() {
    if (!lastGenerateResult || !lastGenerateResult.combined) return;
    const combined = lastGenerateResult.combined;
    // Kept for the needle marker (its position is the end of the last strand
    // drawn); the count is unchanged from what this line always computed.
    simStrands = designToStrands(combined);
    simTotal = simStrands.length;
    // The animation is driven by STRANDS (segments) because strands are what
    // paint; the counter is shown in STITCHES because that is the unit the
    // field caption right underneath it uses. A strand is the segment BETWEEN
    // two consecutive stitches, so N stitches in K runs make N − K strands —
    // and the two numbers were on screen together nine apart ("1289 stitches"
    // in the caption, "1280 / 1280" here, on a design with nine runs).
    // Computed once per run rather than per frame; one entry per strand, so
    // the two arrays index together.
    simOrdinals = strandStitchOrdinals(combined);
    if (!simTotal) return;
    simTl = simTimeline(combined);
    simUnderlay = underlayRuns(simStrands, simTl);
    simClock = sewClock(combined);
    simStopped = false;
    nameSimThreads(simTl);
    originalView = false;
    originalToken++;
    simActive = true;
    simSpeed = 1;
    if (prefersReducedMotion()) {
      // No autoplay: show the finished design; Play still replays on request.
      simIndex = simTotal;
      simPlaying = false;
      repaintView();
    } else {
      simIndex = 0;
      simPlay();
    }
  }

  // Each block named off the chart the Download step and the PDF worksheet
  // name it from (the shop's saved chart, else the one the design's cones
  // came out of): Studio's names at once, the brand's when its chunk lands.
  function nameSimThreads(tl) {
    const id = loadPreferredPaletteId(chartIdForProject(project));
    const hit = getCachedPalette(id);
    simNames = blockThreadNames(tl, (hit || STUDIO_PALETTE).threads);
    if (hit) return;
    loadPalette(id).then((p) => {
      if (simTl === tl && p) simNames = blockThreadNames(tl, p.threads);
    }, () => {});
  }

  function stopSim() {
    if (!simActive) return;
    simPause();
    simActive = false;
    simIndex = 0;
    simStopped = false;
    simTl = null;
    simStrands = [];
    simUnderlay = null;
    simClock = null;
    // Back to the normal full render + selection chrome.
    repaintView();
  }

  // Every way of moving the needle by hand (scrub, step, thread step) pauses
  // and clears the thread-change stop, like any operator's hand on the wheel.
  function simSeek(i) {
    simPause();
    simStopped = false;
    simIndex = clampIndex(i, simTotal);
    scheduleViewRepaint();
  }

  function simScrub(e) {
    simSeek(e.detail.value);
  }

  // One stitch back or forward (`,` / `.`). In strands, which is one stitch
  // inside a run; across a run's start the counter skips the stitch that
  // begins it, since that stitch draws nothing on its own.
  function simStepStitch(dir) {
    simSeek(Math.floor(simIndex) + dir);
  }

  // The previous or next thread change (`<` / `>` and the bar's skip
  // buttons). Lands ON the change, where the machine stops, and says which
  // thread comes next.
  function simStepThread(dir) {
    if (!simTl) return;
    const to = stepBlock(simTl, Math.floor(simIndex), dir);
    simSeek(to);
    if (to > 0 && to < simTotal) {
      simStopped = true;
      liveMsg = simThreadPhrase("At a thread change. Next:", to + 1);
    } else {
      liveMsg = to <= 0 ? "Start of the design" : "End of the design";
    }
  }

  // "Next: thread 3 of 6, 1902 Poinsettia" for the live region.
  function simThreadPhrase(head, idx) {
    if (!simTl) return "";
    const k = blockAt(simTl, idx);
    const name = simNames[k] ? `, ${simNames[k]}` : "";
    return `${head} thread ${k + 1} of ${simTl.blocks.length}${name}`;
  }

  // A click on a thread's band in the scrubber's strip: to the start of that
  // thread, where the machine stops for it, named as the thread to load
  // next (the same landing as `>`); thread 1 is the design's start.
  function simGoToBlock(k) {
    if (!simTl) return;
    const to = blockStart(simTl, k);
    simSeek(to);
    if (to > 0 && to < simTotal) {
      simStopped = true;
      liveMsg = simThreadPhrase("At a thread change. Next:", to + 1);
    } else {
      liveMsg = "Start of the design";
    }
  }

  function simToggleIsolate() {
    simIsolate = !simIsolate;
    scheduleViewRepaint();
  }

  function simCycleSpeed() {
    simSpeed = nextSpeed(simSpeed);
  }

  function simToggleStops() {
    simStopAtChanges = !simStopAtChanges;
  }

  function simTogglePlay() {
    if (simPlaying) simPause();
    else simPlay();
  }

  // The simulator's keys, from the field or the bar (never while typing):
  //   ,  .   one stitch back / forward
  //   <  >   previous / next thread change (Shift + , / .)
  // None of these is an arrow (the canvas nudge), Tab, [ or ] (Reshape's node
  // cursor) or Space; Reshape and Move are switched off while the simulator
  // runs anyway. true when the key was taken.
  function simKey(e) {
    if (!simActive || e.ctrlKey || e.metaKey || e.altKey) return false;
    const t = e.target;
    const fromField = t === canvas || t === document.body;
    const fromBar = !!(t && t.closest && t.closest(".simbar"));
    if (!fromField && !fromBar) return false;
    if (e.key === ",") simStepStitch(-1);
    else if (e.key === ".") simStepStitch(1);
    else if (e.key === "<") simStepThread(-1);
    else if (e.key === ">") simStepThread(1);
    else return false;
    return true;
  }

  // ---- the canvas sizes itself to the pane ---------------------------------
  //
  // The bitmap was hardcoded `width="760" height="560"` and centred in a pane
  // that measures 980x836 at 1440x900 -- 52% of the available area -- and it
  // never grew on a wider screen, so the field stayed a fixed island with 242px
  // of dead height under it and 218px of dead width beside it.
  //
  // The bitmap is also cut at devicePixelRatio (capped at 2) rather than at
  // the CSS size, so the preview is sharp on a HiDPI screen instead of drawn
  // at half resolution and upscaled. That makes canvas.width/height DEVICE px
  // and every other measurement here CSS px — use cssW()/cssH() below, never
  // the raw attributes, and see renderRealistic's `dpr` option for why the
  // drawing code needs no other change.
  //
  // This is a VIEW change only, not a geometry one: renderRealistic derives its
  // entire mm->px transform from the canvas size (hoopTransform(garment,
  // cw, ch, pad)), so a bigger bitmap is the same hoop and the same design at
  // more pixels. No physical constant is touched -- every mm is unchanged, and
  // canvasPointFromEvent already rescales client px to canvas px, so pointer
  // math holds at any size.
  let hoopEl = null;
  let sizeObserver = null;
  let sizeRaf = 0;
  // Device pixel ratio the bitmap is currently sized for. Kept in state (not
  // read fresh at each use) so one paint can never mix two ratios, and so a
  // monitor change resizes the bitmap exactly once — see dprQuery below.
  let dpr = 1;
  let dprQuery = null;

  // The bitmap is sized in DEVICE px, everything else in CSS px. Capped at 2:
  // a 3x phone would triple the memory for a difference nobody can see at
  // arm's length, and this canvas is repainted on every drag frame.
  function currentDpr() {
    const raw = typeof window !== "undefined" ? window.devicePixelRatio : 1;
    return Math.min(2, Math.max(1, raw || 1));
  }

  // CSS-px size of the drawing surface. renderRealistic's transform puts the
  // context in CSS px at any dpr, so ALL layout/hit-test math below uses
  // these two, never canvas.width/height (which are device px).
  function cssW() { return canvas ? canvas.width / dpr : 0; }
  function cssH() { return canvas ? canvas.height / dpr : 0; }

  function fitCanvasToPane() {
    if (!canvas || !hoopEl) return;
    const r = hoopEl.getBoundingClientRect();
    // Floors, so a mid-layout measurement of 0 can never blank the canvas.
    // Deliberately NOT rounded here: the pane's CSS width is routinely
    // fractional (it's a flex child), and rounding it before scaling by dpr
    // throws away up to half a device pixel of the resolution this whole
    // change exists to gain. One rounding, at the end, on the device-px
    // figure that has to be an integer.
    const w = Math.max(320, r.width);
    const h = Math.max(240, r.height);
    const nextDpr = currentDpr();
    const bw = Math.round(w * nextDpr);
    const bh = Math.round(h * nextDpr);
    if (canvas.width === bw && canvas.height === bh && dpr === nextDpr) return;
    dpr = nextDpr;
    // Through a local alias, like setCanvasCursor: a member write on `canvas`
    // itself compiles to a `$.mutate` of `canvas`, which invalidates it
    // and re-runs `$: if (canvas) { project; runtime; paint(); }`, i.e. the
    // full regenerate and its stopSim() that the comment below exists to
    // avoid. Until 2026-11-07 it did exactly that on every resize.
    // EmbroideryField.cursor.spec.js fails on a direct write.
    const el = canvas;
    el.width = bw;  // note: assigning either dimension clears the bitmap,
    el.height = bh; // which is why the repaint below is unconditional.
    // repaintView(), NOT paint(): a resize changes the mm->px transform, not
    // the stitches, and paint() opens with stopSim() because a REGENERATION
    // invalidates the simulator's strand count. Going through paint() here
    // made the simulator un-openable: `.simbar` renders as an in-flow sibling
    // of `.hoop`, so opening it shrinks the canvas -> observer -> paint() ->
    // stopSim() -> `.simbar` unmounts -> canvas grows back -> observer again.
    // repaintView() re-renders from lastGenerateResult at the new size and
    // recomputes perElementRects (drag hit-testing) without touching the
    // simulator; it clears to fabric when there is nothing generated yet.
    repaintView();
  }

  onMount(() => {
    paint();
    if (hoopEl && typeof ResizeObserver !== "undefined") {
      sizeObserver = new ResizeObserver(() => {
        // Deferred to the next frame so our own width/height write cannot
        // re-enter the observer inside the same layout pass.
        if (sizeRaf) return;
        sizeRaf = requestAnimationFrame(() => { sizeRaf = 0; fitCanvasToPane(); });
      });
      sizeObserver.observe(hoopEl);
    }
    // Dragging the window between a HiDPI laptop screen and an external 1x
    // monitor changes devicePixelRatio without changing the CSS layout, so
    // the ResizeObserver above never fires and the bitmap would stay at the
    // old ratio. A `resolution` media query is the standard way to hear it;
    // it only matches the CURRENT ratio, so it's re-armed after each change.
    watchDpr();
    watchPointer();
    fitCanvasToPane();
  });

  function watchDpr() {
    if (typeof window === "undefined" || !window.matchMedia) return;
    if (dprQuery) dprQuery.removeEventListener("change", onDprChange);
    dprQuery = window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
    dprQuery.addEventListener("change", onDprChange);
  }

  function onDprChange() {
    watchDpr();
    fitCanvasToPane();
  }

  // Same shape as watchDpr: ask once, then listen, because the answer can
  // change without a layout change. Plugging a mouse into a tablet flips
  // `any-pointer: fine` while the empty-canvas sentence is on screen, and
  // that sentence is the only thing telling this customer the drawing tools
  // exist. `paint()` is what writes it, so the handler has to re-run paint
  // rather than just set the flag.
  function watchPointer() {
    if (typeof window === "undefined" || !window.matchMedia) return;
    pointerMq = window.matchMedia("(any-pointer: fine)");
    pointerMq.addEventListener("change", onPointerCapabilityChange);
  }

  function onPointerCapabilityChange() {
    hasFinePointer = readFinePointer();
    if (canvas) paint();
  }

  onDestroy(() => {
    setCompareSrc("");
    // The outline pulse is the one loop here that can be mid-flight with no
    // user input driving it, so it has to be cancelled explicitly — otherwise
    // a rAF fires into a destroyed component and repaints a dead canvas.
    if (pulseRafId) cancelAnimationFrame(pulseRafId);
    pulseRafId = 0;
    if (dprQuery) dprQuery.removeEventListener("change", onDprChange);
    dprQuery = null;
    if (pointerMq) pointerMq.removeEventListener("change", onPointerCapabilityChange);
    pointerMq = null;
    if (sizeRaf) cancelAnimationFrame(sizeRaf);
    sizeRaf = 0;
    if (sizeObserver) sizeObserver.disconnect();
    sizeObserver = null;
  });
  // repaint whenever the project (garment/elements/selection) or the
  // runtime image state changes. Drag-move deliberately reuses this same
  // path (cheap full regen) rather than a separate translate-only fast path
  // — regeneration is fast enough here and it keeps one code path for "the
  // project changed" instead of two. `view` is deliberately NOT a dependency
  // here (B2) -- wheel/pan/zoom-button handlers call scheduleViewRepaint()
  // directly instead, so a view-only change never pays for a full generateAll.
  $: if (canvas) { project; runtime; paint(); }

  // The canvas's accessible name. `stats` already says what is on the field
  // in the words the meta line uses, so the two never drift apart; the key
  // hint rides along because a focusable canvas gives no other clue that
  // arrows do anything.
  $: fieldLabel = hasDesign
    ? `Embroidery field. ${stats}. Arrow keys move the selected design, hold Shift for 10 mm steps.`
    : "Embroidery field. Nothing on it yet — add content to see your embroidery here.";

  // ---- zoom / pan -----------------------------------------------------------

  // Zooms from view.zoom to view.zoom*factor, solving for the panX/panY that
  // keep `anchorPx` (a canvas-px point, e.g. the cursor, or the canvas center
  // for the +/- buttons) fixed on screen -- the standard "zoom around a
  // point" recurrence, in canvas-px terms only (no need to know the mm point
  // under the anchor): for k = newZoom/oldZoom,
  //   pan' = (anchor - canvasCenter) * (1 - k) + pan * k
  // This is the same math preview.spec.js's B1 tests solve independently to
  // verify renderRealistic's view contract keeps an arbitrary mm-point fixed.
  function zoomBy(factor, anchorPx) {
    if (!canvas) return;
    const cw = cssW(), ch = cssH();
    const ccx = cw / 2, ccy = ch / 2;
    const p = anchorPx || { x: ccx, y: ccy };
    const oldZoom = view.zoom;
    const newZoom = clampZoom(oldZoom * factor);
    if (newZoom === oldZoom) return;
    const k = newZoom / oldZoom;
    const rawPanX = (p.x - ccx) * (1 - k) + view.panX * k;
    const rawPanY = (p.y - ccy) * (1 - k) + view.panY * k;
    // Soft clamp so panning/zooming can never push the hoop entirely off
    // canvas -- keeps at least some of the field's edge reachable. Shared
    // (lib/interact.js's clampPan) with the pan-drag branch of onPointerMove
    // below, so a pointer-capture drag gets the exact same clamp this does.
    const { panX, panY } = clampPan(rawPanX, rawPanY, newZoom, cw, ch);
    view = { zoom: newZoom, panX, panY };
    scheduleViewRepaint();
  }

  function onWheel(e) {
    e.preventDefault();
    if (dragMode) return; // B3: ignore wheel while a drag (move/resize/pan) is active
    if (!canvas) return;
    const p = canvasPointFromEvent(e);
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    zoomBy(factor, p);
  }

  function zoomIn() { zoomBy(1.25); }
  function zoomOut() { zoomBy(1 / 1.25); }
  function resetView() {
    if (view.zoom === 1 && view.panX === 0 && view.panY === 0) return;
    view = { zoom: 1, panX: 0, panY: 0 };
    scheduleViewRepaint();
  }

  // ---- pointer interaction -------------------------------------------------

  function canvasPointFromEvent(e) {
    const r = canvas.getBoundingClientRect();
    // Returns DRAWING-space px, which renderRealistic's transform makes CSS
    // px — the same space perElementRects and the overlay live in.
    //
    // Two corrections, and they are separate. The canvas's laid-out size
    // (r.width/height) can differ from the size the bitmap was cut for — it's
    // scaled down to fit the viewport via CSS `max-width`, or the observer
    // hasn't caught up with a resize yet — so client px are first converted
    // to bitmap px by canvas.width / r.width. That lands in DEVICE px, which
    // is dpr times too large, so dividing by dpr gets back to drawing space.
    // At dpr 1 with the bitmap matching its box, both factors are 1 and this
    // is the plain offset it has always been.
    const scaleX = canvas.width / r.width / dpr;
    const scaleY = canvas.height / r.height / dpr;
    return { x: (e.clientX - r.left) * scaleX, y: (e.clientY - r.top) * scaleY };
  }

  function cursorForHandle(handle) {
    if (handle === "nw" || handle === "se") return "nwse-resize";
    if (handle === "ne" || handle === "sw") return "nesw-resize";
    if (handle === "body") return "move";
    return "default";
  }

  function rectFor(id) {
    return perElementRects.find((r) => r.id === id) || null;
  }

  // Is the pointer on the selected element's rotate grip? (Grip hit area is
  // slightly larger than the drawn circle — same forgiveness corner handles
  // get from HANDLE_R.)
  function rotateGripHit(selRect, p) {
    if (!selRect || !rotatable()) return false;
    const grip = rotateGripPos(selRect);
    const dx = p.x - grip.x, dy = p.y - grip.y;
    return Math.sqrt(dx * dx + dy * dy) <= ROTATE_GRIP_R + 3;
  }

  // All ready elements' absolute mm bboxes EXCEPT the dragged one — the
  // snap candidates. peById is refreshed by every paint, so mid-drag these
  // track the latest generation (only the dragged element moves; it's
  // excluded precisely because it does).
  function otherBBoxes() {
    const out = [];
    for (const id in peById) {
      if (id !== dragTargetId && peById[id] && peById[id].bboxMm) out.push(peById[id].bboxMm);
    }
    return out;
  }

  function updateHoverCursor(p) {
    if (!canvas) return;
    if (multiSel) {
      const g = groupRectPx();
      const handle = g ? hitTest(g, p.x, p.y, HANDLE_R) : "none";
      if (handle !== "none") {
        setCanvasCursor(cursorForHandle(handle));
        return;
      }
      const hitId = pickElement(perElementRects, p.x, p.y);
      setCanvasCursor(hitId ? "move" : view.zoom > 1 ? "grab" : "default");
      return;
    }
    const selRect = rectFor(project.selectedId);
    if (rotateGripHit(selRect, p)) {
      setCanvasCursor("grab");
      return;
    }
    // Mirrors the pointerdown precedence exactly. Without this the cursor
    // would keep promising "move the element" right up to the moment a click
    // edits a shape instead — the affordance has to agree with the behaviour.
    const hoverEdit = editableOutlinesPx();
    // Reshape mode: a point is grabbable, anywhere else is a marquee.
    if (reshapeOn() && hoverEdit && hoverEdit.el.id === reshape.elId) {
      setCanvasCursor(reshapeNodeAt(hoverEdit, p) ? "grab" : "crosshair");
      return;
    }
    // A selected hand-drawn shape's anchors and handles are grabbable; its
    // edges take a click (insert), which the "pointer" below already says.
    if (hoverEdit && hoverEdit.el.type === "manual" && selectedShapeId && selectedShapeElId === hoverEdit.el.id) {
      const ap = authoredPxFor(hoverEdit.el, selectedShapeId);
      const ah = ap ? hitAuthored(ap, p.x, p.y, !isOpenShape(ap.shape)) : null;
      if (ah && ah.kind !== "edge") {
        setCanvasCursor("grab");
        return;
      }
    }
    if (hoverEdit && hitOverlay(liveOutlinesPx(hoverEdit), p.x, p.y)) {
      setCanvasCursor("pointer");
      return;
    }
    let handle = selRect ? hitTest(selRect, p.x, p.y, HANDLE_R) : "none";
    if (handle === "none") {
      // Nothing on the selected element under the pointer — is some OTHER
      // element's body there instead? (Other elements don't show handles,
      // so this is a plain bounding-box test via pickElement, not hitTest.)
      const hitId = pickElement(perElementRects, p.x, p.y);
      if (hitId) {
        handle = "body";
      } else if (view.zoom > 1) {
        // Empty space, but there's room to pan -- hint it's draggable.
        setCanvasCursor("grab");
        return;
      }
    }
    setCanvasCursor(cursorForHandle(handle));
  }

  function schedulePatchFlush() {
    if (rafScheduled) return;
    rafScheduled = true;
    requestAnimationFrame(() => {
      rafScheduled = false;
      if (pendingPatch) {
        const p = pendingPatch;
        pendingPatch = null;
        // Group drags carry one patch PER member ({ multi: { id: patch } });
        // single-element drags keep the original { id, patch } shape.
        if (p.multi) dispatch("elupdatemany", p.multi);
        else dispatch("elupdate", p);
      }
    });
  }

  // ---- the canvas tool menu (right-click) ----------------------------------
  //
  // `+ Shape` and `+ Draw shapes` left the Content step's tile row on
  // 2026-08-13: Kent asked for the upload buttons to collapse to one, and
  // ruled these two are not uploads at all — they are drawing TOOLS, and a
  // tool belongs on the surface you draw on. Nothing was deleted; both
  // element types, panels and their tests are untouched. Only the way in
  // moved.
  //
  // `{ x, y }` are offsets within the canvas's own positioned parent, so the
  // menu lands under the pointer at any zoom or scroll position.
  let fieldMenu = null;

  function onContextMenu(e) {
    // The simulator owns the canvas while playing; Original view shows the
    // artwork, whose pixels the stitch outlines need not line up with.
    if (simActive || originalView) return;
    // A live hole draft owns the canvas: no menu (its "Add hole" would restart it).
    if (holeDraftOn() || shapeMoveOn()) { e.preventDefault(); return; }
    e.preventDefault();             // our menu, not the browser's
    if (!canvas) return;
    const r = canvas.getBoundingClientRect();
    fieldMenu = { x: e.clientX - r.left, y: e.clientY - r.top, shape: shapeUnderPointer(e) };
  }

  // The recognised shape under a right-click, if any, with the border items
  // the menu offers for it (Kent's 2026-09-09 ask: a clickable border on the
  // image — right-click, Add, Remove). The element is the one a left-click
  // would pick; its shape is the outline the pointer is ON, else the smallest
  // one it is INSIDE — the border is the outline, but nobody aims at a
  // one-pixel line to ask for one. Hidden and deleted shapes are not offered.
  // Selecting the element and the shape first is the editor's own rule
  // ("first click on a shape selects it and stops there"): the amber
  // highlight shows which shape the items are about to change.
  function shapeUnderPointer(e) {
    const plain = shapeUnderPointerPlain(e);
    if (!reshapeOn() || !renderResult) return plain;
    const edit = editableOutlinesPx();
    if (!edit || edit.el.id !== reshape.elId) return plain;
    const node = reshapeNodeAt(edit, canvasPointFromEvent(e));
    if (!node) return plain;
    // Right-clicking a point that is not selected selects it (as a click does).
    if (!reshapeSelHas(edit.el.id, node.shapeId, node.ring, node.index)) {
      const only = new Map();
      selAdd(only, node.shapeId, node.ring, node.index);
      setReshapeSel(only);
    }
    const n = reshapeSelCount(reshape);
    // Point rows lead the menu; "Simplify points" (digitized lane) follows
    // "Select all points" as one row per tolerance.
    const rows = [
      { id: "delpoint", label: n > 1 ? `Delete ${n} points` : "Delete point", value: null, title: "Remove the selected points; a ring keeps at least 3." },
      { id: "selectall", label: "Select all points", value: null, title: "Select every point of this shape.", shapeId: node.shapeId },
      ...(node.ring !== RING_EXTERIOR && node.ring !== RING_ANCHORS
        ? [{ id: "delhole", label: "Delete hole", value: null, title: "Remove this hole; the shape is solid there.", shapeId: node.shapeId, ring: node.ring }]
        : []),
      ...(edit.el.type === "digitized"
        ? SIMPLIFY_TOLS_MM.map((tol) => ({ id: `simplify-${tol}`, label: `Simplify points ${tol} mm`, value: null, title: `Fewer points on this shape, within ${tol} mm of the current outline.`, shapeId: node.shapeId, tol }))
        : []),
    ];
    const rest = plain && plain.items ? plain.items.filter((it) => it.id !== "removepoint") : [];
    if (plain) return { ...plain, items: [...rows, ...rest] };
    const row = (edit.rows || []).find((x) => x && x.id === node.shapeId);
    return { elId: edit.el.id, shapeId: node.shapeId, name: row ? shapeMenuName(row) : "Shape", state: null, items: rows };
  }

  function shapeUnderPointerPlain(e) {
    if (!renderResult || !project) return null;
    const p = canvasPointFromEvent(e);
    // An ANCHOR of the selected hand-drawn shape: the menu's shape section
    // is that shape, with Remove point (2026-09-29 field-node-edit spec §5).
    // The manual lane has no border items; everything else on it falls
    // through to the digitized-only search below, as before.
    const selEl = selectedShapeElement();
    if (selEl && selEl.type === "manual") {
      const ap = authoredPxFor(selEl, selectedShapeId);
      const ah = ap ? hitAuthored(ap, p.x, p.y, !isOpenShape(ap.shape)) : null;
      if (ah && ah.kind === "anchor") {
        const model = popoverModel({ element: selEl, shapeId: selectedShapeId });
        const atFloor = ap.shape.points.length <= anchorFloor(ap.shape);
        return {
          elId: selEl.id,
          shapeId: selectedShapeId,
          name: model ? model.name : "Shape",
          state: null,
          items: [{
            id: "removepoint",
            label: "Remove point",
            value: null,
            title: atFloor ? anchorFloorMessage(ap.shape) : "Remove this point; its two edges become one.",
            disabled: atFloor,
            anchor: ah.index,
          }],
        };
      }
    }
    // Every digitized element's outlines, the selected one first and then
    // the rest topmost first (later elements draw over earlier ones). Not
    // gated on the element's bounding rect: an outline's drawn edge sits a
    // pixel or two outside the geometry it is stroked around, and the whole
    // point of `hitOverlay`'s grab tolerance is that aiming at the line
    // works — the left-click editor has the same rule.
    const els = (project.elements || []).filter((x) => x && x.type === "digitized");
    const ordered = [
      ...els.filter((x) => x.id === project.selectedId),
      ...els.filter((x) => x.id !== project.selectedId).reverse(),
    ];
    const cands = [];
    for (const el of ordered) {
      const edit = outlinesPxFor(el);
      if (!edit) continue;
      const hidden = hiddenShapeIds(el, edit.rows);
      cands.push({ el, edit, live: edit.outlines.filter((o) => !hidden.has(o.id)) });
    }
    let el = null;
    let edit = null;
    let hit = null;
    for (const c of cands) {
      hit = hitOverlay(c.live, p.x, p.y);
      if (hit) { el = c.el; edit = c.edit; break; }
    }
    if (!hit) {
      for (const c of cands) {
        hit = hitShapeInterior(c.live, p.x, p.y);
        if (hit) { el = c.el; edit = c.edit; break; }
      }
    }
    if (!hit) return null;
    // Also when the element is only the PRIMARY of a multi-selection: the
    // group panel has no "Auto Digitize Image" button, so an edit made there
    // would sit unsewn with nothing in front to press. A plain select
    // collapses the group to this element, as it does for any other element.
    if (project.selectedId !== el.id || multiSel) dispatch("select", el.id);
    setSelectedShape(hit.shapeId);
    shapeEditError = "";
    drawOverlay();
    const row = edit.rows.find((x) => x && x.id === hit.shapeId) || {};
    const entry = (el.shapeOverrides || {})[hit.shapeId];
    const design = el.params ? el.params.border : null;
    return {
      elId: el.id,
      shapeId: hit.shapeId,
      name: shapeMenuName(row),
      // What this shape's border ACTUALLY is, read off the stitch plan
      // (design.runs) rather than off the request the two items below write.
      // The menu used to offer "Remove border" on shapes with no border on
      // them -- the engine declines a satin-tiered shape outright and gives a
      // too-narrow one a bean run -- so the action is now labelled by what is
      // there. Absent `runs` the state says "requested" and claims nothing;
      // see lib/borderMenu.js.
      state: shapeBorderState({
        shapeId: hit.shapeId,
        entry,
        designBorder: design,
        index: indexRuns(el.result, new Set((edit.rows || []).map((r) => r && r.id))),
        tier: row.tier,
        pending: borderRequestPending(appliedBorders(el.appliedEdits), hit.shapeId, entry),
      }),
      items: [
        ...borderMenuItems(entry, design),
        ...(isCapPieceId(hit.shapeId) ? [] : [{ id: "moveshape", label: "Move shape", value: null, title: "Drag or nudge this whole shape; its stitches follow when you finish." }]),
        ...(isCapPieceId(hit.shapeId) ? [] : [{ id: "addhole", label: "Add hole", value: null, title: "Draw a polygon inside this shape; it becomes a hole." }]),
      ],
    };
  }

  function shapeMenuName(row) {
    const parts = [row.threadNumber ? "Thread #" + row.threadNumber : "Shape"];
    const a = row.areaMm2;
    if (a != null) parts.push((a >= 100 ? Math.round(a) : Number(a).toFixed(1)) + " mm²");
    return parts.join(" · ");
  }

  // Writes the chosen border value into the SAME field the Digitize panel's
  // Border select writes (`shapeOverrides[sid].border`, contract v1), through
  // the same `elupdate` path `commitShapeEdit` uses — one undo step, the
  // panel's select shows it, and the restitch follows after the idle pause.
  // `null` clears the override (the "Use design setting" item); an entry
  // left empty is dropped, as DigitizePanel's setOverride drops it.
  function chooseBorder(item) {
    const menu = fieldMenu;
    fieldMenu = null;
    if (!menu || !menu.shape || !project) return;
    const el = (project.elements || []).find((x) => x.id === menu.shape.elId);
    if (!el) return;
    const cur = { ...(el.shapeOverrides || {}) };
    const entry = { ...(cur[menu.shape.shapeId] || {}) };
    if (item.value == null) delete entry.border;
    else entry.border = item.value;
    if (Object.keys(entry).length) cur[menu.shape.shapeId] = entry;
    else delete cur[menu.shape.shapeId];
    dispatch("elupdate", { id: el.id, patch: { shapeOverrides: cur } });
  }

  // "Select all points": every point of one shape (all of its rings).
  function selectAllPointsOf(shapeId) {
    const edit = editableOutlinesPx();
    if (!edit || !reshape || edit.el.id !== reshape.elId) return;
    const sel = new Map();
    if (edit.el.type === "manual") {
      const sh = manualShapeOf(edit.el, shapeId);
      if (sh) (sh.points || []).forEach((_, i) => selAdd(sel, shapeId, RING_ANCHORS, i));
    } else {
      // Sparse nodes: "all points" is all NODES of every ring.
      const shellNodes = edit.nodesById.get(shapeId);
      if (shellNodes) shellNodes.forEach((_, i) => selAdd(sel, shapeId, RING_EXTERIOR, i));
      (edit.holesById.get(shapeId) || []).forEach((_, k) => {
        const hn = edit.nodesById.get(ringKey(shapeId, k));
        if (hn) hn.forEach((__, i) => selAdd(sel, shapeId, k, i));
      });
    }
    setReshapeSel(sel);
  }

  // "Delete hole": the hole ring the right-clicked point sits on goes whole;
  // the shape is solid there. (There is no way to ADD a hole yet: a future
  // "Add hole" would draw a new ring inside the shell and append it to the
  // shape's holes_override, through the same ringEditOverrides.)
  function deleteHoleRing(shapeId, ring) {
    const edit = editableOutlinesPx();
    const el = edit && edit.el;
    if (!el || el.type !== "digitized" || ring === RING_EXTERIOR) return;
    if (commitRingEdits(el, editBasis(edit), new Map(), new Map([[shapeId, new Set([ring])]]), new Map())) {
      if (reshapeOn()) setReshapeSel(new Map());
    }
  }

  // One entry point for the shape section's items: Remove point (a
  // hand-drawn shape's anchor, the same path Delete takes) or a border item.
  function chooseMenuItem(item) {
    if (typeof item.id === "string" && item.id.startsWith("simplify-")) {
      const menu = fieldMenu;
      fieldMenu = null;
      const el = menu && menu.shape && project ? (project.elements || []).find((x) => x.id === menu.shape.elId) : null;
      if (el && el.type === "digitized") simplifyShapes(el, [item.shapeId], item.tol);
      repaintNodeChrome();
      return;
    }
    if (item.id === "moveshape") {
      const menu = fieldMenu;
      fieldMenu = null;
      const el = menu && menu.shape && project ? (project.elements || []).find((x) => x.id === menu.shape.elId) : null;
      if (el) enterShapeMove(el, menu.shape.shapeId);
      return;
    }
    if (item.id === "addhole") {
      const menu = fieldMenu;
      fieldMenu = null;
      const el = menu && menu.shape && project ? (project.elements || []).find((x) => x.id === menu.shape.elId) : null;
      if (el) enterHoleDraft(el, menu.shape.shapeId);
      return;
    }
    if (item.id === "delhole") {
      fieldMenu = null;
      deleteHoleRing(item.shapeId, item.ring);
      repaintNodeChrome();
      return;
    }
    if (item.id === "delpoint" || item.id === "selectall") {
      fieldMenu = null;
      if (item.id === "delpoint") deleteReshapeSelection();
      else selectAllPointsOf(item.shapeId);
      repaintNodeChrome();
      return;
    }
    if (item.id !== "removepoint") {
      chooseBorder(item);
      return;
    }
    const menu = fieldMenu;
    fieldMenu = null;
    if (!menu || !menu.shape || item.disabled) return;
    if (removeAnchorOf(menu.shape.elId, menu.shape.shapeId, item.anchor)) focusedAnchor = null;
    repaintNodeChrome();
  }

  function chooseFieldMenu(type) {
    fieldMenu = null;
    dispatch("addelement", type);
  }

  // Any press that is not ON the menu closes it. Capture phase so it runs
  // before the menu button's own click handler would be skipped by the
  // re-render, and `closest` so pressing a menu item does not dismiss it out
  // from under its own click.
  function onWindowPointerDown(e) {
    const inside = (cls) => e.target && e.target.closest && e.target.closest(cls);
    if (fieldMenu && !inside(".fieldmenu")) fieldMenu = null;
    // A press anywhere but on the popover (or its ThreadPicker's open list,
    // .tp-panel) closes it; the canvas press that follows decides whether
    // another shape opens it again.
    if (shapePop && !inside(".shapepop") && !inside(".tp-panel")) closeShapePop();
  }

  // A PointerEvent's `detail` is always 0 (measured 2026-11-05: pointerdown:0
  // mousedown:2 click:2 on a double click), so a double press is counted here: a
  // press within 450 ms and 6 px of the last one is the next of the series.
  //
  // A series is a PAIR: the press after a double press starts a new one.
  // Otherwise a drag begun on a node right after double-clicking it (inside
  // 450 ms, same spot) counted as press 3, read as another double press and
  // toggled the node straight back (field-reshape-nodes (s2) in CI,
  // 2026-11-07). That race was hidden while every pointer event re-ran
  // paint() through a cursor write, which slowed the presses past 450 ms.
  let lastPress = null;   // { t, x, y, n }
  function countPress(e) {
    const prev = lastPress;
    const n = prev && prev.n < 2 && e.timeStamp - prev.t < 450 && Math.hypot(e.clientX - prev.x, e.clientY - prev.y) < 6 ? prev.n + 1 : 1;
    lastPress = { t: e.timeStamp, x: e.clientX, y: e.clientY, n };
  }
  const isDoublePress = () => !!lastPress && lastPress.n >= 2;

  function onPointerDown(e) {
    // A right-click opens the tool menu (onContextMenu) and must never also
    // start a drag, a selection or a shape edit — every branch below assumes
    // the primary button.
    if (e.button !== undefined && e.button !== 0) return;
    countPress(e);
    if (fieldMenu) fieldMenu = null;

    // Auto-dismiss the drag-field hint on the first pointerdown on the
    // canvas WHILE it's actually showing -- gating on showDragHint (rather
    // than dismissing unconditionally) means a click on an empty field
    // before any design exists can never burn the one teaching moment this
    // hint exists for (it isn't eligible/shown yet at that point). App.svelte
    // owns the persisted hints.js dismiss() call; this only reports that the
    // interaction happened.
    if (showDragHint) dispatch("dismisshint");

    // Watch-modes: no select/drag/resize during playback, nor over the
    // Original artwork (a shape click would open the popover over the image,
    // and on the digitized lane hit-test outlines the image does not match).
    if (simActive || originalView) return;
    if (!canvas || !renderResult) return;
    const p = canvasPointFromEvent(e);
    // Move shape: any left press drags the shape (no marquee, no element drag,
    // no node grab; Ctrl/Alt/Shift mean nothing here), or hits Done / Discard.
    if (shapeMoveOn()) {
      shapeMovePress(e, p);
      canvas.focus({ preventScroll: true });
      return;
    }
    // Add hole: while a ring is being drawn the press is a vertex (or the
    // cross, or the close); a press on another element ends the draft and
    // falls through to select it.
    // Ctrl/Cmd is a plain press here: no quick drag or marquee over a live draft.
    if (holeDraftOn() && holeDraftPress(p)) {
      canvas.focus({ preventScroll: true });   // Backspace / Enter / Escape go to the canvas
      return;
    }
    // The anchor focus lasts until the next press: a press ON an anchor sets
    // it again below; any other (an edge insert shifts the indices, a click
    // elsewhere means something else) must not leave Delete aimed at a point.
    if (focusedAnchor) {
      focusedAnchor = null;
      repaintNodeChrome();
    }

    // Ctrl/Cmd+click: toggle the clicked element in the multi-selection.
    // Toggling never starts a drag — the NEXT (plain) pointerdown drags the
    // group. A ctrl-click on empty field is a no-op (selection stays).
    if (e.ctrlKey || e.metaKey) {
      const hitId = pickElement(perElementRects, p.x, p.y);
      if (hitId) dispatch("toggleselect", hitId);
      return;
    }

    // Group mode: the union box owns its area — corners group-resize, body
    // group-moves. A plain click OUTSIDE the group box collapses selection
    // to whatever was clicked (or falls through to pan on empty space).
    if (multiSel) {
      const g = groupRectPx();
      const handle = g ? hitTest(g, p.x, p.y, HANDLE_R) : "none";
      if (handle !== "none") {
        const members = [];
        const memberBoxes = [];
        for (const id of selIds) {
          const el2 = project.elements.find((x) => x.id === id);
          const pe2 = peById[id];
          if (!el2 || !pe2) continue;
          const w = pe2.bboxMm.x1 - pe2.bboxMm.x0;
          // Field names deliberately match groupResizePatches' member
          // contract (offsetXMm/offsetYMm) — a short alias here once
          // silently zeroed every offset in the resize fan-out.
          members.push({ id, offsetXMm: el2.offsetXMm || 0, offsetYMm: el2.offsetYMm || 0, widthMm: w, targetMm: el2.sizeMm != null ? el2.sizeMm : w });
          memberBoxes.push(pe2.bboxMm);
        }
        if (!members.length) return;
        canvas.setPointerCapture(e.pointerId);
        dragMembers = members;
        dragGroupBBoxMm = unionBBox(memberBoxes);
        dragStartPx = p;
        dragTargetId = null;
        if (handle === "body") {
          dragMode = "gmove";
        } else {
          dragMode = "gresize";
          dragHandle = handle;
        }
        setCanvasCursor(cursorForHandle(handle));
        return;
      }
      const hitId = pickElement(perElementRects, p.x, p.y);
      if (hitId) {
        dispatch("select", hitId); // plain click: collapse to that element
        return;
      }
      if (view.zoom > 1) {
        canvas.setPointerCapture(e.pointerId);
        dragMode = "pan";
        dragStartPx = p;
        dragStartPanX = view.panX;
        dragStartPanY = view.panY;
        setCanvasCursor("grabbing");
      }
      return;
    }

    // Rotate grip first — it sits OUTSIDE the selection rect (above the top
    // edge), so it can never shadow a corner/body hit and must be tested
    // before them. Selected element only (it's the only one drawn a grip).
    const selRect = rectFor(project.selectedId);
    if (rotateGripHit(selRect, p)) {
      const el = selectedElement();
      canvas.setPointerCapture(e.pointerId);
      dragMode = "rotate";
      dragTargetId = project.selectedId;
      dragStartPx = p;
      dragStartRotationDeg = (el && el.rotationDeg) || 0;
      dragRotateCenterPx = { x: selRect.x + selRect.w / 2, y: selRect.y + selRect.h / 2 };
      rotateBadgeDeg = dragStartRotationDeg;
      setCanvasCursor("grabbing");
      return;
    }

    // Reshape mode owns the press next: a point is selected or dragged, anywhere
    // else is a marquee (the one new meaning of a bare drag, and only here).
    if (reshapeOn()) {
      const btn = reshapeBtnAt(p);
      if (btn) {
        if (btn === "done") endReshape(); else discardReshape();
        drawOverlay();
        return;
      }
      const rEdit = editableOutlinesPx();
      if (rEdit && rEdit.el.id === reshape.elId && reshapePress(e, p, rEdit)) return;
    }

    // Shape outlines beat the element body. Tested after the rotate grip
    // (which sits outside the rect and must never be shadowed) and before the
    // element rect below, so grabbing a node or a line edits the SHAPE while
    // everywhere else inside the element still moves the whole element.
    const edit = editableOutlinesPx();
    if (edit) {
      // A SELECTED hand-drawn shape's authored anchors, curve handles and
      // edges come first (2026-09-29 field-node-edit spec §5): an anchor or
      // handle press starts a node drag, an edge press waits for its release
      // (a click inserts an anchor there; a drag does nothing). Anywhere else
      // on the outline falls through to the selection branch below.
      if (edit.el.type === "manual" && selectedShapeId && selectedShapeElId === edit.el.id) {
        const ap = authoredPxFor(edit.el, selectedShapeId);
        const ah = ap ? hitAuthored(ap, p.x, p.y, !isOpenShape(ap.shape)) : null;
        if (ah) {
          canvas.setPointerCapture(e.pointerId);
          shapeEditError = "";
          pressClient = { x: e.clientX, y: e.clientY, px: p };
          pressOutline = false;
          if (ah.kind === "edge") {
            pressEdge = { elId: edit.el.id, shapeId: selectedShapeId, index: ah.index };
            return;
          }
          // Pressing an anchor focuses it (a Delete then removes it). Every
          // other press already dropped the focus at the top of this handler.
          if (ah.kind === "anchor") focusedAnchor = { elId: edit.el.id, shapeId: selectedShapeId, index: ah.index };
          // The drag is RELATIVE: `grab` is the node minus the press point, in
          // authored px through the same frozen fit, so a press a few px off
          // the node's centre does not snap the node to the pointer.
          const nodeAt = fieldPxToAuthored(ap.fit, { x: ah.atPx[0], y: ah.atPx[1] });
          const pressAt = fieldPxToAuthored(ap.fit, p);
          // `shapes` and `boxOk` are frozen with the fit: the hold-last-good
          // guard in onPointerMove tests every frame against the element as
          // it stood at press, and only holds a shape at the placement box if
          // it started inside it (one already past keeps the old behaviour).
          nodeEdit = { elId: edit.el.id, shapeId: selectedShapeId, kind: ah.kind, index: ah.index,
                       basis: { fit: ap.fit, shape: ap.shape, shapes: (edit.el.shapes || []).slice(),
                                boxOk: ringInsideBox(ap.shape, ap.fit, hoopSizeMm(project)) },
                       live: ap.shape,
                       grab: { dx: nodeAt.x - pressAt.x, dy: nodeAt.y - pressAt.y }, moving: false };
          setCanvasCursor("grabbing");
          repaintNodeChrome();
          return;
        }
      }
      // Hidden and deleted shapes are not drawn, so they are not grabbable.
      const shapeHit = hitOverlay(liveOutlinesPx(edit), p.x, p.y);
      const capHit = capHitAt(edit, p);
      // The cap rides the silhouette, which is also the outer shape's outline,
      // so one press spot can mean either. The shape wins first (a press on an
      // outline has always selected its shape); pressing the same spot again,
      // with that shape already selected, selects the cap stretch instead, and
      // the next press goes back to the shape. Nodes and double-click stay the
      // shape's, so node editing is untouched.
      const ownShape = !!shapeHit && shapeHit.shapeId === selectedShapeId
        && edit.el.id === selectedShapeElId;
      const wantsCap = !!capHit && (!shapeHit || (ownShape && shapeHit.kind !== "node" && !(e.detail >= 2)));
      const hit = wantsCap ? capHit : shapeHit;
      if (hit) {
        // First click on a shape selects it and stops there — no geometry
        // moves until you have said which shape you mean. On the manual and
        // preset lanes the RING always stops there: a hand-drawn shape is
        // edited through its authored anchors/handles/edges (the branch
        // above), never by dragging the flattened ring; a preset has none.
        // The popover waits for the RELEASE (endDrag's click test): a press
        // that turns into a drag opens nothing. Capture so the release
        // reaches endDrag even if it lands off the canvas.
        if (hit.shapeId !== selectedShapeId || edit.el.id !== selectedShapeElId || edit.el.type !== "digitized"
            || isCapPieceId(hit.shapeId)) {
          selectedShapeId = hit.shapeId;
          selectedShapeElId = edit.el.id;
          shapeEditError = "";
          if (edit.el.type === "manual") dispatch("shapeselect", { elementId: edit.el.id, shapeId: hit.shapeId });
          canvas.setPointerCapture(e.pointerId);
          pressClient = { x: e.clientX, y: e.clientY, px: p };
          pressOutline = true;
          repaintNodeChrome(); // a previously selected shape's ring must go
          return;
        }
        const hitKey = ringKey(hit.shapeId, hit.ring);
        const ring = edit.mmById.get(hitKey);
        const nodes = edit.nodesById.get(hitKey);
        if (ring && nodes) {
          canvas.setPointerCapture(e.pointerId);
          shapeEditError = "";
          if (isDoublePress() && hit.kind === "edge") {
            // Double-click an edge to add a node there (a CORNER, nothing
            // else moves — sparse nodes, 2026-11-05). Commits immediately:
            // there is no drag to wait for.
            const d = pxToMmDelta(hit.atPx[0] - renderResult.toCanvas(0, 0).x,
                                  hit.atPx[1] - renderResult.toCanvas(0, 0).y);
            const grown = insertNodeOnPath(ring, nodes, [d.dx, d.dy]);
            commitNodeRing(edit.el, edit, hitKey, grown.ring, grown.nodes);
            canvas.releasePointerCapture(e.pointerId);
            drawOverlay();
            return;
          }
          if (isDoublePress() && hit.kind === "node") {
            // Double-click a node: corner <-> smooth.
            toggleNodeAt(edit, { shapeId: hit.shapeId, ring: hit.ring, index: hit.index });
            canvas.releasePointerCapture(e.pointerId);
            drawOverlay();
            return;
          }
          shapeEdit = { elId: edit.el.id, shapeId: hit.shapeId, ringId: hit.ring, kind: hit.kind,
                        index: hit.index, startPx: p, startClient: { x: e.clientX, y: e.clientY }, armed: false, ring, nodes, moved: false,
                        basis: editBasis(edit) };
          liveRing = { shapeId: hit.shapeId, key: hitKey, points: ring, nodes };
          setCanvasCursor("grabbing");
          drawOverlay();
          return;
        }
      }
      // Clicked away from every outline — drop the shape selection before
      // falling through, so the next click on an outline selects rather than
      // edits, and Delete stops being armed.
      if (selectedShapeId) {
        setSelectedShape(null);
        focusedAnchor = null;
        // Not a bare drawOverlay: it paints over the last render without
        // clearing, so the dropped amber ring and node dots would stay.
        repaintNodeChrome();
      }
    }

    // Hit-test the SELECTED element's rect first (corners win over body) —
    // that's the only element with visible handles, so it's the only one a
    // resize can start on.
    let targetId = project.selectedId;
    let rect = rectFor(targetId);
    let handle = rect ? hitTest(rect, p.x, p.y, HANDLE_R) : "none";

    if (handle === "none") {
      // Missed the selected element entirely — see if some OTHER element's
      // body is under the pointer instead (topmost wins on overlap).
      const hitId = pickElement(perElementRects, p.x, p.y);
      if (!hitId) {
        // Empty space, no design hit -- pan the view instead when there's
        // room to (zoom > 1). Design-drag always wins over pan (this branch
        // is only reached once neither the selected element's handles nor
        // any other element's body matched), per the spec.
        if (view.zoom > 1) {
          canvas.setPointerCapture(e.pointerId);
          dragMode = "pan";
          dragStartPx = p;
          dragStartPanX = view.panX;
          dragStartPanY = view.panY;
          setCanvasCursor("grabbing");
        }
        return; // selection unchanged either way
      }
      if (hitId !== targetId) dispatch("select", hitId);
      targetId = hitId;
      rect = rectFor(targetId);
      handle = "body"; // pickElement only tests bounding boxes -> always a body-drag start
    }

    const pe = peById[targetId];
    const el = project.elements.find((e2) => e2.id === targetId);
    if (!pe || !el) return; // defensive: rect implies both should exist

    canvas.setPointerCapture(e.pointerId);
    dragTargetId = targetId;
    dragStartPx = p;
    pressClient = { x: e.clientX, y: e.clientY, px: p };
    pressOutline = false;
    dragStartOffXMm = el.offsetXMm || 0;
    dragStartOffYMm = el.offsetYMm || 0;
    dragStartWidthMm = pe.bboxMm.x1 - pe.bboxMm.x0;
    dragStartHeightMm = pe.bboxMm.y1 - pe.bboxMm.y0;
    dragStartBBoxMm = pe.bboxMm; // move-snap translates this by the live drag delta
    dragStartTargetMm = el.sizeMm != null ? el.sizeMm : dragStartWidthMm;
    setCanvasCursor(cursorForHandle(handle));

    if (handle === "body") {
      dragMode = "move";
    } else {
      dragMode = "resize";
      dragHandle = handle;
      // If sizeMm is still "auto-fit" (null), seed it from the design's
      // CURRENT on-screen width so the drag continues from what's visible
      // instead of jumping to whatever the auto-fit width happens to be
      // recomputed as on the next paint.
      if (el.sizeMm == null) {
        dispatch("elupdate", { id: targetId, patch: { sizeMm: dragStartWidthMm } });
      }
    }
  }

  // The cursor, set through a local alias. In Svelte's legacy mode a member
  // write on `canvas` itself (`canvas.style.cursor = ...`) invalidates
  // `canvas`, which re-runs `$: if (canvas) { project; runtime; paint(); }`,
  // and paint() opens with stopSim(): the first pointer move over the field
  // closed the simulator (measured 2026-11-07, any mouse move, any zoom).
  // EVERY cursor write goes through this (the edit-mode hover and drag ones
  // too, 2026-11-07): there each hover re-ran paint(), the full regenerate,
  // and two scheduleViewRepaint()s, to change nothing. A cursor is not a
  // reason to repaint. EmbroideryField.cursor.spec.js fails on a direct one.
  function setCanvasCursor(c) {
    const el = canvas;
    if (el) el.style.cursor = c;
  }

  function onPointerMove(e) {
    if (!canvas) return;
    if (simActive || originalView) { setCanvasCursor("default"); return; }
    const p = canvasPointFromEvent(e);
    if (shapeMove && shapeMove.drag) {
      shapeMoveDrag(e, p);
      return;
    }
    if (marquee) {
      marquee.curPx = p;
      marquee = marquee;
      repaintNodeChrome();
      return;
    }
    if (reshapeDrag) {
      reshapeDragMove(e, p);
      return;
    }
    // A shape edit is its own drag mode — it never sets `dragMode`, so the
    // element move/resize/pan branches below stay untouched by it.
    if (shapeEdit) {
      // Under CLICK_PX of the press it is still a click (a select, the first
      // half of a double-click): nothing moves, nothing commits. Latched once past.
      if (!shapeEdit.armed) {
        if (!pastClickDeadZone(shapeEdit.startClient, { x: e.clientX, y: e.clientY }, CLICK_PX)) return;
        shapeEdit.armed = true;
      }
      const d = pxToMmDelta(p.x - shapeEdit.startPx.x, p.y - shapeEdit.startPx.y);
      // Sparse nodes (2026-11-05): a node drag moves that node exactly and
      // rebuilds its two spans; an edge drag moves both end nodes of the span
      // the edge lies in and rebuilds it and its two outer spans. Alt keeps
      // the soft pull on the polygon vertices (no rebuild).
      const se = shapeEdit;
      let idx;
      if (se.kind === "edge") {
        const k = spanOfEdge(se.nodes, se.index);
        idx = [k, (k + 1) % se.nodes.length];
      } else idx = [se.index];
      let next, nextNodes;
      if (e.altKey) {
        next = se.kind === "edge"
          ? moveEdge(se.ring, se.index, d.dx, d.dy, { soft: true })
          : moveNodes(se.ring, [se.nodes[se.index].i], d.dx, d.dy, { soft: true });
        nextNodes = se.nodes;
      } else {
        const m = moveNodeSet(se.ring, se.nodes, idx, d.dx, d.dy, false);
        next = m.ring;
        nextNodes = m.nodes;
      }
      shapeEdit.moved = true;
      liveRing = { shapeId: shapeEdit.shapeId, key: ringKey(shapeEdit.shapeId, shapeEdit.ringId), points: next, nodes: nextNodes };
      repaintNodeChrome(); // a bare drawOverlay smears every frame of the drag
      return;
    }
    // A hand-drawn node drag: ONE anchor (or one segment's handle) follows
    // the pointer, mapped back to authored px through the fit frozen at press
    // and kept at the press's grab offset (relative, so it never jumps). Moves
    // under CLICK_PX of the press are ignored: until the pointer has really
    // travelled, `live` stays the basis object, so a click commits nothing
    // (endDrag's `changed` test) and trackpad jitter cannot bow a segment.
    if (nodeEdit) {
      if (!nodeEdit.moving) {
        if (!pressClient || Math.hypot(e.clientX - pressClient.x, e.clientY - pressClient.y) < CLICK_PX) return;
        nodeEdit.moving = true;
      }
      const q = fieldPxToAuthored(nodeEdit.basis.fit, p);
      // A dragged node stops at the placement box (Kent's ruling 2026-09-29).
      const at = clampAuthoredToBox(nodeEdit.basis.fit, { x: q.x + nodeEdit.grab.dx, y: q.y + nodeEdit.grab.dy });
      const candidate = nodeEdit.kind === "anchor"
        ? applyAnchorDrag(nodeEdit.live, nodeEdit.index, at)
        : applyHandleDrag(nodeEdit.live, nodeEdit.index, at);
      // Hold last good (2026-09-30 spec §5, ruling 3): a frame that would
      // bulge a bent edge past the placement box (tested on the flattened
      // curve — the point clamp above only holds the through point), or take
      // a cut-out out of the shape it cuts, is dropped and `live` stays where
      // it was. The point clamp stays first: it is what lets a node slide
      // along the box edge.
      const b = nodeEdit.basis;
      const boxHeld = b.boxOk && !ringInsideBox(candidate, b.fit, hoopSizeMm(project));
      const cutHeld = !boxHeld && breaksContainment(b.shapes,
        b.shapes.map((s) => (s && s.id === candidate.id ? candidate : s)));
      if (cutHeld) shapeEditError = CUTOUT_HOLD_HINT;
      // A frame held by the BOX is not the cut-out's doing: a hint left from an
      // earlier frame would name the wrong cause.
      if (boxHeld && shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
      if (!boxHeld && !cutHeld) {
        nodeEdit.live = candidate;
        // Clear only our own hint, never a different message showing.
        if (shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
      }
      nodeEdit = nodeEdit; // reassign for Svelte
      repaintNodeChrome();
      return;
    }
    // An edge press does nothing until its release; it never moves the element.
    if (pressEdge) return;
    if (!dragMode) {
      emitCanvasHover(p);
      updateHoverCursor(p);
      inspectHover(e, p);
      return;
    }
    if (dragMode === "pan") {
      // B-fix (Slice 8 final review): pointer capture lets this drag travel
      // far past the canvas edge, so the raw delta must go through the SAME
      // clampPan() zoomBy() uses -- an unclamped assignment here could push
      // the hoop entirely off canvas with no way back except the fit-reset
      // zoom button.
      const rawPanX = dragStartPanX + (p.x - dragStartPx.x);
      const rawPanY = dragStartPanY + (p.y - dragStartPx.y);
      const { panX, panY } = clampPan(rawPanX, rawPanY, view.zoom, cssW(), cssH());
      view = { zoom: view.zoom, panX, panY };
      scheduleViewRepaint();
      return;
    }
    if (dragMode === "rotate") {
      // Alt = free rotation (skip the 45° magnets), mirroring Alt's
      // suspend-snap role on move/resize.
      const deg = dragRotate(dragStartRotationDeg, dragRotateCenterPx, dragStartPx, p, { free: e.altKey });
      rotateBadgeDeg = deg;
      pendingPatch = { id: dragTargetId, patch: { rotationDeg: deg } };
      schedulePatchFlush();
      return;
    }
    if (dragMode === "gmove" || dragMode === "gresize") {
      const gscale = renderResult && renderResult.scale ? renderResult.scale : 1;
      const gdxMm = (p.x - dragStartPx.x) / gscale;
      const gdyMm = (p.y - dragStartPx.y) / gscale;
      const hoop = hoopSizeMm(project);
      if (dragMode === "gmove") {
        // Same shape as the single-element move: snap the (shifted) union
        // bbox against NON-selected elements + hoop centerlines, then clamp
        // the whole group to the hoop; clamp wins over snap.
        let dX = gdxMm, dY = -gdyMm;
        activeGuides = null;
        if (snapEnabled && !e.altKey && dragGroupBBoxMm) {
          const bbox = {
            x0: dragGroupBBoxMm.x0 + dX, x1: dragGroupBBoxMm.x1 + dX,
            y0: dragGroupBBoxMm.y0 + dY, y1: dragGroupBBoxMm.y1 + dY,
          };
          const others = [];
          for (const id in peById) {
            if (!selIds.includes(id) && peById[id] && peById[id].bboxMm) others.push(peById[id].bboxMm);
          }
          const s = snapMove(bbox, buildSnapLines(others), SNAP_PX / gscale);
          dX += s.dx;
          dY += s.dy;
          if (s.guideXMm != null || s.guideYMm != null) activeGuides = { vXMm: s.guideXMm, hYMm: s.guideYMm };
        }
        const cl = clampGroupDelta(dX, dY, dragGroupBBoxMm, hoop.wMm, hoop.hMm);
        if (activeGuides) {
          if (activeGuides.vXMm != null && Math.abs(cl.dxMm - dX) > 0.01) activeGuides.vXMm = null;
          if (activeGuides.hYMm != null && Math.abs(cl.dyMm - dY) > 0.01) activeGuides.hYMm = null;
          if (activeGuides.vXMm == null && activeGuides.hYMm == null) activeGuides = null;
        }
        moveBadge = {
          xMm: (dragGroupBBoxMm.x0 + dragGroupBBoxMm.x1) / 2 + cl.dxMm,
          yMm: (dragGroupBBoxMm.y0 + dragGroupBBoxMm.y1) / 2 + cl.dyMm,
        };
        const patches = {};
        for (const m of dragMembers) patches[m.id] = { offsetXMm: m.offsetXMm + cl.dxMm, offsetYMm: m.offsetYMm + cl.dyMm };
        pendingPatch = { multi: patches };
      } else {
        // Group resize: one factor from the union box's aspect-locked
        // corner drag, fanned out to every member (targets AND offsets
        // scale about the group center). Factor capped so the scaled
        // union still fits the hoop; groupResizePatches raises it if any
        // member would fall below the stitchable minimum.
        const gW = dragGroupBBoxMm.x1 - dragGroupBBoxMm.x0;
        const gH = dragGroupBBoxMm.y1 - dragGroupBBoxMm.y0;
        const newW = dragResize(gW, gH, dragHandle, gdxMm, gdyMm, MIN_SIZE_MM, hoop.wMm || gW);
        let f = gW > 0 ? newW / gW : 1;
        const fMax = Math.min(hoop.wMm ? hoop.wMm / gW : Infinity, hoop.hMm ? hoop.hMm / gH : Infinity);
        if (f > fMax) f = fMax;
        const gcx = (dragGroupBBoxMm.x0 + dragGroupBBoxMm.x1) / 2;
        const gcy = (dragGroupBBoxMm.y0 + dragGroupBBoxMm.y1) / 2;
        const r = groupResizePatches(dragMembers, f, gcx, gcy, MIN_SIZE_MM);
        // the union box as it will measure, about its (unmoving) centre
        sizeBadge = { wMm: gW * f, hMm: gH * f, xMm: gcx, yMm: gcy };
        pendingPatch = { multi: r.patches };
      }
      schedulePatchFlush();
      return;
    }
    const scale = renderResult && renderResult.scale ? renderResult.scale : 1; // px per mm
    const dxMm = (p.x - dragStartPx.x) / scale;
    const dyMm = (p.y - dragStartPx.y) / scale;
    const { wMm: hoopWmm, hMm: hoopHmm } = hoopSizeMm(project);
    const snapping = snapEnabled && !e.altKey;

    if (dragMode === "resize") {
      let newWidthMm = dragResize(dragStartWidthMm, dragStartHeightMm, dragHandle, dxMm, dyMm, MIN_SIZE_MM, hoopWmm || dragStartWidthMm);
      sizeMatch = null;
      if (snapping) {
        const aspect = dragStartHeightMm > 0 ? dragStartWidthMm / dragStartHeightMm : 1;
        const dims = otherBBoxes().map((b) => ({ w: b.x1 - b.x0, h: b.y1 - b.y0 }));
        const s = snapResizeWidth(newWidthMm, aspect, dims, SNAP_PX / scale);
        // A snapped width must still respect dragResize's own clamp range.
        const maxW = hoopWmm || dragStartWidthMm;
        if (s.match && s.widthMm >= MIN_SIZE_MM && s.widthMm <= maxW) {
          // s.widthMm is the OTHER element's rendered bbox width, but sizeMm
          // is a generation TARGET, and generation grows output past the
          // target by a fixed pull-comp/outline margin. Subtract the dragged
          // element's own measured growth (rendered minus target at drag
          // start) so the REGENERATED bbox — the thing the user sees — is
          // what matches, not the pre-growth target.
          newWidthMm = s.widthMm - (dragStartWidthMm - dragStartTargetMm);
          sizeMatch = s.match;
        }
      }
      // What the design WILL measure: the rendered bbox at drag start, scaled
      // by how far the target moved (the target is the generation width, the
      // bbox runs past it by pull comp; the ratio carries that margin along).
      // The offset does not move in a resize; it is shown so the badge reads
      // the same two numbers the move badge does.
      const f = dragStartTargetMm > 0 ? newWidthMm / dragStartTargetMm : 1;
      sizeBadge = { wMm: dragStartWidthMm * f, hMm: dragStartHeightMm * f, xMm: dragStartOffXMm, yMm: dragStartOffYMm };
      pendingPatch = { id: dragTargetId, patch: { sizeMm: newWidthMm } };
    } else if (dragMode === "move") {
      // Raw (unclamped) offset first so snapping sees the true pointer
      // position; hoop containment is applied AFTER the snap — the clamp
      // always wins, and a guide whose axis the clamp overrode is dropped.
      let offX = dragStartOffXMm + dxMm;
      let offY = dragStartOffYMm - dyMm;
      activeGuides = null;
      if (snapping && dragStartBBoxMm) {
        const bbox = {
          x0: dragStartBBoxMm.x0 + dxMm, x1: dragStartBBoxMm.x1 + dxMm,
          y0: dragStartBBoxMm.y0 - dyMm, y1: dragStartBBoxMm.y1 - dyMm,
        };
        const s = snapMove(bbox, buildSnapLines(otherBBoxes()), SNAP_PX / scale);
        offX += s.dx;
        offY += s.dy;
        if (s.guideXMm != null || s.guideYMm != null) activeGuides = { vXMm: s.guideXMm, hYMm: s.guideYMm };
      }
      const clamped = clampOffsets(offX, offY, dragStartWidthMm, dragStartHeightMm, hoopWmm, hoopHmm);
      if (activeGuides) {
        if (activeGuides.vXMm != null && Math.abs(clamped.offsetXMm - offX) > 0.01) activeGuides.vXMm = null;
        if (activeGuides.hYMm != null && Math.abs(clamped.offsetYMm - offY) > 0.01) activeGuides.hYMm = null;
        if (activeGuides.vXMm == null && activeGuides.hYMm == null) activeGuides = null;
      }
      moveBadge = { xMm: clamped.offsetXMm, yMm: clamped.offsetYMm };
      pendingPatch = { id: dragTargetId, patch: clamped };
    }
    schedulePatchFlush();
  }

  function endDrag(e) {
    // Move shape: release keeps the moved position (committed by Enter / Done);
    // a cancelled pointer puts the drag back to where it started.
    if (shapeMove && shapeMove.drag) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      const d = shapeMove.drag;
      shapeMove = e.type === "pointercancel"
        ? { ...shapeMove, dx: d.dx0, dy: d.dy0, drag: null }
        : { ...shapeMove, drag: null };
      dragReadout = null;
      setCanvasCursor("default");
      repaintNodeChrome();
      return;
    }
    // Reshape mode: a point drag commits ONE patch on release (a click that
    // never travelled, or a cancel, commits nothing); a marquee selects.
    if (reshapeDrag) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      const d = reshapeDrag;
      reshapeDrag = null;
      dragReadout = null;
      if (shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
      const el = project && (project.elements || []).find((x) => x.id === d.elId);
      if (el && d.moving && d.live && d.live.size && e.type !== "pointercancel") {
        if (d.kind === "anchors") commitAnchorEdits(el, d.basis.fit, [...d.live.values()]);
        else commitRingEdits(el, d.basis, d.live, null, d.liveNodes);
      }
      setCanvasCursor("default");
      repaintNodeChrome();
      return;
    }
    if (marquee) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      const m = marquee;
      marquee = null;
      const edit = reshapeOn() ? editableOutlinesPx() : null;
      if (edit && e.type !== "pointercancel" && typeof e.clientX === "number") {
        const moved = Math.hypot(e.clientX - m.startClient.x, e.clientY - m.startClient.y);
        const here = canvasPointFromEvent(e);
        if (moved >= CLICK_PX) {
          const found = reshapeNodesInBox(edit, m.startPx, here);
          const sel = m.add ? cloneSel(reshape.sel) : new Map();
          for (const [sid, rings] of found) for (const [ring, set] of rings) for (const i of set) selAdd(sel, sid, ring, i);
          setReshapeSel(sel);
        } else if (!m.add && moved < INSERT_CLICK_PX && insertNodeFromClick(edit, m.startPx)) {
          // A click ON THE PATH inserted a corner node; later nodes re-indexed,
          // so the point selection goes (the new node is one gesture away).
          if (reshapeSelCount(reshape)) setReshapeSel(new Map());
        } else if (!m.add) {
          // A click: drops the point selection, and (as outside the mode)
          // selects the shape under it and opens its popover.
          if (reshapeSelCount(reshape)) setReshapeSel(new Map());
          const hit = shapeAtPoint(edit.el, here);
          if (hit) {
            selectedShapeId = hit.shapeId;
            selectedShapeElId = edit.el.id;
            if (edit.el.type === "manual") dispatch("shapeselect", { elementId: edit.el.id, shapeId: hit.shapeId });
            openShapePop(e);
          } else if (selectedShapeId || shapePop) {
            setSelectedShape(null);
            focusedAnchor = null;
            if (shapePop) closeShapePop();
          }
        }
      }
      repaintNodeChrome();
      return;
    }
    // A hand-drawn node drag: commit on release through the re-fit rule. A
    // press that never moved the node (`live` is still the basis object —
    // guaranteed for any press-release under CLICK_PX by onPointerMove's dead
    // zone) is the focus gesture — it commits nothing and leaves focusedAnchor set. A
    // cancel commits nothing. A drag never opens the popover.
    if (nodeEdit) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      const el = project && (project.elements || []).find((x) => x.id === nodeEdit.elId);
      const changed = nodeEdit.live !== nodeEdit.basis.shape;
      // The hold hint lives as long as the drag; a drag held from its very
      // first frame commits nothing, so it is dropped here, not by the commit.
      if (shapeEditError === CUTOUT_HOLD_HINT) shapeEditError = "";
      if (el && changed && e.type !== "pointercancel") commitNodeEdit(el, nodeEdit.live);
      nodeEdit = null;
      pressClient = null;
      pressOutline = false;
      pressEdge = null;
      setCanvasCursor("default");
      repaintNodeChrome();
      return;
    }
    // An edge press: a click (under CLICK_PX) inserts an anchor where it was
    // released, committed at once; a drag or a cancel does nothing at all.
    if (pressEdge) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      if (pressClient && e && e.type !== "pointercancel" && typeof e.clientX === "number") {
        const moved = Math.hypot(e.clientX - pressClient.x, e.clientY - pressClient.y);
        const el = project && (project.elements || []).find((x) => x.id === pressEdge.elId);
        const shape = el && manualShapeOf(el, pressEdge.shapeId);
        const fit = el && manualFit(el);
        if (moved < CLICK_PX && shape && fit && renderResult && renderResult.toCanvas) {
          // The click may land up to the edge grab radius off the line, so it too stops at the box.
          const at = clampAuthoredToBox(fit, fieldPxToAuthored(fit, canvasPointFromEvent(e)));
          const grown = insertAnchor(shape, pressEdge.index, at);
          // insertAnchor hands back the SAME shape at MAX_SHAPE_POINTS.
          if (grown === shape) shapeEditError = "This shape already has the maximum number of points.";
          else if (grown) commitNodeEdit(el, grown);
        }
      }
      pressEdge = null;
      pressClient = null;
      pressOutline = false;
      repaintNodeChrome();
      return;
    }
    if (shapeEdit) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
        canvas.releasePointerCapture(e.pointerId);
      }
      // Commit on release. A rejected edit (self-crossing, pinched shut)
      // leaves `shapeEditError` set and simply drops the working ring — the
      // shape snaps back to its last good geometry rather than persisting
      // something the service would refuse.
      // A press that never moved (a click on a node or edge) commits nothing:
      // it would write the seeds and a polygon equal to the current one.
      if (shapeEdit.moved) commitShapeEdit();
      shapeEdit = null;
      liveRing = null;
      pressClient = null;
      pressOutline = false;
      setCanvasCursor("default");
      // The last live ring is painted on the canvas; a REJECTED edit starts
      // no regenerate to clear it, so repaint under the chrome here too.
      repaintNodeChrome();
      return;
    }
    if (canvas && (dragMode || pressOutline) && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
      canvas.releasePointerCapture(e.pointerId);
    }
    // A press on an outline already SELECTED its shape (onPointerDown); if it
    // came back up without travelling, it was a click and opens the popover
    // for that shape. A drag, or a cancel, opens nothing.
    if (pressOutline && pressClient && selectedShapeId && e && e.type !== "pointercancel" && typeof e.clientX === "number") {
      const moved = Math.hypot(e.clientX - pressClient.x, e.clientY - pressClient.y);
      if (moved < CLICK_PX) {
        openShapePop(e);
        drawOverlay();
      }
    }
    // A press-and-release that did not travel is a CLICK, and a click inside
    // a shape opens its popover (spec §4). Tested on the element the press
    // selected, at the RELEASE point. A pointercancel is never a click.
    if (dragMode === "move" && pressClient && e && e.type !== "pointercancel" && typeof e.clientX === "number") {
      const moved = Math.hypot(e.clientX - pressClient.x, e.clientY - pressClient.y);
      if (moved < CLICK_PX) {
        const el = selectedElement();
        const p = canvasPointFromEvent(e);
        const hit = el && SHAPE_LANES.has(el.type) ? shapeAtPoint(el, p) : null;
        if (hit) {
          selectedShapeId = hit.shapeId;
          selectedShapeElId = el.id;
          shapeEditError = "";
          if (el.type === "manual") dispatch("shapeselect", { elementId: el.id, shapeId: hit.shapeId });
          openShapePop(e);
        } else if (selectedShapeId || shapePop) {
          selectedShapeId = null;
          selectedShapeElId = null;
          focusedAnchor = null;
          if (shapePop) closeShapePop();
        }
        // Repaint under the chrome: a deselect drops the amber ring and dots.
        repaintNodeChrome();
      }
    }
    pressClient = null;
    pressOutline = false;
    dragMode = null;
    dragHandle = null;
    dragTargetId = null;
    dragStartPx = null;
    dragStartPanX = 0;
    dragStartPanY = 0;
    dragStartBBoxMm = null;
    dragRotateCenterPx = null;
    dragMembers = null;
    dragGroupBBoxMm = null;
    // Erase drag-only overlay chrome (guides/badges). One view repaint —
    // cheaper than a full generate, and the final patch's paint() (if still
    // in flight) draws with this already-cleared state anyway.
    if (activeGuides || sizeMatch || moveBadge || sizeBadge || rotateBadgeDeg != null) {
      activeGuides = null;
      sizeMatch = null;
      moveBadge = null;
      sizeBadge = null;
      rotateBadgeDeg = null;
      scheduleViewRepaint();
    }
  }

  function onPointerLeave() {
    emitCanvasHover(null);
    inspectHit = null;
    if (!dragMode) setCanvasCursor("default");
  }
</script>

<svelte:window on:keydown={onWindowKey} on:pointerdown|capture={onWindowPointerDown} />

<div class="fieldwrap">
  {#if showDragHint}
    <!-- In-flow, not floating over the canvas. Hint.svelte's own note said
         the floating variant was safe because "nothing else interactive
         underlies it there" -- but it sat at the canvas's top-right corner,
         which is interactive (drag, resize, right-click tool menu) and is
         inside the hoop guide, i.e. sewable field. Measured at 1440x900 it
         covered 18,188px of canvas. This is the same in-flow callout every
         other hint in the app already uses. -->
    <Hint on:dismiss={() => dispatch("dismisshint")}>
      Drag the design to move it — corners resize.
    </Hint>
  {/if}
  <div class="hoop" bind:this={hoopEl}>
    <!-- tabindex + aria-label + on:keydown: the field is reachable and
         operable without a pointer. `role="application"` is what tells a
         screen reader to hand arrow keys to the page instead of using them
         for its own browse mode — which is the whole point of focusing here.
         The bitmap attributes stay as a pre-mount fallback only; fitCanvasToPane
         replaces both with the pane size times devicePixelRatio.

         The warning below fires because Svelte classes <canvas> as an
         interactive element and `application` as a non-interactive role. For
         a static canvas that rule is right — but this one is a focusable
         widget with its own key handling, which is the exact case WAI-ARIA
         defines `application` for. Silenced deliberately, not worked around:
         dropping the role would leave arrow keys to the screen reader's
         browse mode and the nudge would never reach onCanvasKey. -->
    <!-- svelte-ignore a11y_no_interactive_element_to_noninteractive_role -->
    <canvas
      bind:this={canvas}
      data-paint-seq={paintSeq}
      data-reshape={reshape && project && project.selectedId === reshape.elId ? "on" : "off"}
      data-reshape-points={reshapeSelCount(reshape)}
      data-hole-draft={holeDraftOn() ? holeDraft.pointsMm.length : "off"}
      data-shape-move={shapeMoveOn(shapeMove, project, multiSel, simActive) ? "on" : "off"}
      data-shape-move-delta={shapeMoveOn(shapeMove, project, multiSel, simActive) ? `${shapeMove.dx.toFixed(2)},${shapeMove.dy.toFixed(2)}` : ""}
      width="760"
      height="560"
      tabindex="0"
      role="application"
      aria-label={fieldLabel}
      on:keydown={onCanvasKey}
      on:pointerdown={onPointerDown}
      on:pointerdown={() => (inspectHit = null)}
      on:pointermove={onPointerMove}
      on:pointerup={endDrag}
      on:pointercancel={endDrag}
      on:pointerleave={onPointerLeave}
      on:contextmenu={onContextMenu}
      on:wheel={onWheel}
    ></canvas>
    {#if compareOn}
      <!-- Compare view: an overlay over the canvas (no layout space), only
           while lit. Its artwork <img> is pointer-transparent; only the
           handle takes pointer and keys. No <canvas> in here. -->
      <CompareSplit bind:split={compareSplit} src={compareSrc} />
    {/if}
    {#if fieldMenu}
      <!-- Drawing tools live here now instead of in the Content step's tile
           row (Kent's call, 2026-08-13: keep them, but as a right-click tool
           rather than an upload button). Positioned at the pointer, dismissed
           by Escape or any click outside — see onWindowPointerDown. -->
      <ul
        class="fieldmenu"
        style="left: {fieldMenu.x}px; top: {fieldMenu.y}px"
        role="menu"
        aria-label={fieldMenu.shape ? "Shape and canvas tools" : "Canvas tools"}
      >
        {#if fieldMenu.shape}
          <!-- The shape under the pointer, then its border actions (Kent's
               2026-09-09 ask). One toggling item: Add border when it has
               none, Remove border when it has one; and the way back to the
               design-wide setting once an override exists. -->
          <li role="none" class="fieldmenu-head">{fieldMenu.shape.name}</li>
          {#if fieldMenu.shape.state && fieldMenu.shape.state.label}
            <!-- The state line, above the actions, because it is what makes
                 the action legible: "Remove border" under "no border sewn"
                 tells you the request is on and the engine declined it, which
                 is the one thing this menu could not say before. -->
            <li role="none" class="fieldmenu-state" title={fieldMenu.shape.state.title}>
              {fieldMenu.shape.state.label}
            </li>
          {/if}
          {#each fieldMenu.shape.items as it (it.id)}
            <li role="none">
              <button type="button" role="menuitem" title={it.title} disabled={it.disabled} on:click={() => chooseMenuItem(it)}>
                {it.label}
              </button>
            </li>
          {/each}
          <li role="separator" class="fieldmenu-sep"></li>
        {/if}
        <li role="none">
          <button type="button" role="menuitem" on:click={() => chooseFieldMenu("manual")}>
            Draw shapes
          </button>
        </li>
        <li role="none">
          <button type="button" role="menuitem" on:click={() => chooseFieldMenu("shape")}>
            Basic shape
          </button>
        </li>
      </ul>
    {/if}
    {#if popModel && shapePop}
      <!-- The click-to-edit popover (2026-09-29): opened by a left CLICK on
           or inside a shape — see openShapePop / endDrag. Closed by Escape,
           any press outside it, or its own close. -->
      <ShapePopover
        model={popModel}
        anchor={shapePop}
        bounds={hoopBounds}
        position={popPosition && popPosition.elementId === shapePop.elementId ? popPosition : null}
        on:move={(e) => (popPosition = { x: e.detail.x, y: e.detail.y, elementId: shapePop.elementId })}
        applyToSimilar={applyToSimilar}
        on:similar={(e) => (applyToSimilar = e.detail.on)}
        on:change={onPopChange}
        on:action={onPopAction}
        on:close={closeShapePop}
      />
    {/if}
    <!-- The digitize ring: only while a run is in flight, so it never
         sits on the field at rest (e2e/field-chrome.spec.js's one-child rule
         is measured with no run going). -->
    {#if $digitizeBusy.size}<DigitizeRing />{/if}
    {#if !hasDesign && !error && hint && !$digitizeBusy.size}
      <p class="fieldhint" class:on-dark={project && project.fabricRgb && isDark(project.fabricRgb)}>{hint}</p>
    {/if}
  </div>
  <!-- Controls sit BELOW the canvas, not on top of it. Both were
       absolutely positioned inside .hoop: .zoomctl pinned bottom-right
       and .simbar bottom-centre, so they covered sewable field (the zoom
       bar measured 10,351px of canvas at 1440x900) and collided with each
       other whenever the simulator was open -- same `bottom: var(--space-3)`,
       one right-aligned, one centred. The field pane had 242px of unused
       height directly under the canvas to put them in. -->
  <div class="fieldbars">
      <div class="zoomctl">
      <button type="button" class="zoombtn" on:click={zoomOut} disabled={view.zoom <= MIN_ZOOM} aria-label="Zoom out"><Icon name="minus" /></button>
      <span class="zoompct">{Math.round(view.zoom * 100)}%</span>
      <button type="button" class="zoombtn" on:click={zoomIn} disabled={view.zoom >= MAX_ZOOM} aria-label="Zoom in"><Icon name="plus" /></button>
      <button type="button" class="zoombtn zoomfit" on:click={resetView} aria-label="Fit to hoop" use:tip={"fitToHoop"}><Icon name="expand" /></button>
      {#if scaleBar}
        <!-- A ruler, not a control: the bar's width IS the stated length on
             screen (lib/scalebar.js), so the customer reads the design's
             size off it at any zoom. In the zoom bar rather than on the
             canvas so it never covers sewable field.
             The rule sits in a FIXED slot as wide as the longest rule
             pickScaleBar draws (120 px), so a render that changes the scale
             never changes the bar's width: it used to, and a bar near the
             wrap point then re-wrapped after the render, resized .hoop and
             cost a second field render per window resize (2026-11-07). -->
        <span class="scalebar" role="img" aria-label="Scale: {scaleBar.label} on screen" title="{scaleBar.label} at this zoom">
          <span class="scalebar-slot"><i class="scalebar-rule" style="width: {scaleBar.px.toFixed(1)}px"></i></span>
          <span class="scalebar-label">{scaleBar.label}</span>
        </span>
      {/if}
      <!-- The VIEW is one choice of three, so it is a segmented control
           (2026-09-30): Stitches (the flat view), Realistic, Simulate. Six
           bare glyphs used to stand here and a customer could not find
           "Realistic view" among them. The three overlay toggles and snap
           follow, with their names on, since a word is what a person scans
           for. Every aria-label and aria-pressed is unchanged, so the e2e
           specs that drive these buttons by name still do. -->
      <span class="viewseg" role="group" aria-label="View">
        <button
          type="button"
          class="zoombtn viewseg-btn"
          class:viewseg-on={!realisticView && !simActive && !originalView}
          on:click={showFlat}
          disabled={!hasDesign}
          aria-pressed={!realisticView && !simActive && !originalView}
          aria-label="Stitches view"
          use:tip={"flatView"}
        >Stitches</button>
        <button
          type="button"
          class="zoombtn viewseg-btn"
          class:viewseg-on={realisticView && !simActive && !originalView}
          on:click={showRealistic}
          disabled={!hasDesign}
          aria-pressed={realisticView && !simActive && !originalView}
          aria-label="Realistic view"
          use:tip={"realistic"}
        >Realistic</button>
        <button
          type="button"
          class="zoombtn viewseg-btn"
          class:viewseg-on={simActive}
          on:click={() => (simActive ? stopSim() : startSim())}
          disabled={!hasDesign}
          aria-label="Stitch simulator"
          aria-pressed={simActive}
          use:tip={"simulator"}
        >Simulate</button>
        <button
          type="button"
          class="zoombtn viewseg-btn viewseg-orig"
          class:viewseg-on={originalView && !compareOn}
          on:click={showOriginal}
          disabled={!hasDesign || !anyOriginal}
          aria-pressed={originalView && !compareOn}
          aria-label="Original view"
          use:tip={"originalView"}
        >Original</button>
        <button
          type="button"
          class="zoombtn viewseg-btn viewseg-orig"
          class:viewseg-on={compareOn}
          on:click={showCompare}
          disabled={!hasDesign || !anyOriginal}
          aria-pressed={compareOn}
          aria-label="Compare view"
          use:tip={"compareView"}
        >Compare</button>
      </span>
      <span class="zoomsep" aria-hidden="true"></span>
      <button
        type="button"
        class="zoombtn viewtoggle zoomlabelled"
        class:simon={showOutlines}
        on:click={toggleOutlines}
        disabled={!hasDesign}
        aria-pressed={showOutlines}
        aria-label="Show shape outlines"
        use:tip={"outlines"}
      ><Icon name="nodes" /><span class="zoomlabel">Outlines</span></button>
      <button
        type="button"
        class="zoombtn viewtoggle zoomlabelled"
        class:simon={showJumps}
        on:click={toggleJumps}
        disabled={!hasDesign}
        aria-pressed={showJumps}
        aria-label="Show jumps"
        use:tip={"jumps"}
      ><Icon name="jump" /><span class="zoomlabel">Jumps</span></button>
      <button
        type="button"
        class="zoombtn viewtoggle zoomlabelled"
        class:simon={showTrims}
        on:click={toggleTrims}
        disabled={!hasDesign}
        aria-pressed={showTrims}
        aria-label="Show trims"
        use:tip={"trims"}
      ><Icon name="scissors" /><span class="zoomlabel">Trims</span></button>
      <button
        type="button"
        class="zoombtn viewtoggle zoomlabelled"
        class:simon={sewnWidthView}
        on:click={toggleSewnWidth}
        disabled={!hasDesign || !canSewnWidth}
        aria-pressed={sewnWidthView}
        aria-label="Show columns as sewn"
        use:tip={"sewnWidth"}
      ><Icon name="nodes" /><span class="zoomlabel">Sewn width</span></button>
      <button
        type="button"
        class="zoombtn viewtoggle zoomlabelled"
        class:simon={inspectOn}
        on:click={toggleInspect}
        disabled={!hasDesign}
        aria-pressed={inspectOn}
        aria-label="Inspect stitches"
        use:tip={"inspect"}
      ><Icon name="inspect" /><span class="zoomlabel">Inspect</span></button>
      <span class="zoomsep" aria-hidden="true"></span>
      <button
        type="button"
        class="zoombtn viewtoggle"
        class:simon={snapEnabled}
        on:click={toggleSnap}
        aria-pressed={snapEnabled}
        aria-label="Auto-snap"
        use:tip={"autoSnap"}
      ><Icon name="magnet" /></button>
    </div>
    {#if simActive}
      <SimBar
        playing={simPlaying}
        index={Math.floor(simIndex)}
        total={simTotal}
        ordinals={simOrdinals}
        speed={simSpeed}
        timeline={simTl}
        names={simNames}
        stopAtChanges={simStopAtChanges}
        stopped={simStopped}
        isolate={simIsolate}
        hasUnderlay={!!(simUnderlay && simUnderlay.runs.length)}
        phase={phaseAt(simStrands, Math.floor(simIndex), simTotal)}
        sewTime={sewTimeAt(simClock, Math.floor(simIndex), EMB.sewTimeMin, simRate.spm)}
        spm={simRate.spm}
        spmQuoted={simRate.quoted}
        on:toggle={simTogglePlay}
        on:block={(e) => simGoToBlock(e.detail.k)}
        on:isolate={simToggleIsolate}
        on:scrub={simScrub}
        on:thread={(e) => simStepThread(e.detail.dir)}
        on:stops={simToggleStops}
        on:speed={simCycleSpeed}
        on:close={stopSim}
      />
    {/if}
  </div>
  <!-- Keyboard-nudge feedback, spoken not shown. A sibling of `.hoop`, never
       a child: `.hoop` holds the canvas and nothing else, which is what keeps
       chrome off the sewable field (pinned by e2e/field-chrome.spec.js). It
       is off-screen rather than hidden because display:none and
       visibility:hidden both drop an element out of the accessibility tree,
       and a live region outside the tree is never announced. -->
  <p class="fieldlive" aria-live="polite">{liveMsg}</p>
  <EditModeBar bar={modeBar} on:action={onModeBarAction} />
  <!-- The stitch inspector's tooltip: fixed at the pointer, out of flow, and
       outside `.hoop` (which holds the canvas and nothing else). -->
  {#if inspectOn && inspectHit && !simActive && !originalView}
    <StitchInspector info={inspectHit.info} x={inspectHit.x} y={inspectHit.y} />
  {/if}
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if shapeEditError}<span class="err" data-testid="shape-edit-error">{shapeEditError}</span>
    <!-- &nbsp; before each separator, not a plain space: Svelte strips leading
         whitespace inside an element, so " · " rendered as "…hoop· This font".
         Pre-existing on the two older warnings; visible on all three now. -->
    {:else if stats}<span class="stats">{stats}</span>{#if warn}<span class="warn">&nbsp;· Smaller than 5 mm — thread can't stitch this cleanly</span>{/if}{#if hoopNote}<span class="warn">&nbsp;· {hoopNote}</span>{/if}{#if unsupportedNote}<span class="warn">&nbsp;· {unsupportedNote}</span>{/if}{#if letterNote}<span class="warn">&nbsp;· {letterNote}</span>{#if twoLinesFix}&nbsp;<button type="button" class="twolines" on:click={() => dispatch("elupdate", { id: twoLinesFix.id, patch: { text: twoLinesFix.text } })}>Put on two lines</button>{/if}{/if}{#if contrastNote}<span class="warn" data-testid="contrast-note">&nbsp;· {contrastNote}</span>{/if}{/if}
  </div>
</div>
