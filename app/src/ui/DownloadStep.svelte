<script>
  import { generateAll } from "../lib/generate.js";
  import { exportDesign, exportWorksheetPDF } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  import { EMB } from "../lib/emb.js";
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
</script>

<h2>Download</h2>
<div class="formats">
  <button class="primary" on:click={() => dl("dst")}>DST</button>
  <button on:click={() => dl("pes")}>PES</button>
  <button on:click={() => dl("exp")}>EXP</button>
  <button on:click={() => dl("svg")}>SVG</button>
  <button on:click={dlWorksheet} disabled={worksheetBusy}>PDF worksheet</button>
</div>
<p>{msg}</p>
