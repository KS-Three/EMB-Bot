<script>
  // Small dismissible onboarding hint (Slice 7 Task 3). Purely presentational
  // -- hosts (GarmentStep/ContentStep/EmbroideryField) decide WHEN to render
  // one at all (App.svelte computes that from hints.js's shouldShow() +
  // visibleHint(), see App.svelte's own comment) and pass the copy in via
  // the default slot. This component only owns the ✕ button and the
  // floating-vs-in-flow presentation (plan amendment A9): `floating` is true
  // ONLY for the drag-field hint, which sits absolutely positioned over the
  // field canvas's corner (nothing else interactive underlies it there);
  // everything else renders as an in-flow callout row with a distinct
  // background, inserted next to its anchor in the host's own markup. No
  // animation either way (A9).
  import { createEventDispatcher } from "svelte";
  import Icon from "./Icon.svelte";
  export let floating = false;
  const d = createEventDispatcher();
</script>

<div class="hintbubble" class:hintbubble-floating={floating} class:hintbubble-inflow={!floating} role="status">
  <span class="hintbubble-icon" aria-hidden="true"><Icon name="lightbulb" size={20} /></span>
  <p class="hintbubble-text"><slot /></p>
  <button type="button" class="hintbubble-x" on:click={() => d("dismiss")} aria-label="Dismiss hint"><Icon name="close" size={14} /></button>
</div>
