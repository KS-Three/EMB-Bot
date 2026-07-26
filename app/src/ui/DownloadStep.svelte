<script>
  import { generateAll } from "../lib/generate.js";
  import { exportDesign, exportWorksheetPDF, exportPNG } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  import { EMB } from "../lib/emb.js";
  import { nearestThread } from "../lib/threads.js";
  export let project;
  // Task 4 (Slice 5): export now covers every ready element in the project
  // (generateAll's combined design), not just a single text/image design —
  // `runtime` (the per-element flattened-image map, owned by App) is needed
  // for that, replacing the old singleton `flat` prop.
  export let runtime;
  let msg = "";
  let worksheetBusy = false;

  function buildDesign() {
    const { combined } = generateAll(project, runtime);
    if (!combined) throw new Error("Nothing to stitch yet — add some content first.");
    return combined;
  }

  // "Threads" summary (Slice 8 Task 4) -- so a shopper knows what to buy
  // before they even download. Mirrors buildDesign() but never throws: this
  // recomputes reactively on every project/runtime change (including while
  // nothing is ready to stitch yet), so it can't surface as an error banner
  // the way a real download attempt should. `project`/`runtime` are passed
  // as explicit args (not read from closure) so Svelte's static dependency
  // tracking on the `$:` statement below actually sees them (same caveat
  // ImagePanel.svelte documents for its own reactive statements).
  function combinedColors(project, runtime) {
    try {
      const { combined } = generateAll(project, runtime);
      return (combined && combined.colors) || [];
    } catch (e) {
      return [];
    }
  }
  $: threadRows = combinedColors(project, runtime).map((c, i) => {
    const nearest = nearestThread([c.r, c.g, c.b]);
    return { block: i + 1, rgb: nearest.rgb, name: nearest.name };
  });

  function dl(fmt) {
    try {
      triggerDownload(exportDesign(buildDesign(), fmt));
      msg = "Downloaded " + fmt.toUpperCase();
    } catch (e) {
      msg = e.message;
    }
  }

  async function dlWorksheet() {
    worksheetBusy = true;
    try {
      const design = buildDesign();
      const garment = EMB.getGarment(project.garmentId);
      await exportWorksheetPDF(design, garment);
      msg = "Worksheet saved.";
    } catch (e) {
      msg = e.message;
    } finally {
      worksheetBusy = false;
    }
  }

  async function dlPNG() {
    try {
      const design = buildDesign();
      const out = await exportPNG(design);
      triggerDownload({ bytes: out.blob, filename: out.filename, mime: out.mime });
      msg = "Downloaded PNG";
    } catch (e) {
      msg = e.message;
    }
  }
</script>

<h2>Download</h2>

{#if threadRows.length}
  <div class="threadsummary">
    <h3>Threads</h3>
    <ul class="threadlist">
      {#each threadRows as row}
        <li class="threadrow">
          <span class="threadrow-swatch" style="background: rgb({row.rgb[0]},{row.rgb[1]},{row.rgb[2]})"></span>
          <span class="threadrow-name">{row.name}</span>
          <span class="threadrow-block">Block {row.block}</span>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<div class="formats">
  <button class="primary" on:click={() => dl("dst")}>DST</button>
  <button on:click={() => dl("pes")}>PES</button>
  <button on:click={() => dl("exp")}>EXP</button>
  <button on:click={() => dl("svg")}>SVG</button>
  <button on:click={dlPNG}>PNG</button>
  <button on:click={dlWorksheet} disabled={worksheetBusy}>PDF worksheet</button>
</div>
<p>{msg}</p>
