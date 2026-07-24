<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateDesign, generateImageDesign } from "../lib/generate.js";
  import { renderRealistic, hoopTransform, drawHoopOutline } from "../lib/preview.js";
  import { EMB } from "../lib/emb.js";
  import { designRectPx, hitTest, dragResize, dragMove } from "../lib/interact.js";

  export let project;
  export let flat = null;

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

  // Drag state (module-local to this component instance, not reactive —
  // none of it needs to trigger a re-render on its own).
  let dragMode = null; // null | "resize" | "move"
  let dragHandle = null; // "nw"|"ne"|"sw"|"se" when dragMode === "resize"
  let dragStartPx = null; // {x,y} canvas-space pointer start
  let dragStartWidthMm = 0;
  let dragStartHeightMm = 0;
  let dragStartOffXMm = 0;
  let dragStartOffYMm = 0;
  let rafScheduled = false;
  let pendingPatch = null;

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

  // Draws the selection box + 4 corner handles over the just-rendered design.
  function drawOverlay() {
    if (!canvas || !renderResult || !renderResult.designBBoxMm) return;
    const rect = designRectPx(renderResult.designBBoxMm, renderResult.toCanvas);
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

  function paintImage() {
    if (!flat) {
      hasDesign = false;
      hint = "Upload a logo or clean art — flat colors stitch best.";
      clearToFabric();
      dispatch("dims", null);
      return;
    }
    try {
      const design = generateImageDesign(flat, project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      warn = design.widthMM < MIN_SIZE_MM || design.heightMM < MIN_SIZE_MM;
      renderResult = renderRealistic(canvas, design, { hoop: { garment: garmentFor(project) } });
      hasDesign = true;
      drawOverlay();
      dispatch("dims", { widthMM: design.widthMM, heightMM: design.heightMM });
    } catch (e) {
      error = e.message;
      hasDesign = false;
      renderResult = null;
      clearToFabric();
      dispatch("dims", null);
    }
  }

  function paintText() {
    const hasText = project && project.text && project.text.trim().length > 0;
    if (!hasText) {
      hasDesign = false;
      hint = "Your embroidery appears here as you add text.";
      clearToFabric();
      dispatch("dims", null);
      return;
    }
    try {
      const design = generateDesign(project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      warn = design.widthMM < MIN_SIZE_MM || design.heightMM < MIN_SIZE_MM;
      renderResult = renderRealistic(canvas, design, { colorOverride: project.colorRgb, hoop: { garment: garmentFor(project) } });
      hasDesign = true;
      drawOverlay();
      dispatch("dims", { widthMM: design.widthMM, heightMM: design.heightMM });
    } catch (e) {
      error = e.message;
      hasDesign = false;
      renderResult = null;
      clearToFabric();
      dispatch("dims", null);
    }
  }

  function paint() {
    if (!canvas) return;
    error = "";
    stats = "";
    warn = false;
    hint = "";
    renderResult = null;
    if (project.mode === "image") paintImage();
    else paintText();
  }

  onMount(paint);
  // repaint whenever the project (garment/text/font/color/mode/size/offset)
  // or the flattened image state changes. Drag-move deliberately reuses this
  // same path (cheap full regen) rather than a separate translate-only
  // fast path — regeneration is fast enough here and it keeps one code path
  // for "the project changed" instead of two.
  $: if (canvas) { project; flat; paint(); }

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

  function currentRect() {
    if (!renderResult || !renderResult.designBBoxMm) return null;
    return designRectPx(renderResult.designBBoxMm, renderResult.toCanvas);
  }

  function updateHoverCursor(p) {
    if (!canvas) return;
    const rect = currentRect();
    const handle = rect ? hitTest(rect, p.x, p.y, HANDLE_R) : "none";
    canvas.style.cursor = cursorForHandle(handle);
  }

  function schedulePatchFlush() {
    if (rafScheduled) return;
    rafScheduled = true;
    requestAnimationFrame(() => {
      rafScheduled = false;
      if (pendingPatch) {
        const patch = pendingPatch;
        pendingPatch = null;
        dispatch("update", patch);
      }
    });
  }

  function onPointerDown(e) {
    if (!canvas || !renderResult) return;
    const rect = currentRect();
    if (!rect) return;
    const p = canvasPointFromEvent(e);
    const handle = hitTest(rect, p.x, p.y, HANDLE_R);
    if (handle === "none") return;

    canvas.setPointerCapture(e.pointerId);
    dragStartPx = p;
    dragStartOffXMm = project.offsetXMm || 0;
    dragStartOffYMm = project.offsetYMm || 0;
    const bbox = renderResult.designBBoxMm;
    dragStartWidthMm = bbox.x1 - bbox.x0;
    dragStartHeightMm = bbox.y1 - bbox.y0;
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
      if (project.sizeMm == null) {
        dispatch("update", { sizeMm: dragStartWidthMm });
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

    if (dragMode === "resize") {
      const { wMm: hoopWmm } = hoopSizeMm(project);
      const newWidthMm = dragResize(dragStartWidthMm, dragStartHeightMm, dragHandle, dxMm, dyMm, MIN_SIZE_MM, hoopWmm || dragStartWidthMm);
      pendingPatch = { sizeMm: newWidthMm };
    } else if (dragMode === "move") {
      const { wMm: hoopWmm, hMm: hoopHmm } = hoopSizeMm(project);
      pendingPatch = dragMove(dragStartOffXMm, dragStartOffYMm, dxMm, dyMm, dragStartWidthMm, dragStartHeightMm, hoopWmm, hoopHmm);
    }
    schedulePatchFlush();
  }

  function endDrag(e) {
    if (canvas && dragMode && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
      canvas.releasePointerCapture(e.pointerId);
    }
    dragMode = null;
    dragHandle = null;
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
  </div>
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if stats}<span class="stats">{stats}</span>{#if warn}<span class="warn"> · Smaller than 5 mm — thread can't stitch this cleanly</span>{/if}{/if}
  </div>
</div>
