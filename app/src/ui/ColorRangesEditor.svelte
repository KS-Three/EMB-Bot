<script>
  import { createEventDispatcher } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";

  // Per-letter color ranges editor (Font editing abilities Round 1).
  // Owns none of the actual <textarea> -- TextStep.svelte owns that DOM node
  // and tracks its own selectionStart/selectionEnd, passing the live
  // selection down here as `selection` ({start,end}|null). Range indices
  // match text.slice(startIdx,endIdx) exactly (see layoutText's charIdx
  // tagging in src/satinfont.js), so no custom index math is needed anywhere
  // in this component -- selection.start/end ARE startIdx/endIdx.
  export let text = "";
  export let colorRanges = [];
  export let selection = null; // {start, end} | null

  const d = createEventDispatcher();

  function addRange(rgb) {
    if (!selection) return;
    const next = [...colorRanges, { startIdx: selection.start, endIdx: selection.end, colorRgb: rgb }];
    d("change", next);
  }
  function removeRange(i) {
    const next = colorRanges.filter((_, idx) => idx !== i);
    d("change", next);
  }
</script>

<div class="colorranges">
  {#if selection}
    <div class="cr-pending">
      <span class="cr-label">Color "{text.slice(selection.start, selection.end)}":</span>
      <ThreadPicker rgb={[20, 20, 20]} compact on:pick={(e) => addRange(e.detail)} />
    </div>
  {/if}
  {#if colorRanges.length}
    <ul class="cr-list">
      {#each colorRanges as r, i (i)}
        <li>
          <span class="cr-swatch" style="background: rgb({r.colorRgb[0]},{r.colorRgb[1]},{r.colorRgb[2]})"></span>
          <span class="cr-text">"{text.slice(r.startIdx, r.endIdx)}"</span>
          <button type="button" class="cr-remove" aria-label="Remove color range" on:click={() => removeRange(i)}>×</button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .colorranges { margin-top: 8px; }
  .cr-pending { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .cr-label { font-size: var(--fs-xs, 12px); }
  .cr-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .cr-list li { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs, 12px); }
  .cr-swatch { width: 14px; height: 14px; border-radius: 3px; border: 1px solid var(--tint-border, #ccd6fb); display: inline-block; }
  .cr-remove { border: none; background: none; cursor: pointer; font-size: 14px; line-height: 1; color: var(--danger, #c0392b); }
</style>
