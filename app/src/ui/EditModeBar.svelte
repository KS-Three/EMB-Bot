<script>
  // The keyboard / screen-reader twin of the canvas-drawn strip that Move
  // shape, Reshape mode and Add hole paint: the same Done / Discard / cross
  // actions as real buttons, in tab order, with names. Rendered by
  // EmbroideryField as a SIBLING of .hoop (never inside it: the field holds
  // the canvas and nothing else, pinned by e2e/field-chrome.spec.js).
  import { createEventDispatcher } from "svelte";
  export let bar = null;   // editModeBar() result
  const dispatch = createEventDispatcher();
</script>

{#if bar}
  <div class="modebar" role="group" aria-label={bar.label} aria-describedby="modebar-hint" data-testid="modebar" data-mode={bar.mode}>
    <span class="modebar-title">{bar.label}</span>
    <span class="modebar-hint" id="modebar-hint">{bar.hint}</span>
    <span class="modebar-btns">
      {#each bar.buttons as b (b.id)}
        <button type="button" class="modebar-btn" data-testid={`modebar-${b.id}`} disabled={b.disabled} on:click={() => dispatch("action", { id: b.id })}>{b.label}</button>
      {/each}
    </span>
  </div>
{/if}

<style>
  .modebar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; padding: 4px 8px; font-size: var(--fs-sm, 0.8rem); }
  .modebar-title { font-weight: 600; }
  .modebar-hint { opacity: 0.8; flex: 1 1 18rem; }
  .modebar-btns { display: inline-flex; gap: 6px; }
  .modebar-btn { cursor: pointer; }
  .modebar-btn:focus-visible { outline: 2px solid var(--accent, #4f46e5); outline-offset: 2px; }
</style>
