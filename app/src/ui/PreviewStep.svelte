<script>
  import { onMount } from "svelte";
  import { generateDesign } from "../lib/generate.js";
  import { renderRealistic } from "../lib/preview.js";
  export let project;
  let canvas;
  let error = "";
  let stats = "";

  function paint() {
    error = "";
    try {
      const design = generateDesign(project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      renderRealistic(canvas, design, { colorOverride: project.colorRgb });
    } catch (e) {
      error = e.message;
    }
  }

  onMount(paint);
  $: if (canvas && project) paint();
</script>

<h2>Preview</h2>
{#if error}<p class="err">{error}</p>{/if}
<canvas bind:this={canvas} width="640" height="420"></canvas>
<p class="stats">{stats}</p>
