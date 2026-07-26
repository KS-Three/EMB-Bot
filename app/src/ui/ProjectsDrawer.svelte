<script>
  // Slice 7 Task 2 — "My designs" drawer. Purely presentational: it takes a
  // `projects` snapshot (already sorted newest-first by App, via
  // listProjects()) and the current project's id, and emits events for
  // every action -- App owns all the actual registry calls (see App.svelte's
  // openProject/newDesign/renameFromDrawer/duplicateFromDrawer/
  // deleteFromDrawer).
  import { createEventDispatcher } from "svelte";
  export let projects = [];
  export let currentId = null;
  const d = createEventDispatcher();

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
  <div class="drawer" role="dialog" aria-modal="true" aria-label="My designs">
    <div class="drawer-head">
      <h2>My designs</h2>
      <button type="button" class="drawer-close" on:click={() => d("close")} aria-label="Close">✕</button>
    </div>

    <button type="button" class="drawer-new" on:click={() => d("new")}>+ New design</button>

    <div class="drawer-list">
      {#each projects as row (row.id)}
        <div class="drawer-row" class:current={row.id === currentId}>
          {#if renamingId === row.id}
            <div class="drawer-rename-row">
              <input
                type="text"
                bind:value={renameValue}
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
          {/if}
          <div class="drawer-row-actions">
            <button type="button" on:click={() => d("open", row.id)}>Open</button>
            <button type="button" on:click={() => startRename(row.id, row.name)}>Rename</button>
            <button type="button" on:click={() => d("duplicate", row.id)}>Duplicate</button>
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
      {/if}
    </div>
  </div>
</div>
