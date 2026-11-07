<script>
  import EditModeBar from "../src/ui/EditModeBar.svelte";
  // Test-only parent: records the bar's dispatched events (see
  // src/ui/ShapePopover.testHarness.svelte for why).
  export let bar = null;
  export let onEvent = () => {};
</script>

<EditModeBar {bar} on:action={(e) => onEvent(e.detail.id)} />
