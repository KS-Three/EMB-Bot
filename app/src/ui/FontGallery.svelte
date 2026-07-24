<script>
  import { EMB } from "../lib/emb.js";
  import { createEventDispatcher } from "svelte";
  export let selected;
  const d = createEventDispatcher();
  const fonts = Object.entries(EMB.SATIN_FONTS || {}).map(([key, f]) => ({ key, name: f.name || key }));
</script>

<ul class="fontgallery">
  {#each fonts as f}
    <li>
      <button class:sel={f.key === selected} on:click={() => d("pick", f.key)}>{f.name}</button>
    </li>
  {/each}
</ul>
