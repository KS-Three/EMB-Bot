<script>
  import { createEventDispatcher } from "svelte";
  import TextStep from "./TextStep.svelte";
  import ImagePanel from "./ImagePanel.svelte";
  import DesignPanel from "./DesignPanel.svelte";
  import DigitizePanel from "./DigitizePanel.svelte";
  import ManualPanel from "./ManualPanel.svelte";
  import SizePanel from "./SizePanel.svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import FontSelect from "./FontSelect.svelte";
  import Hint from "./Hint.svelte";
  import { selectedIdsOf } from "../lib/project.js";
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
  // The digitizer service's /health payload, or null when it's unreachable.
  // App owns the probe (re-run on entering this step and on "checkservice");
  // this component only gates the "+ Auto-digitize" tile and hands the value
  // to DigitizePanel so an offline panel can say so honestly.
  export let digitizerHealth = null;
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

  // Multi-select (Ctrl+click): while 2+ elements are selected the
  // single-element editor gives way to a compact group panel showing only
  // controls that make sense in bulk. Bulk edits dispatch the same
  // "elupdatemany" shape EmbroideryField's group drags use ({ id: patch }),
  // built over the TEXT members only — image/design elements have no
  // colorRgb/fontKey/weight to bulk-set, so they pass through untouched.
  $: selIds = selectedIdsOf(project);
  $: multi = selIds.length > 1;
  $: selMembers = project.elements.filter((e) => selIds.includes(e.id));
  $: selTextMembers = selMembers.filter((e) => e.type === "text");
  $: primaryText = selTextMembers.find((e) => e.id === project.selectedId) || selTextMembers[0];

  // "All text members agree" per bulk-editable field — drives the active /
  // mixed presentation. null = mixed (or no text members).
  function shared(field) {
    if (!selTextMembers.length) return null;
    const v = JSON.stringify(selTextMembers[0][field] ?? null);
    return selTextMembers.every((e) => JSON.stringify(e[field] ?? null) === v)
      ? selTextMembers[0][field]
      : null;
  }
  $: sharedColor = multi ? shared("colorRgb") : null;
  $: sharedWeight = multi ? shared("weightPreset") : null;
  $: sharedFont = multi ? shared("fontKey") : null;

  function bulkPatch(patch) {
    const patchById = {};
    for (const e of selTextMembers) patchById[e.id] = patch;
    if (Object.keys(patchById).length) d("elupdatemany", patchById);
  }

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
    if (element.type === "design") {
      return element.dstBase64 ? `File · ${truncate(element.name || "design.dst", 18)}` : "File · empty";
    }
    if (element.type === "digitized") {
      return element.result ? `Digitized · ${truncate(element.name || "artwork", 18)}` : "Digitized · empty";
    }
    if (element.type === "manual") {
      const n = (element.shapes || []).length;
      return n ? `Shapes · ${n}` : "Shapes · empty";
    }
    const n = element.nColors || 0;
    return element._hasImage ? `Image · ${n} color${n === 1 ? "" : "s"}` : "Image · empty";
  }

  function selectRow(id, e) {
    // Ctrl/Cmd+click toggles membership in the multi-selection, matching
    // the canvas. Plain click collapses to a single selection.
    if (e && (e.ctrlKey || e.metaKey)) d("toggleselect", id);
    else d("select", id);
  }

  function onRowKeydown(e, id) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectRow(id, e);
    }
  }
</script>

<h2>What are you making?</h2>

<div class="ellist">
  {#each project.elements as row (row.id)}
    <div
      class="elrow"
      class:sel={selIds.includes(row.id)}
      role="button"
      tabindex="0"
      on:click={(e) => selectRow(row.id, e)}
      on:keydown={(e) => onRowKeydown(e, row.id)}
    >
      <span class="elicon">
        {#if row.type === "text"}
          T
        {:else if row.type === "design"}
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"
              fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
            <path d="M13 2v7h7" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
          </svg>
        {:else if row.type === "digitized"}
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M20 4L8 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            <path d="M8 16l-4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="1 3" />
            <circle cx="20" cy="4" r="1.6" fill="currentColor" />
            <path d="M5 5l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" fill="currentColor" />
          </svg>
        {:else if row.type === "manual"}
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M4 18 L9 6 L18 10 L14 20 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
            <circle cx="4" cy="18" r="1.6" fill="currentColor" />
            <circle cx="9" cy="6" r="1.6" fill="currentColor" />
            <circle cx="18" cy="10" r="1.6" fill="currentColor" />
            <circle cx="14" cy="20" r="1.6" fill="currentColor" />
          </svg>
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
  <button type="button" class="eladd" on:click={() => d("addelement", "design")}>+ Design file</button>
  <button type="button" class="eladd" on:click={() => d("addelement", "manual")}>+ Draw shapes</button>
  {#if digitizerHealth}
    <button type="button" class="eladd" on:click={() => d("addelement", "digitized")}>+ Auto-digitize</button>
  {/if}
</div>
{#if !digitizerHealth}
  <p class="digitize-offline">
    Auto-digitize (art in, stitches out) needs the local digitizer service.
    Start it, then
    <button type="button" class="digitize-recheck" on:click={() => d("checkservice")}>check again</button>.
  </p>
{/if}

<!-- Keyed on the selected element's id so switching selection (even between
     two elements of the SAME type, e.g. two image elements) always remounts
     a fresh TextStep/ImagePanel instance -- otherwise per-instance local
     state (ImagePanel's merge-selection, its prevNColors/prevRemoveBg
     re-flatten guard, ...) would leak from whichever element was selected
     before onto the newly-selected one. -->
{#if multi}
  <div class="groupsel">
    <h3>{selIds.length} selected</h3>
    <p class="groupsel-hint">
      Drag on the field to move together — corners resize the group.
      {#if selTextMembers.length < selMembers.length}
        Controls below apply to the {selTextMembers.length} text element{selTextMembers.length === 1 ? "" : "s"} only.
      {/if}
    </p>
    {#if selTextMembers.length}
      <div class="groupsel-row">
        <span class="groupsel-label">Color{sharedColor ? "" : " · mixed"}</span>
        <ThreadPicker rgb={sharedColor || (primaryText && primaryText.colorRgb) || [20, 20, 20]} compact on:pick={(e) => bulkPatch({ colorRgb: e.detail })} />
      </div>
      <div class="groupsel-row">
        <span class="groupsel-label">Weight{sharedWeight ? "" : " · mixed"}</span>
        <div class="groupsel-btns">
          {#each ["thin", "normal", "bold"] as w}
            <button
              type="button"
              class="groupsel-btn"
              class:active={sharedWeight === w}
              on:click={() => bulkPatch({ weightPreset: w })}
            >{w[0].toUpperCase() + w.slice(1)}</button>
          {/each}
        </div>
      </div>
      <div class="groupsel-row">
        <span class="groupsel-label">Font{sharedFont ? "" : " · mixed"}</span>
        <FontSelect
          selected={sharedFont || (primaryText && primaryText.fontKey)}
          currentText={(primaryText && primaryText.text) || ""}
          on:pick={(e) => bulkPatch({ fontKey: e.detail })}
        />
      </div>
    {/if}
  </div>
{:else}
  {#key el.id}
    {#if el.type === "design"}
      <DesignPanel element={el} on:elupdate={(e) => d("elupdate", e.detail)} />
    {:else if el.type === "digitized"}
      <DigitizePanel
        element={el}
        {project}
        health={digitizerHealth}
        on:elupdate={(e) => d("elupdate", e.detail)}
        on:checkservice={() => d("checkservice")}
        on:converttotext={(e) => d("converttotext", e.detail)}
        on:removeelement={(e) => d("removeelement", e.detail)}
      />
    {:else if el.type === "image"}
      <ImagePanel
        element={el}
        {workImage}
        {flat}
        on:elupdate={(e) => d("elupdate", e.detail)}
        on:image={(e) => d("image", e.detail)}
        on:flat={(e) => d("flat", e.detail)}
      />
    {:else if el.type === "manual"}
      <ManualPanel element={el} on:elupdate={(e) => d("elupdate", e.detail)} />
    {:else}
      <TextStep element={el} on:elupdate={(e) => d("elupdate", e.detail)} />
    {/if}
  {/key}

  <SizePanel project={{ ...project, ...el }} {designDims} on:update={(e) => d("elupdate", { id: el.id, patch: e.detail })} />
{/if}

<style>
  .digitize-offline {
    font-size: var(--fs-xs, 12px);
    color: var(--muted, #667);
    margin: 6px 0 0;
  }
  .digitize-recheck {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent, #4f46e5);
    cursor: pointer;
    font-size: inherit;
    text-decoration: underline;
  }
  .groupsel { margin-top: var(--space-4, 12px); }
  .groupsel h3 { margin-bottom: var(--space-2, 6px); }
  .groupsel-hint { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 0 0 10px; }
  .groupsel-row { margin-top: 10px; }
  .groupsel-label { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
  .groupsel-btns { display: flex; gap: 6px; }
  .groupsel-btn {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .groupsel-btn.active {
    background: var(--accent, #4f46e5);
    color: #fff;
    border-color: var(--accent, #4f46e5);
  }
</style>
