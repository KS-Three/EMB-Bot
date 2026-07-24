<script>
  import { onMount } from "svelte";
  import { generateDesign, generateImageDesign } from "../lib/generate.js";
  import { renderRealistic, hoopTransform, drawHoopOutline } from "../lib/preview.js";
  import { EMB } from "../lib/emb.js";

  export let project;
  export let flat = null;

  let canvas;
  let error = "";
  let stats = "";
  let hasDesign = false;
  let hint = "";

  function garmentFor(p) {
    return p && EMB.getGarment(p.garmentId);
  }

  function clearToFabric() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#e9e6df";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // Nice-to-have: still show the hoop bounds on the empty-state canvas
    // when we know the garment, so the field never looks unrelated to size.
    const garment = garmentFor(project);
    if (garment) drawHoopOutline(ctx, hoopTransform(garment, canvas.width, canvas.height, 24));
  }

  function paintImage() {
    if (!flat) {
      hasDesign = false;
      hint = "Upload a logo or clean art — flat colors stitch best.";
      clearToFabric();
      return;
    }
    try {
      const design = generateImageDesign(flat, project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      renderRealistic(canvas, design, { hoop: { garment: garmentFor(project) } });
      hasDesign = true;
    } catch (e) {
      error = e.message;
      hasDesign = false;
      clearToFabric();
    }
  }

  function paintText() {
    const hasText = project && project.text && project.text.trim().length > 0;
    if (!hasText) {
      hasDesign = false;
      hint = "Your embroidery appears here as you add text.";
      clearToFabric();
      return;
    }
    try {
      const design = generateDesign(project);
      stats = `${design.stitchCount} stitches · ${design.widthMM.toFixed(0)}×${design.heightMM.toFixed(0)} mm`;
      renderRealistic(canvas, design, { colorOverride: project.colorRgb, hoop: { garment: garmentFor(project) } });
      hasDesign = true;
    } catch (e) {
      error = e.message;
      hasDesign = false;
      clearToFabric();
    }
  }

  function paint() {
    if (!canvas) return;
    error = "";
    stats = "";
    hint = "";
    if (project.mode === "image") paintImage();
    else paintText();
  }

  onMount(paint);
  // repaint whenever the project (garment/text/font/color/mode) or the
  // flattened image state changes
  $: if (canvas) { project; flat; paint(); }
</script>

<div class="fieldwrap">
  <div class="hoop">
    <canvas bind:this={canvas} width="760" height="560"></canvas>
    {#if !hasDesign && !error && hint}
      <p class="fieldhint">{hint}</p>
    {/if}
  </div>
  <div class="fieldmeta">
    {#if error}<span class="err">{error}</span>
    {:else if stats}<span class="stats">{stats}</span>{/if}
  </div>
</div>
