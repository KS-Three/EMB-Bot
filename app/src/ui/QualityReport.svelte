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
  // True when the design has sewable content this report does NOT cover — a
  // name beside a logo, say. It only changes whether each entry names itself:
  // at exactly one entry the label was hidden as redundant, which is right
  // when that entry IS the design and wrong when it is a part of one. On a
  // mixed design the unlabelled "2,253 stitches" sat under a two-item content
  // list describing a 3,219-stitch design (measured 2026-09-08).
  export let partial = false;

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

  // The four production numbers a person actually decides on, drawn from
  // whichever source already carries each: stitches and thread changes come
  // from preflight's metrics, thread length and trims only from the job's
  // stats (the service computes both, and the Studio dropped them on the
  // floor). Any one may be missing on an older stored job, so each is
  // rendered only when it is really there rather than as a zero.
  //
  // Trims are here because they are HAND WORK, not machine time: every trim
  // leaves thread tails on the garment that somebody clips with scissors
  // afterwards, so "31 trims" is a chore this screen can warn about and the
  // stitch count cannot. Deliberately the raw count and NOT preflight's
  // `trims_per_1000` — the rate is the right thing to grade on (it is what
  // TRIM_HEAVY fires from, and it already rides the Sequencer header) and the
  // wrong thing to hand an operator, who will clip a number of tails, not a
  // rate. Zero is worth printing for the same reason a clean report is:
  // "0 trims" says there is nothing to clip.
  // The headline total and the per-cone rows below are two renderings of the
  // SAME measurement, so a customer can add the rows up and check -- and
  // rounded independently they stop agreeing. Measured 2026-09-08 on the
  // shipped app: `enthusiast_logo` at 80 mm reports thread_m_total 4.03 with
  // thread_m_by_color [2.85, 1.19], which `toFixed(1)` renders as "4.0 m of
  // thread" above rows of 2.9 m and 1.2 m -- a shopping list adding to 4.1
  // under a stated total of 4.0. (The raw values already disagree by 0.01:
  // the service rounds each to 2dp on its own, so the parts sum to 4.04
  // against a stated 4.03.)
  //
  // The per-cone rows are what an operator actually buys against, so they
  // keep their own rounding and the TOTAL is derived from them: the
  // arithmetic on screen is then the arithmetic that works. With no cone
  // list to add up there is nothing to disagree with, so the service's own
  // total stands -- which is also the only case where `thread_m_total` is
  // the more accurate number.
  function facts(preflight, stats, spools) {
    const m = (preflight && preflight.metrics) || {};
    const out = [];
    const stitches = m.stitch_count ?? (stats && stats.stitch_count);
    if (typeof stitches === "number") out.push(`${stitches.toLocaleString()} stitches`);
    const changes = m.color_changes ?? (stats && stats.color_changes);
    if (typeof changes === "number") {
      out.push(`${changes} thread ${changes === 1 ? "change" : "changes"}`);
    }
    if (stats && typeof stats.trims === "number") {
      out.push(`${stats.trims} ${stats.trims === 1 ? "trim" : "trims"}`);
    }
    const addable =
      Array.isArray(spools) &&
      spools.length > 0 &&
      spools.every((c) => typeof c.metres === "number");
    if (addable) {
      const shown = spools.reduce((sum, c) => sum + Number(c.metres.toFixed(1)), 0);
      out.push(`${shown.toFixed(1)} m of thread`);
    } else if (stats && typeof stats.thread_m_total === "number") {
      out.push(`${stats.thread_m_total.toFixed(1)} m of thread`);
    }
    return out;
  }

  // The per-cone breakdown, labelled from the ONE list that may label it:
  // `stats.blocks`, the machine's cone list one per sewn block (service
  // contract 2026-09-04), which is what `thread_m_by_color` is indexed by.
  // Never the colours this app otherwise has — `review.palette` is per LAYER,
  // and a layer can produce no block or several, so zipping the metres
  // against it hands the operator a wrong shopping list (a gradient's five
  // shades under two layer entries). Rendered only when the two arrays are
  // the same length, which a job from before the field cannot satisfy; the
  // bare unlabelled numbers were tried before this and cut.
  //
  // FOLDED BY SPOOL, not listed per block (2026-09-11). A block is a machine
  // STOP; a row in this list is a CONE TO BUY, and since the design-silhouette
  // cap went default on the two stopped being the same number: the cap sews
  // last in whichever cone owns most of the edge, so it re-loads a cone the
  // job already ran on essentially every design (Kent ruled that stop
  // acceptable rather than put the wrong colour on the edge). Listed per
  // block, the shopping list names one spool twice and splits its metres
  // between the two rows — a customer buying from it would buy a spool they
  // already have and under-order the one they need.
  //
  // `number` is the spool id, so it is the key. Metres SUM (that is the whole
  // point of folding them), first-seen order is kept, and `facts()`'s thread
  // total is unchanged because a sum of sums is the same sum.
  function cones(stats) {
    const blocks = stats && stats.blocks;
    const metres = stats && stats.thread_m_by_color;
    if (!Array.isArray(blocks) || !Array.isArray(metres) || blocks.length !== metres.length) return [];
    const out = [];
    const at = new Map();
    blocks.forEach((b, i) => {
      const key = String(b.number);
      const hit = at.get(key);
      if (hit) {
        if (typeof hit.metres === "number" && typeof metres[i] === "number") hit.metres += metres[i];
        return;
      }
      const row = {
        number: b.number,
        name: b.name,
        rgb: Array.isArray(b.rgb) ? b.rgb : [0, 0, 0],
        metres: metres[i],
      };
      at.set(key, row);
      out.push(row);
    });
    return out;
  }
</script>

{#if entries.length}
  <section class="quality" aria-labelledby="quality-h">
    <h3 id="quality-h">Quality check</h3>
    {#each entries as e (e.id)}
      {@const rows = ordered(e.preflight && e.preflight.findings)}
      {@const spools = cones(e.stats)}
      {@const bill = facts(e.preflight, e.stats, spools)}
      <div class="qr">
        <div class="qr-head">
          {#if entries.length > 1 || partial}<span class="qr-name">{e.label}</span>{/if}
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
        {#if spools.length}
          <!-- One line per cone the machine loads, in sew order. Unkeyed: a
               cone can head two blocks. -->
          <ul class="qr-spools" aria-label="Threads to load">
            {#each spools as c}
              <li>
                <span class="qr-swatch" style="background: rgb({c.rgb[0]},{c.rgb[1]},{c.rgb[2]})"></span>
                <span class="qr-spool-name">{c.number} {c.name}</span>
                <span class="qr-spool-m">{typeof c.metres === "number" ? c.metres.toFixed(1) + " m" : ""}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/each}
  </section>
{/if}
