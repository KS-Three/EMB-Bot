<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateAll } from "../lib/generate.js";
  import { exportDesign, exportWorksheetPDF, exportPNG } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  import { EMB } from "../lib/emb.js";
  import { nearestThread } from "../lib/threads.js";
  import { ensureFonts } from "../lib/fontLoader.js";
  export let project;
  // Task 4 (Slice 5): export now covers every ready element in the project
  // (generateAll's combined design), not just a single text/image design —
  // `runtime` (the per-element flattened-image map, owned by App) is needed
  // for that, replacing the old singleton `flat` prop.
  export let runtime;
  const d = createEventDispatcher();
  let msg = "";
  let worksheetBusy = false;

  // Secondary entry point to the font credits dialog (Slice 10B Task 5) --
  // App.svelte owns FontCredits itself (same pattern as the topbar's own
  // "Font credits" button); this just dispatches "credits" upward with the
  // clicked link so App can restore focus to it on close.
  function openCredits(e) {
    d("credits", e.currentTarget);
  }

  // Task 4 review fix (single-click race): text elements' fontKeys must be
  // resolved (lib/fontLoader.js) BEFORE generateAll runs, same as
  // EmbroideryField.svelte's paint(). Reopening a saved project can land
  // directly on this step (StepNav's gating only checks project data, not
  // font readiness) with EmbroideryField's own ensureFonts still in flight,
  // so this component can't just assume its sibling already loaded them.
  function fontKeysOf(proj) {
    return (proj.elements || [])
      .filter((el) => el.type === "text" && el.fontKey)
      .map((el) => el.fontKey);
  }

  // fontsReady gates the (necessarily synchronous, template-bound)
  // combinedColors() derivation below -- it starts false so the very first
  // render never runs generateAll against a possibly-missing font, then
  // flips true once the mount-time ensureFonts() resolves, which re-triggers
  // the `$:` derivation. A load failure just leaves it false forever;
  // combinedColors' own try/catch keeps returning [] in that case, same as
  // any other "nothing to summarize yet" state.
  let fontsReady = false;
  onMount(() => {
    ensureFonts(fontKeysOf(project)).then(() => {
      fontsReady = true;
    }).catch(() => {
      // Font fetch failed; fontsReady stays false, so combinedColors derivation
      // returns [] — the intended degrade when fonts aren't available.
    });
  });

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
  function combinedColors(project, runtime, fontsReady) {
    try {
      const { combined } = generateAll(project, runtime);
      return (combined && combined.colors) || [];
    } catch (e) {
      return [];
    }
  }
  $: threadRows = combinedColors(project, runtime, fontsReady).map((c, i) => {
    const nearest = nearestThread([c.r, c.g, c.b]);
    return { block: i + 1, rgb: nearest.rgb, name: nearest.name };
  });

  async function dl(fmt) {
    try {
      await ensureFonts(fontKeysOf(project));
      triggerDownload(exportDesign(buildDesign(), fmt));
      msg = "Downloaded " + fmt.toUpperCase();
    } catch (e) {
      msg = e.message;
    }
  }

  async function dlWorksheet() {
    worksheetBusy = true;
    try {
      await ensureFonts(fontKeysOf(project));
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
      await ensureFonts(fontKeysOf(project));
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
<p class="fontcredits-footer">
  <button type="button" class="linklike" on:click={openCredits}>Fonts: open-source — see credits</button>
</p>
