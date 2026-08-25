<script>
  import { createEventDispatcher } from "svelte";
  import { WORK_MAX_PX, ALPHA_CUTOFF } from "../lib/flatten.js";
  import { traceShapesFromRGBA, rescaleTracedShapes } from "../lib/manualTrace.js";
  import { CANVAS_W, CANVAS_H, nextShapeIds, flattenShape } from "../lib/manualShapes.js";

  // Upload an image, trace it (app/src/lib/manualTrace.js, PR 1) into a
  // starting set of manual-digitizing shapes, preview the result, and let
  // the user add the finished, id-assigned shapes to ManualPanel's canvas in
  // ONE batch. Every bit of image/trace state in this component (`workImage`,
  // the live trace result, the preview shape list) is LOCAL and preview-only
  // — nothing here ever touches `element` or dispatches a `patch`. The
  // parent (ManualPanel.svelte) owns turning the dispatched "traced" event
  // into a real patch; see its onTraced handler.
  export let existingShapes = []; // READ-ONLY: the element's current shapes,
  // consulted only so newly traced shapes get ids that don't collide (via
  // manualShapes.js's nextShapeIds, the same batch-safe allocator PR 1 added
  // for exactly this caller). Reading this is not "touching element/patch" —
  // this component never writes back to it or anything derived from it.

  // The decoded+downscaled working image ({ rgba, w, h }), or null before an
  // upload — this IS the "local, preview-only working area" the app never
  // reads or writes; it's a real `export let` (not a plain script-local
  // variable) purely so Svelte's own reassignment-is-reactive machinery
  // drives every `$:` block below off one variable the normal way, which
  // doubles as a clean seam for tests to seed "already decoded an image"
  // state directly (jsdom has no real createImageBitmap/canvas decode path —
  // see DigitizePanel.spec.js's precedent for leaving that to Playwright)
  // without faking a file upload. The live app never passes this prop in —
  // it's populated purely by this component's own onFile handler below.
  export let workImage = null;

  const d = createEventDispatcher();

  // Mirrors manualTrace.js's own DEFAULT_N_COLORS — kept in sync by hand
  // since that module doesn't export its tuning constants (they're meant to
  // stay internal defaults, not a public API surface).
  const DEFAULT_N_COLORS = 6;

  let fileName = "";
  let error = "";
  let busy = false;
  let nColors = DEFAULT_N_COLORS;
  let removeBg = true;

  // ---- upload + decode ---------------------------------------------------
  // Identical createImageBitmap-with-<img>+object-URL-fallback pattern
  // DigitizePanel.svelte/ImagePanel.svelte already use for file decode.
  async function loadImage(file) {
    if (typeof createImageBitmap === "function") {
      try {
        return await createImageBitmap(file);
      } catch (e) {
        // fall through to the <img> + object URL fallback below
      }
    }
    const url = URL.createObjectURL(file);
    try {
      return await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("Could not read this image file."));
        img.src = url;
      });
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  // Draw `img` to an offscreen canvas at WORK_MAX_PX long side and read raw
  // RGBA — same offscreen-canvas-downscale step ImagePanel.svelte's own
  // prepRGBA uses (ported from src/app.js's prepRGBA), including snapping
  // low-alpha edge pixels fully transparent so flattenRGBA's background-
  // removal/palette step (inside traceShapesFromRGBA) never treats an
  // anti-aliased edge pixel as its own spurious "opaque" stray color.
  function prepRGBA(img) {
    const iw = img.width, ih = img.height;
    const longest = Math.max(iw, ih) || 1;
    const scale = Math.min(1, WORK_MAX_PX / longest);
    const w = Math.max(1, Math.round(iw * scale));
    const h = Math.max(1, Math.round(ih * scale));

    const cv = document.createElement("canvas");
    cv.width = w;
    cv.height = h;
    const ctx = cv.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);

    const rgba = ctx.getImageData(0, 0, w, h).data;
    for (let i = 3; i < rgba.length; i += 4) {
      if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
    }
    return { rgba, w, h };
  }

  async function onFile(e) {
    const file = e.currentTarget.files && e.currentTarget.files[0];
    e.currentTarget.value = ""; // re-selecting the same file must re-fire change
    if (!file) return;
    error = "";
    busy = true;
    try {
      const img = await loadImage(file);
      workImage = prepRGBA(img);
      fileName = file.name;
      // Hand the decoded image straight up as a tracing BACKDROP, before any
      // question of auto-tracing. The two ways to digitize this artwork are
      // both live from here: take the auto-traced shapes below, or ignore
      // them, close this panel, and click your own nodes around the artwork
      // now showing under the canvas. The second is the whole point of a
      // manual tool and was impossible while the drawing canvas was blank.
      d("image", { image: workImage });
    } catch (err) {
      error = (err && err.message) || "Could not read this image file.";
      workImage = null;
      fileName = "";
      d("image", { image: null });
    } finally {
      busy = false;
    }
  }

  // ---- live trace, reactive on the ALREADY-DECODED workImage -------------
  // Changing nColors/removeBg re-runs traceShapesFromRGBA against the cached
  // pixels only — cheap, no re-upload, no re-decode. tolerance/curve knobs
  // are left at manualTrace.js's own defaults (opts.simplifyTolPx etc. all
  // omitted below) — the two controls exposed here are the genuinely
  // user-facing ones.
  $: traceResult = workImage
    ? traceShapesFromRGBA(workImage.rgba, workImage.w, workImage.h, { nColors, removeBg })
    : { shapes: [], warnings: [] };

  $: warnings = traceResult.warnings || [];

  // Sized to fit CANVAS_W x CANVAS_H — the same canvas ManualPanel's own
  // shape-drawing surface uses — so the preview and the eventual real
  // canvas placement line up 1:1, and "Add" needs no further transform.
  $: previewShapes = workImage
    ? rescaleTracedShapes(traceResult.shapes, workImage.w, workImage.h, CANVAS_W, CANVAS_H)
    : [];

  // Per-color swatch legend: color + how many preview shapes share it, in
  // first-seen (palette) order.
  function legendFor(shapeList) {
    const order = [];
    const counts = new Map();
    for (const s of shapeList) {
      const key = (s.colorRgb || [0, 0, 0]).join(",");
      if (!counts.has(key)) {
        counts.set(key, 0);
        order.push({ key, colorRgb: s.colorRgb });
      }
      counts.set(key, counts.get(key) + 1);
    }
    return order.map((o) => ({ colorRgb: o.colorRgb, count: counts.get(o.key) }));
  }
  $: legend = legendFor(previewShapes);

  // ---- preview rendering ---------------------------------------------------
  // A compact, standalone preview loop — deliberately NOT ManualPanel's own
  // render()/drawShape, which is tightly coupled to its drag/edit/curve-
  // handle state this read-only preview has none of. Curved segments are
  // flattened via manualShapes.js's own flattenShape so no curve math is
  // reimplemented here.
  let previewCanvas;
  function renderPreview(canvas, shapeList) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f4f2ec";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (const s of shapeList) {
      const pts = flattenShape(s.points, s.curves, true);
      if (pts.length < 2) continue;
      const [r, g, b] = s.colorRgb || [20, 20, 20];
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.closePath();
      ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;
      ctx.fill();
      ctx.strokeStyle = `rgb(${r},${g},${b})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }
  $: renderPreview(previewCanvas, previewShapes);

  // ---- actions --------------------------------------------------------------
  function onColorsInput(e) {
    nColors = parseInt(e.target.value, 10);
  }
  function onRemoveBgChange(e) {
    removeBg = e.target.checked;
  }

  function resetLocal() {
    workImage = null;
    fileName = "";
    error = "";
    busy = false;
    nColors = DEFAULT_N_COLORS;
    removeBg = true;
  }

  // Assigns final ids (manualShapes.js's batch-safe nextShapeIds, checked
  // against `existingShapes` so a batch of N never collides with anything
  // already in element.shapes) and dispatches the finished shape array in
  // ONE event — this component never patches element.shapes itself; that's
  // the parent's job (see file banner).
  function addShapes() {
    if (previewShapes.length === 0) return;
    const ids = nextShapeIds(existingShapes, previewShapes.length);
    const shapes = previewShapes.map((s, i) => ({ ...s, id: ids[i] }));
    d("traced", { shapes });
    resetLocal();
  }

  function cancel() {
    resetLocal();
    d("cancel");
  }
</script>

<div class="tip">
  <p class="tip-hint">
    Upload your artwork and it appears behind the drawing canvas to trace over — click your own
    points around it, the same as any hand-drawn shape. Or let it do the first pass for you:
    tune colors/background below, add the traced shapes, and hand-refine them.
    PNG with sharp, non-anti-aliased edges traces best. Art already has a transparent background?
    Uncheck "Remove background" below.
  </p>

  <div class="tip-upload">
    <input type="file" accept="image/png,image/jpeg,image/webp,image/*" on:change={onFile} />
    {#if busy}<span class="tip-filename">Loading…</span>
    {:else if fileName}<span class="tip-filename">{fileName}</span>{/if}
  </div>

  {#if error}<p class="tip-err" role="alert">{error}</p>{/if}

  {#if workImage}
    <div class="tip-controls">
      <label>
        Colors: {nColors}
        <input type="range" min="2" max="8" step="1" value={nColors} on:input={onColorsInput} />
      </label>
      <label class="tip-checkline">
        <input type="checkbox" checked={removeBg} on:change={onRemoveBgChange} />
        Remove background
      </label>
    </div>

    <canvas class="tip-preview" bind:this={previewCanvas} width={CANVAS_W} height={CANVAS_H}></canvas>

    <div class="tip-legend">
      {#if legend.length}
        {#each legend as l (l.colorRgb.join(","))}
          <span class="tip-swatch">
            <span class="tip-swatchcolor" style="background: rgb({l.colorRgb[0]},{l.colorRgb[1]},{l.colorRgb[2]})"></span>
            {l.count} shape{l.count === 1 ? "" : "s"}
          </span>
        {/each}
      {:else}
        <span class="tip-empty">No shapes traced yet — try more colors, or turn off "Remove background".</span>
      {/if}
    </div>

    {#if warnings.length}
      <ul class="tip-warnings" role="alert">
        {#each warnings as w}<li>{w}</li>{/each}
      </ul>
    {/if}
  {/if}

  <div class="tip-actions">
    <button type="button" on:click={cancel}>Cancel</button>
    <button type="button" class="primary" on:click={addShapes} disabled={previewShapes.length === 0}>
      Add {previewShapes.length} shape{previewShapes.length === 1 ? "" : "s"}
    </button>
  </div>
</div>

<style>
  .tip {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
  }
  .tip-hint { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
  .tip-upload { display: flex; align-items: center; gap: 8px; }
  .tip-filename { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); }
  .tip-err { font-size: var(--fs-xs, 12px); color: var(--danger, #c0392b); margin: 0; }
  .tip-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; font-size: var(--fs-xs, 12px); }
  .tip-checkline { display: flex; align-items: center; gap: 6px; }
  .tip-preview {
    width: 100%;
    max-width: 100%;
    height: auto;
    aspect-ratio: 600 / 400;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: #f4f2ec;
    display: block;
  }
  .tip-legend { display: flex; flex-wrap: wrap; gap: 10px; font-size: var(--fs-xs, 12px); }
  .tip-swatch { display: inline-flex; align-items: center; gap: 5px; }
  .tip-swatchcolor { width: 12px; height: 12px; border-radius: 3px; border: 1px solid var(--tint-border, #ccd6fb); display: inline-block; }
  .tip-empty { color: var(--muted, #6b7280); }
  .tip-warnings {
    margin: 0;
    padding-left: 18px;
    font-size: var(--fs-xs, 12px);
    color: var(--danger, #c0392b);
  }
  .tip-actions { display: flex; gap: 6px; justify-content: flex-end; }
  .tip-actions button {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .tip-actions button:disabled { opacity: 0.45; cursor: not-allowed; }
  .tip-actions button.primary {
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    border-color: var(--accent, #4f46e5);
  }
</style>
