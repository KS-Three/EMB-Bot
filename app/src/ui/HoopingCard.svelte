<script>
  // What to hoop under this design: stabilizer, topper, needle. A renderer —
  // the rows come from lib/hooping.js (the engine's `hoopingAdvice`, the same
  // function the PDF worksheet prints), so this component decides nothing.
  //
  // Renders NOTHING for an empty list: no garment we ship, or nothing sewn,
  // means there is no basis for advice, and an empty heading would read as
  // "no stabilizer needed".
  export let rows = [];
</script>

{#if rows.length}
  <section class="hooping" aria-label="What to hoop">
    <h3>What to hoop</h3>
    <dl>
      {#each rows as row}
        <div>
          <dt>{row.label}</dt>
          <dd>
            {row.value}
            {#if row.note}<small>{row.note}</small>{/if}
          </dd>
        </div>
      {/each}
    </dl>
    <p class="basis">Advice for the operator. It does not change the stitches.</p>
  </section>
{/if}

<style>
  /* The rows LOOK like the sheet's `.summary` recap (theme.css) but must not
     wear its class: the e2e specs read the recap as `.sheet dl.summary` in
     strict mode, and a second match fails every one of them. So the row
     rules are repeated here — keep them in step with `.sheet .summary`. */
  /* No top margin: the heading already spaces the list from the recap. */
  dl { margin: 0 0 var(--space-5); }
  dl > div {
    display: flex;
    justify-content: space-between;
    gap: var(--space-4);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
  }
  dt { color: var(--muted); margin: 0; }
  dd { margin: 0; font-weight: var(--fw-medium); text-align: right; }
  small {
    display: block;
    font-weight: var(--fw-regular, 400);
    color: var(--muted);
  }
  .basis {
    margin: calc(-1 * var(--space-3)) 0 var(--space-5);
    font-size: var(--fs-xs);
    color: var(--muted);
  }
</style>
