<script>
  import { createEventDispatcher } from "svelte";
  import TextStep from "./TextStep.svelte";
  import ImagePanel from "./ImagePanel.svelte";
  import SizePanel from "./SizePanel.svelte";
  import Hint from "./Hint.svelte";
  export let project;
  // Whether the "add-elements" onboarding hint should render right now --
  // App computes this (shouldShow("add-elements") + the A7 priority rule +
  // the elements.length < 2 eligibility condition) and also owns the
  // permanent auto-dismiss once a second element gets added (see App.svelte).
  export let showAddElementsHint = false;
  // Passed straight through to ImagePanel; owned by App so image state
  // survives this component (and ImagePanel) being torn down and recreated.
  export let workImage = null;
  export let flat = null;
  // Dims of the last generated design, owned by App (from EmbroideryField's
  // "dims" event) -- passed straight through to SizePanel.
  export let designDims = null;
  const d = createEventDispatcher();

  // ---- Task 5 (Slice 5): the real element manager --------------------------
  // Replaces the Task 4 compile-compat adapter (mode tiles + a flattened
  // v1-shaped "view project") with the real thing: a compact list of every
  // element in the project (click a row to select it, ✕ to remove it),
  // "+ Text" / "+ Image" to add more, and below that the SELECTED element's
  // own editor (TextStep or ImagePanel, both element-scoped now) plus the
  // size panel.
  //
  // Patch convention (see TextStep.svelte / ImagePanel.svelte for the same
  // note): both dispatch "elupdate" events already shaped { id, patch } --
  // this component just bubbles those straight through to App unchanged.
  // SizePanel is the one child that ISN'T element-scoped (out of scope for
  // this task -- it still speaks a plain "update" patch against a
  // project-shaped view object) so it gets wrapped into the same shape here.
  $: el = project.elements.find((e) => e.id === project.selectedId) || project.elements[0];

  function truncate(s, n) {
    return s.length > n ? s.slice(0, n) + "…" : s;
  }

  // One-line summary shown in an element's list row: quoted truncated text
  // for text elements, color count (or "empty") for image elements.
  function summarize(element) {
    if (element.type === "text") {
      const t = (element.text || "").trim();
      return t ? `"${truncate(t, 18)}"` : "Text · empty";
    }
    const n = element.nColors || 0;
    return element._hasImage ? `Image · ${n} color${n === 1 ? "" : "s"}` : "Image · empty";
  }

  function selectRow(id) {
    d("select", id);
  }

  function onRowKeydown(e, id) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectRow(id);
    }
  }
</script>

<h2>What are you making?</h2>

<div class="ellist">
  {#each project.elements as row (row.id)}
    <div
      class="elrow"
      class:sel={row.id === project.selectedId}
      role="button"
      tabindex="0"
      on:click={() => selectRow(row.id)}
      on:keydown={(e) => onRowKeydown(e, row.id)}
    >
      <span class="elicon">
        {#if row.type === "text"}
          T
        {:else}
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <rect x="2" y="4" width="20" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="2" />
            <circle cx="8" cy="10" r="1.6" fill="currentColor" />
            <path
              d="M3 17l5-5 4 4 3-3 6 6"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        {/if}
      </span>
      <span class="elsummary">{summarize(row)}</span>
      <button
        type="button"
        class="elrow-x"
        disabled={project.elements.length <= 1}
        title="Remove"
        aria-label="Remove element"
        on:click|stopPropagation={() => d("removeelement", row.id)}
      >
        ✕
      </button>
    </div>
  {/each}
</div>

{#if showAddElementsHint}
  <Hint on:dismiss={() => d("dismisshint")}>Combine text and a logo in one design.</Hint>
{/if}
<div class="eladd-row">
  <button type="button" class="eladd" on:click={() => d("addelement", "text")}>+ Text</button>
  <button type="button" class="eladd" on:click={() => d("addelement", "image")}>+ Image</button>
</div>

<!-- Keyed on the selected element's id so switching selection (even between
     two elements of the SAME type, e.g. two image elements) always remounts
     a fresh TextStep/ImagePanel instance -- otherwise per-instance local
     state (ImagePanel's merge-selection, its prevNColors/prevRemoveBg
     re-flatten guard, ...) would leak from whichever element was selected
     before onto the newly-selected one. -->
{#key el.id}
  {#if el.type === "image"}
    <ImagePanel
      element={el}
      {workImage}
      {flat}
      on:elupdate={(e) => d("elupdate", e.detail)}
      on:image={(e) => d("image", e.detail)}
      on:flat={(e) => d("flat", e.detail)}
    />
  {:else}
    <TextStep element={el} on:elupdate={(e) => d("elupdate", e.detail)} />
  {/if}
{/key}

<SizePanel project={{ ...project, ...el }} {designDims} on:update={(e) => d("elupdate", { id: el.id, patch: e.detail })} />
