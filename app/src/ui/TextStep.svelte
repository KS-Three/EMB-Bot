<script>
  import FontSelect from "./FontSelect.svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import ColorRangesEditor from "./ColorRangesEditor.svelte";
  import Advanced from "./Advanced.svelte";
  import { createEventDispatcher, onDestroy } from "svelte";
  import { tip } from "../lib/tip.js";
  import { remapColorRanges } from "../lib/colorRanges.js";
  import { isOutlineKey, outlineRequest, outlineRequestKey, digitizeLettering } from "../lib/outlineFonts.js";
  import { markDigitizeBusy, rememberRun, forgetRun, wasRunning } from "../lib/digitizeBusy.js";
  import { LONG_RUN_MS, reviewFromJob } from "../lib/digitizer.js";
  import { friendlyError } from "../lib/friendlyError.js";
  import { rotationPatch } from "../lib/hoop.js";
  import { generateElement } from "../lib/generate.js";
  import { garmentOf } from "../lib/placement.js";
  import { ensureFont } from "../lib/fontLoader.js";
  import { EMB } from "../lib/emb.js";

  // Element-scoped text editor (Task 5, Slice 5): bound to whichever text
  // element is currently selected in ContentStep's element list, not a
  // single project-wide text field like the old v1 shape.
  //
  // Patch convention (documented here, ImagePanel.svelte follows the same
  // one): every edit dispatches an "elupdate" event shaped
  // { id: element.id, patch } directly -- this component already knows its
  // own element's id, so it wraps the patch itself instead of dispatching a
  // bare patch and making the parent guess whose id to attach. ContentStep
  // just bubbles these straight through to App unchanged.
  export let element;
  // The project (garment, fabric, chart) and the service's /health payload —
  // both only read for an OUTLINE font (lib/outlineFonts.js), whose text the
  // service lays out and sews on the button below. Null for the .embf fonts
  // the browser engine sews itself.
  export let project = null;
  export let health = null;
  // App's `currentId` (via ContentStep): element ids repeat across designs,
  // so the run below is fixed to the design it started in, and its resume
  // mark is keyed by design too -- DigitizePanel's 2026-11-13 fix, same
  // shape. null in tests that mount this alone.
  export let projectId = null;
  const d = createEventDispatcher();

  function patch(p, id = element.id, proj = projectId) {
    d("elupdate", proj == null ? { id, patch: p } : { id, patch: p, projectId: proj });
  }
  const runMark = (id) => (projectId == null ? id : projectId + "/" + id);

  // Rotation keeps the lettering's size (hoop.js rotationPatch, 2026-11-13):
  // it needs the lettering's fit aspect, which only a generated design
  // reports. Without a project (tests that mount this alone) the patch turns
  // it only; outline fonts are not turned in size at all (rotationPatch).
  function turnPatchNow(el, deg) {
    let design = null;
    try {
      if (project && el.sizeMm > 0 && !outline) design = generateElement(el, garmentOf(project), {});
    } catch (e) { design = null; }
    return rotationPatch(el, deg, design);
  }
  // A font not loaded yet (review follow-up, 2026-11-13): turning without the
  // aspect refit the lettering to the old sizeMm at the new angle, the
  // original bug, and nothing put it right once the font arrived. So the
  // turn WAITS for fontLoader's own ensureFont (the promise and cache the
  // field loads through) and is patched once, from the element as it then
  // stands; a failed load turns it only, as before. Usually milliseconds: the
  // field cannot draw the lettering without that font either.
  function turnTo(deg) {
    const key = element.fontKey;
    if (project && element.sizeMm > 0 && !outline && key && !(EMB.SATIN_FONTS || {})[key]) {
      const id = element.id, proj = projectId;
      ensureFont(key).catch(() => null).then(() => {
        if (destroyed || element.id !== id || element.fontKey !== key) return;
        patch(turnPatchNow(element, deg), id, proj);
      });
      return;
    }
    patch(turnPatchNow(element, deg));
  }

  // ---- Outline font: digitize on the service ------------------------------
  // Mirrors DigitizePanel.runDigitize: one patch = one undo step, the key of
  // the SUBMITTED request stamped as `appliedConfig` so an edit made
  // mid-flight still reads as behind afterwards (lib/staleness.js), the
  // pinwheel over the field via digitizeBusy, and a remembered run so a
  // reload or an element switch joins the service's job instead of
  // orphaning it. Nothing runs on its own (Kent, 2026-10-05): the click is
  // the run.
  $: outline = isOutlineKey(element.fontKey);
  $: outlineReq = outline && project ? outlineRequest(element, project) : null;
  $: outlineStale = !!(outline && element.result && outlineReq
    && outlineRequestKey(outlineReq) !== element.appliedConfig);
  $: outlineText = (element.text || "").trim().length > 0;
  $: outlineLit = outline && !!health && outlineText && (outlineStale || !element.result);
  let phase = "idle";
  let error = "";
  let runningLong = false;
  let destroyed = false;
  $: markDigitizeBusy(element.id, outline && phase !== "idle");
  onDestroy(() => { destroyed = true; markDigitizeBusy(element.id, false); });
  $: statusLine =
    phase === "running" && runningLong
      ? "Still digitizing — lettering can take a minute or two…" :
    phase === "running" ? "Digitizing your lettering…" :
    phase === "queued" ? "Waiting for the digitizer — another job is running…" :
    phase === "submitting" ? "Sending your text…" : "";

  async function runLettering() {
    if (!outline || !health || phase !== "idle" || !outlineReq || !outlineText) return;
    const el = element;
    const req = outlineReq;
    error = "";
    phase = "submitting";
    runningLong = false;
    const runProject = projectId;
    const mark = runMark(el.id);
    rememberRun(mark);
    try {
      const job = await digitizeLettering(req, {
        onState: (s, info) => {
          if (destroyed) return;
          phase = s === "running" ? "running" : "queued";
          runningLong = s === "running" && !!info && info.runningMs > LONG_RUN_MS;
        },
        isCancelled: () => destroyed,
      });
      if (destroyed || !job) return;
      // Behind ContentStep's per-design `{#key}`: only the design and
      // element the run was started for.
      if (projectId !== runProject || element.id !== el.id) return;
      patch({
        result: job.design,
        warnings: job.warnings || [],
        review: reviewFromJob(job.review, job.stats && job.stats.blocks),
        preflight: job.preflight || null,
        stats: job.stats || null,
        lettering: job.lettering || null,
        appliedConfig: outlineRequestKey(req),
        // The service laid the text out AT this width (outlineRequest), so
        // the design's own width is the element's: a later drag scales it
        // and reads as behind until the next run, like a digitized image.
        sizeMm: req.width_mm,
      }, el.id, runProject);
    } catch (err) {
      if (!destroyed) error = friendlyError(err, "digitize");
    } finally {
      if (!destroyed) {
        phase = "idle";
        runningLong = false;
        forgetRun(mark);
      }
    }
  }

  // A reload or an element switch tore the last run down mid-flight: join
  // the service's job (an identical request is a cache hit there).
  let resumeChecked = false;
  $: if (!resumeChecked && outline && health && outlineReq) {
    resumeChecked = true;
    if (wasRunning(runMark(element.id))) runLettering();
  }

  // Line justification is meaningless on a single line (nothing to justify
  // against), so the control renders disabled rather than hidden -- see the
  // "Justify lines" block below.
  $: multiline = (element.text || "").includes("\n");

  // OCR-suggested-text provenance (digitizer.js's textClusterSeed, gated by
  // OCR_SUGGESTION_MIN_CONFIDENCE): "ocr-suggested" means the textarea below
  // is currently showing a machine guess the user has not yet looked at or
  // touched, not text they typed. See the advisory badge below the
  // textarea — reuses DigitizePanel.svelte's "looks like text" badge visual
  // convention (`.dgp-lbadge`'s pill/border shape) plus its `--warn-text`
  // color already used elsewhere for "needs a look" states, rather than
  // inventing new styling.
  $: unconfirmedOcr = element.textSource === "ocr-suggested";

  // Per-letter color (Font editing abilities Round 1): tracks the textarea's
  // OWN native selection (selectionStart/selectionEnd) so ColorRangesEditor
  // can offer "color the highlighted text" without any custom range-picker
  // widget. null (no/collapsed selection) hides that offer.
  let textareaEl;
  let selection = null;
  function updateSelection() {
    if (!textareaEl) return;
    const s = textareaEl.selectionStart, e = textareaEl.selectionEnd;
    selection = e > s ? { start: s, end: e } : null;
  }

  // Colour ranges are character indices, so every edit has to carry them
  // along (lib/colorRanges.js) or a typo fixed before a coloured word slides
  // the colour onto the wrong letters. The selection is re-read too: paste,
  // autocorrect and dictation change the text without a key-up, which left
  // the "Color …" offer pointing at text that no longer existed.
  function onTextInput(e) {
    const text = e.target.value;
    const p = { text, textSource: null };
    if (element.colorRanges && element.colorRanges.length) {
      p.colorRanges = remapColorRanges(element.text || "", text, element.colorRanges, e.target.selectionEnd);
    }
    patch(p);
    updateSelection();
  }
</script>

{#if unconfirmedOcr}
  <span
    class="ocrbadge"
    title="A classical-CV + OCR pass on the source image guessed this text from the artwork — it can be wrong. Read it and edit as needed before saving."
  >Suggested from image — verify before saving</span>
{/if}
<textarea
  bind:this={textareaEl}
  class="textin"
  rows="2"
  value={element.text}
  on:input={onTextInput}
  on:select={updateSelection}
  on:mouseup={updateSelection}
  on:keyup={updateSelection}
  placeholder="Type a name or word"
></textarea>
{#if !outline}
  <!-- Per-letter colour, curve, weight and slant are the browser engine's
       lettering rules (satinfont.js); an outline font is laid out and sewn
       by the service, which reads text, size, spacing, justification and
       ONE thread colour (lib/outlineFonts.js outlineRequest). Controls the
       run would ignore are not shown for it. -->
  <ColorRangesEditor
    text={element.text}
    colorRanges={element.colorRanges || []}
    {selection}
    on:change={(e) => patch({ colorRanges: e.detail })}
  />
{/if}
<ThreadPicker label="Color" rgb={element.colorRgb} on:pick={(e) => patch({ colorRgb: e.detail })} />
<h3>Font</h3>
<FontSelect
  selected={element.fontKey}
  currentText={element.text}
  on:pick={(e) => patch({ fontKey: e.detail })}
/>
{#if outline}
  <div class="olrun" data-testid="outline-run">
    <button
      type="button"
      class="dgp-run"
      class:dgp-run-stale={outlineStale}
      class:dgp-run-lit={outlineLit}
      disabled={!health || phase !== "idle" || !outlineText}
      title={!health
        ? "The stitch service is offline — an outline font is digitized by the service, so this font needs it running."
        : "Lay this text out in the font and digitize it into satin lettering on the stitch service (slower than the built-in fonts)."}
      on:click={runLettering}
    >{element.result ? "Re-digitize lettering" : "Digitize lettering"}</button>
    {#if statusLine}
      <p class="dgp-status" role="status">{statusLine}</p>
    {:else if !health}
      <p class="dgp-status">The stitch service is offline. This font is digitized by the service, so it sews once the service is back.</p>
    {:else if !element.result}
      <p class="dgp-status">This font is digitized on demand: press the button to stitch your text.</p>
    {/if}
    {#if error}
      <p class="dgp-error" role="alert">{error}</p>
    {/if}
  </div>
{/if}
<!-- Default slot: the size row (ContentStep). Advanced (spec 2026-09-30 §5)
     holds everything below it, plus whatever ContentStep puts in the
     "advanced" slot (the align row, the add-element row). -->
<slot />
<Advanced>
<label class="letterspacing" use:tip={"letterSpacing"}>
  <span>Letter spacing<i class="tipmark" aria-hidden="true"></i></span>
  <input
    type="range"
    min="-1"
    max="6"
    step="0.5"
    value={element.letterSpacingMm || 0}
    on:input={(e) => patch({ letterSpacingMm: parseFloat(e.target.value) })}
  />
  <span class="label">{(element.letterSpacingMm || 0).toFixed(1)} mm</span>
</label>
{#if !outline}
<label class="letterspacing" use:tip={"curve"}>
  <span>Curve<i class="tipmark" aria-hidden="true"></i></span>
  <input
    type="range"
    min="-180"
    max="180"
    step="10"
    value={element.arcDeg || 0}
    on:input={(e) => patch({ arcDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.arcDeg || 0}°</span>
</label>
{/if}
<label class="letterspacing" use:tip={"rotation"}>
  <span>Rotation<i class="tipmark" aria-hidden="true"></i></span>
  <!-- max 359, not 360: a turn is stored in [0, 360) (hoop.js rotationPatch),
       so 360 was saved as 0 and the thumb jumped back to the left end
       (review follow-up, 2026-11-13). -->
  <input
    type="range"
    min="0"
    max="359"
    step="1"
    value={element.rotationDeg || 0}
    on:input={(e) => turnTo(parseInt(e.target.value, 10))}
  />
  <span class="label">{element.rotationDeg || 0}°</span>
</label>
<button
  type="button"
  class="upsidedown"
  on:click={() => turnTo((element.rotationDeg || 0) === 180 ? 0 : 180)}
>
  {(element.rotationDeg || 0) === 180 ? "Right-side up" : "Flip upside-down"}
</button>

{#if !outline}
<div class="weightpresets">
  <span class="weightlabel">Weight</span>
  <div class="weightbtns">
    {#each ["thin", "normal", "bold"] as w}
      <button
        type="button"
        class="weightbtn"
        class:active={(element.weightPreset || "normal") === w}
        on:click={() => patch({ weightPreset: w })}
      >{w[0].toUpperCase() + w.slice(1)}</button>
    {/each}
  </div>
</div>

{/if}
<!-- Justification only means something across multiple lines (single-line
     text auto-centers as a whole, and arc'd lines center on their own
     circle). This used to be HIDDEN until the text had a line break, which
     read as "the feature doesn't exist" -- it now always renders, disabled
     with an explanatory tooltip, so it's discoverable. Named "Justify lines"
     (not "Align") to distinguish it from SizePanel's align row, which
     moves the whole ELEMENT rather than lines within it. -->
<div class="weightpresets">
  <span class="weightlabel">Justify lines</span>
  <div class="weightbtns">
    {#each [["left", "Left"], ["center", "Center"], ["right", "Right"]] as [val, label]}
      <button
        type="button"
        class="weightbtn"
        class:active={multiline && (element.align || "center") === val}
        disabled={!multiline}
        title={multiline
          ? `Justify shorter lines ${val === "center" ? "centered on" : "flush " + val + " against"} the widest line`
          : "Press Enter in the text box to add a second line — justification positions lines against each other"}
        on:click={() => patch({ align: val })}
      >{label}</button>
    {/each}
  </div>
</div>

{#if !outline}
<label class="letterspacing">
  <span>Slant</span>
  <input
    type="range"
    min="-20"
    max="20"
    step="2"
    value={element.slantDeg || 0}
    on:input={(e) => patch({ slantDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.slantDeg || 0}°</span>
</label>
{/if}
<slot name="advanced" />
</Advanced>

<style>
  /* Reuses DigitizePanel.svelte's ".dgp-lbadge" pill shape (font-size,
     border-radius, padding) plus the "--warn-text" color this codebase
     already uses for other "needs a look before you trust it" states
     (DigitizePanel's unstitched-tier label, its resize warning) — a
     visually-distinct, non-blocking advisory, not new styling invented for
     this one badge. Block-level (not inline like dgp-lbadge, which sits
     next to other row badges) since this is the only badge here and reads
     better as its own line directly above the field it's warning about. */
  .ocrbadge {
    display: block;
    width: fit-content;
    margin-bottom: 6px;
    font-size: var(--fs-2xs, 0.6875rem);
    color: var(--warn-text, #8a6d1a);
    border: 1px solid var(--warn-text, #8a6d1a);
    border-radius: 8px;
    padding: 1px 6px;
  }
  /* The outline font's run control: DigitizePanel's .dgp-run look (the same
     button a digitized image has), the same transparent "out of date" state
     and the same halo while Download waits on it. */
  .olrun { margin-top: 8px; }
  .dgp-run {
    padding: 10px 20px;
    min-height: 40px;
    border: 2px solid var(--accent, #4f46e5);
    border-radius: var(--radius-s, 8px);
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    cursor: pointer;
    font-weight: var(--fw-medium, 500);
    font-size: var(--fs-sm, 14px);
  }
  .dgp-run:hover:not(:disabled) {
    background: var(--accent-dark, #4338ca);
    border-color: var(--accent-dark, #4338ca);
  }
  .dgp-run:disabled { opacity: 0.6; cursor: default; }
  .dgp-run.dgp-run-stale { background: transparent; color: var(--accent, #4f46e5); }
  .dgp-run.dgp-run-stale:hover:not(:disabled) {
    background: var(--tint, rgba(79, 70, 229, 0.08));
    border-color: var(--accent, #4f46e5);
  }
  .dgp-run.dgp-run-lit { box-shadow: 0 0 0 4px var(--tint-border, #ccd6fb); }
  .dgp-status { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 6px 0 0; }
  .dgp-error { font-size: var(--fs-xs, 12px); color: var(--danger, #b3261e); margin: 6px 0 0; }
  .upsidedown {
    margin-top: 8px;
    padding: 6px 12px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .weightpresets { margin-top: 10px; }
  .weightlabel { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
  .weightbtns { display: flex; gap: 6px; }
  .weightbtn {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .weightbtn.active {
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    border-color: var(--accent, #4f46e5);
  }
  .weightbtn:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
