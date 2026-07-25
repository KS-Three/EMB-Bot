<script>
  import { generateDesign, generateImageDesign } from "../lib/generate.js";
  import { exportDesign, exportWorksheetPDF } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  import { EMB } from "../lib/emb.js";
  export let project;
  export let flat = null;
  let msg = "";
  let worksheetBusy = false;

  function buildDesign() {
    if (project.mode === "image") {
      if (!flat) throw new Error("Upload a logo or image first.");
      return generateImageDesign(flat, project);
    }
    return generateDesign(project);
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
