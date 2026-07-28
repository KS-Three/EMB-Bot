<script>
  // Font picker (Slice 10B Task 4). This component is now just a trigger
  // button showing the selected font's static preview PNG; the actual
  // browsing/search/filter UI lives in FontBrowser.svelte, opened as a
  // dialog on click. The old dropdown (Slice 8 Task 3) fetched every font
  // binary the moment it opened (a per-font fetch-and-render queue, ~30MB
  // total) -- that fetch-all path is gone. The ONE font this component still
  // ensures eagerly is the currently selected one, so the trigger can show a
  // real rendered preview instead of the flat static PNG -- a single font,
  // not the whole catalog.
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { loadManifest, ensureFont } from "../lib/fontLoader.js";
  import { createEventDispatcher } from "svelte";
  import FontBrowser from "./FontBrowser.svelte";

  export let selected;
  export let currentText = "";
  const dispatch = createEventDispatcher();

  let fonts = [];
  let manifestLoaded = false;
  loadManifest().then((man) => {
    fonts = man.fonts.map((f) => ({ key: f.key, name: f.name, group: f.group }));
    manifestLoaded = true;
  }).catch(() => { manifestLoaded = true; });

  $: selName = (fonts.find((f) => f.key === selected) || {}).name
    || (manifestLoaded ? "Choose a font" : "Loading fonts…");

  // ---- Selected-font trigger preview ---------------------------------------
  // Mirrors the old dropdown's trigger behavior: the ONE font that's already
  // selected gets ensured/rendered so the trigger shows a real satin
  // thumbnail rather than the static PNG. This is not the fetch-all path --
  // it's exactly one font, the same one already chosen.
  const THUMB_W = 280, THUMB_H = 44;
  let selThumb = "";
  let selThumbFor = null;
  $: if (selected && selected !== selThumbFor) {
    selThumbFor = selected;
    selThumb = ""; // fall back to the static PNG while this one re-renders
    renderSelThumb(selected);
  }
  async function renderSelThumb(key) {
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
    if (selThumbFor === key) selThumb = url;
  }

  // ---- Browser dialog + focus restore --------------------------------------
  let browserOpen = false;
  let openerEl = null;

  function openBrowser(e) {
    openerEl = e.currentTarget;
    browserOpen = true;
  }

  function closeBrowser() {
    browserOpen = false;
    if (openerEl) openerEl.focus();
  }

  function onPick(e) {
    dispatch("pick", e.detail);
  }

  $: triggerThumb = selThumb || (selected ? "/fonts/previews/" + selected + ".png" : "");
</script>

<div class="fontselect">
  <button type="button" class="fs-trigger" on:click={openBrowser}>
    {#if triggerThumb}
      <img class="fs-thumb" src={triggerThumb} alt={selName} />
    {/if}
    <span class="fs-name">{selName}</span>
  </button>
</div>

{#if browserOpen}
  <FontBrowser
    {selected}
    {currentText}
    on:pick={onPick}
    on:close={closeBrowser}
  />
{/if}
