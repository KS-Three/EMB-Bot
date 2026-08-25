<script>
  import FontSelect from "./FontSelect.svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import ColorRangesEditor from "./ColorRangesEditor.svelte";
  import { createEventDispatcher } from "svelte";

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
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
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
  on:input={(e) => patch({ text: e.target.value, textSource: null })}
  on:select={updateSelection}
  on:mouseup={updateSelection}
  on:keyup={updateSelection}
  placeholder="Type a name or word"
></textarea>
<ColorRangesEditor
  text={element.text}
  colorRanges={element.colorRanges || []}
  {selection}
  on:change={(e) => patch({ colorRanges: e.detail })}
/>
<ThreadPicker label="Color" rgb={element.colorRgb} on:pick={(e) => patch({ colorRgb: e.detail })} />
<h3>Font</h3>
<FontSelect
  selected={element.fontKey}
  currentText={element.text}
  on:pick={(e) => patch({ fontKey: e.detail })}
/>
<label class="letterspacing">
  <span>Letter spacing</span>
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
<label class="letterspacing">
  <span>Curve</span>
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
<label class="letterspacing">
  <span>Rotation</span>
  <input
    type="range"
    min="0"
    max="360"
    step="1"
    value={element.rotationDeg || 0}
    on:input={(e) => patch({ rotationDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.rotationDeg || 0}°</span>
</label>
<button
  type="button"
  class="upsidedown"
  on:click={() => patch({ rotationDeg: (element.rotationDeg || 0) === 180 ? 0 : 180 })}
>
  {(element.rotationDeg || 0) === 180 ? "Right-side up" : "Flip upside-down"}
</button>

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

<!-- Justification only means something across multiple lines (single-line
     text auto-centers as a whole, and arc'd lines center on their own
     circle). This used to be HIDDEN until the text had a line break, which
     read as "the feature doesn't exist" -- it now always renders, disabled
     with an explanatory tooltip, so it's discoverable. Named "Justify lines"
     (not "Align") to distinguish it from SizePanel's "Align in hoop", which
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
    color: #fff;
    border-color: var(--accent, #4f46e5);
  }
  .weightbtn:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
