<script>
  import { createEventDispatcher } from "svelte";

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

  // The width shown always reflects the *real* current width: an explicit
  // sizeMm if one is set (by the user or by a handle drag), otherwise the
  // auto-fit width from the last generated design.
  $: widthMm = project.sizeMm != null ? project.sizeMm : (designDims ? designDims.widthMM : null);
  // Height is never user-editable -- it's always whatever the last
  // generated design came out to, so aspect ratio follows automatically.
  $: heightMm = designDims ? designDims.heightMM : null;

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

  $: warn = !!designDims && (designDims.widthMM < MIN_SIZE_MM || designDims.heightMM < MIN_SIZE_MM);

  function onWidthChange(e) {
    const v = parseFloat(e.target.value);
    if (!Number.isFinite(v)) return;
    const mm = unit === "in" ? v * MM_PER_INCH : v;
    d("update", { sizeMm: Math.max(MIN_SIZE_MM, mm) });
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
      min="0"
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
