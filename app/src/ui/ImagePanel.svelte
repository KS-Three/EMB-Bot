<script>
  import { createEventDispatcher } from "svelte";
  import { flattenRGBA, flatToRGBA, flatShares, mergeFlat, WORK_MAX_PX, ALPHA_CUTOFF } from "../lib/flatten.js";

  export let project;
  const d = createEventDispatcher();

  let previewCanvas;
  let fileName = "";
  let error = "";
  let busy = false;

  // Working RGBA at WORK_MAX_PX resolution, alpha-cut, kept around so "Reset
  // colors" can re-flatten without re-reading the file.
  let workingRGBA = null;
  let workW = 0;
  let workH = 0;

  let flat = null; // current flattened palette state (component-local mirror; App holds the copy it needs)
  let selected = {}; // palette index -> true, toggled for "Merge selected"

  // Draw an image (ImageBitmap or HTMLImageElement) to an offscreen canvas at
  // WORK_MAX_PX long side, read pixels, and force low-alpha pixels fully
  // transparent so downstream flattening treats them as background.
  // Ported from src/app.js prepRGBA (lines 95-108).
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

  function emitFlat(f) {
    flat = f;
    d("flat", f);
    renderPreview();
  }

  // Re-run the flatten pipeline from the kept working RGBA at the current
  // project settings (colors / remove-bg).
  function recompute() {
    if (!workingRGBA) {
      selected = {};
      emitFlat(null);
      return;
    }
    const f = flattenRGBA(workingRGBA, workW, workH, { nColors: project.nColors, removeBg: project.removeBg });
    selected = {};
    emitFlat(f);
  }

  async function onFileChange(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    error = "";
    busy = true;
    try {
      const img = await loadImage(file);
      const prep = prepRGBA(img);
      workingRGBA = prep.rgba;
      workW = prep.w;
      workH = prep.h;
      fileName = file.name;
      // keep the reactive re-flatten guard in sync so it doesn't immediately
      // re-fire with stale "previous" values
      prevNColors = project.nColors;
      prevRemoveBg = project.removeBg;
      recompute();
    } catch (err) {
      error = (err && err.message) || "Could not read this image file.";
      workingRGBA = null;
      fileName = "";
      emitFlat(null);
    } finally {
      busy = false;
      e.target.value = ""; // allow re-selecting the same file later
    }
  }

  function onColorsInput(e) {
    d("update", { nColors: parseInt(e.target.value, 10) });
  }

  function onRemoveBgChange(e) {
    d("update", { removeBg: e.target.checked });
  }

  // Re-flatten whenever the colors slider / remove-bg checkbox change the
  // project settings (they round-trip through App before landing back here).
  let prevNColors = project.nColors;
  let prevRemoveBg = project.removeBg;
  $: if (workingRGBA && (project.nColors !== prevNColors || project.removeBg !== prevRemoveBg)) {
    prevNColors = project.nColors;
    prevRemoveBg = project.removeBg;
    recompute();
  }

  function toggleSwatch(i) {
    const next = { ...selected };
    if (next[i]) delete next[i];
    else next[i] = true;
    selected = next;
  }

  function mergeSelected() {
    const idxList = Object.keys(selected).map(Number);
    if (!flat || idxList.length < 2) return;
    const merged = mergeFlat(flat, idxList);
    selected = {};
    emitFlat(merged);
  }

  function resetColors() {
    recompute();
  }

  // Paint the flattened palette to the small preview canvas, nearest-neighbor
  // upscaled so flat art reads crisply. Ported from src/app.js renderFlatPreview
  // (lines 140-164). The canvas element itself always exists (see markup) so
  // this ref is stable across flat null <-> non-null transitions.
  function renderPreview() {
    if (!previewCanvas) return;
    const ctx = previewCanvas.getContext("2d");
    if (!flat) {
      previewCanvas.width = 1;
      previewCanvas.height = 1;
      ctx.clearRect(0, 0, 1, 1);
      return;
    }
    const w = flat.w, h = flat.h;
    const off = document.createElement("canvas");
    off.width = w;
    off.height = h;
    const rgba = flatToRGBA(flat);
    off.getContext("2d").putImageData(new ImageData(rgba, w, h), 0, 0);

    const scale = Math.max(1, Math.round(360 / Math.max(w, h)));
    previewCanvas.width = w * scale;
    previewCanvas.height = h * scale;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    ctx.drawImage(off, 0, 0, previewCanvas.width, previewCanvas.height);
  }

  $: shares = flat ? flatShares(flat) : [];
  $: selectedCount = Object.keys(selected).length;
</script>

<div class="uploadbox">
  <input type="file" accept="image/*" on:change={onFileChange} />
  {#if busy}<span class="filename">Loading…</span>
  {:else if fileName}<span class="filename">{fileName}</span>{/if}
</div>
<p class="hint">Best results: logos and flat-color art. Photos with gradients won't stitch cleanly.</p>

{#if error}<p class="err">{error}</p>{/if}

<canvas class="flatprev" class:hidden={!flat} bind:this={previewCanvas}></canvas>

<label>
  Colors: {project.nColors}
  <input type="range" min="2" max="8" step="1" value={project.nColors} on:input={onColorsInput} />
</label>
<label>
  <input type="checkbox" checked={project.removeBg} on:change={onRemoveBgChange} />
  Remove background
</label>

<div class="swatches">
  {#if flat}
    <!-- Hide empty palette slots (median-cut can return more entries than the
         art uses — a 0.0% chip is just noise to a beginner). -->
    {#each flat.palette as c, i}
      {#if shares[i] > 0.0005}
        <button
          type="button"
          class="swatch"
          class:sel={!!selected[i]}
          style="background: rgb({c[0]},{c[1]},{c[2]})"
          on:click={() => toggleSwatch(i)}
          title={(shares[i] * 100).toFixed(1) + "%"}
        >
          <span class="pct">{(shares[i] * 100).toFixed(1)}%</span>
        </button>
      {/if}
    {/each}
  {:else}
    <span class="swatch-hint">Upload an image to see its flattened colors here.</span>
  {/if}
</div>

<div class="swatch-actions">
  <button on:click={mergeSelected} disabled={!flat || selectedCount < 2}>Merge selected</button>
  <button on:click={resetColors} disabled={!flat}>Reset colors</button>
</div>
