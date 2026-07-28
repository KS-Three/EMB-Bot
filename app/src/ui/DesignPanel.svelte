<script>
  import { createEventDispatcher } from "svelte";
  import { EMB } from "../lib/emb.js";
  import ThreadPicker from "./ThreadPicker.svelte";

  // Editor panel for an imported pre-digitized design element (.dst file).
  // The file's raw bytes live on the element as base64 (see project.js's
  // defaultDesignElement) so a saved project reloads the exact stitches; this
  // panel only ever decodes for DISPLAY (block list, stats) — generation
  // decodes through generate.js's cache.
  export let element;

  const d = createEventDispatcher();
  const MAX_BYTES = 1024 * 1024; // 1MB — DSTs are KB-scale; localStorage isn't infinite

  let error = "";

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  function toBase64(bytes) {
    // btoa needs a binary string; build it in chunks so a large-ish file
    // can't blow the argument-count limit of String.fromCharCode.apply.
    let bin = "";
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return btoa(bin);
  }

  async function onFile(e) {
    error = "";
    const file = e.currentTarget.files && e.currentTarget.files[0];
    e.currentTarget.value = ""; // re-selecting the same file must re-fire change
    if (!file) return;
    if (file.size > MAX_BYTES) {
      error = "That file is over 1 MB — embroidery DSTs are normally much smaller.";
      return;
    }
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      EMB.decodeDST(bytes); // validate BEFORE storing — a bad file never lands on the element
      patch({ dstBase64: toBase64(bytes), name: file.name, blockColors: {}, sizeMm: null });
    } catch (err) {
      error = String((err && err.message) || err);
    }
  }

  // Decoded view of the CURRENT file, for the stats line and block list.
  // Cheap (KB-scale walk) and memoized per dstBase64 value by Svelte's
  // reactive statement only re-running when the dependency changes.
  $: decoded = decodeSafe(element.dstBase64);
  function decodeSafe(b64) {
    if (!b64) return null;
    try {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return EMB.decodeDST(bytes);
    } catch (e) {
      return null; // corrupt stored data -- treat as "no file yet"
    }
  }

  // Takes `el` as an explicit argument (rather than closing over the
  // `element` prop) so the template call site blockRgb(element, i) makes the
  // dependency VISIBLE to Svelte's legacy-mode invalidation — a closure read
  // wouldn't re-render the swatch after a pick patches the element.
  function blockRgb(el, i) {
    const o = (el.blockColors || {})[i];
    if (o) return o;
    const def = EMB.IMPORT_BLOCK_COLORS[i % EMB.IMPORT_BLOCK_COLORS.length];
    return [def[0], def[1], def[2]];
  }

  function pickBlock(i, rgb) {
    patch({ blockColors: { ...(element.blockColors || {}), [i]: rgb } });
  }

  // Pre-digitized stitches only scale, they don't re-digitize — density
  // changes with size. Warn once the resize leaves the "looks the same" zone.
  $: scaleFactor = decoded && element.sizeMm ? element.sizeMm / Math.max(0.1, decoded.widthMM) : 1;
  $: scaleWarn = scaleFactor < 0.75 || scaleFactor > 1.5;
</script>

<div class="designpanel">
  <label class="dp-upload">
    <span class="dp-upload-btn">{decoded ? "Replace DST file…" : "Choose a .dst file…"}</span>
    <input type="file" accept=".dst,.DST" on:change={onFile} />
  </label>

  {#if error}<p class="dp-error" role="alert">{error}</p>{/if}

  {#if decoded}
    <p class="dp-stats">
      {element.name || "Imported design"} — {decoded.stitchCount.toLocaleString()} stitches ·
      {decoded.widthMM.toFixed(0)}×{decoded.heightMM.toFixed(0)} mm ·
      {decoded.colorCount} color{decoded.colorCount === 1 ? "" : "s"} · {decoded.trimCount} trims
    </p>

    <div class="dp-blocks">
      <span class="dp-blocks-label">Thread per color block</span>
      {#each Array.from({ length: decoded.colorCount }) as _, i}
        <div class="dp-block">
          <span class="dp-block-n">Block {i + 1}</span>
          <ThreadPicker rgb={blockRgb(element, i)} compact on:pick={(e) => pickBlock(i, e.detail)} />
        </div>
      {/each}
    </div>

    <p class="dp-note" class:warn={scaleWarn}>
      {#if scaleWarn}
        Resized to {(scaleFactor * 100).toFixed(0)}% — pre-digitized stitches scale with the design,
        so density and detail change too. Best kept near the original size.
      {:else}
        Pre-digitized file: it sews exactly as digitized. Resizing scales the stitches themselves.
      {/if}
    </p>
  {:else}
    <p class="dp-note">
      Drop in any Tajima .dst design — from a design site, a digitizer, or another machine —
      and place it like any other element. Colors aren't stored in DST files, so pick a thread
      per block below once it's loaded.
    </p>
  {/if}
</div>
