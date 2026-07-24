<script>
  import { STEPS } from "../lib/flow.js";
  import { createEventDispatcher } from "svelte";
  export let step;
  export let canNext;
  const d = createEventDispatcher();
</script>

<nav class="stepnav">
  <button on:click={() => d("back")} disabled={step === STEPS[0]}>Back</button>
  <ol>
    {#each STEPS as s}
      <li class:active={s === step}></li>
    {/each}
  </ol>
  <button class="primary" on:click={() => d("next")} disabled={!canNext || step === STEPS[STEPS.length - 1]}>Next</button>
</nav>
