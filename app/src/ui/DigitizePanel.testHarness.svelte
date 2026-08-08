<script>
  import DigitizePanel from "./DigitizePanel.svelte";

  // Test-only wrapper (see DigitizePanel.spec.js) — never imported by the
  // app itself. Same reason ManualPanel needed one: DigitizePanel dispatches
  // its edits as a Svelte component event ("elupdate", createEventDispatcher's
  // `d("elupdate", ...)`), which Svelte 5 no longer exposes to a caller via a
  // mounted instance's `$on` (see https://svelte.dev/e/component_api_changed).
  // Wrapping it in a real *.svelte parent that listens with the normal
  // `on:elupdate={...}` directive sidesteps that — the same { id, patch }
  // shallow-merge loop App.svelte's own elUpdate does — while also handing
  // the raw patch to `onPatch` for tests that want to assert on it directly.
  export let element;
  export let project = {};
  export let health = null;
  export let onPatch = () => {};

  function handle(e) {
    element = { ...element, ...e.detail.patch };
    onPatch(e.detail);
  }
</script>

<DigitizePanel {element} {project} {health} on:elupdate={handle} />
