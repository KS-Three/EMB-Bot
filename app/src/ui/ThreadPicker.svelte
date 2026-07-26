<script>
  import { createEventDispatcher } from "svelte";
  import { THREADS, nearestThread } from "../lib/threads.js";

  // Named-thread color picker (Slice 8 Task 4), used everywhere a thread
  // color is chosen (TextStep's element color, ImagePanel's per-swatch
  // thread overrides, and — via the same swatch-grid pattern — anywhere
  // else a raw <input type="color"> used to live).
  //
  // B6 (NON-NEGOTIABLE, plan amendment): this is NOT a floating popover.
  // The scrollable .panel-body clips absolutely-positioned overlays (the
  // Slice-7 A9 lesson) so the grid below the trigger renders IN NORMAL
  // DOCUMENT FLOW -- it pushes following content down while open instead of
  // floating over it, same idea as GarmentStep's in-flow fabric-color row.
  export let rgb; // current color, [r,g,b]
  export let label = ""; // optional text label rendered above the trigger
  export let compact = false; // ImagePanel's per-swatch usage: swatch-only trigger, no name text

  const d = createEventDispatcher();

  let open = false;

  function toHex(c) {
    return "#" + c.map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0")).join("");
  }
  function fromHex(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  // Reactive so both the trigger's name/swatch and the grid's selected ring
  // stay in sync whenever the `rgb` prop changes (including from outside,
  // e.g. a project load).
  $: nearest = nearestThread(rgb);

  function toggle() {
    open = !open;
  }

  function pick(t) {
    d("pick", t.rgb);
    open = false;
  }

  // The native color dialog stays open across repeated "input" events while
  // the user drags inside it -- collapsing our in-flow panel on "input"
  // would unmount this very <input> mid-interaction. "change" only fires
  // once the user has committed a color and the native dialog has closed,
  // so it's the right moment to dispatch + collapse (Task: "collapses on
  // pick or Esc").
  function pickCustom(e) {
    d("pick", fromHex(e.currentTarget.value));
    open = false;
  }

  function onKeydown(e) {
    if (open && e.key === "Escape") open = false;
  }
</script>

<svelte:window on:keydown={onKeydown} />

<div class="threadpicker" class:compact>
  {#if label}<span class="tp-label">{label}</span>{/if}
  <button
    type="button"
    class="tp-trigger"
    on:click|stopPropagation={toggle}
    aria-haspopup="true"
    aria-expanded={open}
    title={nearest.name}
  >
    <span class="tp-swatch" style="background: rgb({rgb[0]},{rgb[1]},{rgb[2]})"></span>
    {#if !compact}<span class="tp-name">{nearest.name}</span>{/if}
    <span class="tp-chevron" class:open aria-hidden="true">▾</span>
  </button>

  {#if open}
    <div class="tp-panel">
      <div class="tp-grid" role="listbox" aria-label={label || "Thread color"}>
        {#each THREADS as t, i (t.name)}
          <button
            type="button"
            class="tp-cell"
            class:sel={i === nearest.index}
            style="background: rgb({t.rgb[0]},{t.rgb[1]},{t.rgb[2]})"
            title={t.name}
            aria-label={t.name}
            role="option"
            aria-selected={i === nearest.index}
            on:click|stopPropagation={() => pick(t)}
          ></button>
        {/each}
      </div>
      <label class="tp-custom">
        <span>Custom…</span>
        <input type="color" value={toHex(rgb)} on:click|stopPropagation on:change|stopPropagation={pickCustom} />
      </label>
    </div>
  {/if}
</div>
