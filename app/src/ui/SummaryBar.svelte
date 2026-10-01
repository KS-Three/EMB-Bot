<script>
  // The panel's sticky foot (spec §2.3): three figures the customer keeps
  // glancing at while editing, and the one Download. Figures come from the
  // same rows the review recap used (lib/estimate.js sewSummary), so the
  // bar and the sheet can never disagree.
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
