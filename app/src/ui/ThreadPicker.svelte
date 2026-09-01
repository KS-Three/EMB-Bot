<script>
  import { createEventDispatcher } from "svelte";
  import { PALETTE_INDEX, STUDIO_PALETTE, getCachedPalette, loadPalette, nearestInList, filterThreads, loadPreferredPaletteId, savePreferredPaletteId } from "../lib/threads.js";
  import Icon from "./Icon.svelte";

  // Named-thread color picker (Slice 8 Task 4), used everywhere a thread
  // color is chosen (TextStep's element color, ImagePanel's per-swatch
  // thread overrides, and — via the same swatch-grid pattern — anywhere
  // else a raw <input type="color"> used to live).
  //
  // Brand catalogs (Ember-audit follow-up): alongside the generic "Studio
  // basics" list the picker now offers real manufacturer charts (Isacord,
  // Madeira, Robison-Anton -- see lib/threadBrands.js) with a name/code
  // search. The chosen palette is remembered app-wide (localStorage) so a
  // shop that stitches with Isacord sees Isacord everywhere by default.
  //
  // B6 (NON-NEGOTIABLE, plan amendment): this is NOT a floating popover.
  // The scrollable .panel-body clips absolutely-positioned overlays (the
  // Slice-7 A9 lesson) so the grid below the trigger renders IN NORMAL
  // DOCUMENT FLOW -- it pushes following content down while open instead of
  // floating over it, same idea as GarmentStep's in-flow fabric-color row.
  export let rgb; // current color, [r,g,b]
  export let label = ""; // optional text label rendered above the trigger
  export let compact = false; // ImagePanel's per-swatch usage: swatch-only trigger, no name text
  // Who this picker belongs to, for the trigger's accessible name only —
  // never rendered. `label` above can't do this job: it draws visible text.
  export let name = "";

  const d = createEventDispatcher();

  let open = false;
  let query = "";
  let paletteId = loadPreferredPaletteId();

  function onPaletteChange(e) {
    paletteId = e.currentTarget.value;
    query = "";
    savePreferredPaletteId(paletteId);
  }

  function toHex(c) {
    return "#" + c.map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0")).join("");
  }
  function fromHex(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function threadLabel(t) {
    return t.code ? `${t.code} ${t.name}` : t.name;
  }

  // Brand thread lists load lazily (threads.js loadPalette — the ~1.1MB
  // data chunk stays out of the main bundle). While a brand chart is in
  // flight, `palette` falls back to Studio so nearest/grid math always has
  // a real list, and `pending` keeps the UI honest about it (the trigger
  // shows "…" instead of claiming a Studio shade name under a brand
  // preference). After the first load every palette switch is a sync cache
  // hit. The id equality check on resolve drops stale responses if the
  // user flips palettes faster than the chunk arrives.
  let palette = STUDIO_PALETTE;
  let pending = false;
  function ensurePalette(id) {
    const hit = getCachedPalette(id);
    if (hit) {
      palette = hit;
      pending = false;
      return;
    }
    pending = true;
    loadPalette(id).then(
      (p) => {
        if (paletteId !== id) return; // stale — a newer selection won
        palette = p;
        pending = false;
      },
      () => {
        if (paletteId !== id) return;
        pending = false; // chunk failed to load; Studio fallback stays up
      }
    );
  }

  // Reactive so both the trigger's name/swatch and the grid's selected ring
  // stay in sync whenever the `rgb` prop OR the chosen palette changes
  // (including from outside, e.g. a project load).
  $: ensurePalette(paletteId);
  $: nearest = nearestInList(palette.threads, rgb);
  $: shown = filterThreads(palette.threads, query);

  function toggle() {
    open = !open;
  }

  function pick(t) {
    d("pick", t.rgb);
    open = false;
    query = "";
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
  <!-- In `compact` mode the trigger is a bare swatch: no text child, and a
       `title` is not an accessible name a screen reader or voice control can
       rely on — so every compact picker (one per shape row, 29 of them on a
       two-colour logo) was a button with no name at all. `name` qualifies it
       with the row it belongs to; without one it still says what it is and
       which thread it currently holds. -->
  <button
    type="button"
    class="tp-trigger"
    on:click|stopPropagation={toggle}
    aria-haspopup="true"
    aria-expanded={open}
    aria-label={"Thread color" + (name ? " for " + name : "") + " — " +
      (pending ? "loading" : threadLabel(nearest))}
    title={threadLabel(nearest)}
  >
    <span class="tp-swatch" style="background: rgb({rgb[0]},{rgb[1]},{rgb[2]})"></span>
    {#if !compact}<span class="tp-name">{pending ? "…" : threadLabel(nearest)}</span>{/if}
    <span class="tp-chevron" class:open aria-hidden="true">
      <Icon name="chevron" size={compact ? 12 : 14} />
    </span>
  </button>

  {#if open}
    <div class="tp-panel">
      <div class="tp-tools">
        <select class="tp-brand" value={paletteId} on:change={onPaletteChange} on:click|stopPropagation aria-label="Thread brand">
          {#each PALETTE_INDEX as p (p.id)}
            <option value={p.id}>{p.label}</option>
          {/each}
        </select>
        {#if paletteId !== "studio"}
          <input
            type="search"
            class="tp-search"
            placeholder="Search name or number…"
            bind:value={query}
            on:click|stopPropagation
            aria-label="Search threads"
          />
        {/if}
      </div>
      <div class="tp-grid" class:big={paletteId !== "studio"} role="listbox" aria-label={label || "Thread color"}>
        {#if pending}
          <p class="tp-empty">Loading chart…</p>
        {:else}
        {#each shown as t, i (threadLabel(t) + i)}
          <button
            type="button"
            class="tp-cell"
            class:sel={t === palette.threads[nearest.index]}
            style="background: rgb({t.rgb[0]},{t.rgb[1]},{t.rgb[2]})"
            title={threadLabel(t)}
            aria-label={threadLabel(t)}
            role="option"
            aria-selected={t === palette.threads[nearest.index]}
            on:click|stopPropagation={() => pick(t)}
          ></button>
        {/each}
        {#if !shown.length}
          <p class="tp-empty">No threads match “{query}”.</p>
        {/if}
        {/if}
      </div>
      <label class="tp-custom">
        <span>Custom…</span>
        <input type="color" value={toHex(rgb)} on:click|stopPropagation on:change|stopPropagation={pickCustom} />
      </label>
    </div>
  {/if}
</div>
