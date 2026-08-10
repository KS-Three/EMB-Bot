<script>
  import StepNav from "./StepNav.svelte";

  // Test-only wrapper (see StepNav.spec.js) — never imported by the app
  // itself. Same reason TraceImportPanel/ManualPanel/DigitizePanel needed
  // one: Svelte 5 no longer exposes a mounted instance's dispatched events
  // via `$on` (see https://svelte.dev/e/component_api_changed) — a test that
  // mounts StepNav directly has no way to observe what it dispatches.
  // Wrapping it in a real *.svelte parent that listens with the normal
  // `on:goto={...}`/`on:back={...}`/`on:next={...}` directives sidesteps
  // that, forwarding received event details to callback props a test can
  // assert on directly.
  export let step;
  export let project;
  export let canNext = true;
  export let onGoto = () => {};
  export let onBack = () => {};
  export let onNext = () => {};
</script>

<StepNav
  {step}
  {project}
  {canNext}
  on:goto={(e) => onGoto(e.detail)}
  on:back={() => onBack()}
  on:next={() => onNext()}
/>
