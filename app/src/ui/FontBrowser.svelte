<script>
  // Font picker dialog (Slice 10B Task 4) -- replaces the old dropdown whose
  // thumbnail queue fetched every font binary (~30MB) the moment it opened
  // (Slice 8 Task 3's fetch-everything-eagerly helpers, now deleted). This
  // grid renders from the manifest + pre-rendered static PNGs (Slice 10B
  // Task 3, /fonts/previews/<key>.png) and NEVER fetches a font binary just
  // to show the grid.
  // ensureFont is only ever called for (a) the font the user actually picks,
  // and (b) FontSelect's own trigger preview of the current selection --
  // both outside this component. Live "your text" tiles below render ONLY
  // for fonts already decoded into EMB.SATIN_FONTS by some other path (e.g.
  // already the selected font); every other tile shows its static PNG.
  //
  // Dialog mechanics copied from ProjectsDrawer.svelte: role=dialog
  // aria-modal, tabindex="-1" focus-on-mount, Tab trap via focusableEls(),
  // Escape closes. Focus RESTORE is the opener's job (FontSelect owns the
  // trigger button here, same division of labor ProjectsDrawer uses with
  // App.svelte).
  import { createEventDispatcher, onMount } from "svelte";
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { loadManifest, ensureFont } from "../lib/fontLoader.js";
  import { filterFonts, sizeBand } from "../lib/fontFilter.js";

  export let selected = null;
  export let currentText = "";
  // Approximate "how big is this element right now" signal used only for the
  // non-blocking "sized outside this font's best range" note. TextStep does
  // not have the element's actual rendered stitch-out height handy here, so
  // this is the user-set target size (element.sizeMm), not a measured
  // height -- an approximation, not a promise. null disables the note.
  export let currentHeightMm = null;
  const d = createEventDispatcher();

  const GROUPS = ["All", "Sans", "Serif", "Script", "Display", "Small", "More"];
  let fonts = [];
  let query = "";
  let group = "All";
  let manifestFailed = false;
  loadManifest().then((m) => { fonts = m.fonts; }).catch(() => { manifestFailed = true; });

  $: shown = filterFonts(fonts, query, group);

  // Live "your text" tile rendering -- ONLY for fonts already decoded. The
  // grid must never trigger binary fetches (that was Stage A's 30MB
  // dropdown problem); static preview PNGs carry undecoded fonts.
  let liveThumbs = {};
  $: renderLive(shown, currentText);
  function renderLive(list, text) {
    const t = (text || "").trim().slice(0, 12);
    if (!t) { liveThumbs = {}; return; }
    const next = {};
    for (const f of list) {
      const font = (EMB.SATIN_FONTS || {})[f.key];
      if (!font) continue;
      try {
        const c = document.createElement("canvas");
        c.width = 360; c.height = 56;
        const design = EMB.buildLetteringDesign(font, t, {
          garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5, underlay: false,
        });
        renderRealistic(c, design, { colorOverride: [45, 45, 50], fabric: "#ffffff", pad: 8 });
        next[f.key] = c.toDataURL();
      } catch (e) { /* fall back to the static PNG */ }
    }
    liveThumbs = next;
  }

  function bestAt(f) {
    const band = sizeBand(f.sizeMm);
    if (!band) return "";
    return `best at ${band.min}–${band.max} mm`;
  }

  function outsideBand(f) {
    if (currentHeightMm == null) return false;
    const band = sizeBand(f.sizeMm);
    if (!band) return false;
    return currentHeightMm < band.min || currentHeightMm > band.max;
  }

  async function pick(key) {
    try { await ensureFont(key); } catch (e) { /* generate paths surface errors */ }
    d("pick", key);
    d("close");
  }

  // ---- Dialog mechanics (ProjectsDrawer pattern) ---------------------------
  let panelEl;

  onMount(() => {
    if (panelEl) panelEl.focus();
  });

  function focusableEls() {
    if (!panelEl) return [];
    return Array.from(
      panelEl.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
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
  class="fb-backdrop"
  role="presentation"
  on:click={(e) => {
    if (e.target === e.currentTarget) d("close");
  }}
>
  <div
    class="fb-panel"
    role="dialog"
    aria-modal="true"
    aria-label="Choose a font"
    tabindex="-1"
    bind:this={panelEl}
    on:keydown={onPanelKeydown}
  >
    <div class="fb-head">
      <h2>Choose a font</h2>
      <button type="button" class="fb-close" on:click={() => d("close")} aria-label="Close">✕</button>
    </div>

    <div class="fb-controls">
      <label class="fb-search">
        <span class="fb-search-label">Find a font</span>
        <input type="text" bind:value={query} placeholder="Search by name…" autocomplete="off" />
      </label>
      <div class="fb-groups">
        {#each GROUPS as g}
          <button
            type="button"
            class="fb-chip"
            class:active={group === g}
            on:click={() => (group = g)}
          >{g}</button>
        {/each}
      </div>
    </div>

    <div class="fb-body">
      {#if manifestFailed}
        <p class="fb-empty">Couldn't load the font list — check your connection and reopen.</p>
      {:else if shown.length === 0}
        <p class="fb-empty">No fonts match "{query}".</p>
      {:else}
        <div class="fb-grid">
          {#each shown as f (f.key)}
            <button
              type="button"
              class="fb-tile"
              class:sel={f.key === selected}
              on:click={() => pick(f.key)}
            >
              <span class="fb-tile-img">
                <img
                  src={liveThumbs[f.key] || "/fonts/previews/" + f.key + ".png"}
                  alt={f.name}
                  loading="lazy"
                />
              </span>
              <span class="fb-tile-name">{f.name}</span>
              {#if bestAt(f)}
                <span class="fb-tile-band">{bestAt(f)}</span>
              {/if}
              {#if f.key === selected && outsideBand(f)}
                <span class="fb-tile-warn">sized outside this font's best range</span>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .fb-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--overlay);
    padding: var(--space-5);
  }

  .fb-panel {
    width: min(880px, 100%);
    max-height: min(720px, 90vh);
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border-radius: var(--radius-l);
    box-shadow: var(--shadow-2);
  }

  .fb-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--border);
  }

  .fb-head h2 { margin: 0; font-size: var(--fs-lg); }

  .fb-close {
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
  .fb-close:hover { border-color: var(--accent); color: var(--accent); }

  .fb-controls {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--border);
  }

  .fb-search { display: flex; flex-direction: column; gap: var(--space-1); }
  .fb-search-label { font-size: var(--fs-sm); color: var(--muted); }
  .fb-search input {
    width: 100%;
    padding: var(--space-2) var(--space-3);
    border: 2px solid var(--border);
    border-radius: var(--radius-s);
    font: inherit;
  }
  .fb-search input:focus { border-color: var(--accent); }

  .fb-groups { display: flex; flex-wrap: wrap; gap: var(--space-2); }

  .fb-chip {
    padding: var(--space-1) var(--space-3);
    min-height: 32px;
    border: 2px solid var(--border);
    border-radius: var(--radius-full);
    background: var(--surface);
    color: var(--ink);
    font-size: var(--fs-sm);
    cursor: pointer;
  }
  .fb-chip:hover { border-color: var(--accent); }
  .fb-chip.active { border-color: var(--accent); background: var(--tint); color: var(--accent); }

  .fb-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: var(--space-5);
  }

  .fb-empty { color: var(--muted); font-size: var(--fs-md); text-align: center; margin: var(--space-6) 0; }

  .fb-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: var(--gap);
  }

  .fb-tile {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-1);
    padding: var(--space-3);
    border: 2px solid var(--border);
    border-radius: var(--radius-m);
    background: var(--surface);
    text-align: left;
    cursor: pointer;
  }
  .fb-tile:hover { border-color: var(--accent); }
  .fb-tile.sel { border-color: var(--accent); background: var(--tint); }

  .fb-tile-img {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 48px;
    border-radius: var(--radius-s);
    background: var(--bg);
    overflow: hidden;
  }
  .fb-tile-img img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }

  .fb-tile-name { font-size: var(--fs-sm); font-weight: 600; color: var(--ink); }
  .fb-tile-band { font-size: var(--fs-xs); color: var(--muted); }
  .fb-tile-warn { font-size: var(--fs-xs); color: var(--warn); }
</style>
