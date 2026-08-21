<script>
  import { createEventDispatcher } from "svelte";
  import { EMB } from "../lib/emb.js";
  import ThreadPicker from "./ThreadPicker.svelte";
  import Icon from "./Icon.svelte";

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
  // changes with size. sizeMm means POST-rotATION width (the engine rotates
  // before its scale/clamp math), so the scale factor compares it against
  // the decoded design's extents in the CURRENT orientation.
  $: rotation = element.rotationDeg || 0;
  $: nativeWidthNow = rotatedWidth(decoded, rotation);
  $: scaleFactor = decoded && element.sizeMm ? element.sizeMm / Math.max(0.1, nativeWidthNow) : 1;
  // Kent's rule (2026-07-29): ANY resize of an uploaded stitch file gets a
  // warning — density silently changes from the first percent, not just
  // past the old 75–150% band. The band still marks the "expect visible
  // problems" escalation.
  $: resized = Math.abs(scaleFactor - 1) > 0.02;
  $: scaleWarnHard = scaleFactor < 0.75 || scaleFactor > 1.5;

  function rotatedWidth(dec, deg) {
    if (!dec) return 0.1;
    const rot = ((deg % 360) + 360) % 360;
    if (rot === 0 || rot === 180) return dec.widthMM;
    if (rot === 90 || rot === 270) return dec.heightMM;
    const rad = (rot * Math.PI) / 180;
    // Bbox width of a rotated axis-aligned box — close enough for a warning
    // threshold (the engine computes the true rotated stitch bbox itself).
    return Math.abs(dec.widthMM * Math.cos(rad)) + Math.abs(dec.heightMM * Math.sin(rad));
  }
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

    <!-- The import side of the axis bug DownloadStep already warns about on
         the export side. EMB-Bot's DST codec is transposed vs. the Tajima
         standard, so a file digitized anywhere else arrives on its side and
         the stats line above prints those swapped numbers as fact. Fixing the
         codec is gated (it would re-orient every DST EMB-Bot has written), so
         say so and point at Rotate. Measured on all five committed pro
         references: 5/5 exact transposition. -->
    <p class="dp-note warn" data-testid="dst-import-orientation-note">
      <span class="dp-warn-icon"><Icon name="warning" size={14} /></span> If this
      came from other software and looks turned on its side, it is: EMB-Bot reads
      DST on the opposite axis convention, so the {decoded.widthMM.toFixed(0)}×{decoded.heightMM.toFixed(0)} mm
      above is swapped too. Use Rotate to stand it up, then check the size — on a
      hat or beanie a sideways design gets shrunk to fit the short side. Designs
      made in EMB-Bot are unaffected.
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

    <label class="letterspacing">
      <span>Rotation</span>
      <input
        type="range"
        min="0"
        max="360"
        step="1"
        value={rotation}
        on:input={(e) => patch({ rotationDeg: parseInt(e.target.value, 10) })}
      />
      <span class="label">{rotation}°</span>
    </label>
    <button
      type="button"
      class="upsidedown"
      on:click={() => patch({ rotationDeg: rotation === 180 ? 0 : 180 })}
    >
      {rotation === 180 ? "Right-side up" : "Flip upside-down"}
    </button>

    <p class="dp-note" class:warn={resized}>
      {#if resized}
        <span class="dp-warn-icon"><Icon name="warning" size={14} /></span> Resized to {(scaleFactor * 100).toFixed(0)}% — a stitch file is NOT re-digitized when
        you resize it: the existing stitches just scale, so thread density and detail change
        with the size.{#if scaleWarnHard}&nbsp;This is well outside the safe 75–150% range —
        expect gaps or bunching when it sews.{:else}&nbsp;Small changes are usually fine; stay
        inside 75–150% of the original.{/if}
      {:else}
        Pre-digitized file: it sews exactly as digitized. Resizing scales the stitches
        themselves (no re-digitizing), so density changes with size.
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

<style>
  /* The warning icon sits inline in running text (.dp-note), not its own
     flex row, so it needs its own baseline nudge -- text-bottom instead of
     the default alphabetic baseline keeps it centered against the line
     instead of hanging low. */
  .dp-warn-icon {
    display: inline-flex;
    vertical-align: text-bottom;
    color: var(--warn);
  }

  /* Same look as TextStep's flip button (that one is component-scoped, so
     the rule can't be shared). */
  .upsidedown {
    margin-top: 8px;
    padding: 6px 12px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
</style>
