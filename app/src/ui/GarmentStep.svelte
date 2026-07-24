<script>
  import { EMB } from "../lib/emb.js";
  import { createEventDispatcher } from "svelte";
  export let project;
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

<h2>What are you putting this on?</h2>
<div class="tiles">
  {#each tiles as t}
    <button class="tile" class:sel={project.garmentId === t.id} on:click={() => d("update", { garmentId: t.id })}>
      {t.label}
    </button>
  {/each}
</div>
