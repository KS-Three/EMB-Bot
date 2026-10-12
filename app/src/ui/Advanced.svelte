<script>
  // "Advanced ›" -- the one disclosure behind which an editor keeps its power
  // tools (spec 2026-09-30 §5). Nothing is removed: the slot is always
  // rendered and merely `hidden` while closed, so the same components keep
  // their state, their test ids and their bindings, and a closed section is
  // out of the tab order and the accessibility tree. Open/closed lives in
  // lib/advanced.js so it survives the panel being rebuilt.
  import { advancedOpen, toggleAdvanced } from "../lib/advanced.js";
</script>

<div class="advanced">
  <button
    type="button"
    class="advanced-toggle"
    data-testid="advanced-toggle"
    aria-expanded={$advancedOpen}
    aria-controls="advanced-body"
    on:click={toggleAdvanced}
  >Advanced<span class="advanced-chev" aria-hidden="true">›</span></button>
  <div class="advanced-body" id="advanced-body" data-testid="advanced-body" hidden={!$advancedOpen}>
    <slot />
  </div>
</div>

<style>
  .advanced { margin-top: var(--space-4, 12px); }
  .advanced-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 0;
    border: 0;
    background: none;
    color: var(--muted);
    font: inherit;
    font-size: var(--fs-sm, 13px);
    font-weight: var(--fw-medium, 500);
    cursor: pointer;
  }
  .advanced-toggle:hover { color: var(--ink); }
  .advanced-chev { display: inline-block; font-size: 1.2em; line-height: 1; }
  @media (prefers-reduced-motion: no-preference) {
    .advanced-chev { transition: transform 150ms ease; }
  }
  .advanced-toggle[aria-expanded="true"] .advanced-chev { transform: rotate(90deg); }
  .advanced-body { padding-top: var(--space-2, 6px); }
  .advanced-body[hidden] { display: none; }
</style>
