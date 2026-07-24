<script>
  import { createEventDispatcher } from "svelte";
  import TextStep from "./TextStep.svelte";
  import ImagePanel from "./ImagePanel.svelte";
  import SizePanel from "./SizePanel.svelte";
  export let project;
  // Passed straight through to ImagePanel; owned by App so image state
  // survives this component (and ImagePanel) being torn down and recreated.
  export let workImage = null;
  export let flat = null;
  // Dims of the last generated design, owned by App (from EmbroideryField's
  // "dims" event) -- passed straight through to SizePanel.
  export let designDims = null;
  const d = createEventDispatcher();
</script>

<h2>What are you making?</h2>
<div class="tiles">
  <button class="tile" class:sel={project.mode === "text"} on:click={() => d("update", { mode: "text" })}>
    Text
  </button>
  <button class="tile" class:sel={project.mode === "image"} on:click={() => d("update", { mode: "image" })}>
    Logo or image
  </button>
</div>

{#if project.mode === "image"}
  <ImagePanel
    {project}
    {workImage}
    {flat}
    on:update={(e) => d("update", e.detail)}
    on:image={(e) => d("image", e.detail)}
    on:flat={(e) => d("flat", e.detail)}
  />
{:else}
  <TextStep {project} on:update={(e) => d("update", e.detail)} />
{/if}

<SizePanel {project} {designDims} on:update={(e) => d("update", e.detail)} />
