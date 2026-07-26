<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateAll } from "../lib/generate.js";
  import { renderRealistic, hoopTransform, drawHoopOutline } from "../lib/preview.js";
  import { EMB } from "../lib/emb.js";
  import { designRectPx, hitTest, pickElement, dragResize, dragMove, clampOffsets } from "../lib/interact.js";
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

  // Drag state (module-local to this component instance, not reactive —
  // none of it needs to trigger a re-render on its own).
  let dragMode = null; // null | "resize" | "move"
  let dragHandle = null; // "nw"|"ne"|"sw"|"se" when dragMode === "resize"
  let dragTargetId = null; // element id the current drag applies to
  let dragStartPx = null; // {x,y} canvas-space pointer start
  let dragStartWidthMm = 0;
  let dragStartHeightMm = 0;
  let dragStartOffXMm = 0;
  let dragStartOffYMm = 0;
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

  function clearToFabric() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#e9e6df";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // Nice-to-have: still show the hoop bounds on the empty-state canvas
    // when we know the garment, so the field never looks unrelated to size.
    const garment = garmentFor(project);
    if (garment) drawHoopOutline(ctx, hoopTransform(garment, canvas.width, canvas.height, 24));
  }

  function accentColor() {
    if (typeof document === "undefined") return "#2f6fed";
    const v = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    return v || "#2f6fed";
  }

  // Draws the selection box + 4 corner handles ONLY around the SELECTED
  // element's rect — every other element renders plain (no overlay), even
  // if it's also "ready" this paint.
  function drawOverlay() {
    if (!canvas) return;
    const rect = perElementRects.find((r) => r.id === project.selectedId);
    if (!rect) return;
    const ctx = canvas.getContext("2d");
    const color = accentColor();
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
    renderResult = renderRealistic(canvas, c, { hoop: { garment } });
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

  onMount(paint);
  // repaint whenever the project (garment/elements/selection) or the
  // runtime image state changes. Drag-move deliberately reuses this same
  // path (cheap full regen) rather than a separate translate-only fast path
  // — regeneration is fast enough here and it keeps one code path for "the
  // project changed" instead of two.
  $: if (canvas) { project; runtime; paint(); }

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
      handle = hitId ? "body" : "none";
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
      if (!hitId) return; // empty space: no drag, selection unchanged
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
    ></canvas>
    {#if !hasDesign && !error && hint}
      <p class="fieldhint">{hint}</p>
    {/if}
    {#if showDragHint}
      <Hint floating on:dismiss={() => dispatch("dismisshint")}>
        Drag the design to move it — corners resize.
      </Hint>
    {/if}
  </div>
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if stats}<span class="stats">{stats}</span>{#if warn}<span class="warn"> · Smaller than 5 mm — thread can't stitch this cleanly</span>{/if}{/if}
  </div>
</div>
