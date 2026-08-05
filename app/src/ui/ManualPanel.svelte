<script>
  import { createEventDispatcher } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import { defaultManualShape } from "../lib/project.js";
  import { CANVAS_W, CANVAS_H, isValidShape, isNearStart } from "../lib/manualShapes.js";

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

  $: shapes = element.shapes || [];
  $: selectedShape = shapes.find((s) => s.id === selectedShapeId) || null;
  $: canFinish = isValidShape(draft);

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

  function onCanvasClick(e) {
    const pt = canvasPointFromEvent(e);
    if (draft.length >= 2 && isNearStart(draft, pt.x, pt.y)) {
      finishShape();
      return;
    }
    draft = [...draft, pt];
  }

  // A double-click is two `click` events (each already added a point) THEN
  // one `dblclick` — the second click's point is the accidental duplicate
  // this gesture creates (the user meant "done here", not "one more point
  // on top of the last one"), so drop it before finishing.
  function onCanvasDblClick() {
    if (draft.length > 0) draft = draft.slice(0, -1);
    finishShape();
  }

  function undoPoint() {
    draft = draft.slice(0, -1);
  }
  function clearDraft() {
    draft = [];
  }

  function selectShape(id) {
    selectedShapeId = selectedShapeId === id ? null : id;
  }

  function deleteShape(id) {
    patch({ shapes: shapes.filter((s) => s.id !== id) });
    if (selectedShapeId === id) selectedShapeId = null;
  }

  function updateShape(id, p) {
    patch({ shapes: shapes.map((s) => (s.id === id ? { ...s, ...p } : s)) });
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

  function render(canvas, shapeList, draftPts, selectedId) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f4f2ec";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const s of shapeList) {
      if (!isValidShape(s.points)) continue;
      const [r, g, b] = s.colorRgb || [20, 20, 20];
      const isSel = s.id === selectedId;
      drawPolygon(
        ctx, s.points,
        `rgba(${r},${g},${b},0.55)`,
        isSel ? "#4f46e5" : `rgb(${r},${g},${b})`,
        isSel ? 3 : 1.5
      );
      // Stitch-type label at the shape's centroid.
      let cx = 0, cy = 0;
      for (const p of s.points) { cx += p.x; cy += p.y; }
      cx /= s.points.length; cy /= s.points.length;
      ctx.fillStyle = "#111";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(s.stitchType === "satin" ? "SATIN" : "FILL", cx, cy);
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

  $: render(canvasEl, shapes, draft, selectedShapeId);
</script>

<div class="manualpanel">
  <p class="hint">
    Click to place points. Click near the first point (or double-click) to close the shape.
    Draw as many shapes as you like, then pick each one's stitch type, color, and angle below.
  </p>

  <canvas
    bind:this={canvasEl}
    class="mp-canvas"
    width={CANVAS_W}
    height={CANVAS_H}
    on:click={onCanvasClick}
    on:dblclick={onCanvasDblClick}
    role="img"
    aria-label="Shape drawing canvas"
  ></canvas>

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
