<script>
  // Compare view's overlay (2026-11-07): the artwork laid exactly over the
  // field canvas, clipped to the LEFT of a draggable vertical split, so the
  // stitches show to the right of it. The field renders the artwork side
  // (fabric + the registered artwork, from repaintView, through the same
  // placement Original view uses) on an OFFSCREEN canvas at the field
  // canvas's bitmap size and hands it in as `src`; shown as an <img> because
  // .hoop holds exactly one <canvas>. This component only owns the split.
  //
  // Overlay only: absolutely positioned inside `.hoop`, it takes no layout
  // space, and everything but the handle is pointer-transparent, so the
  // wheel still zooms and the field keeps its own pointer rules. Moving the
  // split is a CSS clip — nothing is repainted while it moves.
  import { clampSplit, splitFromClientX, splitKey, clipForSplit, splitPercent, splitValueText } from "../lib/compareSplit.js";

  export let split = 0.5;
  // Object URL of the artwork side's bitmap ("" until the first is ready).
  export let src = "";

  let wrap;
  let dragging = false;

  $: s = clampSplit(split);
  $: pct = splitPercent(s);

  function onKey(e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const next = splitKey(s, e.key, e.shiftKey);
    if (next == null) return; // Tab, [ ], < > , . … are not the handle's
    e.preventDefault();
    // The window listeners (field Delete/Escape, App undo) never see a key
    // the handle used.
    e.stopPropagation();
    split = next;
  }

  function onDown(e) {
    if (e.button !== 0 || !wrap) return;
    dragging = true;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* jsdom */ }
    e.currentTarget.focus();
    e.preventDefault();
  }
  function onMove(e) {
    if (!dragging || !wrap) return;
    split = splitFromClientX(e.clientX, wrap.getBoundingClientRect());
  }
  function onUp(e) {
    if (!dragging) return;
    onMove(e);
    dragging = false;
  }
</script>

<div class="cmp" bind:this={wrap} data-testid="compare-split" data-split={s.toFixed(3)}>
  {#if src}<img class="cmp-art" {src} alt="" aria-hidden="true" draggable="false" style="clip-path: {clipForSplit(s)}" />{/if}
  <span class="cmp-tag cmp-tag-l" aria-hidden="true">Artwork</span>
  <span class="cmp-tag cmp-tag-r" aria-hidden="true">Stitches</span>
  <!-- A focusable separator is WAI-ARIA's "window splitter": arrows move it,
       aria-valuenow says where. Svelte classes `separator` as non-interactive
       because a static one is; this one is the focusable variant the pattern
       defines, so the tabindex warning is silenced deliberately. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="cmp-handle"
    class:cmp-dragging={dragging}
    style="left: {s * 100}%"
    role="separator"
    tabindex="0"
    aria-orientation="vertical"
    aria-label="Compare split"
    aria-valuemin="0"
    aria-valuemax="100"
    aria-valuenow={pct}
    aria-valuetext={splitValueText(s)}
    on:keydown={onKey}
    on:pointerdown={onDown}
    on:pointermove={onMove}
    on:pointerup={onUp}
    on:pointercancel={onUp}
  >
    <span class="cmp-line" aria-hidden="true"></span>
    <span class="cmp-grip" aria-hidden="true"></span>
  </div>
</div>

<style>
  .cmp {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }
  .cmp-art {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    max-width: none;
    max-height: none;
    object-fit: fill;
    border: 0;
    pointer-events: none;
    user-select: none;
  }
  .cmp-tag {
    position: absolute;
    top: 8px;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
    line-height: 16px;
    background: rgba(0, 0, 0, 0.55);
    color: #fff;
    pointer-events: none;
    user-select: none;
  }
  .cmp-tag-l { left: 8px; }
  .cmp-tag-r { right: 8px; }
  .cmp-handle {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 24px;
    margin-left: -12px;
    cursor: ew-resize;
    pointer-events: auto;
    touch-action: none;
    outline: none;
  }
  .cmp-line {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 11px;
    width: 2px;
    background: #fff;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.45);
  }
  .cmp-grip {
    position: absolute;
    top: 50%;
    left: 2px;
    width: 20px;
    height: 36px;
    margin-top: -18px;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
  }
  .cmp-handle:focus-visible .cmp-grip,
  .cmp-dragging .cmp-grip {
    box-shadow: 0 0 0 3px var(--accent, #4f46e5);
  }
</style>
