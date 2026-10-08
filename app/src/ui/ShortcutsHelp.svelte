<script>
  // "?" keyboard-shortcuts overlay. It lists the shortcuts the Studio already
  // has -- every row below is read from a real handler (named in SOURCES), not
  // invented. If you add or change a shortcut, change its row here.
  //
  // Self-contained on purpose: it owns its own window keydown (App.svelte's
  // onGlobalKey is shared with undo/redo and Delete), opens on "?" only when
  // the user is not typing and no other dialog is up, and hands focus back to
  // whatever had it. Dialog mechanics follow FontCredits.svelte.
  import { tick } from "svelte";
  import Icon from "./Icon.svelte";

  // SOURCES: App.svelte onGlobalKey (undo/redo), EmbroideryField.svelte
  // onCanvasKey + onWindowKey (nudge, Esc, Delete), ManualPanel.svelte
  // onCanvasKeydown (hand-drawn shapes), DigitizePanel.svelte point editing,
  // dialogs' own Esc/Tab handling.
  const GROUPS = [
    {
      title: "Anywhere",
      rows: [
        { keys: [["Ctrl", "Z"]], what: "Undo" },
        { keys: [["Ctrl", "Y"], ["Ctrl", "Shift", "Z"]], what: "Redo" },
        { keys: [["Esc"]], what: "Close the open dialog, menu or popover" },
        { keys: [["?"]], what: "Show this list" },
      ],
    },
    {
      title: "On the design (click it first)",
      rows: [
        { keys: [["←"], ["→"], ["↑"], ["↓"]], what: "Nudge the selected design 1 mm" },
        { keys: [["Shift", "←↑↓→"]], what: "Nudge 10 mm" },
        { keys: [["Delete"], ["Backspace"]], what: "Delete the selected shape or point" },
        { keys: [["Esc"]], what: "Let go of a focused point" },
      ],
    },
    {
      title: "Drawing a shape by hand",
      rows: [
        { keys: [["Enter"]], what: "Finish the shape" },
        { keys: [["Backspace"]], what: "Take back the last point" },
        { keys: [["Esc"]], what: "Cancel the outline you are drawing" },
        { keys: [["Ctrl", "C"], ["Ctrl", "V"]], what: "Copy and paste the selected shape" },
        { keys: [["Ctrl", "D"]], what: "Duplicate the selected shape" },
        { keys: [["Delete"]], what: "Delete the selected shape" },
      ],
    },
    {
      title: "Editing outline points",
      rows: [
        { keys: [["←"], ["→"], ["↑"], ["↓"]], what: "Move the focused point" },
        { keys: [["Delete"], ["Backspace"]], what: "Remove the focused point" },
      ],
    },
  ];

  let open = false;
  let panelEl;
  let opener = null;

  function typing(t) {
    const tag = t && t.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || !!(t && t.isContentEditable);
  }

  async function show() {
    opener = document.activeElement;
    open = true;
    await tick();
    if (panelEl) panelEl.focus();
  }

  function close() {
    open = false;
    if (opener && opener.isConnected && opener.focus) opener.focus();
    opener = null;
  }

  function onWindowKey(e) {
    if (open || e.key !== "?" || e.ctrlKey || e.metaKey || e.altKey) return;
    if (typing(e.target)) return;
    // Another dialog is up: "?" is not ours to answer there.
    if (document.querySelector('[role="dialog"]')) return;
    e.preventDefault();
    show();
  }

  function onPanelKeydown(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      close();
      return;
    }
    if (e.key === "Tab") {
      // Only one focusable thing (Close) plus the panel: keep Tab inside.
      e.preventDefault();
      const btn = panelEl.querySelector("button");
      if (btn) btn.focus();
    }
  }
</script>

<svelte:window on:keydown={onWindowKey} />

{#if open}
  <div class="sh-backdrop" role="presentation" on:click={(e) => { if (e.target === e.currentTarget) close(); }}>
    <div
      class="sh-panel"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      tabindex="-1"
      bind:this={panelEl}
      on:keydown={onPanelKeydown}
    >
      <div class="sh-head">
        <h2>Keyboard shortcuts</h2>
        <button type="button" class="sh-close" on:click={close} aria-label="Close"><Icon name="close" size={16} /></button>
      </div>
      <div class="sh-body">
        {#each GROUPS as g (g.title)}
          <section>
            <h3>{g.title}</h3>
            <dl>
              {#each g.rows as r (r.what)}
                <div class="sh-row">
                  <dt>
                    {#each r.keys as combo, i}
                      {#if i > 0}<span class="sh-or">or</span>{/if}
                      <span class="sh-combo">{#each combo as k, j}{#if j > 0}<span class="sh-plus">+</span>{/if}<kbd>{k}</kbd>{/each}</span>
                    {/each}
                  </dt>
                  <dd>{r.what}</dd>
                </div>
              {/each}
            </dl>
          </section>
        {/each}
        <p class="sh-note">On a Mac, use Cmd in place of Ctrl.</p>
      </div>
    </div>
  </div>
{/if}

<style>
  .sh-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--overlay);
    padding: var(--space-5);
  }
  .sh-panel {
    width: min(560px, 100%);
    max-height: min(720px, 90vh);
    display: flex;
    flex-direction: column;
    background: var(--surface);
    color: var(--ink);
    border-radius: var(--radius-l);
    box-shadow: var(--shadow-2);
  }
  .sh-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--border);
  }
  .sh-head h2 { margin: 0; font-size: var(--fs-lg); }
  .sh-close {
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
  .sh-close:hover { border-color: var(--ink); color: var(--ink); }
  .sh-body { overflow-y: auto; padding: var(--space-4) var(--space-5) var(--space-5); }
  .sh-body h3 { margin: var(--space-4) 0 var(--space-2); font-size: var(--fs-md); }
  .sh-body section:first-child h3 { margin-top: 0; }
  dl { margin: 0; }
  .sh-row {
    display: grid;
    grid-template-columns: minmax(150px, 220px) 1fr;
    gap: var(--space-3);
    padding: 4px 0;
    align-items: baseline;
  }
  dt { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  dd { margin: 0; font-size: var(--fs-sm); }
  .sh-combo { white-space: nowrap; }
  .sh-plus, .sh-or { color: var(--muted); font-size: var(--fs-sm); margin: 0 3px; }
  kbd {
    display: inline-block;
    min-width: 1.6em;
    padding: 1px 6px;
    text-align: center;
    font: inherit;
    font-size: var(--fs-sm);
    border: 1px solid var(--border);
    border-bottom-width: 2px;
    border-radius: var(--radius-s);
    background: var(--surface);
    color: var(--ink);
  }
  .sh-note { margin: var(--space-4) 0 0; color: var(--muted); font-size: var(--fs-sm); }
</style>
