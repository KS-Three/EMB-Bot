<script>
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { loadManifest, ensureFont } from "../lib/fontLoader.js";
  import { createEventDispatcher } from "svelte";

  export let selected;
  const dispatch = createEventDispatcher();

  const GROUP_ORDER = ["Sans", "Serif", "Script", "Display", "Small", "More"];

  // Font list now comes from the manifest (single source of truth for name +
  // group -- see tools/font-categories.json, which feeds the manifest at
  // build time), not from Object.entries(EMB.SATIN_FONTS): that map starts
  // EMPTY at boot under lazy font loading (Slice 10A), so deriving the list
  // from it would render an empty dropdown until something happened to
  // populate SATIN_FONTS. loadManifest() is small and cached (fontLoader.js),
  // so this resolves quickly without needing any font binary fetched yet.
  let fonts = [];
  loadManifest().then((man) => {
    fonts = man.fonts.map((f) => ({ key: f.key, name: f.name, group: f.group }));
  });

  // Fonts grouped under headers, in a fixed group order, groups with no
  // members omitted entirely. Recomputes reactively once `fonts` arrives
  // from the manifest (starts [] -> groupedFonts starts [] too, then fills
  // in when the promise above resolves).
  $: groupedFonts = GROUP_ORDER
    .map((group) => ({ group, items: fonts.filter((f) => f.group === group) }))
    .filter((g) => g.items.length > 0);

  let open = false;
  let root;
  let thumbs = {}; // key -> dataURL, filled in once that font's thumbnail resolves
  const thumbsPending = new Set(); // keys currently being fetched/rendered -- de-dupes concurrent requests

  // Bigger thumbnails (Slice 8 Task 3): 280x44 "Sample" renders, up from the
  // previous 220x56 -- easier to judge a script/display font's shape at a
  // glance. Render "Sample" in a font to a small canvas -> data URL. Cached.
  const THUMB_W = 280, THUMB_H = 44;

  // Fire-and-forget: fetches/decodes the font (ensureFont -- cached after the
  // first call, instant if already resolved elsewhere) then renders its
  // thumbnail. `thumbs` is reassigned on completion so every reader (the
  // selected-font trigger button, each option row) re-renders as soon as its
  // own font arrives -- thumbnails fill in progressively rather than
  // blocking the dropdown open.
  function ensureThumb(key) {
    if (thumbs[key] !== undefined || thumbsPending.has(key)) return;
    thumbsPending.add(key);
    (async () => {
      let url = "";
      try {
        const font = await ensureFont(key);
        const c = document.createElement("canvas");
        c.width = THUMB_W; c.height = THUMB_H;
        const design = EMB.buildLetteringDesign(font, "Sample", {
          garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5, underlay: false,
        });
        renderRealistic(c, design, { colorOverride: [45, 45, 50], fabric: "#ffffff", pad: 8 });
        url = c.toDataURL();
      } catch (e) { url = ""; }
      thumbsPending.delete(key);
      thumbs = { ...thumbs, [key]: url };
    })();
  }

  function ensureAll() { for (const f of fonts) ensureThumb(f.key); }
  function toggle() { open = !open; if (open) ensureAll(); }
  function pick(key) { dispatch("pick", key); open = false; }
  function onWinClick(e) { if (open && root && !root.contains(e.target)) open = false; }

  $: selName = (fonts.find((f) => f.key === selected) || {}).name || "Choose a font";
  // The collapsed trigger button shows the selected font's thumbnail even
  // before the dropdown is ever opened, so it needs its own fetch trigger.
  $: if (selected) ensureThumb(selected);
  $: selThumb = selected ? thumbs[selected] || "" : "";
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
      {#each groupedFonts as g}
        <li class="fs-group-header" role="presentation">{g.group}</li>
        {#each g.items as f}
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
      {/each}
    </ul>
  {/if}
</div>
