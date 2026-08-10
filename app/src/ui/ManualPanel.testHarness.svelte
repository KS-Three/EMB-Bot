<script>
  import ManualPanel from "./ManualPanel.svelte";

  // Test-only wrapper (see ManualPanel.spec.js) — never imported by the
  // app itself. ManualPanel dispatches its edits as a Svelte component
  // event ("elupdate", createEventDispatcher's `d("elupdate", ...)`), which
  // Svelte 5 no longer exposes to a caller via a mounted instance's `$on`
  // (see https://svelte.dev/e/component_api_changed) — a test that mounts
  // ManualPanel directly has no way to observe what it dispatches. Wrapping
  // it in a real *.svelte parent that listens with the normal
  // `on:elupdate={...}` directive sidesteps that: this is exactly the
  // { id, patch } shallow-merge loop App.svelte's own elUpdate does (see
  // App.svelte), so a rendered ManualPanel here behaves the same as it does
  // live in the Studio — patches applied, `element.shapes` updated, the
  // next click/drag sees the new state — while also handing the raw patch
  // to `onPatch` for tests that want to assert on it directly.
  export let element;
  export let onPatch = () => {};
  // Forwarded straight through to ManualPanel's own `traceWorkImage` test
  // seam (see its comment) — lets a spec seed the nested TraceImportPanel's
  // "already decoded an image" state without a real file upload.
  export let traceWorkImage = null;

  function handle(e) {
    element = { ...element, ...e.detail.patch };
    onPatch(e.detail);
  }
</script>

<ManualPanel {element} {traceWorkImage} on:elupdate={handle} />
