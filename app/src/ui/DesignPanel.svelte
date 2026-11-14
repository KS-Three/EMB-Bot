<script>
  import { createEventDispatcher, onDestroy } from "svelte";
  import { buildBlockThumbs, blockStitchCounts } from "../lib/blockThumbs.js";
  import { EMB } from "../lib/emb.js";
  import { designFilePatch } from "../lib/designImport.js";
  import ThreadPicker from "./ThreadPicker.svelte";
  import Icon from "./Icon.svelte";
  import Advanced from "./Advanced.svelte";
  import { rotationPatch } from "../lib/hoop.js";
  import { rotatedWidth } from "../lib/staleness.js";

  // Editor panel for an imported pre-digitized design element (.dst file).
  // The file's raw bytes live on the element as base64 (see project.js's
  // defaultDesignElement) so a saved project reloads the exact stitches; this
  // panel only ever decodes for DISPLAY (block list, stats) — generation
  // decodes through generate.js's cache.
  export let element;

  const d = createEventDispatcher();
  const MAX_BYTES = 1024 * 1024; // 1MB — DSTs are KB-scale; localStorage isn't infinite

  let error = "";
  // ContentStep remounts this panel when the open design changes, but that
  // does not stop a file still being read: its patch, addressed by element
  // id, would land on design B's element with the same id (2026-11-13
  // review). A torn-down panel's read is dropped.
  let destroyed = false;
  onDestroy(() => (destroyed = true));

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }
  // Rotation keeps the design's size (hoop.js rotationPatch, 2026-11-13).
  const turnTo = (deg) => patch(rotationPatch(element, deg));

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
      if (destroyed) return;
      // Validates BEFORE storing — a bad file never lands on the element.
      patch(designFilePatch(bytes, file.name));
    } catch (err) {
      error = String((err && err.message) || err);
    }
  }

  // Decoded view of the CURRENT file, for the stats line and block list.
  // Memoized per dstBase64 string HERE, not by the reactive statement: that
  // re-runs on every patch to the element (App replaces it with
  // `{ ...el, ...patch }`, so a rotation tick invalidates `element`), and an
  // un-memoized decode hands back a new object each time -- which made every
  // rotation tick rebuild every block thumbnail (#1349 review).
  $: decoded = decodeSafe(element.dstBase64);
  let lastB64 = null;
  let lastDecoded = null;
  function decodeSafe(b64) {
    if (b64 === lastB64) return lastDecoded;
    lastB64 = b64;
    lastDecoded = decodeUncached(b64);
    return lastDecoded;
  }
  function decodeUncached(b64) {
    if (!b64) return null;
    try {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      // Same reader the generation path uses (generate.js's decodeCached), so
      // the stats line below and the stitches on the canvas can never disagree
      // about which way round the file is.
      return EMB.decodeDSTStandard(bytes);
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

  // ---- Block thumbnails -------------------------------------------------
  // Per-block stitch counts are cheap and shown at once. The pictures are not
  // free (a 22k-stitch file is ~100 ms of canvas work), so they are built only
  // once the block list is actually on screen (IntersectionObserver; a browser
  // without one counts as visible) and one task after the row text paints.
  $: counts = decoded ? blockStitchCounts(decoded) : [];
  let visible = false;
  let thumbs = [];
  let buildTimer = null;

  function watchVisible(node) {
    if (typeof IntersectionObserver !== "function") { visible = true; return {}; }
    const io = new IntersectionObserver((es) => {
      for (const e of es) if (e.isIntersecting) { visible = true; io.disconnect(); }
    });
    io.observe(node);
    return { destroy: () => io.disconnect() };
  }

  // The canvas is built outside Svelte's tree; this puts it in its row.
  function place(node, canvas) {
    const set = (c) => { node.textContent = ""; if (c) node.appendChild(c); };
    set(canvas);
    return { update: set };
  }

  function colorsKey(el, n) {
    const out = [];
    for (let i = 0; i < n; i++) out.push(blockRgb(el, i).join(","));
    return out.join("|");
  }

  $: key = decoded ? colorsKey(element, decoded.colorCount) : "";
  $: if (visible && decoded) schedule(decoded, key);
  // Svelte 5's legacy mode treats a reassigned object as changed even when it
  // is the same object, so this statement still re-runs on every element
  // patch. The pictures depend only on the file and its colours: skip unless
  // one of those moved since the last scheduled build.
  let schedDec = null;
  let schedKey = null;
  function schedule(dec, k) {
    if (dec === schedDec && k === schedKey) return;
    schedDec = dec;
    schedKey = k;
    if (buildTimer != null) clearTimeout(buildTimer);
    if (!dec.stitches || !dec.stitches.length) return;
    buildTimer = setTimeout(() => {
      buildTimer = null;
      try {
        const colors = [];
        for (let i = 0; i < dec.colorCount; i++) colors.push(blockRgb(element, i));
        thumbs = buildBlockThumbs(dec, { colors, width: 56, height: 28 });
      } catch (e) {
        thumbs = []; // a thumbnail is decoration; never take the picker down with it
      }
    }, 0);
  }
  onDestroy(() => { if (buildTimer != null) clearTimeout(buildTimer); });

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
  // `rotatedWidth` is staleness.js's, the engine's own measure of the turned
  // stitches (review follow-up, 2026-11-13). This panel kept a turned-
  // RECTANGLE copy, which read a round design turned 45 degrees as 41% wider
  // than it sews: "Resized to 71%" on a design at 100%. With the true width
  // the factor is the scale the engine applies, so the 2% note and the
  // 75-150% band still mean what they say: how far the stitches were scaled.
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

    <div class="dp-blocks" use:watchVisible>
      <span class="dp-blocks-label">Thread per color block</span>
      {#each Array.from({ length: decoded.colorCount }) as _, i}
        <div class="dp-block">
          <span class="dp-thumb" aria-hidden="true" use:place={thumbs[i] && thumbs[i].canvas}></span>
          <span class="dp-block-n">Block {i + 1}</span>
          <span class="dp-block-st">{(counts[i] || 0).toLocaleString()} st</span>
          <ThreadPicker rgb={blockRgb(element, i)} compact on:pick={(e) => pickBlock(i, e.detail)} />
        </div>
      {/each}
    </div>

    <!-- Default slot: the size row (ContentStep). Advanced (spec 2026-09-30
         §5) holds the file's details: the old-DST note, rotation and the
         resize note, plus whatever ContentStep puts in the "advanced" slot. -->
    <slot />
    <Advanced>
    <!-- This note used to say the opposite, and was wrong in a way that
         mattered. A third-party file DID arrive turned round — but measured on
         the canvas on 2026-09-07, it arrived MIRRORED as well, and the note
         told customers to "use Rotate to stand it up", which no rotation can
         do. The import now reads DST in the Tajima convention
         (EMB.decodeDSTStandard), so a file from anywhere else lands correct and
         there is nothing left to warn about on that side.

         The writer was put right on 2026-09-08 (both record weight tables
         swapped, byte-identical to pystitch), so a .dst this app writes NOW
         re-imports correctly. What survives is narrower and does not shrink
         on its own: a file written BEFORE that fix is in the old dialect and
         still comes back mirrored, and nothing in the file says which it is.
         So the note stays, scoped to old files, and keeps the advice that was
         always the better one anyway — My designs preserves more than any
         .dst can. -->
    <p class="dp-note warn" data-testid="dst-own-file-note">
      <span class="dp-warn-icon"><Icon name="warning" size={14} /></span> Reopening
      something you made here? Use <strong>My designs</strong>. A .dst this app
      wrote <strong>before September 2026</strong> comes back mirrored — EMB-Bot
      used to write DST on the opposite axis convention from every other program.
      Files written since, and files from anywhere else, import correctly.
    </p>

    <label class="letterspacing">
      <span>Rotation</span>
      <!-- max 359: a turn is stored in [0, 360), see TextStep's slider. -->
      <input
        type="range"
        min="0"
        max="359"
        step="1"
        value={rotation}
        on:input={(e) => turnTo(parseInt(e.target.value, 10))}
      />
      <span class="label">{rotation}°</span>
    </label>
    <button
      type="button"
      class="upsidedown"
      on:click={() => turnTo(rotation === 180 ? 0 : 180)}
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
    <slot name="advanced" />
    </Advanced>
  {:else}
    <p class="dp-note">
      Drop in any Tajima .dst design — from a design site, a digitizer, or another machine —
      and place it like any other element. Colors aren't stored in DST files, so pick a thread
      per block below once it's loaded. To reopen something you made in EMB-Bot, use
      My designs rather than its .dst — it keeps more than a DST can, and a file this
      app wrote before September 2026 comes back mirrored.
    </p>
    <slot />
    <Advanced><slot name="advanced" /></Advanced>
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
