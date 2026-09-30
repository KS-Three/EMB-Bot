<script>
  import Configurator from "./Configurator.svelte";
  export let subtitle = "Left Chest · 4×4 in";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  export let onAdd = () => {};
  export let onDownload = () => {};
</script>

<Configurator {subtitle} {sewFacts} {colorCount} {canDownload} on:addelement={onAdd} on:download={onDownload}>
  <p slot="design" data-testid="design-slot">design goes here</p>
  <p slot="garment" data-testid="garment-slot">garment goes here</p>
</Configurator>
