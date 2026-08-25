<script>
  // Font credits dialog (Slice 10B Task 5) -- required reading for the 69
  // open-source fonts the Studio ships under OFL/CC licenses. Every row is
  // GENERATED from the manifest via creditLines() (lib/credits.js); nothing
  // here is hand-maintained, so a manifest update (new font, license fix)
  // shows up automatically next time this dialog opens.
  //
  // Dialog mechanics copied from ProjectsDrawer.svelte / FontBrowser.svelte:
  // role=dialog aria-modal, tabindex="-1" focus-on-mount, Tab trap via
  // focusableEls(), Escape closes. Focus RESTORE is the opener's job
  // (App.svelte owns the "Font credits" trigger button, same division of
  // labor FontBrowser uses with FontSelect).
  import { createEventDispatcher, onMount } from "svelte";
  import { loadManifest } from "../lib/fontLoader.js";
  import { creditLines } from "../lib/credits.js";
  import Icon from "./Icon.svelte";

  const d = createEventDispatcher();

  let lines = [];
  let manifestFailed = false;
  loadManifest()
    .then((m) => { lines = creditLines(m.fonts); })
    .catch(() => { manifestFailed = true; });

  // ---- Dialog mechanics (ProjectsDrawer/FontBrowser pattern) ---------------
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
  class="fc-backdrop"
  role="presentation"
  on:click={(e) => {
    if (e.target === e.currentTarget) d("close");
  }}
>
  <div
    class="fc-panel"
    role="dialog"
    aria-modal="true"
    aria-label="Font licenses & credits"
    tabindex="-1"
    bind:this={panelEl}
    on:keydown={onPanelKeydown}
  >
    <div class="fc-head">
      <h2>Font licenses &amp; credits</h2>
      <button type="button" class="fc-close" on:click={() => d("close")} aria-label="Close"><Icon name="close" size={16} /></button>
    </div>

    <p class="fc-note">
      Fonts adapted from the Ink/Stitch open embroidery font collection
      (<a href="https://github.com/inkstitch/embroidery-fonts" target="_blank" rel="noopener">github.com/inkstitch/embroidery-fonts</a>),
      modified for EMB-Bot: adapted for machine embroidery and compiled to the .embf binary format.
      Each font's full license text and copyright notice ship with this app ("license" link per font)
      and are embedded in the font binary itself.
    </p>

    <div class="fc-body">
      {#if manifestFailed}
        <p class="fc-empty">Couldn't load font data</p>
      {:else if lines.length === 0}
        <p class="fc-empty">Loading…</p>
      {:else}
        <ul class="fc-list">
          {#each lines as line (line.binHref)}
            <li class="fc-row">
              <strong class="fc-name">{line.name}</strong>
              {#if line.licenseId}
                <!-- "SEE-LICENSE-FILE" is an internal sentinel for one
                     grandfathered font whose license is an ad-hoc grant, not
                     a standard id — show readable text, not the token. -->
                <span class="fc-license">{line.licenseId === "SEE-LICENSE-FILE" ? "See license file" : line.licenseId}</span>
              {/if}
              {#if line.attribution}
                <small class="fc-attribution">{line.attribution}</small>
              {/if}
              {#if line.source}
                <small class="fc-source">{line.source}</small>
              {/if}
              <!-- Full license text is REQUIRED reading distance from the
                   credit (OFL condition 2 / CC notice duties) — link the
                   local stand-alone copy, not the upstream repo. -->
              <a href={line.licenseHref} target="_blank" rel="noopener" class="fc-link">license</a>
              <a href={line.binHref} download class="fc-link">font data</a>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
</div>

<style>
  .fc-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--overlay);
    padding: var(--space-5);
  }

  .fc-panel {
    width: min(640px, 100%);
    max-height: min(720px, 90vh);
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border-radius: var(--radius-l);
    box-shadow: var(--shadow-2);
  }

  .fc-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--border);
  }

  .fc-head h2 { margin: 0; font-size: var(--fs-lg); }

  .fc-close {
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
  .fc-close:hover { border-color: var(--accent); color: var(--accent); }

  .fc-note {
    margin: 0;
    padding: var(--space-4) var(--space-5) 0;
    color: var(--muted);
    font-size: var(--fs-sm);
  }

  .fc-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: var(--space-4) var(--space-5) var(--space-5);
  }

  .fc-empty { color: var(--muted); font-size: var(--fs-md); text-align: center; margin: var(--space-6) 0; }

  .fc-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .fc-row {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--space-2) var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
  }
  .fc-row:last-child { border-bottom: none; }

  .fc-name { color: var(--ink); font-size: var(--fs-md); }

  .fc-license {
    padding: 0 var(--space-2);
    border-radius: var(--radius-full);
    background: var(--tint);
    color: var(--accent);
    font-size: var(--fs-xs);
    font-weight: var(--fw-bold, 700);
  }

  .fc-attribution {
    flex-basis: 100%;
    color: var(--muted);
    font-size: var(--fs-xs);
  }

  .fc-source {
    color: var(--muted);
    font-size: var(--fs-xs);
  }

  .fc-link {
    margin-left: auto;
    color: var(--accent);
    font-size: var(--fs-sm);
  }
</style>
