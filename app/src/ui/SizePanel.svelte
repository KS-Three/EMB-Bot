<script>
  import { createEventDispatcher } from "svelte";
  import { EMB } from "../lib/emb.js";
  import { alignOffset } from "../lib/interact.js";

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
  // sizeMm to the placement box (typed over-box value) or further limits it
  // when a tall-aspect design is height-bound, and since 2026-09-07
  // designDims is the stitch bbox, which pull compensation puts slightly
  // OUTSIDE the box the design was fit to. All three make the requested and
  // the sewn width legitimately differ.
  // Falls back to the requested sizeMm only before anything has stitched.
  $: widthMm = designDims ? designDims.widthMM : project.sizeMm;
  // Height is never user-editable -- it's always whatever the last
  // generated design came out to, so aspect ratio follows automatically.
  $: heightMm = designDims ? designDims.heightMM : null;

  // The garment's PLACEMENT BOX width in mm -- the upper bound for a typed W.
  // Named "hoop" for historical reasons and kept that way because every call
  // site below reads it; it is not the physical hoop, which is a separate
  // ceiling check (lib/hoop.js: "the hoop is a CEILING check, never a clamp").
  // Infinity (no clamp) when the garment can't be resolved.
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
    if (u === "in") return (mm / MM_PER_INCH).toFixed(2);
    if (u === "cm") return (mm / 10).toFixed(1);
    return String(Math.round(mm));
  }

  function toMm(v, u) {
    if (u === "in") return v * MM_PER_INCH;
    if (u === "cm") return v * 10;
    return v;
  }

  function stepFor(u) {
    return u === "in" ? "0.01" : u === "cm" ? "0.1" : "1";
  }

  $: wDisplay = fromMm(widthMm, unit);
  $: hDisplay = fromMm(heightMm, unit);
  $: wMax = isFinite(hoopWmm) ? fromMm(hoopWmm, unit) : undefined;

  // The bound is enforced in onWidthChange, NOT as a min/max on the input.
  //
  // These two numbers measure different things and it is a category error to
  // let one police the other: what the field DISPLAYS is the width the design
  // actually sews (designDims, the stitch bbox), while `hoopWmm` bounds what
  // the user may REQUEST. A design auto-fit to the garment's placement box
  // sews slightly wider than that box — pull compensation pushes the satin
  // rails outward, by 0.2 mm on plain lettering and up to 9.6 mm on the widest
  // of the 7,470 designs measured 2026-09-07 — so the honest display is
  // legitimately, permanently over the request bound.
  //
  // With max="5.00" on the input that made the FIRST screen of the most common
  // quick start ("Name on a hat") render an input the browser reports as
  // `rangeOverflow: true, valid: false` — value 5.05, max 5.00 — on a design
  // with nothing wrong with it. Any `:invalid` styling, and any future form
  // validation, would fire on a correct design; the spinner arrows also
  // refused to move.
  //
  // Removing the attributes changes no behaviour a user can reach: every typed
  // value has always gone through onWidthChange's
  // Math.min(hoopWmm, Math.max(MIN_SIZE_MM, mm)) clamp, which is untouched.
  // `wMax` is kept because the title below tells the user the bound in words —
  // which the bare attribute never did.
  $: wTitle = isFinite(hoopWmm)
    ? `Width of the stitched design. Up to ${wMax} ${unit} fits this garment — larger values are scaled down to fit.`
    : "Width of the stitched design.";

  $: warn = !!designDims && (designDims.widthMM < MIN_SIZE_MM || designDims.heightMM < MIN_SIZE_MM);

  function onWidthChange(e) {
    const v = parseFloat(e.target.value);
    if (!Number.isFinite(v)) return;
    const mm = toMm(v, unit);
    const clamped = Math.min(hoopWmm, Math.max(MIN_SIZE_MM, mm));
    d("update", { sizeMm: clamped });
  }

  // Height input (Ember-audit follow-up): the engine's only size knob is
  // targetWidthMm (aspect is always locked), so a typed height converts to
  // the width that produces it via the CURRENT design's aspect ratio.
  // Editable only once something has generated (no designDims = no ratio to
  // solve with; the input stays disabled).
  function onHeightChange(e) {
    const v = parseFloat(e.target.value);
    if (!Number.isFinite(v) || !designDims || !designDims.heightMM) return;
    const hMm = toMm(v, unit);
    const aspect = designDims.widthMM / designDims.heightMM;
    const wMm = hMm * aspect;
    const clamped = Math.min(hoopWmm, Math.max(MIN_SIZE_MM, wMm));
    d("update", { sizeMm: clamped });
  }

  function autoFit() {
    d("update", { sizeMm: null, offsetXMm: 0, offsetYMm: 0 });
  }

  // ---- Align in hoop --------------------------------------------------------
  // Element-level placement, distinct from TextStep's "Justify lines" (which
  // positions LINES against each other inside one text block). This moves the
  // whole selected element -- any type -- flush against a hoop edge, i.e. the
  // one-click version of dragging until the field's snap catches.
  //
  // Needs the element's GENERATED width (designDims), so it stays disabled
  // until something has stitched -- same rule the height input follows -- and
  // when the garment can't be resolved (hoopWmm Infinity).
  $: canAlign = !!designDims && isFinite(hoopWmm);

  function alignTo(mode) {
    if (!canAlign) return;
    d("update", { offsetXMm: alignOffset(mode, designDims.widthMM, hoopWmm) });
  }

  // Which of the three positions the element is currently sitting at (null =
  // somewhere in between, e.g. hand-dragged). "center" is tested FIRST so a
  // design too wide to have any slack -- where all three modes collapse to
  // offset 0 -- reads as centered rather than arbitrarily matching "left".
  $: alignActive = (() => {
    if (!canAlign) return null;
    const cur = project.offsetXMm || 0;
    for (const mode of ["center", "left", "right"]) {
      if (Math.abs(alignOffset(mode, designDims.widthMM, hoopWmm) - cur) < 0.05) return mode;
    }
    return null;
  })();
</script>

<div class="sizepanel">
  <h3>Size</h3>
  <div class="sizerow">
    <span class="sizelabel">W</span>
    <input
      class="sizeinput"
      type="number"
      step={stepFor(unit)}
      value={wDisplay}
      on:change={onWidthChange}
      aria-label="Width"
      title={wTitle}
    />
    <span class="sizex">×</span>
    <span class="sizelabel">H</span>
    <input
      class="sizeinput"
      type="number"
      step={stepFor(unit)}
      value={hDisplay}
      disabled={!designDims}
      on:change={onHeightChange}
      aria-label="Height"
    />
    <select class="unitselect" bind:value={unit}>
      <option value="in">in</option>
      <option value="cm">cm</option>
      <option value="mm">mm</option>
    </select>
    <button type="button" class="autofit" on:click={autoFit}>Auto-fit</button>
  </div>
  <div class="alignrow">
    <span class="alignlabel">Align in hoop</span>
    <div class="alignbtns">
      {#each [["left", "Left"], ["center", "Center"], ["right", "Right"]] as [mode, label]}
        <button
          type="button"
          class="alignbtn"
          class:active={alignActive === mode}
          disabled={!canAlign}
          title={canAlign
            ? `Move this element flush ${mode === "center" ? "to the hoop's center" : "against the hoop's " + mode + " edge"}`
            : "Available once the design has stitched"}
          on:click={() => alignTo(mode)}
        >{label}</button>
      {/each}
    </div>
  </div>
  {#if warn}
    <p class="warn">Smaller than 5 mm — thread can't stitch this cleanly</p>
  {/if}
</div>

<style>
  .alignrow { margin-top: 10px; }
  /* Type comes from theme.css's shared section-label rule. */
  .alignlabel { display: block; margin-bottom: 4px; }
  .alignbtns { display: flex; gap: 6px; }
  .alignbtn {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .alignbtn.active {
    background: var(--accent, #4f46e5);
    color: #fff;
    border-color: var(--accent, #4f46e5);
  }
  .alignbtn:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
