<script>
  import { createEventDispatcher, onDestroy } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import {
    buildDigitizeConfig,
    digitize,
    decodedFromDesignCached,
    describeWarnings,
  } from "../lib/digitizer.js";

  // Editor panel for an auto-digitized artwork element (build step 10).
  // The element stores the source image (processing size, PNG base64), the
  // digitizing params (service field names), and the BAKED result Design —
  // see project.js's defaultDigitizedElement. This panel owns the review
  // loop: upload -> params -> Digitize -> poll -> result lands on the
  // element; a param change with a result in hand re-digitizes automatically
  // (the service's job cache makes an unchanged re-ask free).
  export let element;
  export let project; // garmentId rides into the config (fabric preset service-side)
  export let health = null; // /health payload or null; App owns the probe

  const d = createEventDispatcher();

  // Processing size (long edge). The pipeline needs nowhere near the
  // original resolution ("2000 px across is plenty" — service limits), and
  // this base64 lives in localStorage with the project, so smaller is a
  // feature: at 1200 px a flat-color logo PNG is typically well under 500 KB.
  const PROCESS_MAX_PX = 1200;
  // Storage guard on the stored base64 itself (localStorage isn't infinite —
  // same reasoning as DesignPanel's 1 MB DST cap).
  const MAX_SOURCE_B64 = 2_000_000;

  let error = "";
  let phase = "idle"; // idle | submitting | queued | running
  let fileBusy = false;
  let rerunWanted = false;
  let destroyed = false;
  onDestroy(() => {
    destroyed = true;
  });

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // ---- upload ---------------------------------------------------------------

  async function loadImage(file) {
    if (typeof createImageBitmap === "function") {
      try {
        return await createImageBitmap(file);
      } catch (e) {
        // fall through to the <img> + object URL fallback
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

  async function onFile(e) {
    const file = e.currentTarget.files && e.currentTarget.files[0];
    e.currentTarget.value = ""; // re-selecting the same file must re-fire change
    if (!file) return;
    error = "";
    fileBusy = true;
    try {
      const img = await loadImage(file);
      const iw = img.width, ih = img.height;
      const scale = Math.min(1, PROCESS_MAX_PX / (Math.max(iw, ih) || 1));
      const w = Math.max(1, Math.round(iw * scale));
      const h = Math.max(1, Math.round(ih * scale));
      const cv = document.createElement("canvas");
      cv.width = w;
      cv.height = h;
      cv.getContext("2d").drawImage(img, 0, 0, w, h);
      const dataUrl = cv.toDataURL("image/png");
      const b64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      if (b64.length > MAX_SOURCE_B64) {
        error = "That image is too heavy to save with the design — the limit is about 1.5 MB after downscaling. Simplify or shrink it and try again.";
        return;
      }
      // New artwork resets everything the old artwork produced.
      patch({ sourcePng: b64, name: file.name, result: null, warnings: [], blockColors: {}, sizeMm: null });
    } catch (err) {
      error = String((err && err.message) || err);
    } finally {
      fileBusy = false;
    }
  }

  // ---- digitize -------------------------------------------------------------

  // `el` is passed explicitly (never closed over) so a re-run always reads
  // the element as it is NOW — the blockRgb(element, i) lesson from
  // DesignPanel applies to async work too.
  async function runDigitize(el) {
    if (!el.sourcePng || !health) return;
    if (phase !== "idle") {
      rerunWanted = true; // a change landed mid-flight; run again after
      return;
    }
    error = "";
    phase = "submitting";
    try {
      const cfg = buildDigitizeConfig(el, project);
      const job = await digitize(el.sourcePng, cfg, {
        onState: (s) => {
          if (!destroyed) phase = s === "running" ? "running" : "queued";
        },
        isCancelled: () => destroyed,
      });
      if (destroyed || !job) return;
      patch({ result: job.design, warnings: job.warnings || [] });
    } catch (err) {
      if (!destroyed) error = String((err && err.message) || err);
    } finally {
      if (!destroyed) {
        phase = "idle";
        if (rerunWanted) {
          rerunWanted = false;
          runDigitize(element);
        }
      }
    }
  }

  // Param changes re-digitize automatically once a result exists (the review
  // loop); before the first result the Digitize button is the explicit start.
  // Same prev-value guard pattern as ImagePanel's re-flatten.
  let prevParamsJson = JSON.stringify(element.params);
  $: {
    const now = JSON.stringify(element.params);
    if (now !== prevParamsJson) {
      prevParamsJson = now;
      if (element.result) runDigitize(element);
    }
  }

  function setParam(key, value) {
    patch({ params: { ...element.params, [key]: value } });
  }

  // ---- derived view state ---------------------------------------------------

  $: pending = phase !== "idle";
  $: statusLine =
    phase === "running" ? "Digitizing your art…" :
    phase === "queued" ? "Waiting for the digitizer — another job is running…" :
    phase === "submitting" ? "Sending your art…" : "";

  $: decoded = element.result ? decodedFromDesignCached(element.result) : null;
  $: warningLines = describeWarnings(element.warnings);

  // Resize honesty (Kent's rule, same as DesignPanel): the field's resize
  // handles SCALE baked stitches, they don't re-digitize — density changes
  // with size. Unlike a .dst import, here the fix is one click away:
  // re-digitize at the resized width.
  $: rotation = element.rotationDeg || 0;
  $: nativeWidthNow = rotatedWidth(decoded, rotation);
  $: scaleFactor = decoded && element.sizeMm ? element.sizeMm / Math.max(0.1, nativeWidthNow) : 1;
  $: resized = Math.abs(scaleFactor - 1) > 0.02;

  function rotatedWidth(dec, deg) {
    if (!dec) return 0.1;
    const rot = ((deg % 360) + 360) % 360;
    if (rot === 0 || rot === 180) return dec.widthMM;
    if (rot === 90 || rot === 270) return dec.heightMM;
    const rad = (rot * Math.PI) / 180;
    return Math.abs(dec.widthMM * Math.cos(rad)) + Math.abs(dec.heightMM * Math.sin(rad));
  }

  // "Re-digitize at N mm": make the dragged size the new digitize target.
  // The params patch triggers the auto re-run; sizeMm clears in the same
  // patch so the fresh native-size stitches aren't immediately re-scaled.
  function redigitizeAtSize(el) {
    const target = Math.round(el.sizeMm * 10) / 10;
    patch({ params: { ...el.params, target_width_mm: target }, sizeMm: null });
  }

  // Same explicit-argument pattern as DesignPanel's blockRgb.
  function blockRgb(el, i) {
    const o = (el.blockColors || {})[i];
    if (o) return o;
    const c = ((el.result && el.result.colors) || [])[i] || { r: 0, g: 0, b: 0 };
    return [c.r || 0, c.g || 0, c.b || 0];
  }

  function blockName(el, i) {
    const c = ((el.result && el.result.colors) || [])[i];
    return (c && c.name) || "Color " + (i + 1);
  }

  function pickBlock(i, rgb) {
    patch({ blockColors: { ...(element.blockColors || {}), [i]: rgb } });
  }

  const FILL_ANGLES = [
    { value: null, label: "Auto (per shape)" },
    { value: 0, label: "0°" },
    { value: 30, label: "30°" },
    { value: 45, label: "45°" },
    { value: 60, label: "60°" },
    { value: 90, label: "90°" },
    { value: 135, label: "135°" },
  ];

  function onAngleChange(e) {
    const v = e.currentTarget.value;
    setParam("fill_angle_deg", v === "auto" ? null : parseFloat(v));
  }
</script>

<div class="digipanel">
  <label class="dgp-upload">
    <span class="dgp-upload-btn">{element.sourcePng ? "Replace artwork…" : "Choose artwork…"}</span>
    <input type="file" accept="image/png,image/jpeg,image/webp,image/*" on:change={onFile} disabled={fileBusy} />
  </label>
  {#if fileBusy}<p class="dgp-note">Reading the image…</p>{/if}

  {#if !element.sourcePng}
    <p class="dgp-note">
      Upload flat art — a logo, a mark, lettering as an image — and it comes back as stitches you
      can place like any other element. Clean, solid colors digitize best; photos and gradients
      won't sew cleanly.
    </p>
  {:else}
    <div class="dgp-src">
      <img
        class="dgp-thumb"
        src={"data:image/png;base64," + element.sourcePng}
        alt={element.name || "Artwork"}
      />
      <span class="dgp-srcname">{element.name || "Artwork"}</span>
    </div>

    {#if !health}
      <div class="dgp-offline">
        <p>
          The digitizer service isn't running, so digitizing is off.
          {#if element.result}Your stitched result is saved with the design and still sews and exports.{/if}
        </p>
        <p class="dgp-cmd">Start it: <code>python -m digitizer_service</code> in the digitizer folder.</p>
        <button type="button" class="dgp-check" on:click={() => d("checkservice")}>Check again</button>
      </div>
    {/if}

    <div class="dgp-params">
      <label class="dgp-param">
        <span>Stitch width</span>
        <input
          type="number"
          min="10"
          max="400"
          step="1"
          value={element.params.target_width_mm}
          on:change={(e) => setParam("target_width_mm", Math.max(10, parseFloat(e.currentTarget.value) || 80))}
        />
        <span class="dgp-unit">mm</span>
      </label>
      <label class="dgp-param">
        <span>Colors (max {element.params.max_colors})</span>
        <input
          type="range"
          min="2"
          max="12"
          step="1"
          value={element.params.max_colors}
          on:input={(e) => setParam("max_colors", parseInt(e.currentTarget.value, 10))}
        />
      </label>
      <label class="dgp-checkline">
        <input
          type="checkbox"
          checked={element.params.satin}
          on:change={(e) => setParam("satin", e.currentTarget.checked)}
        />
        Satin for thin shapes
      </label>
      <label class="dgp-param">
        <span>Fill angle</span>
        <select
          value={element.params.fill_angle_deg == null ? "auto" : String(element.params.fill_angle_deg)}
          on:change={onAngleChange}
        >
          {#each FILL_ANGLES as a}
            <option value={a.value == null ? "auto" : String(a.value)}>{a.label}</option>
          {/each}
        </select>
      </label>
      <label class="dgp-param">
        <span>Border</span>
        <select
          value={element.params.border}
          on:change={(e) => setParam("border", e.currentTarget.value)}
        >
          <option value="off">None</option>
          <option value="auto">Auto (satin where it fits)</option>
          <option value="bean">Bean (light outline)</option>
        </select>
      </label>
    </div>

    <button
      type="button"
      class="dgp-run"
      disabled={pending || !health}
      on:click={() => runDigitize(element)}
    >
      {pending ? "Digitizing…" : element.result ? "Digitize again" : "Digitize"}
    </button>
    {#if statusLine}<p class="dgp-status" role="status">{statusLine}</p>{/if}
    {#if error}<p class="dgp-error" role="alert">{error}</p>{/if}

    {#if element.result}
      <p class="dgp-stats">
        {element.result.stitchCount.toLocaleString()} stitches ·
        {element.result.widthMM.toFixed(0)}×{element.result.heightMM.toFixed(0)} mm ·
        {element.result.colorCount} color{element.result.colorCount === 1 ? "" : "s"}
      </p>

      {#if warningLines.length}
        <ul class="dgp-warnings">
          {#each warningLines as w (w.code + w.text)}
            <li>{w.text}</li>
          {/each}
        </ul>
      {/if}

      {#if resized}
        <p class="dgp-resize">
          Resized to {(scaleFactor * 100).toFixed(0)}% — the stitches scale, so thread density
          changes with size. Re-digitize at this size to regenerate them for it.
        </p>
        <button
          type="button"
          class="dgp-resizefix"
          disabled={pending || !health}
          on:click={() => redigitizeAtSize(element)}
        >
          Re-digitize at {element.sizeMm.toFixed(0)} mm
        </button>
      {/if}

      <div class="dgp-blocks">
        <span class="dgp-blocks-label">Thread per color</span>
        {#each Array.from({ length: (element.result.colors || []).length }) as _, i}
          <div class="dgp-block">
            <span class="dgp-block-n">{blockName(element, i)}</span>
            <ThreadPicker rgb={blockRgb(element, i)} compact on:pick={(e) => pickBlock(i, e.detail)} />
          </div>
        {/each}
      </div>

      <label class="letterspacing">
        <span>Rotation</span>
        <input
          type="range"
          min="0"
          max="360"
          step="1"
          value={rotation}
          on:input={(e) => patch({ rotationDeg: parseInt(e.currentTarget.value, 10) })}
        />
        <span class="label">{rotation}°</span>
      </label>
    {/if}
  {/if}
</div>

<style>
  .digipanel { margin-top: 4px; }
  .dgp-upload { display: inline-block; cursor: pointer; }
  .dgp-upload input[type="file"] {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    overflow: hidden;
  }
  .dgp-upload-btn {
    display: inline-block;
    padding: 6px 12px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    font-size: var(--fs-xs, 12px);
  }
  .dgp-upload:focus-within .dgp-upload-btn {
    outline: 2px solid var(--accent, #4f46e5);
    outline-offset: 1px;
  }
  .dgp-note { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 8px 0 0; }
  .dgp-src { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
  .dgp-thumb {
    width: 56px;
    height: 56px;
    object-fit: contain;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: #fff;
  }
  .dgp-srcname { font-size: var(--fs-xs, 12px); color: var(--muted, #667); word-break: break-all; }
  .dgp-offline {
    margin-top: 10px;
    padding: 8px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    font-size: var(--fs-xs, 12px);
  }
  .dgp-offline p { margin: 0 0 6px; }
  .dgp-cmd code { font-size: 11px; }
  .dgp-check,
  .dgp-resizefix {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .dgp-params { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
  .dgp-param { display: flex; align-items: center; gap: 8px; font-size: var(--fs-xs, 12px); }
  .dgp-param > span:first-child { min-width: 96px; }
  .dgp-param input[type="number"] { width: 70px; }
  .dgp-param input[type="range"] { flex: 1; }
  .dgp-unit { color: var(--muted, #667); }
  .dgp-checkline { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs, 12px); }
  .dgp-run {
    margin-top: 12px;
    padding: 7px 16px;
    border: 1px solid var(--accent, #4f46e5);
    border-radius: var(--radius-s, 6px);
    background: var(--accent, #4f46e5);
    color: #fff;
    cursor: pointer;
    font-size: var(--fs-s, 13px);
  }
  .dgp-run:disabled { opacity: 0.6; cursor: default; }
  .dgp-status { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 6px 0 0; }
  .dgp-error { font-size: var(--fs-xs, 12px); color: var(--danger, #b3261e); margin: 6px 0 0; }
  .dgp-stats { font-size: var(--fs-xs, 12px); margin: 10px 0 0; }
  .dgp-warnings {
    margin: 8px 0 0;
    padding-left: 18px;
    font-size: var(--fs-xs, 12px);
    color: var(--warn-text, #8a6d1a);
  }
  .dgp-warnings li { margin-top: 2px; }
  .dgp-resize { font-size: var(--fs-xs, 12px); color: var(--warn-text, #8a6d1a); margin: 8px 0 6px; }
  .dgp-blocks { margin-top: 10px; }
  .dgp-blocks-label { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
  .dgp-block { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
  .dgp-block-n { font-size: var(--fs-xs, 12px); min-width: 130px; }
</style>
