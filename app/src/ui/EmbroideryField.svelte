<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateAll } from "../lib/generate.js";
  import { ensureFonts } from "../lib/fontLoader.js";
  import { renderRealistic, isDark } from "../lib/preview.js";
  import { designToStrands } from "../lib/strands.js";
  import { advanceIndex, clampIndex, nextSpeed } from "../lib/simulate.js";
  import { EMB } from "../lib/emb.js";
  import { designRectPx, hitTest, pickElement, dragResize, clampOffsets, clampPan, buildSnapLines, snapMove, snapResizeWidth, rotateHandlePx, dragRotate, unionBBox, clampGroupDelta, groupResizePatches } from "../lib/interact.js";
  import { selectedIdsOf } from "../lib/project.js";
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
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    if (activeGuides.hYMm != null) {
      const y = Math.round(renderResult.toCanvas(0, activeGuides.hYMm).y) + 0.5;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
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
    const x = Math.round(Math.min(Math.max(cx - w / 2, 4), canvas.width - w - 4));
    const y = Math.round(Math.min(Math.max(cy - h / 2, 4), canvas.height - h - 4));
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

  function drawOverlay() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
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
    warn = widthMM < MIN_SIZE_MM || heightMM < MIN_SIZE_MM;
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
      hint = "Your embroidery appears here as you add content.";
      lastGenerateResult = null;
      clearToFabric();
      dispatch("dims", null);
      dispatch("stats", { stitchCount: 0 });
      return;
    }

    const garment = garmentFor(project);
    const c = result.combined;
    stats = `${c.stitchCount} stitches · ${c.widthMM.toFixed(0)}×${c.heightMM.toFixed(0)} mm`;
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
      hoop: { garment },
      fabricRgb: project.fabricRgb,
      weave: true,
      view,
      showJumps,
      showTrims,
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
        hoop: { garment },
        fabricRgb: project.fabricRgb,
        weave: true,
        view,
        showJumps,
        showTrims,
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

  onMount(paint);
  // repaint whenever the project (garment/elements/selection) or the
  // runtime image state changes. Drag-move deliberately reuses this same
  // path (cheap full regen) rather than a separate translate-only fast path
  // — regeneration is fast enough here and it keeps one code path for "the
  // project changed" instead of two. `view` is deliberately NOT a dependency
  // here (B2) -- wheel/pan/zoom-button handlers call scheduleViewRepaint()
  // directly instead, so a view-only change never pays for a full generateAll.
  $: if (canvas) { project; runtime; paint(); }

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
    const cw = canvas.width, ch = canvas.height;
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
    // The canvas's CSS size (r.width/height) can differ from its internal
    // pixel size (canvas.width/height) — e.g. it's scaled down to fit the
    // viewport via CSS `max-width`. Without this ratio, pointer coordinates
    // would be off by that scale factor on any screen where the canvas is
    // displayed smaller than its native 760x560.
    const scaleX = canvas.width / r.width;
    const scaleY = canvas.height / r.height;
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

  function onPointerDown(e) {
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
      const { panX, panY } = clampPan(rawPanX, rawPanY, view.zoom, canvas.width, canvas.height);
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

<div class="fieldwrap">
  <div class="hoop">
    <canvas
      bind:this={canvas}
      width="760"
      height="560"
      on:pointerdown={onPointerDown}
      on:pointermove={onPointerMove}
      on:pointerup={endDrag}
      on:pointercancel={endDrag}
      on:pointerleave={onPointerLeave}
      on:wheel={onWheel}
    ></canvas>
    {#if !hasDesign && !error && hint}
      <p class="fieldhint" class:on-dark={project && project.fabricRgb && isDark(project.fabricRgb)}>{hint}</p>
    {/if}
    {#if showDragHint}
      <Hint floating on:dismiss={() => dispatch("dismisshint")}>
        Drag the design to move it — corners resize.
      </Hint>
    {/if}
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
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if stats}<span class="stats">{stats}</span>{#if warn}<span class="warn"> · Smaller than 5 mm — thread can't stitch this cleanly</span>{/if}{/if}
  </div>
</div>
