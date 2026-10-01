<script>
  // The garment row (spec §3): three pills for the commonest placements,
  // a fourth for anything else in force, and More › for the full list.
  // A menu, not a dialog — the Studio's e2e suite addresses its dialogs by
  // bare role, and this is a pick-one list, which is what a menu is.
  import { createEventDispatcher, tick } from "svelte";
  import { EMB } from "../lib/emb.js";
  import { garmentArt } from "./garmentArt.js";
  import { pillsFor } from "../lib/garmentPills.js";
  export let garmentId;
  const d = createEventDispatcher();

  const garments = (EMB.GARMENTS || []).map((g) => ({ id: g.id, label: g.label || g.id }));
  $: pills = pillsFor(garmentId, garments);

  let open = false;
  let moreBtn = null;
  let menuEl = null;

  function pick(id) {
    open = false;
    d("update", { garmentId: id });
  }
  async function toggle() {
    open = !open;
    if (open) {
      await tick();
      const cur = menuEl && menuEl.querySelector('[aria-checked="true"]');
      (cur || (menuEl && menuEl.querySelector("button")))?.focus();
    }
  }
  function onMenuKey(e) {
    if (e.key === "Escape") {
      e.stopPropagation();
      open = false;
      moreBtn && moreBtn.focus();
    }
  }
  // A press anywhere outside the picker closes the menu.
  function onWindowDown(e) {
    if (open && menuEl && !menuEl.contains(e.target) && e.target !== moreBtn) open = false;
  }
  // Focus leaving the picker (Tab out to the summary bar, say) closes it too —
  // a menu left open drew over the Download sheet. A null relatedTarget is
  // ignored: a press on a menu item in a browser that does not focus buttons
  // on click reports null, and closing there would swallow the pick.
  let root = null;
  function onFocusOut(e) {
    if (open && root && e.relatedTarget && !root.contains(e.relatedTarget)) open = false;
  }
</script>

<svelte:window on:pointerdown={onWindowDown} />

<div class="gpicker" bind:this={root} on:focusout={onFocusOut}>
  <div class="gpills" role="group" aria-label="Garment">
    {#each pills as p (p.id)}
      <button
        type="button"
        class="gpill"
        class:sel={p.selected}
        aria-pressed={p.selected}
        title={p.title}
        on:click={() => pick(p.id)}
      >{p.text}</button>
    {/each}
    <button
      type="button"
      class="gpill gpill-more"
      aria-haspopup="menu"
      aria-expanded={open}
      aria-label="More garments"
      bind:this={moreBtn}
      on:click={toggle}
    >More ›</button>
  </div>
  {#if open}
    <div class="gmenu" role="menu" aria-label="All garments" tabindex="-1" bind:this={menuEl} on:keydown={onMenuKey}>
      {#each garments as g (g.id)}
        <button
          type="button"
          class="gmenu-item"
          role="menuitemradio"
          aria-checked={g.id === garmentId}
          on:click={() => pick(g.id)}
        >
          <span class="gart" aria-hidden="true">{@html garmentArt(g.id)}</span>
          <span>{g.label}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>
