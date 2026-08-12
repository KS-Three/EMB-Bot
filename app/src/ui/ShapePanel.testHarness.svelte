<script>
  import ShapePanel from "./ShapePanel.svelte";

  // Test-only wrapper (see ShapePanel.spec.js) — never imported by the app
  // itself. Same reason TextStep.testHarness.svelte exists: Svelte 5 gives a
  // test no way to observe a mounted component's dispatched events, so a
  // real parent listens with on:elupdate and mirrors App.svelte's
  // { id, patch } shallow-merge, letting the rendered panel react to its own
  // edits the way it does live in the Studio.
  export let element;
  export let onPatch = () => {};

  function handle(e) {
    element = { ...element, ...e.detail.patch };
    onPatch(e.detail);
  }
</script>

<ShapePanel {element} on:elupdate={handle} />
