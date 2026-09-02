<script>
  // The digitizer's own preflight report, on the review step.
  //
  // `preflight.py` has always produced a finished quality report for every
  // digitize -- a 0-100 score, a letter grade, typed findings, 31 metrics --
  // and the service has always attached it to the job. The Studio stored the
  // whole thing on the element and rendered ONE number out of it
  // (`metrics.trims_per_1000`, in the Sequencer header); `score` and `grade`
  // appeared nowhere in `app/src` at all. So the app knew a design was a D
  // and let the user sew it without saying so.
  //
  // Nothing here computes or judges anything. The findings are rendered
  // verbatim: preflight's own module contract is that a message is "written
  // for the person at the machine: sentence case, says what to DO, never
  // engine vocabulary", which is exactly the copy this screen wants, and
  // re-wording it here would fork one voice into two that drift.
  import Icon from "./Icon.svelte";

  // [{ id, label, preflight, stats }] -- one per digitized element. App owns
  // the selection because only it knows the project; this component owns how
  // a report READS.
  export let entries = [];

  // A grade is a deduction from 100 (info 0, warn 12, block 30), so it counts
  // findings by weight rather than measuring the cloth. Treated as a
  // headline, never as the substance: the findings under it are what a person
  // acts on, which is why the grade is a chip and not a hero number.
  function tone(grade) {
    if (grade === "A" || grade === "B") return "good";
    if (grade === "C") return "warn";
    return "bad";
  }

  // Worst first. A block finding is "will visibly go wrong"; a warn "will
  // cost machine time or quality"; info is "sew anyway" — so this is reading
  // order, not decoration.
  const RANK = { block: 0, warn: 1, info: 2 };
  function ordered(findings) {
    return [...(findings || [])].sort(
      (a, b) => (RANK[a.severity] ?? 3) - (RANK[b.severity] ?? 3));
  }

  function iconFor(severity) {
    return severity === "info" ? "lightbulb" : "warning";
  }

  // The three production numbers a person actually decides on, drawn from
  // whichever source already carries each: stitches and thread changes come
  // from preflight's metrics, thread length only from the job's stats (the
  // service computes it, and until now the Studio dropped it on the floor).
  // Any one may be missing on an older stored job, so each is rendered only
  // when it is really there rather than as a zero.
  function facts(preflight, stats) {
    const m = (preflight && preflight.metrics) || {};
    const out = [];
    const stitches = m.stitch_count ?? (stats && stats.stitch_count);
    if (typeof stitches === "number") out.push(`${stitches.toLocaleString()} stitches`);
    const changes = m.color_changes ?? (stats && stats.color_changes);
    if (typeof changes === "number") {
      out.push(`${changes} thread ${changes === 1 ? "change" : "changes"}`);
    }
    if (stats && typeof stats.thread_m_total === "number") {
      out.push(`${stats.thread_m_total.toFixed(1)} m of thread`);
    }
    return out;
  }

  // NO per-colour breakdown here, and it is not an oversight — resist adding
  // one by zipping `stats.thread_m_by_color` against the colours this app has.
  // That array is indexed PER SEWN BLOCK against `plan.palette`, which the
  // service does not send: `StitchPlan`'s own contract spells out that the
  // per-block list is deliberately not `PipelineResult.palette` (the per-layer
  // list the review screen edits), because a layer can produce no block or
  // several, "so the two lists have different lengths and different" identity.
  // Rendering the bare numbers was tried and cut: thirteen unlabelled metre
  // figures tell an operator nothing, and labelling them from the wrong list
  // would quietly hand them a wrong shopping list. A real per-cone breakdown
  // wants the service to send the per-block cone list alongside the metres.
</script>

{#if entries.length}
  <section class="quality" aria-labelledby="quality-h">
    <h3 id="quality-h">Quality check</h3>
    {#each entries as e (e.id)}
      {@const rows = ordered(e.preflight && e.preflight.findings)}
      {@const bill = facts(e.preflight, e.stats)}
      <div class="qr">
        <div class="qr-head">
          {#if entries.length > 1}<span class="qr-name">{e.label}</span>{/if}
          {#if e.preflight}
            <span class="qr-grade tone-{tone(e.preflight.grade)}">
              <b>{e.preflight.grade}</b>
              <span class="qr-score">{e.preflight.score}/100</span>
            </span>
          {/if}
        </div>

        {#if !e.preflight}
          <!-- A job from before this field existed, or one run with preflight
               off. Saying so beats an empty panel that reads as "all clear". -->
          <p class="qr-none">No quality report for this artwork — re-run Digitize to get one.</p>
        {:else if !rows.length}
          <p class="qr-clean"><Icon name="check" size={15} /> Nothing to flag. This one is ready to sew.</p>
        {:else}
          <!-- Unkeyed on purpose: a code is NOT unique in a report. Preflight
               emits one finding per offending thing, so THREAD_MATCH_POOR
               arrives once per bad thread — keying on `code` crashes the block
               with `each_key_duplicate` the moment a design has two. There is
               no stable identity to key on and no per-row state to preserve,
               so position is the honest key. -->
          <ul class="qr-list">
            {#each rows as f}
              <li class="sev-{f.severity}">
                <Icon name={iconFor(f.severity)} size={15} />
                <span>{f.message}</span>
              </li>
            {/each}
          </ul>
        {/if}

        {#if bill.length}
          <p class="qr-bill">{bill.join(" · ")}</p>
        {/if}
      </div>
    {/each}
  </section>
{/if}
