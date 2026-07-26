<script>
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { createEventDispatcher } from "svelte";

  export let selected;
  const dispatch = createEventDispatcher();

  // Hardcoded key -> group map (Slice 8 Task 3) for the 21 shipped font keys.
  // Any key not listed here (future additions) lands in "More" rather than
  // being dropped, so the list never silently loses a font.
  const FONT_GROUP_MAP = {
    geneva_simple: "Sans",
    medium_font: "Sans",
    barstitch_regular: "Sans",
    barstitch_bold: "Sans",
    excalibur_KOR: "Sans",
    milli_marif_bold: "Sans",

    apex_simple_AGS: "Serif",
    violin_serif: "Serif",
    emilio_20: "Serif",
    emilio_20_bold: "Serif",
    roman_ags: "Serif",

    aventurina: "Script",
    pacificlo: "Script",
    amitaclo: "Script",
    mam_script: "Script",
    chicken_scratch: "Script",
    monicha: "Script",
    auberge_marif: "Script",
    digory_doodles_bean: "Script",

    manga_impact: "Display",
    tt_masters: "Display",
  };
  const GROUP_ORDER = ["Sans", "Serif", "Script", "Display", "More"];

  function groupFor(key) {
    return FONT_GROUP_MAP[key] || "More";
  }

  const fonts = Object.entries(EMB.SATIN_FONTS).map(([key, f]) => ({
    key,
    name: f.name || key,
    group: groupFor(key),
  }));

  // Fonts grouped under headers, in a fixed group order, groups with no
  // members omitted entirely (e.g. no unknown keys today -> no "More").
  const groupedFonts = GROUP_ORDER
    .map((group) => ({ group, items: fonts.filter((f) => f.group === group) }))
    .filter((g) => g.items.length > 0);

  let open = false;
  let root;
  let thumbs = {}; // key -> dataURL (cached; the font rendered as real satin)

  // Bigger thumbnails (Slice 8 Task 3): 280x44 "Sample" renders, up from the
  // previous 220x56 -- easier to judge a script/display font's shape at a
  // glance. Render "Sample" in a font to a small canvas -> data URL. Cached.
  const THUMB_W = 280, THUMB_H = 44;

  function thumbFor(key) {
    if (thumbs[key] !== undefined) return thumbs[key];
    let url = "";
    try {
      const c = document.createElement("canvas");
      c.width = THUMB_W; c.height = THUMB_H;
      const design = EMB.buildLetteringDesign(EMB.SATIN_FONTS[key], "Sample", {
        garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5, underlay: false,
      });
      renderRealistic(c, design, { colorOverride: [45, 45, 50], fabric: "#ffffff", pad: 8 });
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
