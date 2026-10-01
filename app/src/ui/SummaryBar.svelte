<script>
  // The panel's sticky foot (spec §2.3): three figures the customer keeps
  // glancing at while editing, and the one Download. Size and stitches come
  // from the browser estimate's rows (lib/estimate.js sewSummary); colors
  // counts distinct spools. The sheet does NOT always read the same numbers:
  // DownloadStep lists colour BLOCKS, not spools, and a digitized-only
  // design's sheet shows the service's plan figures, which run ~1.6% apart
  // from the browser estimate (see lib/estimate.js).
  import { createEventDispatcher } from "svelte";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  const d = createEventDispatcher();

  const DASH = "—";
  function row(facts, label) {
    const r = (facts || []).find((x) => x.label === label);
    return r ? r.value : DASH;
  }
  $: size = row(sewFacts, "Size");
  $: stitches = row(sewFacts, "Stitches");
  $: colors = colorCount > 0 ? String(colorCount) : DASH;
  $: colorLabel = colorCount === 1 ? "color" : "colors";
</script>

<div class="summarybar">
  <div class="summarybar-figures">
    <div class="summarybar-figure"><b>{size}</b><span>size</span></div>
    <div class="summarybar-figure"><b>{stitches}</b><span>stitches</span></div>
    <div class="summarybar-figure"><b>{colors}</b><span>{colorLabel}</span></div>
  </div>
  <button
    type="button"
    class="primary summarybar-download"
    disabled={!canDownload}
    title={canDownload ? "" : "Add text or a logo first"}
    on:click={() => d("download")}
  >Download</button>
</div>
