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
  export let position = null;           // null | { x, y } — a dragged spot, wins over anchor

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
  // A dragged position (Kent 2026-09-29: the dialog sometimes hides what he is
  // editing) wins over the anchor; the same clamp applies to either.
  const clampX = (x, bw, pw) => Math.max(0, Math.min(x, Math.max(0, (bw || Infinity) - pw - 4)));
  const clampY = (y, bh, ph) => Math.max(0, Math.min(y, Math.max(0, (bh || Infinity) - ph - 4)));
  $: left = clampX(position ? position.x : anchor.x + 8, bounds.w, w);
  $: top = clampY(position ? position.y : anchor.y + 8, bounds.h, h);

  // Header drag: remember where inside the dialog the pointer grabbed it, then
  // report the dialog's new top-left (in the parent's px) on every move.
  let drag = null;
  function onHeadDown(e) {
    if (e.button !== undefined && e.button !== 0) return;
    drag = { dx: e.clientX - left, dy: e.clientY - top };
    try { e.currentTarget.setPointerCapture?.(e.pointerId); } catch { /* synthetic pointer */ }
    e.preventDefault();
  }
  function onHeadMove(e) {
    if (!drag) return;
    d("move", {
      x: clampX(e.clientX - drag.dx, bounds.w, w),
      y: clampY(e.clientY - drag.dy, bounds.h, h),
    });
  }
  function onHeadUp(e) {
    if (!drag) return;
    drag = null;
    try { e.currentTarget.releasePointerCapture?.(e.pointerId); } catch { /* already released */ }
  }

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

  // A row's note is read out with its control (aria-describedby), so a screen
  // reader hears "Cut out, switch, on — Cuts Shape 1." rather than the switch
  // alone. Null on a row without a note, which omits the attribute.
  const noteId = (row) => (row.note ? `shapepop-note-${row.key}` : null);

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
  <!-- Pointer-only drag handle by design (no keyboard move); the dialog's own
       name and Escape are unchanged. -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="shapepop-head"
    title="Drag to move"
    on:pointerdown={onHeadDown}
    on:pointermove={onHeadMove}
    on:pointerup={onHeadUp}
    on:pointercancel={onHeadUp}
  ><span class="shapepop-grip" aria-hidden="true">⋮⋮</span>{model.name}</div>
  {#each model.rows as row (row.key)}
    {#if row.kind === "thread"}
      <div class="shapepop-row">
        <span class="shapepop-label">Color</span>
        <ThreadPicker compact rgb={row.rgb} name={model.name} on:pick={(e) => d("change", { key: "color", value: e.detail })} />
      </div>
    {:else if row.kind === "choice"}
      <label class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <select value={row.value} aria-label={row.label} aria-describedby={noteId(row)} on:change={(e) => d("change", { key: row.key, value: e.currentTarget.value })}>
          {#each row.options as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </label>
    {:else if row.kind === "number"}
      <label class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <input
          type="number" step={row.step == null ? 1 : row.step} min={row.min} placeholder="auto" aria-label={row.label} aria-describedby={noteId(row)}
          value={row.value == null ? "" : row.value}
          on:input={(e) => { if (row.key !== "widthMm") d("change", { key: row.key, value: e.currentTarget.value }); }}
          on:change={(e) => { if (row.key === "widthMm") d("change", { key: row.key, value: e.currentTarget.value }); }}
        />
        {#if row.hint}<span class="shapepop-hint">{row.hint}</span>{/if}
      </label>
    {:else if row.kind === "action"}
      <button type="button" class="shapepop-action" class:danger={row.danger} on:click={() => d("action", { key: row.key })}>
        {row.label}
      </button>
    {:else if row.kind === "toggle"}
      <div class="shapepop-row">
        <span class="shapepop-label">{row.label}</span>
        <button
          type="button" role="switch" class="shapepop-toggle"
          aria-checked={row.value ? "true" : "false"} aria-label={row.label} aria-describedby={noteId(row)}
          on:click={() => d("change", { key: row.key, value: !row.value })}
        >{row.value ? "On" : "Off"}</button>
      </div>
    {/if}
    {#if row.note}<p class="shapepop-note" id={noteId(row)} class:warn={row.warn}>{row.note}</p>{/if}
  {/each}
</div>
