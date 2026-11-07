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
  /* Out of flow, always. An in-flow bar that mounts when a mode starts
     shrinks .hoop (it shares .fieldwrap's column), the ResizeObserver
     rescales the canvas mid-gesture, and every Move / hole e2e that compares
     before/after geometry fails (PR 1313, studio-e2e shard 1). So the bar
     sits off-screen like .fieldlive -- still in the accessibility tree, so a
     screen reader and Tab reach it -- and shows as a fixed overlay only while
     a keyboard user is inside it. Neither state takes layout space. */
  .modebar {
    position: fixed; width: 1px; height: 1px; margin: -1px; padding: 0;
    overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0;
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font-size: var(--fs-sm, 0.8rem);
  }
  .modebar:focus-within {
    width: auto; height: auto; margin: 0; overflow: visible; clip-path: none; white-space: normal;
    left: 50%; bottom: 16px; transform: translateX(-50%); max-width: min(40rem, calc(100vw - 32px));
    z-index: 50; padding: 6px 10px; border-radius: 6px;
    background: var(--surface, #fff); color: var(--ink, #111); border: 1px solid var(--border, #ccc);
  }
  .modebar-title { font-weight: 600; }
  .modebar-hint { opacity: 0.8; flex: 1 1 18rem; }
  .modebar-btns { display: inline-flex; gap: 6px; }
  .modebar-btn { cursor: pointer; }
  .modebar-btn:focus-visible { outline: 2px solid var(--accent, #4f46e5); outline-offset: 2px; }
</style>
