<script>
  import { createEventDispatcher } from "svelte";
  import { EMB } from "../lib/emb.js";

  export let project;
  // Dims of the last generated design ({ widthMM, heightMM }) or null when
  // nothing has stitched yet. Owned by App -- EmbroideryField dispatches a
  // "dims" event after every generate attempt (success or failure), which
  // App stores and passes down through ContentStep. That's also how this
  // panel stays live-synced while the user drags the field's resize
  // handles: a drag patches project.sizeMm, which triggers a regenerate in
  // EmbroideryField, which redispatches "dims" here.
  export let designDims = null;

  const d = createEventDispatcher();
  const MM_PER_INCH = 25.4;
  const MIN_SIZE_MM = 5;

  // Unit is local display-only state (never persisted, never sent in a
  // patch) -- everything in `project` always stays in mm. Default inches
  // since Kent (the primary user) is US-based.
  let unit = "in";

  // The width shown always reflects the *actual* generated width
  // (designDims.widthMM), not the requested sizeMm -- the engine clamps
  // sizeMm to the hoop (typed over-hoop value) or further limits it when a
  // tall-aspect design is height-bound, so the two can legitimately differ.
  // Falls back to the requested sizeMm only before anything has stitched.
  $: widthMm = designDims ? designDims.widthMM : project.sizeMm;
  // Height is never user-editable -- it's always whatever the last
  // generated design came out to, so aspect ratio follows automatically.
  $: heightMm = designDims ? designDims.heightMM : null;

  // Hoop width in mm for the current garment -- upper bound for typed W
  // input. Infinity (no clamp) when the garment can't be resolved.
  function hoopWidthMm(p) {
    const garment = p && EMB.getGarment(p.garmentId);
    return garment ? garment.widthIn * MM_PER_INCH : Infinity;
  }
  $: hoopWmm = hoopWidthMm(project);

  // `unit` is passed in (rather than closed over) so Svelte's dependency
  // tracking for the `$:` statements below -- which only sees identifiers
  // textually present in the reactive statement itself, not ones read
  // inside a called function's body -- picks up the unit toggle and
  // recomputes the display strings when it changes.
  function fromMm(mm, u) {
    if (mm == null) return "";
    return u === "in" ? (mm / MM_PER_INCH).toFixed(2) : String(Math.round(mm));
  }

  $: wDisplay = fromMm(widthMm, unit);
  $: hDisplay = fromMm(heightMm, unit);
  $: wMin = fromMm(MIN_SIZE_MM, unit);
  $: wMax = isFinite(hoopWmm) ? fromMm(hoopWmm, unit) : undefined;

  $: warn = !!designDims && (designDims.widthMM < MIN_SIZE_MM || designDims.heightMM < MIN_SIZE_MM);

  function onWidthChange(e) {
    const v = parseFloat(e.target.value);
    if (!Number.isFinite(v)) return;
    const mm = unit === "in" ? v * MM_PER_INCH : v;
    const clamped = Math.min(hoopWmm, Math.max(MIN_SIZE_MM, mm));
    d("update", { sizeMm: clamped });
  }

  function autoFit() {
    d("update", { sizeMm: null, offsetXMm: 0, offsetYMm: 0 });
  }
</script>

<div class="sizepanel">
  <h3>Size</h3>
  <div class="sizerow">
    <span class="sizelabel">W</span>
    <input
      class="sizeinput"
      type="number"
      step={unit === "in" ? "0.01" : "1"}
      min={wMin}
      max={wMax}
      value={wDisplay}
      on:change={onWidthChange}
    />
    <span class="sizex">×</span>
    <span class="sizelabel">H</span>
    <input class="sizeinput" type="text" readonly value={hDisplay} />
    <select class="unitselect" bind:value={unit}>
      <option value="in">in</option>
      <option value="mm">mm</option>
    </select>
    <button type="button" class="autofit" on:click={autoFit}>Auto-fit</button>
  </div>
  {#if warn}
    <p class="warn">Smaller than 5 mm — thread can't stitch this cleanly</p>
  {/if}
</div>
