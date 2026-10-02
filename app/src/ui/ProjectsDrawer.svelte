<script>
  // Slice 7 Task 2 — "My designs" drawer. Purely presentational: it takes a
  // `projects` snapshot (already sorted newest-first by App, via
  // listProjects()) and the current project's id, and emits events for
  // every action -- App owns all the actual registry calls (see App.svelte's
  // openProject/newDesign/renameFromDrawer/duplicateFromDrawer/
  // deleteFromDrawer).
  import { createEventDispatcher, onMount } from "svelte";
  import Icon from "./Icon.svelte";
  import TemplateRow from "./TemplateRow.svelte";
  import DesignFilter from "./DesignFilter.svelte";
  import { EMB } from "../lib/emb.js";
  import { filterProjects, hasFactCriteria, factsLine } from "../lib/libraryFacts.js";
  export let projects = [];
  export let currentId = null;
  // One-line status/error from App's .embproj import handling ("" hides it).
  // Presentational like everything else here: App owns the actual file
  // parsing/registry calls and just feeds the outcome back down.
  export let notice = "";
  const d = createEventDispatcher();

  // ---- Filter: find a design by what it is ---------------------------------
  // Runs over the index entries the drawer already has: each carries `facts`
  // (stitches, spools, size) once its design has been generated, so nothing
  // is loaded to filter. An entry saved before facts existed has none until
  // it is next opened; under a stitch/color/hoop filter those are left out
  // and COUNTED below the list, never passed off as non-matches. The hoop
  // table and fit rule are the engine's own (src/garments.js).
  //
  // The controls only show with two or more saved designs, and `criteria`
  // outlives them: deleting down to one design unmounts DesignFilter with its
  // last value still bound here. So the filter applies only while its controls
  // are on screen — otherwise the one design left stays hidden behind a filter
  // nobody can see or clear.
  const hoops = EMB.HOOPS || [];
  let criteria = {};
  $: canFilter = projects.length > 1;
  $: filtered = filterProjects(projects, canFilter ? criteria : {}, EMB.hoopFit);
  $: filtering = hasFactCriteria(criteria) || !!(criteria.text && criteria.text.trim());

  // ---- .embproj import (hidden file input) ---------------------------------
  // The drawer only picks the file; App does the reading/parsing (same
  // separation as every other drawer action). Clearing .value after each
  // pick lets the user re-select the same file after a failed attempt —
  // without it the input's change event never re-fires for an unchanged
  // path.
  let fileInput;

  function onFilePicked(e) {
    const file = e.currentTarget.files && e.currentTarget.files[0];
    e.currentTarget.value = "";
    if (file) d("importfile", file);
  }

  // ---- Focus handling (A11Y/UX finding 5) ----------------------------------
  // The dialog is role="dialog" aria-modal="true", which is a lie unless
  // focus actually moves in, stays trapped, and comes back out again. This
  // drawer previously did none of that: opening it left focus wherever it
  // was on the page behind the backdrop, Tab could walk focus straight out
  // of the dialog into that hidden page, and closing it never gave focus
  // back to whatever opened it (that last part is App.svelte's job -- see
  // its myDesignsBtn/drawerWasOpen handling).
  let drawerEl;

  onMount(() => {
    // tabindex="-1" on the drawer div (below) makes it a legal, if unusual,
    // focus target: programmatically focusable via .focus() but skipped by
    // normal Tab navigation, which is exactly what a dialog's initial focus
    // should be when there's no obviously-more-specific control to land on
    // (e.g. a heading, not the first button, so screen readers announce the
    // dialog before its content).
    if (drawerEl) drawerEl.focus();
  });

  function focusableEls() {
    if (!drawerEl) return [];
    return Array.from(
      drawerEl.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => el.offsetParent !== null); // skip hidden elements
  }

  // Wraps Tab/Shift+Tab between the drawer's first and last focusable
  // elements so focus can never escape to the page behind the backdrop
  // while the dialog is open.
  function onDrawerKeydown(e) {
    if (e.key !== "Tab") return;
    const els = focusableEls();
    if (els.length === 0) return;
    const first = els[0];
    const last = els[els.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first || !drawerEl.contains(document.activeElement)) {
        e.preventDefault();
        last.focus();
      }
    } else if (document.activeElement === last || !drawerEl.contains(document.activeElement)) {
      e.preventDefault();
      first.focus();
    }
  }

  // ---- Autofocus action (A11Y/UX finding 6) --------------------------------
  // Applied to the inline rename <input> (use:autofocus below). Without
  // this the input rendered on "Rename" click but never received focus, so
  // the blur-commit in commitRename() was unreachable by keyboard (nothing
  // to Tab away FROM) and mouse users got a caretless field they had to
  // click a second time just to start typing.
  function autofocus(node) {
    node.focus();
    node.select();
  }

  // ---- Two-tap delete (plan amendment A5) ----------------------------------
  // First click arms a row's Delete button ("Really delete?"). A second
  // click on the SAME row within 300ms is ignored -- that's an accidental
  // double-click firing both halves of the gesture as one, not a deliberate
  // second tap. Any click after that window (but before the 3s auto-disarm)
  // confirms and dispatches "delete". Arming a different row disarms
  // whichever one was previously armed, so at most one row is ever armed.
  let armedId = null;
  let armedAt = 0;
  let disarmTimer = null;

  function onDeleteClick(id) {
    const now = Date.now();
    if (armedId === id) {
      if (now - armedAt < 300) return; // double-click guard
      clearTimeout(disarmTimer);
      armedId = null;
      d("delete", id);
      return;
    }
    armedId = id;
    armedAt = now;
    clearTimeout(disarmTimer);
    disarmTimer = setTimeout(() => {
      armedId = null;
    }, 3000);
  }

  // ---- Inline rename --------------------------------------------------------
  let renamingId = null;
  let renameValue = "";

  function startRename(id, name) {
    renamingId = id;
    renameValue = name;
  }

  function commitRename(id) {
    if (renamingId !== id) return;
    const name = renameValue;
    renamingId = null;
    d("rename", { id, name });
  }

  function onRenameKeydown(e, id) {
    if (e.key === "Enter") {
      e.preventDefault();
      commitRename(id);
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation(); // cancel the rename only -- don't also close the drawer
      renamingId = null;
    }
  }

  // ---- Friendly updatedAt: "today" / "yesterday" / M/D ---------------------
  function friendlyDate(ts) {
    if (!ts) return "";
    const then = new Date(ts);
    const startOfDay = (dt) => new Date(dt.getFullYear(), dt.getMonth(), dt.getDate()).getTime();
    const diffDays = Math.round((startOfDay(new Date()) - startOfDay(then)) / 86400000);
    if (diffDays === 0) return "today";
    if (diffDays === 1) return "yesterday";
    return `${then.getMonth() + 1}/${then.getDate()}`;
  }
</script>

<svelte:window
  on:keydown={(e) => {
    if (e.key === "Escape") d("close");
  }}
/>

<div
  class="drawer-backdrop"
  role="presentation"
  on:click={(e) => {
    if (e.target === e.currentTarget) d("close");
  }}
>
  <div
    class="drawer"
    role="dialog"
    aria-modal="true"
    aria-label="My designs"
    tabindex="-1"
    bind:this={drawerEl}
    on:keydown={onDrawerKeydown}
  >
    <div class="drawer-head">
      <h2>My designs</h2>
      <button type="button" class="drawer-close" on:click={() => d("close")} aria-label="Close"><Icon name="close" size={16} /></button>
    </div>

    <button type="button" class="drawer-new" on:click={() => d("new")}>+ New design</button>
    <button type="button" class="drawer-new" on:click={() => fileInput && fileInput.click()}>
      Import design file (.embproj)
    </button>
    <input
      type="file"
      accept=".embproj,application/json"
      hidden
      bind:this={fileInput}
      on:change={onFilePicked}
      aria-label="Import design file"
    />
    {#if notice}
      <p class="drawer-notice" role="alert">{notice}</p>
    {/if}

    <div class="drawer-list">
      <!-- Saved designs first, templates after (Kent, 2026-10-01): with the
           three template cards on top the filter sat ~700px down the list,
           below the fold on a laptop and on a phone. -->
      {#if canFilter}
        <DesignFilter {hoops} bind:criteria />
        {#if filtering}
          <p class="drawer-count" role="status">
            {filtered.shown.length} of {projects.length} designs
          </p>
        {/if}
      {/if}
      {#each filtered.shown as row (row.id)}
        <div class="drawer-row" class:current={row.id === currentId}>
          {#if renamingId === row.id}
            <div class="drawer-rename-row">
              <input
                type="text"
                bind:value={renameValue}
                use:autofocus
                on:keydown={(e) => onRenameKeydown(e, row.id)}
                on:blur={() => commitRename(row.id)}
                aria-label="Rename project"
              />
            </div>
          {:else}
            <div class="drawer-row-info">
              <span class="drawer-row-name" title={row.name}>{row.name}</span>
              <span class="drawer-row-date">{friendlyDate(row.updatedAt)}</span>
            </div>
            {#if row.facts}
              <p class="drawer-row-facts">{factsLine(row.facts, hoops, EMB.hoopFit)}</p>
            {/if}
          {/if}
          <div class="drawer-row-actions">
            <button type="button" on:click={() => d("open", row.id)}>Open</button>
            <button type="button" on:click={() => startRename(row.id, row.name)}>Rename</button>
            <button type="button" on:click={() => d("duplicate", row.id)}>Duplicate</button>
            <button type="button" on:click={() => d("export", row.id)}>Export</button>
            <button
              type="button"
              class="danger"
              class:armed={armedId === row.id}
              on:click={() => onDeleteClick(row.id)}
            >
              {armedId === row.id ? "Really delete?" : "Delete"}
            </button>
          </div>
        </div>
      {/each}
      {#if projects.length === 0}
        <p class="drawer-empty">No saved designs yet.</p>
      {:else if filtered.shown.length === 0}
        <p class="drawer-empty">No saved design matches.</p>
      {/if}
      {#if filtered.unmeasured > 0}
        <p class="drawer-empty">
          {filtered.unmeasured === 1
            ? "1 design isn't measured yet, so it can't be matched on stitches, colors or hoop."
            : `${filtered.unmeasured} designs aren't measured yet, so they can't be matched on stitches, colors or hoop.`}
          A design is measured when it is opened; an empty one has nothing to measure.
        </p>
      {/if}
      <h3 class="drawer-templates-head">Start from a template</h3>
      <TemplateRow on:pick={(e) => d("template", e.detail)} />
    </div>
  </div>
</div>
