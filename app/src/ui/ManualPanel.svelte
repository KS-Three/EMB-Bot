<script>
  import { createEventDispatcher } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import { defaultManualShape } from "../lib/project.js";
  import {
    CANVAS_W, CANVAS_H, MAX_SHAPE_POINTS,
    isValidShape, isNearStart, isDuplicateOfLast, shapeIssues,
  } from "../lib/manualShapes.js";

  // Manual digitizing mode (MVP slice): draw straight-line polygon outlines
  // directly on a canvas, then assign each one a stitch type/color/angle by
  // hand. Zero image analysis anywhere in this component. Patch convention
  // (see TextStep.svelte's comment for the same one): every edit dispatches
  // an "elupdate" event shaped { id: element.id, patch } directly.
  export let element;
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // The in-progress shape being drawn right now is ephemeral UI state, same
  // pattern ImagePanel's merge-selection uses — it's NOT part of the
  // persisted element, so it resets if this panel remounts (switching
  // elements, reloading). Only COMPLETED shapes (element.shapes) persist.
  let draft = [];
  let selectedShapeId = null;
  let canvasEl;
  // Brief on-canvas hint shown when a click is dropped because the draft
  // already hit MAX_SHAPE_POINTS — cleared on a timer so it reads as a
  // transient nudge, not a persistent error banner.
  let capHint = false;
  let capHintTimer = null;

  // ---- Vertex editing for a finished shape ------------------------------
  // A selected finished shape can be dropped into "edit points" mode: drag
  // an existing vertex to a new spot, and the released position is
  // re-validated through the same shapeIssues() the draft-drawing flow
  // already uses before it's ever written back — same "drag, then patch on
  // release" shape DigitizePanel.svelte's boundary editor established
  // (see its startEditDrag/onEditPointerMove/editingId/editPoints/dragIndex),
  // reimplemented fresh here against this component's single <canvas>
  // (hit-testing a click by distance to each point) rather than
  // DigitizePanel's per-vertex SVG elements. A drag that leaves the shape
  // self-intersecting/degenerate is never patched through — editPoints stays
  // local-only and editIssues (below) surfaces the same rejection text
  // draftIssues does, so the user sees why and can keep adjusting instead of
  // having the edit silently dropped.
  const VERTEX_HIT_R = 8; // canvas-px radius for "this click/drag is on that vertex"
  let editingId = null;
  let editPoints = [];
  let dragIndex = null;

  $: shapes = element.shapes || [];
  $: selectedShape = shapes.find((s) => s.id === selectedShapeId) || null;
  // Only surface issues once there are enough points for them to be
  // meaningful (self-intersection/area problems don't exist below a
  // triangle) — otherwise every fresh draft would open with "Needs at
  // least 3 points," which is just the obvious starting state, not a
  // problem to report.
  $: draftIssues = draft.length >= 3 ? shapeIssues(draft) : [];
  $: canFinish = draft.length >= 3 && draftIssues.length === 0;
  // Same "only surface once meaningful" reasoning as draftIssues — computed
  // continuously (not just after a drag ends) so a mid-drag self-intersect
  // shows up live, the same way the draft-drawing flow already behaves.
  $: editIssues = editingId ? shapeIssues(editPoints) : [];

  function nextShapeId(list) {
    let max = 0;
    for (const s of list) {
      const m = /^s(\d+)$/.exec(s.id);
      if (m) max = Math.max(max, parseInt(m[1], 10));
    }
    return "s" + (max + 1);
  }

  function canvasPointFromEvent(e) {
    const rect = canvasEl.getBoundingClientRect();
    const scaleX = canvasEl.width / rect.width;
    const scaleY = canvasEl.height / rect.height;
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
  }

  function finishShape() {
    if (!isValidShape(draft)) return;
    const shape = { ...defaultManualShape(nextShapeId(shapes)), points: draft };
    patch({ shapes: [...shapes, shape] });
    draft = [];
    selectedShapeId = shape.id;
  }

  function flashCapHint() {
    capHint = true;
    if (capHintTimer) clearTimeout(capHintTimer);
    capHintTimer = setTimeout(() => { capHint = false; }, 2000);
  }

  function onCanvasClick(e) {
    // Vertex-edit mode owns the canvas's pointer gestures (drag-to-move via
    // onCanvasPointerDown/Move/Up below) — a plain click while editing
    // shouldn't also drop a new draft point.
    if (editingId) return;
    const pt = canvasPointFromEvent(e);
    if (draft.length >= 2 && isNearStart(draft, pt.x, pt.y)) {
      finishShape();
      return;
    }
    // Same "ignore the click" precedent as the closing-radius check above:
    // a duplicate-consecutive click (double-tap jitter, not a deliberate
    // second point) or a click past the point cap just doesn't add a point.
    if (isDuplicateOfLast(draft, pt.x, pt.y)) return;
    if (draft.length >= MAX_SHAPE_POINTS) {
      flashCapHint();
      return;
    }
    draft = [...draft, pt];
  }

  // A double-click is two `click` events THEN one `dblclick`. The second
  // click lands on (or within DUP_POINT_EPS_PX of) the same point as the
  // first, so onCanvasClick's duplicate-consecutive-point dedupe already
  // drops it before this handler ever runs — nothing extra to undo here,
  // just finish with whatever's in the draft.
  function onCanvasDblClick() {
    if (editingId) return;
    finishShape();
  }

  function undoPoint() {
    draft = draft.slice(0, -1);
  }
  function clearDraft() {
    draft = [];
  }

  function selectShape(id) {
    // Switching (or clearing) the selection always drops any in-progress
    // vertex edit — editPoints is local-only UI state tied to one shape, and
    // there's no "still editing shape A while shape B is selected" state
    // this component means to support.
    stopShapeEdit();
    selectedShapeId = selectedShapeId === id ? null : id;
  }

  function deleteShape(id) {
    if (editingId === id) stopShapeEdit();
    patch({ shapes: shapes.filter((s) => s.id !== id) });
    if (selectedShapeId === id) selectedShapeId = null;
  }

  function updateShape(id, p) {
    patch({ shapes: shapes.map((s) => (s.id === id ? { ...s, ...p } : s)) });
  }

  // ---- Vertex editing ----------------------------------------------------
  function startShapeEdit(id) {
    const shape = shapes.find((s) => s.id === id);
    if (!shape) return;
    editingId = id;
    editPoints = shape.points.map((p) => ({ ...p }));
    dragIndex = null;
  }

  function stopShapeEdit() {
    editingId = null;
    editPoints = [];
    dragIndex = null;
  }

  // Nearest vertex within VERTEX_HIT_R of (x, y), or -1 — this component's
  // canvas-hit-testing stand-in for DigitizePanel's per-vertex SVG elements
  // (each of which gets its own pointerdown handler there; here there's one
  // canvas, so the hit test does the same job by distance).
  function hitTestVertex(points, x, y) {
    let best = -1;
    let bestD = VERTEX_HIT_R;
    for (let i = 0; i < points.length; i++) {
      const d = Math.hypot(points[i].x - x, points[i].y - y);
      if (d <= bestD) {
        bestD = d;
        best = i;
      }
    }
    return best;
  }

  function onCanvasPointerDown(e) {
    if (!editingId) return;
    const pt = canvasPointFromEvent(e);
    const idx = hitTestVertex(editPoints, pt.x, pt.y);
    if (idx === -1) return;
    e.preventDefault();
    dragIndex = idx;
    try {
      canvasEl.setPointerCapture(e.pointerId);
    } catch (err) {
      // Pointer capture is unavailable in some test/embedded environments
      // (DigitizePanel's startEditDrag notes the same) — dragging still
      // works off plain pointermove, just less robustly past the canvas
      // edge.
    }
  }

  function onCanvasPointerMove(e) {
    if (dragIndex == null) return;
    editPoints[dragIndex] = canvasPointFromEvent(e);
    editPoints = editPoints;
  }

  // "Drag, then patch on release": the moved vertex only reaches
  // element.shapes (via updateShape) if the resulting polygon is still
  // valid — an invalid drag leaves editPoints (and its live editIssues
  // message) as the only trace, exactly like a draft that hasn't been
  // finished yet.
  function endVertexDrag(e) {
    if (dragIndex == null) return;
    dragIndex = null;
    if (editingId && shapeIssues(editPoints).length === 0) {
      updateShape(editingId, { points: editPoints.map((p) => ({ ...p })) });
    }
    try {
      canvasEl.releasePointerCapture(e.pointerId);
    } catch (err) {
      // See onCanvasPointerDown.
    }
  }

  function onAngleInput(e) {
    if (!selectedShape) return;
    const raw = e.target.value;
    const v = raw.trim() === "" ? null : parseFloat(raw);
    updateShape(selectedShape.id, { angleDeg: Number.isFinite(v) ? v : null });
  }

  function summary(shape) {
    return `Shape ${shape.id.replace(/^s/, "")} · ${shape.stitchType === "satin" ? "Satin" : "Fill"}`;
  }

  // ---- Keyboard shortcuts ------------------------------------------------
  // Scoped to specific interactive elements — the canvas (tabindex +
  // on:keydown below) AND the shape-row/delete buttons (selecting a shape
  // by clicking its row moves DOM focus there, not to the canvas, so Delete
  // needs somewhere to fire from right after that click too) — same
  // "attach to a specific interactive element, not window" convention
  // DigitizePanel's onEditVertexKeydown uses for its per-vertex handles,
  // rather than a global window listener that would fire regardless of
  // which panel/element is on screen.
  //   Escape  — exit vertex-edit mode if active, else cancel the draft.
  //   Enter   — finish the draft (only once canFinish agrees it's sewable).
  //   Delete/
  //   Backspace — delete the selected finished shape, but ONLY when no
  //     draft is in progress and no vertex edit is in progress: a draft or
  //     an in-progress edit is unrelated state the user is actively
  //     building, and Delete's job here is never to reach past that and
  //     nuke a different, already-finished shape by surprise.
  function onCanvasKeydown(e) {
    if (e.key === "Escape") {
      if (editingId) {
        stopShapeEdit();
        e.preventDefault();
      } else if (draft.length) {
        clearDraft();
        e.preventDefault();
      }
      return;
    }
    if (e.key === "Enter") {
      if (canFinish) {
        finishShape();
        e.preventDefault();
      }
      return;
    }
    if (e.key === "Delete" || e.key === "Backspace") {
      if (selectedShapeId && draft.length === 0 && !editingId) {
        deleteShape(selectedShapeId);
        e.preventDefault();
      }
    }
  }

  // ---- Drawing ---------------------------------------------------------
  function drawPolygon(ctx, points, fillStyle, strokeStyle, lineWidth) {
    if (points.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
    if (fillStyle) {
      ctx.closePath();
      ctx.fillStyle = fillStyle;
      ctx.fill();
    }
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
  }

  function render(canvas, shapeList, draftPts, selectedId, editId, editPts, editValid) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f4f2ec";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const s of shapeList) {
      const editing = s.id === editId;
      // The shape being edited draws from the LIVE (possibly momentarily
      // invalid, mid-drag) editPts instead of its last-persisted points —
      // everything else still only draws once it's a real polygon.
      const pts = editing ? editPts : s.points;
      if (!editing && !isValidShape(pts)) continue;
      const [r, g, b] = s.colorRgb || [20, 20, 20];
      const isSel = s.id === selectedId;
      const invalid = editing && !editValid;
      drawPolygon(
        ctx, pts,
        invalid ? "rgba(192,57,43,0.25)" : `rgba(${r},${g},${b},0.55)`,
        invalid ? "#c0392b" : (isSel ? "#4f46e5" : `rgb(${r},${g},${b})`),
        isSel || editing ? 3 : 1.5
      );
      if (editing) {
        // Draggable vertex handles instead of the centroid label — this IS
        // the "edit points" affordance.
        for (const p of pts) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
          ctx.fillStyle = "#fff";
          ctx.fill();
          ctx.strokeStyle = invalid ? "#c0392b" : "#4f46e5";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      } else {
        // Stitch-type label at the shape's centroid.
        let cx = 0, cy = 0;
        for (const p of pts) { cx += p.x; cy += p.y; }
        cx /= pts.length; cy /= pts.length;
        ctx.fillStyle = "#111";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(s.stitchType === "satin" ? "SATIN" : "FILL", cx, cy);
      }
    }

    if (draftPts.length) {
      drawPolygon(ctx, draftPts, null, "#4f46e5", 2);
      for (let i = 0; i < draftPts.length; i++) {
        const p = draftPts[i];
        ctx.beginPath();
        ctx.arc(p.x, p.y, i === 0 ? 5 : 3, 0, Math.PI * 2);
        ctx.fillStyle = i === 0 ? "#4f46e5" : "#fff";
        ctx.fill();
        ctx.strokeStyle = "#4f46e5";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }

  $: render(canvasEl, shapes, draft, selectedShapeId, editingId, editPoints, editIssues.length === 0);
</script>

<div class="manualpanel">
  <p class="hint">
    Click to place points. Click near the first point (or double-click) to close the shape.
    Draw as many shapes as you like, then pick each one's stitch type, color, and angle below.
    Escape cancels a draft, Enter finishes it, Delete removes the selected shape.
  </p>

  <div class="mp-canvas-wrap">
    <canvas
      bind:this={canvasEl}
      class="mp-canvas"
      width={CANVAS_W}
      height={CANVAS_H}
      tabindex="0"
      on:click={onCanvasClick}
      on:dblclick={onCanvasDblClick}
      on:pointerdown={onCanvasPointerDown}
      on:pointermove={onCanvasPointerMove}
      on:pointerup={endVertexDrag}
      on:pointercancel={endVertexDrag}
      on:pointerleave={endVertexDrag}
      on:keydown={onCanvasKeydown}
      role="img"
      aria-label="Shape drawing canvas"
    ></canvas>
    {#if capHint}
      <p class="mp-caphint" role="status">Point limit reached ({MAX_SHAPE_POINTS} max) — finish or clear this shape.</p>
    {/if}
  </div>

  {#if draftIssues.length}
    <p class="mp-draftissue" role="alert">{draftIssues.join(" ")}</p>
  {/if}
  {#if editingId && editIssues.length}
    <p class="mp-draftissue" role="alert">{editIssues.join(" ")}</p>
  {/if}

  <div class="mp-tools">
    <button type="button" on:click={undoPoint} disabled={!draft.length}>Undo point</button>
    <button type="button" on:click={clearDraft} disabled={!draft.length}>Clear shape</button>
    <button type="button" class="primary" on:click={finishShape} disabled={!canFinish}>Finish shape</button>
  </div>

  {#if shapes.length}
    <ul class="mp-shapelist">
      {#each shapes as s (s.id)}
        <li>
          <button
            type="button"
            class="mp-shaperow"
            class:sel={s.id === selectedShapeId}
            on:click={() => selectShape(s.id)}
            on:keydown={onCanvasKeydown}
          >
            <span class="mp-swatch" style="background: rgb({s.colorRgb[0]},{s.colorRgb[1]},{s.colorRgb[2]})"></span>
            <span class="mp-shapename">{summary(s)}</span>
          </button>
          <button
            type="button"
            class="mp-remove"
            title="Delete shape"
            aria-label="Delete shape"
            on:click={() => deleteShape(s.id)}
            on:keydown={onCanvasKeydown}
          >✕</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mp-empty">No shapes yet — draw one above to get started.</p>
  {/if}

  {#if selectedShape}
    <div class="mp-assign">
      <h3>{summary(selectedShape)}</h3>
      <div class="mp-row">
        <span class="mp-label">Stitch type</span>
        <div class="mp-btns">
          {#each [["fill", "Fill"], ["satin", "Satin"]] as [val, label]}
            <button
              type="button"
              class="mp-btn"
              class:active={selectedShape.stitchType === val}
              on:click={() => updateShape(selectedShape.id, { stitchType: val })}
            >{label}</button>
          {/each}
        </div>
      </div>
      <div class="mp-row">
        <span class="mp-label">Points</span>
        {#if editingId === selectedShape.id}
          <button type="button" class="mp-btn active" on:click={stopShapeEdit}>Done editing</button>
        {:else}
          <button
            type="button"
            class="mp-btn"
            disabled={draft.length > 0}
            on:click={() => startShapeEdit(selectedShape.id)}
          >Edit points</button>
        {/if}
      </div>
      <div class="mp-row">
        <span class="mp-label">Color</span>
        <ThreadPicker compact rgb={selectedShape.colorRgb} on:pick={(e) => updateShape(selectedShape.id, { colorRgb: e.detail })} />
      </div>
      <label class="mp-row mp-angle">
        <span class="mp-label">Fill angle</span>
        <input
          type="number"
          step="1"
          placeholder="auto"
          value={selectedShape.angleDeg == null ? "" : selectedShape.angleDeg}
          on:input={onAngleInput}
        />
        <span class="mp-deg">° (blank = auto)</span>
      </label>
    </div>
  {/if}
</div>

<style>
  .manualpanel { display: flex; flex-direction: column; gap: 10px; }
  .hint { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
  .mp-canvas-wrap { position: relative; }
  .mp-canvas {
    width: 100%;
    max-width: 100%;
    height: auto;
    aspect-ratio: 600 / 400;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: #f4f2ec;
    cursor: crosshair;
    touch-action: none;
    display: block;
  }
  .mp-caphint {
    position: absolute;
    left: 50%;
    bottom: 10px;
    transform: translateX(-50%);
    margin: 0;
    padding: 4px 10px;
    border-radius: var(--radius-s, 8px);
    background: rgba(17, 17, 17, 0.82);
    color: #fff;
    font-size: var(--fs-xs, 12px);
    white-space: nowrap;
    pointer-events: none;
  }
  .mp-draftissue {
    font-size: var(--fs-xs, 12px);
    color: var(--danger, #c0392b);
    margin: 0;
  }
  .mp-tools { display: flex; gap: 6px; flex-wrap: wrap; }
  .mp-tools button {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .mp-tools button:disabled { opacity: 0.45; cursor: not-allowed; }
  .mp-tools button.primary {
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    border-color: var(--accent, #4f46e5);
  }
  .mp-shapelist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .mp-shapelist li { display: flex; align-items: center; gap: 4px; }
  .mp-shaperow {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
    text-align: left;
  }
  .mp-shaperow.sel { border-color: var(--accent, #4f46e5); background: rgba(79,70,229,0.08); }
  .mp-swatch { width: 14px; height: 14px; border-radius: 3px; border: 1px solid var(--tint-border, #ccd6fb); display: inline-block; flex: none; }
  .mp-remove { border: none; background: none; cursor: pointer; font-size: 13px; color: var(--danger, #c0392b); padding: 4px; }
  .mp-empty { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
  .mp-assign { border-top: 1px solid var(--tint-border, #ccd6fb); padding-top: 10px; margin-top: 4px; }
  .mp-assign h3 { margin: 0 0 8px; font-size: var(--fs-xs, 12px); }
  .mp-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
  .mp-label { display: block; font-size: var(--fs-xs, 12px); min-width: 70px; }
  .mp-btns { display: flex; gap: 6px; }
  .mp-btn {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .mp-btn.active { background: var(--accent, #4f46e5); color: var(--accent-ink, #fff); border-color: var(--accent, #4f46e5); }
  .mp-angle input {
    width: 64px;
    padding: 5px 8px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    font-size: var(--fs-xs, 12px);
  }
  .mp-deg { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); }
</style>
