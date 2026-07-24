<script>
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { createEventDispatcher } from "svelte";

  export let selected;
  const dispatch = createEventDispatcher();

  const fonts = Object.entries(EMB.SATIN_FONTS).map(([key, f]) => ({ key, name: f.name || key }));
  let open = false;
  let root;
  let thumbs = {}; // key -> dataURL (cached; the font rendered as real satin)

  // Render "Sample" in a font to a small canvas → data URL. Cached.
  function thumbFor(key) {
    if (thumbs[key] !== undefined) return thumbs[key];
    let url = "";
    try {
      const c = document.createElement("canvas");
      c.width = 220; c.height = 56;
      const design = EMB.buildLetteringDesign(EMB.SATIN_FONTS[key], "Sample", {
        garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5, underlay: false,
      });
      renderRealistic(c, design, { colorOverride: [45, 45, 50], fabric: "#ffffff", pad: 6 });
      url = c.toDataURL();
    } catch (e) { url = ""; }
    thumbs[key] = url;
    return url;
  }

  function ensureAll() { for (const f of fonts) thumbFor(f.key); thumbs = thumbs; }
  function toggle() { open = !open; if (open) ensureAll(); }
  function pick(key) { dispatch("pick", key); open = false; }
  function onWinClick(e) { if (open && root && !root.contains(e.target)) open = false; }

  $: selName = (fonts.find((f) => f.key === selected) || {}).name || "Choose a font";
  $: selThumb = selected ? thumbFor(selected) : "";
</script>

<svelte:window on:click={onWinClick} />

<div class="fontselect" bind:this={root}>
  <button type="button" class="fs-trigger" on:click|stopPropagation={toggle} aria-haspopup="listbox" aria-expanded={open}>
    {#if selThumb}
      <img class="fs-thumb" src={selThumb} alt={selName} />
    {:else}
      <span class="fs-name">{selName}</span>
    {/if}
    <span class="fs-chevron" class:open>▾</span>
  </button>

  {#if open}
    <ul class="fs-list" role="listbox">
      {#each fonts as f}
        <li>
          <button
            type="button"
            class="fs-opt"
            class:sel={f.key === selected}
            role="option"
            aria-selected={f.key === selected}
            on:click|stopPropagation={() => pick(f.key)}
          >
            {#if thumbs[f.key]}
              <img class="fs-thumb" src={thumbs[f.key]} alt={f.name} />
            {:else}
              <span class="fs-name">{f.name}</span>
            {/if}
            <span class="fs-optname">{f.name}</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
