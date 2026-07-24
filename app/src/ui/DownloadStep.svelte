<script>
  import { generateDesign } from "../lib/generate.js";
  import { exportDesign } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  export let project;
  let msg = "";

  function dl(fmt) {
    try {
      triggerDownload(exportDesign(generateDesign(project), fmt));
      msg = "Downloaded " + fmt.toUpperCase();
    } catch (e) {
      msg = e.message;
    }
  }
</script>

<h2>Download</h2>
<div class="formats">
  <button class="primary" on:click={() => dl("dst")}>DST</button>
  <button on:click={() => dl("pes")}>PES</button>
  <button on:click={() => dl("exp")}>EXP</button>
  <button on:click={() => dl("svg")}>SVG</button>
</div>
<p>{msg}</p>
