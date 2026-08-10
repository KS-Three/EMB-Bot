<script>
  import { createEventDispatcher } from "svelte";
  import { flattenRGBA, flatToRGBA, flatShares, mergeFlat, WORK_MAX_PX, ALPHA_CUTOFF } from "../lib/flatten.js";
  import ThreadPicker from "./ThreadPicker.svelte";
  import Icon from "./Icon.svelte";

  // Element-scoped image editor (Task 5, Slice 5). Pattern (see
  // TextStep.svelte for the same convention): settings patches dispatch an
  // "elupdate" event shaped { id: element.id, patch } directly. The
  // "image"/"flat" events stay id-less on purpose -- App always applies them
  // to whichever element is CURRENTLY SELECTED (project.selectedId), which
  // is safe because this panel only ever edits the selected element (it's
  // remounted via ContentStep's `{#key el.id}` whenever selection changes,
  // so there's never a stale in-flight upload for a different element).
  export let element;
  // Working image state is owned by App (not this component) and passed
  // down as props, so it survives ImagePanel being destroyed and recreated
  // whenever the user navigates steps or switches which element is
  // selected. See .superpowers/sdd/final-review-s2.md Important #1.
  // workImage: prepped working source ({ rgba, w, h }, alpha-cut, at
  // WORK_MAX_PX) -- "Reset colors" and the colors/remove-bg controls
  // re-flatten from this prop, never from local state.
  export let workImage = null;
  // flat: current flattened palette state, derived from workImage.
  export let flat = null;
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  let previewCanvas;
  let fileName = "";
  let error = "";
  let busy = false;

  // Merge-selection is ephemeral UI state (not part of the working image), so
  // it's fine for it to reset when the panel remounts.
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

  // Flatten `img` ({ rgba, w, h }) at the given settings and dispatch the
  // result up to App (which owns `flat`); `img` may be null to clear.
  //
  // element.threadRgb is keyed by PALETTE INDEX, and every call here derives
  // a brand-new palette from scratch (median-cut over the source pixels) --
  // the old indices don't correspond to anything in the new palette (a
  // stale key could silently color the wrong swatch, or vanish entirely).
  // Rather than try to remap indices through a re-flatten with no old->new
  // mapping to remap through, clear overrides here: a predictable reset the
  // user can react to (re-pick colors) beats silent corruption they can't
  // see. mergeSelected below does the same for the merge case, which DOES
  // have an old->new map but keeps the same clear-on-change policy for
  // consistency (see final-review-s5.md Important #1).
  function flattenFrom(img, nColors, removeBg) {
    selected = {};
    patch({ threadRgb: {} });
    if (!img) {
      d("flat", null);
      return;
    }
    const f = flattenRGBA(img.rgba, img.w, img.h, { nColors, removeBg });
    d("flat", f);
  }

  // Re-run the flatten pipeline from the workImage PROP (never local state)
  // at the current element settings (colors / remove-bg).
  function recompute() {
    flattenFrom(workImage, element.nColors, element.removeBg);
  }

  async function onFileChange(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    error = "";
    busy = true;
    try {
      const img = await loadImage(file);
      const prep = prepRGBA(img);
      fileName = file.name;
      // keep the reactive re-flatten guard in sync so it doesn't immediately
      // re-fire with stale "previous" values
      prevNColors = element.nColors;
      prevRemoveBg = element.removeBg;
      // Dispatch the new working image up to App first, then flatten from
      // the freshly-read `prep` directly (not the workImage prop -- the
      // round trip through App hasn't happened yet at this point).
      d("image", prep);
      flattenFrom(prep, element.nColors, element.removeBg);
    } catch (err) {
      error = (err && err.message) || "Could not read this image file.";
      fileName = "";
      d("image", null);
      flattenFrom(null, element.nColors, element.removeBg);
    } finally {
      busy = false;
      e.target.value = ""; // allow re-selecting the same file later
    }
  }

  function onColorsInput(e) {
    patch({ nColors: parseInt(e.target.value, 10) });
  }

  function onRemoveBgChange(e) {
    patch({ removeBg: e.target.checked });
  }

  // Re-flatten whenever the colors slider / remove-bg checkbox change the
  // element settings (they round-trip through App before landing back here).
  let prevNColors = element.nColors;
  let prevRemoveBg = element.removeBg;
  $: if (workImage && (element.nColors !== prevNColors || element.removeBg !== prevRemoveBg)) {
    prevNColors = element.nColors;
    prevRemoveBg = element.removeBg;
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
    // Merging compacts and remaps every palette index (src/flatten.js
    // mergeColors), so any existing threadRgb override keys point at the
    // wrong (or a now-nonexistent) swatch -- clear them (see flattenFrom's
    // comment above for why "clear" over "remap").
    patch({ threadRgb: {} });
    d("flat", merged);
  }

  function resetColors() {
    recompute();
  }

  // Paint the flattened palette to the small preview canvas, nearest-neighbor
  // upscaled so flat art reads crisply. Ported from src/app.js renderFlatPreview
  // (lines 140-164). The canvas element itself always exists (see markup) so
  // this ref is stable across flat null <-> non-null transitions.
  function renderPreview(f, canvasEl) {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext("2d");
    if (!f) {
      canvasEl.width = 1;
      canvasEl.height = 1;
      ctx.clearRect(0, 0, 1, 1);
      return;
    }
    const w = f.w, h = f.h;
    const off = document.createElement("canvas");
    off.width = w;
    off.height = h;
    const rgba = flatToRGBA(f);
    off.getContext("2d").putImageData(new ImageData(rgba, w, h), 0, 0);

    const scale = Math.max(1, Math.round(360 / Math.max(w, h)));
    canvasEl.width = w * scale;
    canvasEl.height = h * scale;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    ctx.drawImage(off, 0, 0, canvasEl.width, canvasEl.height);
  }
  // Reactive on both `flat` (prop, updates after any re-flatten) and
  // `previewCanvas` (bound after mount) so a remount with an existing `flat`
  // prop re-hydrates the preview immediately -- not just fresh flattens.
  $: renderPreview(flat, previewCanvas);

  $: shares = flat ? flatShares(flat) : [];
  $: selectedCount = Object.keys(selected).length;

  // ---- per-swatch thread color overrides (Task 5, Slice 5) ----------------
  // element.threadRgb is a { [paletteIndex]: [r,g,b] } map (see
  // lib/project.js's defaultImageElement and lib/imageRegions.js's
  // flatToRegions, which already reads it at generation time -- this panel
  // is just the UI for setting it).
  // Reactive (not a plain function called from the template) on purpose:
  // Svelte's dependency tracking for a template expression only sees
  // identifiers referenced TEXTUALLY in that expression, not ones read
  // inside a called function's body (the same caveat SizePanel.svelte
  // documents for its `$:` statements) -- a template call like
  // `hasOverride(i)` that internally reads `element` would never be
  // re-evaluated when `element.threadRgb` changes, since `element` never
  // appears in the mustache expression itself. Exposing the map as a plain
  // reactive value the template reads directly (`threadOverrides[i]`,
  // `i in threadOverrides`) sidesteps that entirely.
  $: threadOverrides = element.threadRgb || {};

  function onThreadPick(i, rgb) {
    patch({ threadRgb: { ...(element.threadRgb || {}), [i]: rgb } });
  }
  function clearThread(i) {
    const next = { ...(element.threadRgb || {}) };
    delete next[i];
    patch({ threadRgb: next });
  }
</script>

<div class="uploadbox">
  <input type="file" accept="image/*" on:change={onFileChange} />
  {#if busy}<span class="filename">Loading…</span>
  {:else if fileName}<span class="filename">{fileName}</span>{/if}
</div>
<p class="hint">Best results: logos and flat-color art. Photos with gradients won't stitch cleanly.</p>
<p class="hint">
  PNG with sharp, non-anti-aliased edges and a bigger image hold detail best. Art already has a
  transparent background? Leave "Remove background" unchecked below.
</p>

{#if error}<p class="err">{error}</p>{/if}

<canvas class="flatprev" class:hidden={!flat} bind:this={previewCanvas}></canvas>

<label>
  Colors: {element.nColors}
  <input type="range" min="2" max="8" step="1" value={element.nColors} on:input={onColorsInput} />
</label>
<label>
  <input type="checkbox" checked={element.removeBg} on:change={onRemoveBgChange} />
  Remove background
</label>

<div class="swatches">
  {#if flat}
    <!-- Hide empty palette slots (median-cut can return more entries than the
         art uses — a 0.0% chip is just noise to a beginner). -->
    {#each flat.palette as c, i}
      {#if shares[i] > 0.0005}
        <div class="swatchwrap">
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
          <!-- Thread color override for this swatch -- a distinct control
               from the swatch button above (merge-select stays a plain
               click; ThreadPicker's own trigger stopPropagates internally,
               and the reset button does the same, so neither is ever
               mistaken for a swatch click). -->
          <div class="swatchthread">
            <ThreadPicker
              compact
              rgb={threadOverrides[i] || c}
              on:pick={(e) => onThreadPick(i, e.detail)}
            />
            {#if i in threadOverrides}
              <button
                type="button"
                class="threadreset"
                on:click|stopPropagation={() => clearThread(i)}
                title="Reset to the original color"
                aria-label="Reset thread color to original"
              >
                <Icon name="reset" size={12} />
              </button>
            {/if}
          </div>
        </div>
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
