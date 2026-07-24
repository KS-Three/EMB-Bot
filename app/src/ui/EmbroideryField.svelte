<script>
  import { onMount } from "svelte";
  import { generateDesign } from "../lib/generate.js";
  import { renderRealistic } from "../lib/preview.js";

  export let project;

  let canvas;
  let error = "";
  let stats = "";
  let hasDesign = false;

  function clearToFabric() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#e9e6df";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function paint() {
    if (!canvas) return;
    error = "";
    stats = "";
    const hasText = project && project.text && project.text.trim().length > 0;
    if (!hasText) {
      hasDesign = false;
      clearToFabric();
      return;
    }
    try {
      const design = generateDesign(project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      renderRealistic(canvas, design, { colorOverride: project.colorRgb });
      hasDesign = true;
    } catch (e) {
      error = e.message;
      hasDesign = false;
      clearToFabric();
    }
  }

  onMount(paint);
  // repaint whenever the project (garment/text/font/color) changes
  $: if (canvas && project) paint();
</script>

<div class="fieldwrap">
  <div class="hoop">
    <canvas bind:this={canvas} width="760" height="560"></canvas>
    {#if !hasDesign && !error}
      <p class="fieldhint">Your embroidery appears here as you add text.</p>
    {/if}
  </div>
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if stats}<span class="stats">{stats}</span>{/if}
  </div>
</div>
