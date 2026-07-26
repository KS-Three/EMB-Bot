<script>
  import { EMB } from "../lib/emb.js";
  import { createEventDispatcher } from "svelte";
  import TemplateRow from "./TemplateRow.svelte";
  import Hint from "./Hint.svelte";
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
</script>

{#if showTemplatesHint}
  <Hint on:dismiss={() => d("dismisshint")}>One click starts a ready-made design.</Hint>
{/if}
<TemplateRow on:pick={(e) => d("template", e.detail)} />

<h2>What are you putting this on?</h2>
<div class="tiles">
  {#each tiles as t}
    <button class="tile" class:sel={project.garmentId === t.id} on:click={() => d("update", { garmentId: t.id })}>
      {t.label}
    </button>
  {/each}
</div>
