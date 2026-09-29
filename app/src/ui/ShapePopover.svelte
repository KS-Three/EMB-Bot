<script>
  // The click-to-edit popover (2026-09-29 spec §5). Renders a
  // lib/shapePopover.js model where the shape was clicked and emits what the
  // field then turns into an `elupdate` patch. Knows nothing about projects
  // or lanes — the model is the whole contract — so the same markup serves an
  // auto-digitized shape and a hand-drawn one.
  import { createEventDispatcher, onMount, tick } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";

  export let model;
  export let anchor = { x: 0, y: 0 };   // px inside the positioned parent (.hoop)
  export let bounds = { w: 0, h: 0 };   // that parent's box, for clamping

  const d = createEventDispatcher();
  let root;
  // Fallback size until the browser has laid the dialog out (jsdom never
  // does): roughly the rendered size at the default font scale.
  const POP_W = 260;
  const POP_H = 240;
  let w = POP_W;
  let h = POP_H;

  // Sit just right/below the click, but never past the parent's edge: on a
  // short viewport the dialog may cover the shape — the outline highlight
  // stays visible around it (spec §6).
  $: left = Math.max(0, Math.min(anchor.x + 8, Math.max(0, (bounds.w || Infinity) - w - 4)));
  $: top = Math.max(0, Math.min(anchor.y + 8, Math.max(0, (bounds.h || Infinity) - h - 4)));

  onMount(async () => {
    // Focus first, synchronously: the dialog is in the DOM by onMount, and
    // waiting a tick would let a caller (or a test) look before it lands.
    if (root) (root.querySelector("select, input, button") || root).focus();
    await tick();
    if (root) {
      const r = root.getBoundingClientRect();
      if (r.width) w = r.width;
      if (r.height) h = r.height;
    }
  });

  function onKey(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      d("close");
    }
  }
</script>

<!-- role=dialog with a real name: the shape's own, so a screen reader hears
     which shape it is about to change. Escape closes; the field closes it on
     an outside pointerdown (EmbroideryField.onWindowPointerDown). -->
<div
  class="shapepop"
  role="dialog"
  aria-label={model.name}
  tabindex="-1"
  bind:this={root}
  style="left: {left}px; top: {top}px"
  on:keydown={onKey}
>
  <div class="shapepop-head">{model.name}</div>
  {#each model.rows as row (row.key)}
    {#if row.kind === "thread"}
      <div class="shapepop-row">
        <span class="shapepop-label">Color</span>
        <ThreadPicker compact rgb={row.rgb} name={model.name} on:pick={(e) => d("change", { key: "color", value: e.detail })} />
      </div>
    {:else if row.kind === "choice"}
      <label class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <select value={row.value} aria-label={row.label} on:change={(e) => d("change", { key: row.key, value: e.currentTarget.value })}>
          {#each row.options as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </label>
    {:else if row.kind === "number"}
      <label class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <input
          type="number" step="1" placeholder="auto" aria-label={row.label}
          value={row.value == null ? "" : row.value}
          on:input={(e) => d("change", { key: row.key, value: e.currentTarget.value })}
        />
        {#if row.hint}<span class="shapepop-hint">{row.hint}</span>{/if}
      </label>
    {:else if row.kind === "action"}
      <button type="button" class="shapepop-action" class:danger={row.danger} on:click={() => d("action", { key: row.key })}>
        {row.label}
      </button>
    {/if}
  {/each}
</div>
