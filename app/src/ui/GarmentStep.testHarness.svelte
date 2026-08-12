<script>
  import GarmentStep from "./GarmentStep.svelte";

  // Test-only wrapper (see GarmentStep.spec.js) — never imported by the app
  // itself. Same reason TextStep.testHarness.svelte exists: GarmentStep
  // dispatches its edits as a Svelte component event ("update"), which
  // Svelte 5 no longer exposes to a caller via a mounted instance's `$on`
  // (https://svelte.dev/e/component_api_changed). Wrapping it in a real
  // *.svelte parent that listens with the normal `on:update={...}` directive
  // sidesteps that, mirroring the same top-level shallow merge App.svelte's
  // own apply() does, so a rendered GarmentStep here reacts to its own picks
  // (the hoop selection moving, the reset link appearing) the same way it
  // does live in the Studio.
  export let project;
  export let onUpdate = () => {};

  function handle(e) {
    project = { ...project, ...e.detail };
    onUpdate(e.detail);
  }
</script>

<GarmentStep {project} on:update={handle} />
