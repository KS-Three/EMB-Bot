<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateAll } from "../lib/generate.js";
  import { renderRealistic, isDark } from "../lib/preview.js";
  import { EMB } from "../lib/emb.js";
  import { designRectPx, hitTest, pickElement, dragResize, dragMove, clampOffsets, clampPan } from "../lib/interact.js";
  import Hint from "./Hint.svelte";

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

  // Drag state (module-local to this component instance, not reactive —
  // none of it needs to trigger a re-render on its own).
  let dragMode = null; // null | "resize" | "move" | "pan"
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

  // Draws the selection box + 4 corner handles ONLY around the SELECTED
  // element's rect — every other element renders plain (no overlay), even
  // if it's also "ready" this paint.
  function drawOverlay() {
    if (!canvas) return;
    const rect = perElementRects.find((r) => r.id === project.selectedId);
    if (!rect) return;
    const ctx = canvas.getContext("2d");
    const color = selectionColor();
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
        dispatch("elupdate", { id: pe.id, patch: clamped });
      }
    }
  }

  function paint() {
    if (!canvas) return;
    error = "";
    stats = "";
    warn = false;
    hint = "";
    renderResult = null;
    perElementRects = [];
    peById = {};

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
      });
      perElementRects = [];
      if (renderResult && renderResult.toCanvas) {
        for (const pe of lastGenerateResult.perElement) {
          const rect = designRectPx(pe.bboxMm, renderResult.toCanvas);
          if (rect) perElementRects.push({ id: pe.id, ...rect });
        }
      }
      drawOverlay();
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

  function updateHoverCursor(p) {
    if (!canvas) return;
    const selRect = rectFor(project.selectedId);
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
        dispatch("elupdate", p);
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

    if (!canvas || !renderResult) return;
    const p = canvasPointFromEvent(e);

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
    const scale = renderResult && renderResult.scale ? renderResult.scale : 1; // px per mm
    const dxMm = (p.x - dragStartPx.x) / scale;
    const dyMm = (p.y - dragStartPx.y) / scale;
    const { wMm: hoopWmm, hMm: hoopHmm } = hoopSizeMm(project);

    if (dragMode === "resize") {
      const newWidthMm = dragResize(dragStartWidthMm, dragStartHeightMm, dragHandle, dxMm, dyMm, MIN_SIZE_MM, hoopWmm || dragStartWidthMm);
      pendingPatch = { id: dragTargetId, patch: { sizeMm: newWidthMm } };
    } else if (dragMode === "move") {
      const moved = dragMove(dragStartOffXMm, dragStartOffYMm, dxMm, dyMm, dragStartWidthMm, dragStartHeightMm, hoopWmm, hoopHmm);
      pendingPatch = { id: dragTargetId, patch: moved };
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
      <button type="button" class="zoombtn" on:click={zoomOut} disabled={view.zoom <= MIN_ZOOM} aria-label="Zoom out">−</button>
      <span class="zoompct">{Math.round(view.zoom * 100)}%</span>
      <button type="button" class="zoombtn" on:click={zoomIn} disabled={view.zoom >= MAX_ZOOM} aria-label="Zoom in">+</button>
      <button type="button" class="zoombtn zoomfit" on:click={resetView} aria-label="Fit to hoop" title="Fit to hoop">⤢</button>
    </div>
  </div>
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if stats}<span class="stats">{stats}</span>{#if warn}<span class="warn"> · Smaller than 5 mm — thread can't stitch this cleanly</span>{/if}{/if}
  </div>
</div>
