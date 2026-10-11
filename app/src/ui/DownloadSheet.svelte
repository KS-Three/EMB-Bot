<script>
  // The Download sheet (spec §2.4): what used to be the "create" review step
  // and the "download" step, one above the other, in a dialog the summary
  // bar opens. DownloadStep is rendered here UNCHANGED — its buttons,
  // test ids and the "Download" h2 are what every export e2e reads.
  import { createEventDispatcher, onMount } from "svelte";
  import QualityReport from "./QualityReport.svelte";
  import HoopingCard from "./HoopingCard.svelte";
  import DownloadStep from "./DownloadStep.svelte";
  import QuoteSettings from "./QuoteSettings.svelte";
  import Icon from "./Icon.svelte";
  export let project;
  export let designName = "";
  export let runtime;
  export let digitizerHealth = null;
  export let summaryRows = [];
  // Stabilizer / topper / needle for the whole design (lib/hooping.js).
  export let hoopingRows = [];
  export let qualityEntries = [];
  export let qualityPartial = false;
  export let ready = false;
  // The operator's quote inputs (lib/quote.js). Owned by App, which stores
  // them and rebuilds `summaryRows` from them; this only relays the edit.
  export let quote = {};
  const d = createEventDispatcher();

  let el = null;
  onMount(() => { if (el) el.focus(); });

  // aria-modal is only true if Tab cannot leave: wrap between the sheet's
  // first and last focusable controls (same pattern as FontCredits).
  function onKey(e) {
    if (e.key === "Escape") { e.stopPropagation(); d("close"); return; }
    if (e.key !== "Tab" || !el) return;
    const els = Array.from(el.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter((n) => n.offsetParent !== null);
    if (!els.length) return;
    const first = els[0], last = els[els.length - 1];
    const a = document.activeElement;
    if (e.shiftKey && (a === first || a === el || !el.contains(a))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && (a === last || !el.contains(a))) { e.preventDefault(); first.focus(); }
  }
</script>

<div class="sheet" role="dialog" aria-modal="true" aria-label="Download" tabindex="-1" bind:this={el} on:keydown={onKey}>
  <div class="sheet-head">
    {#if ready}
      <h2>Ready to stitch</h2>
    {:else}
      <h2>Nothing to stitch yet</h2>
    {/if}
    <button type="button" class="sheet-close" aria-label="Close" on:click={() => d("close")}><Icon name="close" size={16} /></button>
  </div>
  {#if !ready}
    <p>
      This design has no content the machine can sew. Close this and type some
      lettering, upload artwork, or draw a shape — the field updates live as you do.
    </p>
  {/if}
  <dl class="summary">
    {#each summaryRows as row}
      <div><dt>{row.label}</dt><dd>{row.value}</dd></div>
    {/each}
  </dl>
  <QuoteSettings {quote} on:change={(e) => d("quote", e.detail)} />
  <HoopingCard rows={hoopingRows} />
  <QualityReport entries={qualityEntries} partial={qualityPartial} on:locate={(e) => d("locate", e.detail)} />
  <DownloadStep {project} {designName} {runtime} {digitizerHealth} on:credits={(e) => d("credits", e.detail)} />
</div>
