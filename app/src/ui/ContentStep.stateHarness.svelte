<script>
  import ContentStep from "./ContentStep.svelte";

  // Test-only wrapper (ContentStep.preRunWidth.spec.js) — never imported by the
  // app. Unlike ContentStep.testHarness.svelte it APPLIES each element patch
  // to `project`, the shallow merge App's elUpdate does, so a width typed in
  // the Size panel reaches the next run the way it does in the Studio.
  export let project;
  export let digitizerHealth = null;
  export let onElUpdate = () => {};

  function apply(d) {
    project = {
      ...project,
      elements: project.elements.map((e) => (e.id === d.id ? { ...e, ...d.patch } : e)),
    };
    onElUpdate(d);
  }
</script>

<ContentStep {project} {digitizerHealth} on:elupdate={(e) => apply(e.detail)} />
