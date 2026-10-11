<script>
  // The panel (spec §2.2): one scroll, sections in a fixed order, no step
  // numbers, and the summary bar pinned to the foot. This is a LAYOUT
  // shell — the sections' contents arrive through slots so App.svelte's
  // wiring of ContentStep and GarmentStep is unchanged.
  import { createEventDispatcher } from "svelte";
  import SummaryBar from "./SummaryBar.svelte";
  export let title = "Your design";
  export let subtitle = "";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  // Bound by App so a project switch can scroll the panel back to the top.
  export let body = null;
  const d = createEventDispatcher();
</script>

<div class="cfg-body" bind:this={body}>
  <h2 class="cfg-title">{title}</h2>
  <p class="cfg-sub">{subtitle}</p>
  <div class="startseg" role="group" aria-label="Start with">
    <button type="button" class="startseg-btn" on:click={() => d("addelement", "text")}>Add text</button>
    <button type="button" class="startseg-btn" on:click={() => d("addelement", "artwork")}>Upload file</button>
  </div>
  <section class="cfg-section" data-section="design"><slot name="design" /></section>
  <section class="cfg-section" data-section="garment"><slot name="garment" /></section>
</div>
<SummaryBar {sewFacts} {colorCount} {canDownload} on:download={() => d("download")} />
