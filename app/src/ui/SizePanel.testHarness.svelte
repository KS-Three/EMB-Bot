<script>
  import SizePanel from "./SizePanel.svelte";

  // Test-only wrapper (see SizePanel.spec.js) — never imported by the app.
  // Same reason ShapePanel.testHarness.svelte exists: Svelte 5 gives a test no
  // way to observe a mounted component's dispatched events, so a real parent
  // listens and records.
  //
  // `designDims` is deliberately NOT recomputed from the update. The design
  // regenerating is EmbroideryField's job and takes a real engine; holding it
  // fixed is exactly the state these tests are about — two out-of-range
  // entries in a row, where the clamped design does not change and the
  // one-way `value={wDisplay}` therefore never rewrote the field.
  export let project;
  export let designDims = null;
  export let onUpdate = () => {};

  function handle(e) {
    project = { ...project, ...e.detail };
    onUpdate(e.detail);
  }
</script>

<SizePanel {project} {designDims} on:update={handle} />
