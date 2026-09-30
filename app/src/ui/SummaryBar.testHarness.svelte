<script>
  import SummaryBar from "./SummaryBar.svelte";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  export let onDownload = () => {};
</script>

<SummaryBar {sewFacts} {colorCount} {canDownload} on:download={onDownload} />
