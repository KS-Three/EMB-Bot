<script>
  import CalibratePanel from "./CalibratePanel.svelte";

  // Test-only wrapper (see CalibratePanel.spec.js) — never imported by the
  // app. Same reason GarmentStep.testHarness.svelte exists: the panel
  // dispatches "update" and "close" as component events, which Svelte 5
  // does not expose through a mounted instance's `$on`.
  export let project;
  export let digitizerHealth = null;
  export let onUpdate = () => {};
  export let onClose = () => {};
</script>

<CalibratePanel {project} {digitizerHealth} on:update={(e) => onUpdate(e.detail)} on:close={onClose} />
