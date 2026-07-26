<script>
  import { EMB } from "../lib/emb.js";
  import { createEventDispatcher } from "svelte";
  import TemplateRow from "./TemplateRow.svelte";
  import Hint from "./Hint.svelte";
  import { garmentArt } from "./garmentArt.js";
  export let project;
  // Whether the "templates" onboarding hint should render right now -- App
  // computes this from hints.js's shouldShow("templates") plus the A7
  // cross-hint priority rule (drag-field/add-elements can outrank it even
  // while this step is active, since the embroidery field is visible
  // alongside every step -- see App.svelte's `visibleHintKey`).
  export let showTemplatesHint = false;
  const d = createEventDispatcher();

  function readable(id) {
    return id
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  const tiles = (EMB.GARMENTS || []).map((g) => ({
    id: g.id,
    label: g.label || g.name || readable(g.id),
  }));

  // 8 garment-common fabric tones (Slice 8 Task 2). Render-only -- picking
  // one just patches project.fabricRgb (stitch generation never sees it, see
  // generate.js); the field re-renders the SAME design against a different
  // background/hoop-chrome/weave. Kept local rather than in lib/ -- this is
  // UI-only data, not logic that needs its own spec.
  const FABRIC_SWATCHES = [
    { name: "White", rgb: [255, 255, 255] },
    { name: "Natural", rgb: [235, 232, 223] },
    { name: "Sand", rgb: [214, 199, 175] },
    { name: "Red", rgb: [179, 35, 45] },
    { name: "Royal", rgb: [32, 64, 150] },
    { name: "Navy", rgb: [25, 34, 60] },
    { name: "Forest", rgb: [30, 79, 52] },
    { name: "Black", rgb: [20, 20, 22] },
  ];
  const DEFAULT_FABRIC_RGB = [235, 232, 223];

  function sameRgb(a, b) {
    return Array.isArray(a) && Array.isArray(b) && a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
  }

  function toHex(rgb) {
    return "#" + rgb.map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0")).join("");
  }

  function fromHex(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  $: fabricRgb = project.fabricRgb || DEFAULT_FABRIC_RGB;
  $: isCustomFabric = !FABRIC_SWATCHES.some((f) => sameRgb(fabricRgb, f.rgb));
</script>

{#if showTemplatesHint}
  <Hint on:dismiss={() => d("dismisshint")}>One click starts a ready-made design.</Hint>
{/if}
<TemplateRow on:pick={(e) => d("template", e.detail)} />

<h2>What are you putting this on?</h2>
<div class="tiles">
  {#each tiles as t}
    <button class="tile" class:sel={project.garmentId === t.id} on:click={() => d("update", { garmentId: t.id })}>
      <span class="gart" aria-hidden="true">{@html garmentArt(t.id)}</span>
      <span class="tile-label">{t.label}</span>
    </button>
  {/each}
</div>

<h3>Fabric color</h3>
<div class="fabricrow">
  {#each FABRIC_SWATCHES as f}
    <button
      type="button"
      class="fabricswatch"
      class:sel={sameRgb(fabricRgb, f.rgb)}
      style="background: rgb({f.rgb[0]},{f.rgb[1]},{f.rgb[2]})"
      title={f.name}
      aria-label={f.name}
      on:click={() => d("update", { fabricRgb: f.rgb })}
    ></button>
  {/each}
  <input
    type="color"
    class="fabricswatch fabriccustom"
    class:sel={isCustomFabric}
    value={toHex(fabricRgb)}
    title="Custom fabric color"
    aria-label="Custom fabric color"
    on:input={(e) => d("update", { fabricRgb: fromHex(e.currentTarget.value) })}
  />
</div>
