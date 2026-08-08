<script>
  import TraceImportPanel from "./TraceImportPanel.svelte";

  // Test-only wrapper (see TraceImportPanel.spec.js) — never imported by the
  // app itself. Same reason ManualPanel/DigitizePanel needed one: Svelte 5
  // no longer exposes a mounted instance's dispatched events via `$on` (see
  // https://svelte.dev/e/component_api_changed) — a test that mounts
  // TraceImportPanel directly has no way to observe what it dispatches.
  // Wrapping it in a real *.svelte parent that listens with the normal
  // `on:traced={...}`/`on:cancel={...}` directives sidesteps that, forwarding
  // received event details to callback props a test can assert on directly.
  //
  // `existingShapes`/`workImage` just pass straight through to the real
  // component's own props — `workImage` in particular is TraceImportPanel's
  // documented test seam for "already decoded an image" state (see its own
  // comment), letting a test skip the real file-upload/image-decode path
  // jsdom has no implementation for.
  export let existingShapes = [];
  export let workImage = null;
  export let onTraced = () => {};
  export let onCancel = () => {};
</script>

<TraceImportPanel
  {existingShapes}
  {workImage}
  on:traced={(e) => onTraced(e.detail)}
  on:cancel={() => onCancel()}
/>
