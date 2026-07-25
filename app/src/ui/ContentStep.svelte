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

  // ---- Task 4 (Slice 5) compile-compat adapter -----------------------------
  // TextStep/ImagePanel/SizePanel below are still v1-shaped: they read/write
  // top-level project fields (project.mode, project.text, project.fontKey,
  // project.nColors, project.sizeMm, ...) that the v2 model moved onto
  // project.elements[i]. Reworking those three components into real
  // per-element editors is Task 5's job, not this one — so instead of
  // touching their internals, we adapt right here: flatten the SELECTED
  // element's fields onto a project-shaped view object for them to read,
  // and route their "update" patches back onto that same element via a new
  // "elupdate" event (App: updateElement(project, id, patch)). This is a
  // stand-in for real multi-element editing (it only ever edits ONE
  // element, whichever is selected) — just enough to keep the build and
  // runtime working without crashing.
  $: el = project.elements.find((e) => e.id === project.selectedId) || project.elements[0];
  $: viewProject = { ...project, ...el, mode: el.type };

  function onChildUpdate(patch) {
    // The Text/Logo tiles below dispatch a `{ mode }` patch to switch which
    // panel is shown. In v2, an element's type is fixed at creation (there's
    // no "change this element's type" op in project.js — only addElement()
    // for a NEW element) so `mode` isn't a real element field. Forward it
    // through as a plain top-level project patch (harmless/inert — Task 5
    // owns rebuilding this tile-switcher for real multi-element add/select)
    // rather than routing it onto the element like every other patch here.
    if ("mode" in patch) {
      d("update", patch);
      return;
    }
    d("elupdate", { id: el.id, patch });
  }
</script>

<h2>What are you making?</h2>
<div class="tiles">
  <button class="tile" class:sel={el.type === "text"} on:click={() => onChildUpdate({ mode: "text" })}>
    Text
  </button>
  <button class="tile" class:sel={el.type === "image"} on:click={() => onChildUpdate({ mode: "image" })}>
    Logo or image
  </button>
</div>

{#if el.type === "image"}
  <ImagePanel
    project={viewProject}
    {workImage}
    {flat}
    on:update={(e) => onChildUpdate(e.detail)}
    on:image={(e) => d("image", e.detail)}
    on:flat={(e) => d("flat", e.detail)}
  />
{:else}
  <TextStep project={viewProject} on:update={(e) => onChildUpdate(e.detail)} />
{/if}

<SizePanel project={viewProject} {designDims} on:update={(e) => onChildUpdate(e.detail)} />
