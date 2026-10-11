<script>
  // The operator's own numbers behind the quote rows above it (2026-10-01):
  // which machine, the speed they run it at, what a cone costs, what an hour
  // is worth. Closed by default — a customer who wants a file never has to
  // see it, and a shop fills it in once. Every field is optional and an empty
  // one simply leaves its row off the recap (lib/quote.js).
  //
  // The component owns no state of record: it shows `quote`, and every edit
  // is dispatched as a whole cleaned record for the owner to store.
  import { createEventDispatcher } from "svelte";
  import { MACHINE_PROFILES, profileById, cleanQuote } from "../lib/quote.js";
  export let quote = {};
  const d = createEventDispatcher();

  $: profile = profileById(quote && quote.profileId);
  $: spmHint = profile && profile.maxSpm
    ? `Leave blank for the 650 spm planning rate. This machine is rated up to ${profile.maxSpm.toLocaleString()} spm; few jobs hold that.`
    : "Leave blank for the 650 spm planning rate.";

  function set(key, value) {
    d("change", cleanQuote({ ...(quote || {}), [key]: value }));
  }
  const shown = (v) => (v == null ? "" : String(v));
</script>

<details class="quote">
  <summary>Quote settings</summary>
  <p class="quote-note">
    Saved in this browser and used for every project. Leave a box empty and
    its line stays off the quote.
  </p>
  <label>
    <span>Machine</span>
    <select
      value={shown(quote.profileId)}
      on:change={(e) => set("profileId", e.currentTarget.value || null)}
      aria-label="Machine model"
    >
      <option value="">Other machine</option>
      {#each MACHINE_PROFILES as p (p.id)}
        <option value={p.id}>{p.label}</option>
      {/each}
    </select>
  </label>
  <label>
    <span>Speed I run at (spm)</span>
    <input
      type="number" inputmode="numeric" min="1" step="10" placeholder="650"
      value={shown(quote.spm)}
      on:change={(e) => set("spm", e.currentTarget.value)}
      aria-describedby="quote-spm-hint"
    />
  </label>
  <p class="quote-hint" id="quote-spm-hint">{spmHint}</p>
  <label>
    <span>Thread cone price ($)</span>
    <input
      type="number" inputmode="decimal" min="0" step="0.01"
      value={shown(quote.conePrice)}
      on:change={(e) => set("conePrice", e.currentTarget.value)}
    />
  </label>
  <label>
    <span>Thread on that cone (m)</span>
    <input
      type="number" inputmode="numeric" min="1" step="100" placeholder="e.g. 5000"
      value={shown(quote.coneM)}
      on:change={(e) => set("coneM", e.currentTarget.value)}
    />
  </label>
  <label>
    <span>Machine rate ($ per hour)</span>
    <input
      type="number" inputmode="decimal" min="0" step="0.5"
      value={shown(quote.hourRate)}
      on:change={(e) => set("hourRate", e.currentTarget.value)}
    />
  </label>
</details>

<style>
  .quote { margin: 0 0 var(--space-5); }
  .quote summary { cursor: pointer; color: var(--muted); }
  .quote label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    padding: var(--space-2) 0;
  }
  .quote label span { color: var(--muted); }
  .quote input, .quote select { width: 11rem; max-width: 55%; }
  .quote-note, .quote-hint {
    margin: var(--space-2) 0;
    font-size: var(--fs-2xs);
    color: var(--muted);
    line-height: 1.4;
  }
</style>
