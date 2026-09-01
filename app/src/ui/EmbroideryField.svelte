<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { generateAll, charList } from "../lib/generate.js";
  import { ensureFonts } from "../lib/fontLoader.js";
  import { renderRealistic, isDark } from "../lib/preview.js";
  import { designToStrands } from "../lib/strands.js";
  import { advanceIndex, clampIndex, nextSpeed } from "../lib/simulate.js";
  import { EMB } from "../lib/emb.js";
  import { designRectPx, hitTest, pickElement, dragResize, clampOffsets, clampPan, buildSnapLines, snapMove, snapResizeWidth, rotateHandlePx, dragRotate, unionBBox, clampGroupDelta, groupResizePatches } from "../lib/interact.js";
  import { selectedIdsOf } from "../lib/project.js";
  import { effectiveHoop, hoopFitNote } from "../lib/hoop.js";
  import { shapeOutlinesInFieldMm, pulseAt, createPulseTracker, hitOverlay, moveNode, moveEdge, insertNode, fieldMmToOutlineMm } from "../lib/shapeOverlay.js";
  import { boundaryIssues, canonicalShapeEdits, editsKey } from "../lib/digitizer.js";
  import Hint from "./Hint.svelte";
  import Icon from "./Icon.svelte";

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

  // Result of the last renderRealistic() call — { toCanvas, scale, designBBoxMm } —
  // kept around so pointer handlers and the selection overlay can hit-test /
  // draw against the exact transform that was just used to paint the canvas.
  let renderResult = null;

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
  let view = { zoom: 1, panX: 0, panY: 0 };
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 4;
  let rafViewScheduled = false;

  // Diagnostic overlays (view-only, ephemeral — same lifecycle as zoom/pan):
  // dashed needle-up travel lines and X markers at trims.
  let showJumps = false;
  let showTrims = false;
  function toggleJumps() { showJumps = !showJumps; scheduleViewRepaint(); }
  function toggleTrims() { showTrims = !showTrims; scheduleViewRepaint(); }
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
  let simSpeed = 1;
  let simRafId = 0;
  let simLastTs = 0;

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

  function garmentFor(p) {
    return p && EMB.getGarment(p.garmentId);
  }

  function hoopSizeMm(p) {
    const garment = garmentFor(p);
    return garment
      ? { wMm: garment.widthIn * MM_PER_INCH, hMm: garment.heightIn * MM_PER_INCH }
      : { wMm: 0, hMm: 0 };
  }

  const EMPTY_DESIGN = { stitches: [] };

  // B4: the empty state shares the SAME renderRealistic() call the populated
  // state uses below (fabricRgb fill, luminance-aware hoop outline, weave,
  // view) -- no separate hardcoded-color fill path. An empty design just
  // means designToStrands() inside renderRealistic contributes zero strands;
  // the background/hoop-outline/weave painting is identical either way.
  function clearToFabric() {
    if (!canvas) return;
    const garment = garmentFor(project);
    renderResult = renderRealistic(canvas, EMPTY_DESIGN, {
      dpr,
      hoop: garment ? { garment } : undefined,
      fabricRgb: project && project.fabricRgb,
      weave: true,
      view,
    });
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
      if (el.type !== "digitized" || !digitizedRows(el)) continue;
      pulses.seen(el.id, outlinePulseKey(el), now);
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
  let shapeEdit = null;     // { elId, shapeId, kind, index, startPx, ring }
  let liveRing = null;      // { shapeId, points } — the drag's working geometry
  let shapeEditError = "";

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

  // The outlines of the SELECTED digitized element, in canvas px — what the
  // pointer actually hit-tests against. Only the selected element is editable;
  // the others' outlines are there to show what was found, not to be grabbed.
  function editableOutlinesPx() {
    const el = selectedElement();
    if (!el || el.type !== "digitized" || !renderResult || !renderResult.toCanvas) return null;
    const rows = digitizedRows(el);
    const pe = peById[el.id];
    if (!rows || !pe || !pe.bboxMm) return null;
    const mm = shapeOutlinesInFieldMm(
      rows, pe.bboxMm, el.rotationDeg || 0, pendingBoundaries(el));
    return {
      el,
      rows,
      pe,
      outlines: mm.map((o) => ({
        id: o.id,
        points: (liveRing && liveRing.shapeId === o.id ? liveRing.points : o.points)
          .map(([x, y]) => {
            const c = renderResult.toCanvas(x, y);
            return [c.x, c.y];
          }),
      })),
      mmById: new Map(mm.map((o) => [o.id, o.points])),
    };
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
    };
  }

  function commitShapeEdit() {
    if (!shapeEdit || !liveRing) return;
    const el = project.elements.find((x) => x.id === shapeEdit.elId);
    const basis = shapeEdit.basis;
    if (!el || !basis || !basis.rows || !basis.bboxMm) return;

    const service = fieldMmToOutlineMm(
      liveRing.points, basis.rows, basis.bboxMm, basis.rotationDeg);
    if (!service) return;
    // Same validation the panel editor runs before it will save: a
    // self-intersecting or pinched ring is rejected here rather than sent for
    // the service to 400 on.
    const issues = boundaryIssues(service);
    if (issues.length) {
      shapeEditError = issues[0];
      return;
    }
    shapeEditError = "";
    const cur = { ...(el.shapeOverrides || {}) };
    cur[shapeEdit.shapeId] = {
      ...(cur[shapeEdit.shapeId] || {}),
      boundary_override: service.map(([x, y]) => [x, y]),
    };
    dispatch("elupdate", { id: el.id, patch: { shapeOverrides: cur } });
  }

  // Requirement 6: delete the selected shape. Rides `deletedShapeIds`, the
  // same list DigitizePanel's own delete uses — so a shape removed here is
  // struck through and RESTORABLE from the Layers list exactly as before,
  // rather than being a second, one-way kind of deletion.
  // Clearing the shape selection when the ELEMENT selection moves away keeps
  // Delete from acting on a shape whose element is no longer in front of the
  // user. Cheap to compute, and it also drops the highlight.
  $: if (project && project.selectedId !== undefined) {
    const sel = selectedElement();
    if (!sel || sel.type !== "digitized") selectedShapeId = null;
  }

  function deleteSelectedShape() {
    if (!selectedShapeId) return false;
    const el = selectedElement();
    if (!el || el.type !== "digitized") return false;
    const cur = el.deletedShapeIds || [];
    if (cur.includes(selectedShapeId)) return false;
    dispatch("elupdate", { id: el.id, patch: { deletedShapeIds: [...cur, selectedShapeId] } });
    selectedShapeId = null;
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

  function nudgeSelected(dxMm, dyMm) {
    // The simulator is a watch-mode (pointer editing is disabled there too),
    // and mid-boundary-edit the arrows belong to the ring being dragged.
    if (!project || simActive || shapeEdit) return;
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
      // The clamp refused the move — the design is already against the hoop
      // edge on that axis. Saying so is the only feedback a non-sighted user
      // gets that the key did anything at all.
      liveMsg = "At the edge of the hoop";
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
    return parts.length ? `${parts.join(" and ")} from center` : "Centered in the hoop";
  }

  function onCanvasKey(e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser/OS shortcuts alone
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
    // Escape closes the tool menu before anything else looks at the key.
    if (e.key === "Escape" && fieldMenu) {
      fieldMenu = null;
      e.preventDefault();
      return;
    }
    if (e.key !== "Delete" && e.key !== "Backspace") return;
    if (!selectedShapeId || simActive) return;
    // Never steal the key from a field the user is typing in — Backspace
    // especially. Same guard App.svelte's own global handler uses.
    const t = e.target;
    const tag = t && t.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;
    if (deleteSelectedShape()) e.preventDefault();
  }

  // An element whose saved edits have not been stitched yet. Whole-element
  // rather than per-shape on purpose: stage 5 resolves overlap BETWEEN shapes,
  // so editing one boundary genuinely moves its neighbours' stitches too.
  // Marking only the edited shape would be a more precise-looking half-truth.
  function isStale(el) {
    if (!el || el.type !== "digitized" || !el.result) return false;
    const edits = canonicalShapeEdits(el);
    return editsKey(edits) !== (el.appliedEdits || editsKey({}));
  }

  // Hatching over the stitches of an element whose edits have not been sewn
  // yet. Drawn UNDER the outlines so the thing being edited stays crisp.
  function drawStaleWash(ctx) {
    if (!renderResult || !renderResult.toCanvas || !project) return;
    for (const el of project.elements || []) {
      if (!isStale(el)) continue;
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
  }

  function drawShapeOutlines(ctx) {
    if (!renderResult || !renderResult.toCanvas || !project) return;
    const now = performance.now();
    let stillPulsing = false;

    for (const el of project.elements || []) {
      if (el.type !== "digitized") continue;
      const rows = digitizedRows(el);
      if (!rows) continue;
      const pe = peById[el.id];
      if (!pe || !pe.bboxMm) continue;

      const outlines = shapeOutlinesInFieldMm(
        rows, pe.bboxMm, el.rotationDeg || 0, pendingBoundaries(el));
      if (!outlines.length) continue;

      const started = pulses.startedAt(el.id);
      const pulse = started == null ? 0 : pulseAt(now - started);
      if (pulse > 0) stillPulsing = true;

      // Hidden shapes stay out of the drawing but stayed IN the transform, so
      // toggling one off does not shift the others.
      // Not drawn: shapes the user turned off, and shapes deleted in review.
      // A deleted shape stays in `review.shapes` on purpose (that is what
      // makes it restorable from the Layers list), so it has to be filtered
      // here or the canvas would keep outlining artwork that no longer sews.
      const hidden = new Set([
        ...rows.filter((r) => r && r.stitched === false).map((r) => r.id),
        ...(el.deletedShapeIds || []),
      ]);

      ctx.save();
      ctx.lineJoin = "round";
      for (const o of outlines) {
        if (hidden.has(o.id)) continue;
        // Mid-drag, the shape being edited renders from the working ring
        // rather than from the last committed review — otherwise the outline
        // would sit still until the pointer came up.
        const src = liveRing && liveRing.shapeId === o.id ? liveRing.points : o.points;
        const pts = src.map(([x, y]) => renderResult.toCanvas(x, y));
        if (pts.length < 3) continue;
        // Highlighted when SELECTED, not only while dragging: the highlight
        // is what tells you which shape a Delete or a drag will act on.
        const editing = o.id === selectedShapeId;
        // The default view is the stitch-out, so only the shape being acted
        // on is outlined until the user asks for all of them.
        //
        // Clicking still selects with the outlines hidden: hit-testing runs
        // off the geometry (hitOverlay), never off what was drawn, and the
        // shape highlights the moment it is picked. What IS lost is the
        // signpost that the shapes are individually clickable at all — which
        // is what the toggle is for, and why it sits with the other two
        // diagnostic overlays rather than being hidden in a menu. (Note the
        // Layers list does not drive this: selectedShapeId is set from a
        // canvas hit only.)
        if (!showOutlines && !editing) continue;

        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.closePath();

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
          ? "rgba(255, 214, 64, 0.95)"     // the shape under the pointer
          : `rgba(${OUTLINE_RGB}, ${0.85 + 0.15 * pulse})`;
        ctx.lineWidth = (editing ? 1.9 : 1.4) + 1.4 * pulse;
        ctx.stroke();

        const r = NODE_R + 1.7 * pulse + (editing ? 0.6 : 0);
        for (const p of pts) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
          // Same casing logic as the line: a node lands on the edge too, and
          // an unringed dot is invisible against matching stitches.
          ctx.fillStyle = editing
            ? "rgba(255, 214, 64, 0.95)"
            : `rgba(${OUTLINE_RGB}, ${0.85 + 0.15 * pulse})`;
          ctx.fill();
          ctx.strokeStyle = `rgba(10, 22, 30, ${0.75 + 0.25 * pulse})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    if (stillPulsing) schedulePulseFrame();
  }

  function drawOverlay() {
    if (!canvas) return;
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
      dispatch("dims", null);
      return;
    }
    const widthMM = pe.bboxMm.x1 - pe.bboxMm.x0;
    const heightMM = pe.bboxMm.y1 - pe.bboxMm.y0;
    // "Smaller than 5 mm" is advice about a design that IS there and is too
    // small to sew cleanly. On an element with no stitches at all it is not
    // advice, it is noise — and it sat directly in front of the message that
    // actually explains the problem ("this font can't stitch E, m and b"),
    // reading as two unrelated faults instead of one cause.
    warn = pe.design.stitchCount > 0 &&
      (widthMM < MIN_SIZE_MM || heightMM < MIN_SIZE_MM);
    dispatch("dims", { widthMM, heightMM });
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
    return (proj.elements || [])
      .filter((el) => el.type === "text" && el.fontKey)
      .map((el) => el.fontKey);
  }

  async function paint() {
    if (!canvas) return;
    // Any regeneration invalidates the simulator's strand count -- stop it
    // (harmless no-op when it isn't running).
    stopSim();
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
    renderResult = null;
    perElementRects = [];
    peById = {};

    if (fontErr) {
      // Font load failure surfaces through the existing element-error UI
      // (same treatment as a generateAll() throw below), never an unhandled
      // rejection.
      error = String(fontErr.message || fontErr);
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
        : "Your embroidery appears here as you add content.";
      lastGenerateResult = null;
      clearToFabric();
      dispatch("dims", null);
      dispatch("stats", { stitchCount: 0 });
      return;
    }

    const garment = garmentFor(project);
    const c = result.combined;
    // The chosen hoop rides the review stats line, and the ceiling check
    // runs against the combined design (not just the selected element) —
    // the whole design has to fit the physical hoop.
    const { hoop } = effectiveHoop(project);
    stats = `${c.stitchCount} stitches · ${c.widthMM.toFixed(0)}×${c.heightMM.toFixed(0)} mm · ${hoop.label} hoop`;
    hoopNote = hoopFitNote(c.widthMM, c.heightMM, hoop) || "";
    // Something DID stitch, but not all of it — e.g. Latin mixed into Hebrew.
    // Rides the stats line next to the other warnings rather than blocking.
    unsupportedNote = (result.unsupported && result.unsupported.length)
      ? `This font can\u2019t stitch ${charList(result.unsupported)}` : "";
    // Reports the COMBINED design's stitch count (not just the selected
    // element's) -- App uses this for the "drag-field" hint's A8 eligibility
    // condition, which is about whether there's anything on the field to
    // drag at all, regardless of which element happens to be selected.
    dispatch("stats", { stitchCount: c.stitchCount });
    // colorOverride is gone — each element now bakes its own color into its
    // stitches at generation time (see generate.js's generateElement), so
    // the combined design already carries the right colors per-part.
    lastGenerateResult = result; // B2: cached for view-only repaints below
    renderResult = renderRealistic(canvas, c, {
      dpr,
      hoop: { garment },
      fabricRgb: project.fabricRgb,
      weave: true,
      view,
      showJumps,
      showTrims,
      threadStyle: realisticView ? "realistic" : "flat",
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
      const garment = garmentFor(project);
      renderResult = renderRealistic(canvas, lastGenerateResult.combined, {
        dpr,
        hoop: { garment },
        fabricRgb: project.fabricRgb,
        weave: true,
        view,
        showJumps,
        showTrims,
        threadStyle: realisticView ? "realistic" : "flat",
        // While simulating, every repaint (zoom/pan included) draws only the
        // sewn-so-far prefix -- otherwise a mid-playback wheel event would
        // flash the finished design.
        limitStrands: simActive ? Math.floor(simIndex) : undefined,
      });
      perElementRects = [];
      if (renderResult && renderResult.toCanvas) {
        for (const pe of lastGenerateResult.perElement) {
          const rect = designRectPx(pe.bboxMm, renderResult.toCanvas);
          if (rect) perElementRects.push({ id: pe.id, ...rect });
        }
      }
      // Selection chrome is hidden during playback -- the simulator is a
      // watch-mode, not an edit-mode (pointer editing is disabled below too).
      if (!simActive) drawOverlay();
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
    simIndex = advanceIndex(simIndex, dt, simSpeed, simTotal);
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
    simTotal = designToStrands(lastGenerateResult.combined).length;
    if (!simTotal) return;
    simActive = true;
    simIndex = 0;
    simSpeed = 1;
    simPlay();
  }

  function stopSim() {
    if (!simActive) return;
    simPause();
    simActive = false;
    simIndex = 0;
    // Back to the normal full render + selection chrome.
    repaintView();
  }

  function simScrub(e) {
    simPause();
    simIndex = clampIndex(e.currentTarget.value, simTotal);
    scheduleViewRepaint();
  }

  function simCycleSpeed() {
    simSpeed = nextSpeed(simSpeed);
  }

  function simTogglePlay() {
    if (simPlaying) simPause();
    else simPlay();
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
    canvas.width = bw;  // note: assigning either dimension clears the bitmap,
    canvas.height = bh; // which is why the repaint below is unconditional.
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

  onDestroy(() => {
    // The outline pulse is the one loop here that can be mid-flight with no
    // user input driving it, so it has to be cancelled explicitly — otherwise
    // a rAF fires into a destroyed component and repaints a dead canvas.
    if (pulseRafId) cancelAnimationFrame(pulseRafId);
    pulseRafId = 0;
    if (dprQuery) dprQuery.removeEventListener("change", onDprChange);
    dprQuery = null;
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
    const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, oldZoom * factor));
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
        canvas.style.cursor = cursorForHandle(handle);
        return;
      }
      const hitId = pickElement(perElementRects, p.x, p.y);
      canvas.style.cursor = hitId ? "move" : view.zoom > 1 ? "grab" : "default";
      return;
    }
    const selRect = rectFor(project.selectedId);
    if (rotateGripHit(selRect, p)) {
      canvas.style.cursor = "grab";
      return;
    }
    // Mirrors the pointerdown precedence exactly. Without this the cursor
    // would keep promising "move the element" right up to the moment a click
    // edits a shape instead — the affordance has to agree with the behaviour.
    const hoverEdit = editableOutlinesPx();
    if (hoverEdit && hitOverlay(hoverEdit.outlines, p.x, p.y)) {
      canvas.style.cursor = "pointer";
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
        canvas.style.cursor = "grab";
        return;
      }
    }
    canvas.style.cursor = cursorForHandle(handle);
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
    if (simActive) return;          // the simulator owns the canvas while playing
    e.preventDefault();             // our menu, not the browser's
    if (!canvas) return;
    const r = canvas.getBoundingClientRect();
    fieldMenu = { x: e.clientX - r.left, y: e.clientY - r.top };
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
    if (!fieldMenu) return;
    if (e.target && e.target.closest && e.target.closest(".fieldmenu")) return;
    fieldMenu = null;
  }

  function onPointerDown(e) {
    // A right-click opens the tool menu (onContextMenu) and must never also
    // start a drag, a selection or a shape edit — every branch below assumes
    // the primary button.
    if (e.button !== undefined && e.button !== 0) return;
    if (fieldMenu) fieldMenu = null;

    // Auto-dismiss the drag-field hint on the first pointerdown on the
    // canvas WHILE it's actually showing -- gating on showDragHint (rather
    // than dismissing unconditionally) means a click on an empty field
    // before any design exists can never burn the one teaching moment this
    // hint exists for (it isn't eligible/shown yet at that point). App.svelte
    // owns the persisted hints.js dismiss() call; this only reports that the
    // interaction happened.
    if (showDragHint) dispatch("dismisshint");

    if (simActive) return; // watch-mode: no select/drag/resize during playback
    if (!canvas || !renderResult) return;
    const p = canvasPointFromEvent(e);

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
        canvas.style.cursor = cursorForHandle(handle);
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
        canvas.style.cursor = "grabbing";
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
      canvas.style.cursor = "grabbing";
      return;
    }

    // Shape outlines beat the element body. Tested after the rotate grip
    // (which sits outside the rect and must never be shadowed) and before the
    // element rect below, so grabbing a node or a line edits the SHAPE while
    // everywhere else inside the element still moves the whole element.
    const edit = editableOutlinesPx();
    if (edit) {
      const hit = hitOverlay(edit.outlines, p.x, p.y);
      if (hit) {
        // First click on a shape selects it and stops there — no geometry
        // moves until you have said which shape you mean.
        if (hit.shapeId !== selectedShapeId) {
          selectedShapeId = hit.shapeId;
          shapeEditError = "";
          drawOverlay();
          return;
        }
        const ring = edit.mmById.get(hit.shapeId);
        if (ring) {
          canvas.setPointerCapture(e.pointerId);
          shapeEditError = "";
          if (e.detail >= 2 && hit.kind === "edge") {
            // Double-click an edge to add a node there — the canvas
            // equivalent of the panel editor's "click an edge midpoint".
            // Commits immediately: there is no drag to wait for.
            const d = pxToMmDelta(hit.atPx[0] - renderResult.toCanvas(0, 0).x,
                                  hit.atPx[1] - renderResult.toCanvas(0, 0).y);
            const grown = insertNode(ring, hit.index, [d.dx, d.dy]);
            shapeEdit = { elId: edit.el.id, shapeId: hit.shapeId, kind: "node",
                          index: hit.index + 1, startPx: p, ring: grown,
                          basis: editBasis(edit) };
            liveRing = { shapeId: hit.shapeId, points: grown };
            commitShapeEdit();
            shapeEdit = null;
            liveRing = null;
            drawOverlay();
            return;
          }
          shapeEdit = { elId: edit.el.id, shapeId: hit.shapeId, kind: hit.kind,
                        index: hit.index, startPx: p, ring,
                        basis: editBasis(edit) };
          liveRing = { shapeId: hit.shapeId, points: ring };
          canvas.style.cursor = "grabbing";
          drawOverlay();
          return;
        }
      }
      // Clicked away from every outline — drop the shape selection before
      // falling through, so the next click on an outline selects rather than
      // edits, and Delete stops being armed.
      if (selectedShapeId) {
        selectedShapeId = null;
        drawOverlay();
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
          canvas.style.cursor = "grabbing";
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
    dragStartOffXMm = el.offsetXMm || 0;
    dragStartOffYMm = el.offsetYMm || 0;
    dragStartWidthMm = pe.bboxMm.x1 - pe.bboxMm.x0;
    dragStartHeightMm = pe.bboxMm.y1 - pe.bboxMm.y0;
    dragStartBBoxMm = pe.bboxMm; // move-snap translates this by the live drag delta
    dragStartTargetMm = el.sizeMm != null ? el.sizeMm : dragStartWidthMm;
    canvas.style.cursor = cursorForHandle(handle);

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

  function onPointerMove(e) {
    if (!canvas) return;
    if (simActive) { canvas.style.cursor = "default"; return; }
    const p = canvasPointFromEvent(e);
    // A shape edit is its own drag mode — it never sets `dragMode`, so the
    // element move/resize/pan branches below stay untouched by it.
    if (shapeEdit) {
      const d = pxToMmDelta(p.x - shapeEdit.startPx.x, p.y - shapeEdit.startPx.y);
      const next = shapeEdit.kind === "edge"
        ? moveEdge(shapeEdit.ring, shapeEdit.index, d.dx, d.dy)
        : moveNode(shapeEdit.ring, shapeEdit.index, d.dx, d.dy);
      liveRing = { shapeId: shapeEdit.shapeId, points: next };
      drawOverlay();
      return;
    }
    if (!dragMode) {
      updateHoverCursor(p);
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
    if (shapeEdit) {
      if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
        canvas.releasePointerCapture(e.pointerId);
      }
      // Commit on release. A rejected edit (self-crossing, pinched shut)
      // leaves `shapeEditError` set and simply drops the working ring — the
      // shape snaps back to its last good geometry rather than persisting
      // something the service would refuse.
      commitShapeEdit();
      shapeEdit = null;
      liveRing = null;
      if (canvas) canvas.style.cursor = "default";
      drawOverlay();
      return;
    }
    if (canvas && dragMode && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
      canvas.releasePointerCapture(e.pointerId);
    }
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
    if (activeGuides || sizeMatch || moveBadge || rotateBadgeDeg != null) {
      activeGuides = null;
      sizeMatch = null;
      moveBadge = null;
      rotateBadgeDeg = null;
      scheduleViewRepaint();
    }
  }

  function onPointerLeave() {
    if (!dragMode && canvas) canvas.style.cursor = "default";
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
      width="760"
      height="560"
      tabindex="0"
      role="application"
      aria-label={fieldLabel}
      on:keydown={onCanvasKey}
      on:pointerdown={onPointerDown}
      on:pointermove={onPointerMove}
      on:pointerup={endDrag}
      on:pointercancel={endDrag}
      on:pointerleave={onPointerLeave}
      on:contextmenu={onContextMenu}
      on:wheel={onWheel}
    ></canvas>
    {#if fieldMenu}
      <!-- Drawing tools live here now instead of in the Content step's tile
           row (Kent's call, 2026-08-13: keep them, but as a right-click tool
           rather than an upload button). Positioned at the pointer, dismissed
           by Escape or any click outside — see onWindowPointerDown. -->
      <ul
        class="fieldmenu"
        style="left: {fieldMenu.x}px; top: {fieldMenu.y}px"
        role="menu"
        aria-label="Canvas tools"
      >
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
    {#if !hasDesign && !error && hint}
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
      <button type="button" class="zoombtn zoomfit" on:click={resetView} aria-label="Fit to hoop" title="Fit to hoop"><Icon name="expand" /></button>
      <button
        type="button"
        class="zoombtn viewtoggle"
        class:simon={snapEnabled}
        on:click={toggleSnap}
        aria-pressed={snapEnabled}
        aria-label="Auto-snap"
        title="Auto-snap to other elements and hoop center (hold Alt to suspend)"
      ><Icon name="magnet" /></button>
      <button
        type="button"
        class="zoombtn viewtoggle"
        class:simon={showOutlines}
        on:click={toggleOutlines}
        disabled={!hasDesign}
        aria-pressed={showOutlines}
        aria-label="Show shape outlines"
        title="Outline every digitized shape — off for a clean view of the stitch-out"
      ><Icon name="nodes" /></button>
      <button
        type="button"
        class="zoombtn viewtoggle"
        class:simon={showJumps}
        on:click={toggleJumps}
        disabled={!hasDesign}
        aria-pressed={showJumps}
        aria-label="Show jumps"
        title="Show needle-up travel (jumps)"
      ><Icon name="jump" /></button>
      <button
        type="button"
        class="zoombtn viewtoggle"
        class:simon={showTrims}
        on:click={toggleTrims}
        disabled={!hasDesign}
        aria-pressed={showTrims}
        aria-label="Show trims"
        title="Show thread trims"
      ><Icon name="scissors" /></button>
      <button
        type="button"
        class="zoombtn viewtoggle"
        class:simon={realisticView}
        on:click={toggleRealistic}
        disabled={!hasDesign}
        aria-pressed={realisticView}
        aria-label="Realistic view"
        title="Realistic thread — off for a flat view of coverage and stitch structure"
      ><Icon name="sparkle" /></button>
      <button
        type="button"
        class="zoombtn"
        class:simon={simActive}
        on:click={() => (simActive ? stopSim() : startSim())}
        disabled={!hasDesign}
        aria-label="Stitch simulator"
        aria-pressed={simActive}
        title="Stitch simulator — watch the sew order"
      ><Icon name="play" /></button>
    </div>
    {#if simActive}
      <div class="simbar" role="group" aria-label="Stitch simulator controls">
        <button type="button" class="zoombtn" on:click={simTogglePlay} aria-label={simPlaying ? "Pause" : "Play"}>
          <Icon name={simPlaying ? "pause" : "play"} />
        </button>
        <input
          type="range"
          class="simscrub"
          min="0"
          max={simTotal}
          step="1"
          value={Math.floor(simIndex)}
          on:input={simScrub}
          aria-label="Stitch progress"
        />
        <span class="simcount">{Math.floor(simIndex)} / {simTotal}</span>
        <button type="button" class="zoombtn simspeed" on:click={simCycleSpeed} aria-label="Playback speed">
          {simSpeed}x
        </button>
        <button type="button" class="zoombtn" on:click={stopSim} aria-label="Close simulator"><Icon name="close" /></button>
      </div>
    {/if}
  </div>
  <!-- Keyboard-nudge feedback, spoken not shown. A sibling of `.hoop`, never
       a child: `.hoop` holds the canvas and nothing else, which is what keeps
       chrome off the sewable field (pinned by e2e/field-chrome.spec.js). It
       is off-screen rather than hidden because display:none and
       visibility:hidden both drop an element out of the accessibility tree,
       and a live region outside the tree is never announced. -->
  <p class="fieldlive" aria-live="polite">{liveMsg}</p>
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if shapeEditError}<span class="err" data-testid="shape-edit-error">{shapeEditError}</span>
    <!-- &nbsp; before each separator, not a plain space: Svelte strips leading
         whitespace inside an element, so " · " rendered as "…hoop· This font".
         Pre-existing on the two older warnings; visible on all three now. -->
    {:else if stats}<span class="stats">{stats}</span>{#if warn}<span class="warn">&nbsp;· Smaller than 5 mm — thread can't stitch this cleanly</span>{/if}{#if hoopNote}<span class="warn">&nbsp;· {hoopNote}</span>{/if}{#if unsupportedNote}<span class="warn">&nbsp;· {unsupportedNote}</span>{/if}{/if}
  </div>
</div>
