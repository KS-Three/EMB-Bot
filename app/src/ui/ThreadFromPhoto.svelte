<script>
  import { rankThreads, samplePatch, matchWord } from "../lib/colorMatch.js";

  // Match a thread from a photo: choose a picture of a garment, a logo or a
  // colour chip, click the colour, and get the chart's nearest threads with
  // the colour difference (CIEDE2000 — lib/colorMatch.js) beside each.
  //
  // Rendered IN FLOW inside ThreadPicker's panel (the B6 rule there: nothing
  // floats, the scrollable panel body clips overlays). The photo never leaves
  // the browser — it is decoded onto a canvas and read back, nothing uploads.
  //
  // What this is NOT: a colour measurement. A phone photo carries its
  // lighting and white balance, and the chart's own RGB values are screen
  // approximations of real thread. The note below says so in the UI, on
  // purpose, before any number appears.
  export let threads = []; // the chosen chart's thread list
  export let chartLabel = ""; // its display name, for the results heading
  export let onpick = () => {}; // called with the thread a row's button chooses
  // Injected in tests (jsdom has no canvas). Resolves to
  // { image: ImageData-shaped, source: something drawImage accepts | null }.
  export let decode = decodeFile;

  // Long side of the working copy. A phone photo is 12 MP; nothing here
  // needs more than this to average a patch, and it bounds the pixel buffer.
  const MAX_SIDE = 1200;
  const SHOWN = 5;

  let canvas;
  let image = null; // { data, width, height } the samples are read from
  let mark = null; // { x, y } in image pixels — where the last click landed
  let sample = null; // { rgb, count }
  let error = "";
  let busy = false;

  async function decodeFile(file) {
    const bmp = await createImageBitmap(file);
    const k = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    const w = Math.max(1, Math.round(bmp.width * k));
    const h = Math.max(1, Math.round(bmp.height * k));
    const off = document.createElement("canvas");
    off.width = w;
    off.height = h;
    const ctx = off.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(bmp, 0, 0, w, h);
    if (bmp.close) bmp.close();
    return { image: ctx.getImageData(0, 0, w, h), source: off };
  }

  async function onFile(e) {
    const file = e.currentTarget.files && e.currentTarget.files[0];
    if (!file) return;
    error = "";
    busy = true;
    try {
      const got = await decode(file);
      image = got.image;
      mark = null;
      sample = null;
      pendingSource = got.source;
    } catch (err) {
      image = null;
      error = "Could not read that file as a picture. Try a JPEG or PNG.";
    } finally {
      busy = false;
    }
  }

  // The canvas only exists once `image` is set, so the decoded picture is
  // drawn on the tick after it mounts.
  let pendingSource = null;
  $: if (canvas && image && pendingSource) {
    canvas.width = image.width;
    canvas.height = image.height;
    const ctx = canvas.getContext("2d");
    if (ctx) ctx.drawImage(pendingSource, 0, 0);
    pendingSource = null;
  }

  // Patch half-width in image pixels: ~1.7% of the long side across, so the
  // click reads an area a finger-width wide on the preview, not one pixel.
  $: radius = image ? Math.max(2, Math.round(Math.max(image.width, image.height) / 120)) : 0;

  function sampleAt(x, y) {
    const got = samplePatch(image, x, y, radius);
    if (!got) return; // a see-through patch: keep the last answer
    mark = { x, y };
    sample = got;
  }

  function onClick(e) {
    if (!image) return;
    const r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const x = Math.min(image.width - 1, Math.max(0, ((e.clientX - r.left) / r.width) * image.width));
    const y = Math.min(image.height - 1, Math.max(0, ((e.clientY - r.top) / r.height) * image.height));
    sampleAt(Math.floor(x), Math.floor(y));
  }

  // Keyboard: Enter/Space samples (the centre first), arrows walk the mark.
  function onKey(e) {
    if (!image) return;
    const at = mark || { x: Math.floor(image.width / 2), y: Math.floor(image.height / 2) };
    const step = Math.max(1, radius);
    const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    const m = moves[e.key];
    if (!m && e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
    const [dx, dy] = m || [0, 0];
    sampleAt(
      Math.min(image.width - 1, Math.max(0, at.x + dx)),
      Math.min(image.height - 1, Math.max(0, at.y + dy))
    );
  }

  // Reactive on `threads` as well as the sample, so switching brand in the
  // picker re-ranks the colour already clicked.
  $: matches = sample ? rankThreads(threads, sample.rgb, SHOWN) : [];

  const css = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
  const label = (t) => (t.code ? `${t.code} ${t.name}` : t.name);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="tfp" on:click|stopPropagation>
  <p class="tfp-note">
    An approximate starting point, not a colour measurement: lighting and the
    camera's white balance shift what a photo records, and chart colours are
    screen values. Check the pick against real thread.
  </p>

  <label class="tfp-file">
    <span>Choose a photo</span>
    <input type="file" accept="image/*" on:change={onFile} />
  </label>
  {#if busy}<p class="tfp-hint" role="status">Reading photo…</p>{/if}
  {#if error}<p class="tfp-error" role="alert">{error}</p>{/if}

  {#if image}
    <div class="tfp-stage">
      <!-- svelte-ignore a11y_no_noninteractive_tabindex a11y_no_noninteractive_element_interactions a11y_no_interactive_element_to_noninteractive_role -->
      <canvas
        bind:this={canvas}
        class="tfp-canvas"
        role="img"
        aria-label="Your photo — click a colour to match it"
        tabindex="0"
        on:click={onClick}
        on:keydown={onKey}
      ></canvas>
      {#if mark}
        <span
          class="tfp-mark"
          aria-hidden="true"
          style="left: {((mark.x + 0.5) / image.width) * 100}%; top: {((mark.y + 0.5) / image.height) * 100}%; width: {((2 * radius + 1) / image.width) * 100}%; aspect-ratio: 1;"
        ></span>
      {/if}
    </div>

    {#if !sample}
      <p class="tfp-hint">Click the colour you want to match.</p>
    {:else}
      <div class="tfp-sampled">
        <span class="tfp-chip" aria-hidden="true" style="background: {css(sample.rgb)}"></span>
        <span>Sampled colour · average of {sample.count} pixels</span>
      </div>
      {#if !matches.length}
        <p class="tfp-hint" role="status">Loading chart…</p>
      {:else}
        <ol class="tfp-list" aria-label={"Nearest threads in " + chartLabel}>
          {#each matches as t (t.index)}
            <li>
              <button type="button" class="tfp-row" aria-label={"Use " + label(t)} on:click={() => onpick(t)}>
                <span class="tfp-pair" aria-hidden="true">
                  <span style="background: {css(sample.rgb)}"></span>
                  <span style="background: {css(t.rgb)}"></span>
                </span>
                <span class="tfp-name">{label(t)}</span>
                <span class="tfp-de" title="CIEDE2000 colour difference — lower is closer; under about 2 is hard to tell apart">
                  ΔE {t.deltaE.toFixed(1)}<small>{matchWord(t.deltaE)}</small>
                </span>
              </button>
            </li>
          {/each}
        </ol>
      {/if}
    {/if}
  {/if}
</div>

<style>
  .tfp {
    width: 100%;
    margin-top: var(--space-3);
    padding-top: var(--space-3);
    border-top: 1px solid var(--border);
    font-size: var(--fs-sm);
  }
  .tfp-note,
  .tfp-hint {
    margin: 0 0 var(--space-2);
    color: var(--muted);
    line-height: 1.35;
  }
  .tfp-error {
    margin: 0 0 var(--space-2);
    color: var(--danger, #b3261e);
  }
  .tfp-file {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
    margin-bottom: var(--space-2);
    font-size: inherit;
    text-align: left;
  }
  .tfp-file input {
    max-width: 100%;
    font-size: var(--fs-sm);
  }
  .tfp-stage {
    position: relative;
    margin-bottom: var(--space-2);
    line-height: 0;
  }
  .tfp-canvas {
    display: block;
    width: 100%;
    height: auto;
    border: 1px solid var(--border);
    border-radius: var(--radius-s);
    cursor: crosshair;
  }
  .tfp-canvas:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  /* The patch that was averaged, drawn to scale over the photo. Two rings so
     it reads on a light garment and a dark one alike. */
  .tfp-mark {
    position: absolute;
    min-width: 10px;
    transform: translate(-50%, -50%);
    border: 2px solid #fff;
    box-shadow: 0 0 0 1px #000, inset 0 0 0 1px #000;
    pointer-events: none;
  }
  .tfp-sampled {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
    color: var(--muted);
  }
  .tfp-chip {
    flex: 0 0 auto;
    width: 22px;
    height: 22px;
    border: 1px solid var(--border);
    border-radius: var(--radius-s);
  }
  .tfp-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .tfp-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-1) var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-s);
    background: var(--surface);
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .tfp-row:hover {
    border-color: var(--accent);
  }
  /* Sampled colour and thread colour edge to edge: the eye judges a match
     far better across a shared border than across a gap. */
  .tfp-pair {
    display: flex;
    flex: 0 0 auto;
    width: 36px;
    height: 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius-s);
    overflow: hidden;
  }
  .tfp-pair span {
    flex: 1 1 50%;
  }
  .tfp-name {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tfp-de {
    flex: 0 0 auto;
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .tfp-de small {
    display: block;
    color: var(--muted);
    font-size: var(--fs-xs);
  }
</style>
