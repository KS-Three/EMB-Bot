<script>
  import ContentStep from "./ContentStep.svelte";

  // Test-only wrapper (see ContentStep.projectSwitch.spec.js) — never
  // imported by the app. Svelte 5 does not expose a mounted instance's
  // component events to `$on`, so a real parent listens with `on:elupdate`
  // and hands each detail ({ id, patch, projectId? }) to `onElUpdate` — the
  // shape App's elUpdate receives. `projectId` stands in for App's
  // `currentId`; switching it with `project` is App.enterProject. ImagePanel's
  // id-less "image"/"flat" events go to `onImage`/`onFlat`, which App applies
  // to whatever element is selected when they arrive.
  export let project;
  export let projectId = null;
  export let digitizerHealth = null;
  export let onElUpdate = () => {};
  export let onImage = () => {};
  export let onFlat = () => {};
</script>

<ContentStep
  {project}
  {projectId}
  {digitizerHealth}
  on:elupdate={(e) => onElUpdate(e.detail)}
  on:image={(e) => onImage(e.detail)}
  on:flat={(e) => onFlat(e.detail)}
/>
