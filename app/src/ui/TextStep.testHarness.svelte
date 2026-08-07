<script>
  import TextStep from "./TextStep.svelte";

  // Test-only wrapper (see TextStep.spec.js) — never imported by the app
  // itself. Same reason ManualPanel.testHarness.svelte exists: TextStep
  // dispatches its edits as a Svelte component event ("elupdate",
  // createEventDispatcher's `d("elupdate", ...)`), which Svelte 5 no longer
  // exposes to a caller via a mounted instance's `$on` (see
  // https://svelte.dev/e/component_api_changed) — a test that mounts
  // TextStep directly has no way to observe what it dispatches. Wrapping it
  // in a real *.svelte parent that listens with the normal
  // `on:elupdate={...}` directive sidesteps that, mirroring the exact
  // { id, patch } shallow-merge loop App.svelte's own elUpdate does, so a
  // rendered TextStep here reacts to its own edits (a badge disappearing on
  // input) the same way it does live in the Studio.
  export let element;
  export let onPatch = () => {};

  function handle(e) {
    element = { ...element, ...e.detail.patch };
    onPatch(e.detail);
  }
</script>

<TextStep {element} on:elupdate={handle} />
