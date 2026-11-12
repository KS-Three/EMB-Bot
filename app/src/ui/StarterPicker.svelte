<script>
  // The starter design picker (PRODUCT.md launch item 3): the pack's twelve
  // designs as cards -- the art itself as the thumbnail, the manifest's title,
  // and the art's provenance line with a link to its source page. Picking a
  // card fetches that design's .dst and dispatches "pick" with the element
  // patch; App adds it to the open project (lib/starterPack.js).
  //
  // Static files only: nothing here needs the digitizer service.
  //
  // No grade, score or finding is shown on a card, on purpose (Kent's ruling;
  // see lib/starterPack.js).
  //
  // Dialog mechanics as FontCredits.svelte: role=dialog aria-modal, focus
  // moves in on mount, Tab is trapped, Escape closes. Focus RESTORE is the
  // opener's job (App.svelte).
  import { createEventDispatcher, onMount } from "svelte";
  import { loadStarterPack, loadStarterPatch } from "../lib/starterPack.js";
  import Icon from "./Icon.svelte";

  const d = createEventDispatcher();

  let designs = [];
  let packFailed = false;
  loadStarterPack()
    .then((list) => { designs = list; })
    .catch(() => { packFailed = true; });

  // The card being fetched (its id), and the one whose fetch failed.
  let loadingId = null;
  let failedId = null;

  async function pick(design) {
    if (loadingId) return;
    loadingId = design.id;
    failedId = null;
    try {
      d("pick", await loadStarterPatch(design));
    } catch (e) {
      failedId = design.id;
    } finally {
      loadingId = null;
    }
  }

  let panelEl;
  onMount(() => {
    if (panelEl) panelEl.focus();
  });

  function focusableEls() {
    if (!panelEl) return [];
    return Array.from(
      panelEl.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter((el) => el.offsetParent !== null);
  }

  function onPanelKeydown(e) {
    if (e.key === "Escape") {
      d("close");
      return;
    }
    if (e.key !== "Tab") return;
    const els = focusableEls();
    if (els.length === 0) return;
    const first = els[0];
    const last = els[els.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first || !panelEl.contains(document.activeElement)) {
        e.preventDefault();
        last.focus();
      }
    } else if (document.activeElement === last || !panelEl.contains(document.activeElement)) {
      e.preventDefault();
      first.focus();
    }
  }
</script>

<div
  class="sp-backdrop"
  role="presentation"
  on:click={(e) => {
    if (e.target === e.currentTarget) d("close");
  }}
>
  <div
    class="sp-panel"
    role="dialog"
    aria-modal="true"
    aria-label="Starter designs"
    tabindex="-1"
    bind:this={panelEl}
    on:keydown={onPanelKeydown}
  >
    <div class="sp-head">
      <h2>Starter designs</h2>
      <button type="button" class="sp-close" on:click={() => d("close")} aria-label="Close"><Icon name="close" size={16} /></button>
    </div>

    <!-- Says only what the manifest records. Not "ready to sew": the pack has
         had stitch-file checks, not a sew-out (ROADMAP gate 1). -->
    <p class="sp-note">
      Pick one to add it to your design. The artwork is CC0 or public domain; each card names
      its artist and links to its source.
    </p>

    <div class="sp-body">
      {#if packFailed}
        <p class="sp-empty">Couldn't load the starter designs. Close this and try again.</p>
      {:else if designs.length === 0}
        <p class="sp-empty">Loading…</p>
      {:else}
        <ul class="sp-grid">
          {#each designs as design (design.id)}
            <li class="sp-card" data-starter={design.id}>
              <button
                type="button"
                class="sp-pick"
                aria-label={"Add " + design.title}
                aria-busy={loadingId === design.id}
                disabled={!!loadingId}
                on:click={() => pick(design)}
              >
                <span class="sp-thumb"><img src={design.artUrl} alt="" loading="lazy" /></span>
                <span class="sp-title">{design.title}</span>
              </button>
              <small class="sp-credit">
                {design.credit} ·
                <a href={design.sourceUrl} target="_blank" rel="noopener" aria-label={"Source of " + design.title}>source</a>
              </small>
              {#if failedId === design.id}
                <small class="sp-failed" role="status">Couldn't load this one. Try again.</small>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
</div>

<style>
  .sp-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--overlay);
    padding: var(--space-5);
  }

  .sp-panel {
    width: min(760px, 100%);
    max-height: min(760px, 90vh);
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border-radius: var(--radius-l);
    box-shadow: var(--shadow-2);
  }

  .sp-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--border);
  }
  .sp-head h2 { margin: 0; font-size: var(--fs-lg); }

  .sp-close {
    width: 32px;
    height: 32px;
    min-height: 0;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: var(--radius-s);
    background: var(--surface);
    color: var(--muted);
    cursor: pointer;
  }
  .sp-close:hover { border-color: var(--ink); color: var(--ink); }

  .sp-note {
    margin: 0;
    padding: var(--space-4) var(--space-5) 0;
    color: var(--muted);
    font-size: var(--fs-sm);
  }

  .sp-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: var(--space-4) var(--space-5) var(--space-5);
  }

  .sp-empty { color: var(--muted); font-size: var(--fs-md); text-align: center; margin: var(--space-6) 0; }

  .sp-grid {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: var(--space-4);
  }

  .sp-card { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }

  .sp-pick {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-m);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    font-size: var(--fs-md);
    font-weight: var(--fw-medium);
    text-align: left;
    cursor: pointer;
  }
  .sp-pick:hover:not(:disabled) { border-color: var(--accent); }
  .sp-pick:disabled { cursor: progress; }
  .sp-pick[aria-busy="true"] { border-color: var(--accent); background: var(--tint); }

  /* The art sits on the workspace neutral, not white: the pack has a white
     baseball and a black jack-o'-lantern, and both have to read. */
  .sp-thumb {
    display: block;
    height: 120px;
    padding: var(--space-2);
    border-radius: var(--radius-s);
    background: var(--field-bg);
  }
  /* Sized by the box, not by the file: the pack's SVGs range from 48 px
     icons to a tall leaf, and every card has to be the same height. */
  .sp-thumb img { display: block; width: 100%; height: 100%; object-fit: contain; }

  .sp-credit { color: var(--muted); font-size: var(--fs-xs); overflow-wrap: anywhere; }
  .sp-credit a { color: inherit; }
  .sp-failed { color: var(--ink); font-size: var(--fs-xs); }
</style>
