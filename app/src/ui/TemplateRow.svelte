<script>
  import { createEventDispatcher } from "svelte";
  import { TEMPLATES } from "../lib/templates.js";
  const d = createEventDispatcher();
</script>

<h3>Quick start</h3>
<div class="templates">
  {#each TEMPLATES as t}
    <button class="tcard" on:click={() => d("pick", t)}>
      <span class="tcard-label">{t.label}</span>
      <span class="tcard-hint">{t.hint}</span>
    </button>
  {/each}
</div>
