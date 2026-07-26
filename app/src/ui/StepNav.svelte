<script>
  import { STEPS, canAdvance } from "../lib/flow.js";
  import { createEventDispatcher } from "svelte";
  export let step;
  export let project;
  export let canNext;
  const d = createEventDispatcher();

  // Labels per plan amendment B11 -- "create" (the settings-recap step) reads
  // as "Review" here; the underlying step id is unchanged (flow.js/App.svelte
  // still key off "create").
  const LABELS = { garment: "Garment", content: "Content", create: "Review", download: "Download" };

  // A step is clickable if it's the current step or one already behind it
  // (always allowed -- you can always go back to review something you've
  // already done), OR if every gate between the start and that step passes
  // for the CURRENT project (so jumping ahead skips nothing). Walking the
  // gate chain from STEPS[0] with today's `project` -- rather than trying to
  // reconstruct "how did we get here" from history -- is sufficient because
  // canAdvance(stepId, project) only ever looks at the project's current
  // state, never step order/history.
  function maxReachableIndex(proj) {
    let i = 0;
    while (i < STEPS.length - 1 && canAdvance(STEPS[i], proj)) i++;
    return i;
  }

  $: currentIndex = STEPS.indexOf(step);
  $: maxIndex = maxReachableIndex(project);
  $: clickable = STEPS.map((_, i) => i <= currentIndex || i <= maxIndex);

  function goto(s, i) {
    if (!clickable[i]) return;
    d("goto", s);
  }
</script>

<nav class="stepnav">
  <ol class="stepnav-steps">
    {#each STEPS as s, i}
      <li>
        <button
          type="button"
          class="stepnav-step"
          class:active={s === step}
          disabled={!clickable[i]}
          aria-current={s === step ? "step" : undefined}
          on:click={() => goto(s, i)}
        >{LABELS[s] ?? s}</button>
      </li>
    {/each}
  </ol>
  <div class="stepnav-controls">
    <button type="button" on:click={() => d("back")} disabled={step === STEPS[0]}>Back</button>
    <button type="button" class="primary" on:click={() => d("next")} disabled={!canNext || step === STEPS[STEPS.length - 1]}>Next</button>
  </div>
</nav>
