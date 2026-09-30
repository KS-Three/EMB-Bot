<script>
  import ShapePopover from "./ShapePopover.svelte";
  // Test-only parent (see ShapePopover.spec.js) — Svelte 5 gives a test no
  // way to observe a mounted component's dispatched events, so a real parent
  // records them. Same pattern as ShapePanel.testHarness.svelte.
  export let model;
  export let anchor = { x: 40, y: 40 };
  export let bounds = { w: 800, h: 600 };
  export let onEvent = () => {};
</script>

<div style="position: relative; width: {bounds.w}px; height: {bounds.h}px">
  <ShapePopover
    {model} {anchor} {bounds}
    on:change={(e) => onEvent("change", e.detail)}
    on:action={(e) => onEvent("action", e.detail)}
    on:close={() => onEvent("close", null)}
  />
</div>
