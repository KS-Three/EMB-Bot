<script>
  import { createEventDispatcher } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import {
    SHAPE_KINDS, SHAPE_LABELS, defaultShapeParams, resolvedShapeParams,
    STAR_MIN_POINTS, STAR_MAX_POINTS, STAR_MIN_INNER_RATIO, STAR_MAX_INNER_RATIO,
  } from "../lib/shapePresets.js";

  // Preset basic-shape element editor (launch-checklist item 4): pick a
  // kind, tune its per-shape params, pick a thread color. The element's
  // SIZE is the same sizeMm every element type has, edited by the Size
  // panel ContentStep renders directly below this one (and by the canvas
  // resize handles) — no second size input here to fight it. Satin-vs-fill
  // is deliberately absent: that's the engine classifier's call for preset
  // shapes (see generate.js's "shape" branch).
  //
  // Patch convention (see TextStep.svelte's comment for the same one):
  // every edit dispatches "elupdate" shaped { id: element.id, patch }.
  export let element;
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // Always read through the kind's defaults so an element saved before a
  // param existed still renders real values, never blank inputs.
  $: params = resolvedShapeParams(element.kind, element.params);

  function pickKind(kind) {
    if (kind === element.kind) return;
    // Params are per-kind, so switching kind resets them to that kind's
    // defaults — a star's inner ratio has no meaning on a rectangle.
    patch({ kind, params: defaultShapeParams(kind) });
  }

  function setParam(key, value) {
    patch({ params: { ...params, [key]: value } });
  }

  function numParam(key, e, fallback) {
    const v = parseFloat(e.target.value);
    setParam(key, Number.isFinite(v) ? v : fallback);
  }
</script>

<div class="shapepanel">
  <p class="hint">
    Pick a shape — it digitizes automatically. Set its size below and drag it
    into place on the right.
  </p>

  <div class="sp-row">
    <span class="sp-label">Shape</span>
    <div class="sp-btns">
      {#each SHAPE_KINDS as kind}
        <button
          type="button"
          class="sp-btn"
          class:active={element.kind === kind}
          on:click={() => pickKind(kind)}
        >{SHAPE_LABELS[kind]}</button>
      {/each}
    </div>
  </div>

  {#if element.kind === "rect"}
    <label class="sp-row">
      <span class="sp-label">Height</span>
      <input
        type="number"
        step="1"
        min="1"
        value={params.heightMm}
        on:change={(e) => numParam("heightMm", e, 30)}
      />
      <span class="sp-unit">mm</span>
    </label>
    <label class="sp-row">
      <span class="sp-label">Corner radius</span>
      <input
        type="number"
        step="1"
        min="0"
        value={params.cornerRadiusMm}
        on:change={(e) => numParam("cornerRadiusMm", e, 0)}
      />
      <span class="sp-unit">mm (0 = square corners)</span>
    </label>
    <p class="sp-note">Width is the W in Size below.</p>
  {:else if element.kind === "star"}
    <label class="sp-row">
      <span class="sp-label">Star points</span>
      <input
        type="number"
        step="1"
        min={STAR_MIN_POINTS}
        max={STAR_MAX_POINTS}
        value={params.points}
        on:change={(e) => numParam("points", e, 5)}
      />
    </label>
    <label class="sp-row">
      <span class="sp-label">Inner radius</span>
      <input
        type="range"
        min={Math.round(STAR_MIN_INNER_RATIO * 100)}
        max={Math.round(STAR_MAX_INNER_RATIO * 100)}
        step="1"
        value={Math.round(params.innerRatio * 100)}
        on:input={(e) => setParam("innerRatio", parseInt(e.target.value, 10) / 100)}
      />
      <span class="sp-unit">{Math.round(params.innerRatio * 100)}% — lower is sharper tips</span>
    </label>
  {/if}

  <div class="sp-row">
    <span class="sp-label">Color</span>
    <ThreadPicker compact rgb={element.colorRgb} on:pick={(e) => patch({ colorRgb: e.detail })} />
  </div>
</div>

<style>
  .shapepanel { display: flex; flex-direction: column; gap: 10px; }
  .hint { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
  .sp-row { display: flex; align-items: center; gap: 8px; }
  .sp-label { display: block; font-size: var(--fs-xs, 12px); min-width: 80px; }
  .sp-btns { display: flex; gap: 6px; flex-wrap: wrap; }
  .sp-btn {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .sp-btn.active {
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    border-color: var(--accent, #4f46e5);
  }
  .sp-row input[type="number"] {
    width: 64px;
    padding: 5px 8px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    font-size: var(--fs-xs, 12px);
  }
  .sp-row input[type="range"] { flex: 1; max-width: 160px; }
  .sp-unit { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); }
  .sp-note { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
</style>
