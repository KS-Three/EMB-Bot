<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateAll } from "../lib/generate.js";
  import { exportDesignPreferService, exportWorksheetPDF, exportPNG } from "../lib/exporters.js";
  import { triggerDownload } from "../lib/download.js";
  import { EMB } from "../lib/emb.js";
  import { PALETTE_INDEX, STUDIO_PALETTE, getCachedPalette, loadPalette, nearestInList, loadPreferredPaletteId, savePreferredPaletteId } from "../lib/threads.js";
  import { ensureFonts } from "../lib/fontLoader.js";
  import { effectiveHoop, hoopFitNote } from "../lib/hoop.js";
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

  // Studio only prefers the digitizer service's export path for a project made
  // ENTIRELY of auto-digitized content — MASTER_SCOPE.md scopes this
  // deliberately: lettering/manual designs stay on the browser's own encoder,
  // which is the one with actual sew evidence behind it; the service's DST has
  // spec-correctness but has never been sewn. A project mixing element types
  // (e.g. a digitized logo plus a text element) is NOT purely digitized and
  // stays on the browser path too -- there's no way to export "part" of a
  // combined design through two different encoders.
  function isPurelyDigitized(project) {
    const els = project.elements || [];
    return els.length > 0 && els.every((el) => el.type === "digitized");
  }

  // Encoder provenance, surfaced rather than left implicit.
  //
  // The gate above decides WHICH DST encoder runs, and until now nothing told
  // the user which one they got. That matters for exactly one format: the
  // browser's own DST codec is confirmed transposed against the Tajima
  // standard (five independent sources, incl. Ink/Stitch's pystitch — see
  // MASTER_SCOPE.md's "DST codec axis bug"), so a browser-encoded DST reads a
  // quarter-turn rotated in third-party software, and its color-change record
  // (0x43 vs the standard 0xC3) is not seen as a color change at all.
  //
  // Deliberately NOT extended to PES/EXP. Both browser encoders had real
  // byte-framing defects, both were FIXED 2026-08-05 (PR #58) and now decode
  // identity/rms 0 against pyembroidery, so warning on them would be telling
  // the user something untrue. DST is the one still open, and it is open
  // pending a sew-out — fixing the codec would re-orient every DST EMB-Bot
  // has ever written, which is Kent's call, not this dialog's.
  //
  // This is a prediction, not an observation: `exportDesignPreferService`
  // silently falls back to the browser encoder if the service is unreachable,
  // so a purely-digitized project can still produce a browser DST. The
  // post-download message below reports what actually happened, from `via`.
  $: dstUsesBrowserEncoder = !isPurelyDigitized(project);

  // What the download actually used, set from the returned `via` after every
  // stitch-format download so the label is observed rather than predicted.
  let lastExport = null;

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
  // Which thread chart the summary (and PDF worksheet) names cones from --
  // shared preference with ThreadPicker, changeable right here too so a
  // shopper can flip between "generic shade names" and their actual brand's
  // catalog numbers at the moment they're writing the shopping list.
  let paletteId = loadPreferredPaletteId();
  function onPaletteChange(e) {
    paletteId = e.currentTarget.value;
    savePreferredPaletteId(paletteId);
  }

  // Same lazy-chart pattern as ThreadPicker: brand thread lists live in a
  // dynamic-imported chunk (threads.js loadPalette), so the summary renders
  // from Studio's list while a brand chart is in flight (chartPending keeps
  // the header honest) and swaps to real catalog names the moment it lands.
  // The id equality check drops a stale response if the user flips charts
  // faster than the chunk loads.
  let chart = STUDIO_PALETTE;
  let chartPending = false;
  function ensureChart(id) {
    const hit = getCachedPalette(id);
    if (hit) {
      chart = hit;
      chartPending = false;
      return;
    }
    chartPending = true;
    loadPalette(id).then(
      (p) => {
        if (paletteId !== id) return;
        chart = p;
        chartPending = false;
      },
      () => {
        if (paletteId !== id) return;
        chartPending = false;
      }
    );
  }
  $: ensureChart(paletteId);

  function threadLabel(t) {
    return t.code ? `${t.code} ${t.name}` : t.name;
  }

  $: threadRows = combinedColors(project, runtime, fontsReady).map((c, i) => {
    const nearest = nearestInList(chart.threads, [c.r, c.g, c.b]);
    return { block: i + 1, rgb: nearest.rgb, name: threadLabel(nearest) };
  });

  // ---- The hoop-exceeds gate ------------------------------------------
  //
  // A design bigger than the chosen hoop was, until now, one clause of grey
  // caption text under the canvas while Download stayed enabled the whole
  // time. That is a file the machine physically cannot stitch, handed over
  // without a question — so exporting one now costs a deliberate yes.
  //
  // Computed here rather than plumbed down from the canvas: `hoopNote` is a
  // local `let` inside EmbroideryField and is never dispatched anywhere, and
  // this component already has both halves (it imports `effectiveHoop` for the
  // worksheet, and `generateAll` for the design). Never-throws for the same
  // reason `combinedColors` does not: it runs on every project change,
  // including while nothing is ready to stitch.
  function exceedsNote(project, runtime) {
    try {
      const { combined } = generateAll(project, runtime);
      if (!combined) return "";
      const { hoop } = effectiveHoop(project);
      return hoopFitNote(combined.widthMM, combined.heightMM, hoop) || "";
    } catch (e) {
      return "";
    }
  }
  $: hoopExceeds = exceedsNote(project, runtime);

  // The format the confirm is holding, or null when it is closed. Holding the
  // FORMAT rather than a boolean is what lets one dialog serve every button
  // without a second piece of state to keep in step.
  let pendingFmt = null;
  let confirmEl;
  let confirmOpener = null;

  function askThenDl(fmt) {
    // `hoopFitNote` is silent when the design fits, when no hoop is known, and
    // when it only needs rotating — so the dialog appears on exactly the case
    // it is for, and every other download is one click as before.
    if (!hoopExceeds) return dl(fmt);
    confirmOpener = typeof document !== "undefined" ? document.activeElement : null;
    pendingFmt = fmt;
    return undefined;
  }

  function closeConfirm() {
    pendingFmt = null;
    // Focus restore is the opener's job — the convention FontCredits records.
    if (confirmOpener && confirmOpener.focus) confirmOpener.focus();
    confirmOpener = null;
  }

  function confirmDl() {
    const fmt = pendingFmt;
    closeConfirm();
    if (fmt) dl(fmt);
  }

  function onConfirmKeydown(e) {
    if (e.key === "Escape") { closeConfirm(); return; }
    if (e.key !== "Tab" || !confirmEl) return;
    const els = Array.from(confirmEl.querySelectorAll("button:not([disabled])"))
      .filter((el) => el.offsetParent !== null);
    if (!els.length) return;
    const first = els[0], last = els[els.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first || !confirmEl.contains(document.activeElement)) {
        e.preventDefault(); last.focus();
      }
    } else if (document.activeElement === last || !confirmEl.contains(document.activeElement)) {
      e.preventDefault(); first.focus();
    }
  }

  $: if (confirmEl) confirmEl.focus();

  async function dl(fmt) {
    try {
      await ensureFonts(fontKeysOf(project));
      const out = await exportDesignPreferService(buildDesign(), fmt, {
        label: project.name,
        preferService: isPurelyDigitized(project),
      });
      triggerDownload(out);
      // Name the encoder in BOTH directions. The old message only ever
      // labelled the service path, so a browser-encoded file — the one case
      // where the encoder is known to matter — was the silent default.
      lastExport = { fmt, via: out.via };
      msg = "Downloaded " + fmt.toUpperCase()
        + (out.via === "service" ? " (digitizer service encoder)" : " (browser encoder)");
    } catch (e) {
      lastExport = null;
      msg = e.message;
    }
  }

  async function dlWorksheet() {
    worksheetBusy = true;
    try {
      await ensureFonts(fontKeysOf(project));
      const design = buildDesign();
      // pdfsheet.js prints color.name when present -- label each block with
      // the preferred chart's nearest cone ("1902 Poinsettia" beats "Color
      // 2" when you're standing in front of the thread rack). buildDesign()
      // returns a freshly-generated design, so annotating it here can't leak
      // into any cached/shared state. The palette load is awaited here (not
      // read from `chart`) so a worksheet clicked before the lazy chunk
      // lands still bakes the RIGHT chart's names, never Studio's.
      const list = (await loadPalette(paletteId)).threads;
      design.colors = (design.colors || []).map((c) => ({
        ...c,
        name: threadLabel(nearestInList(list, [c.r, c.g, c.b])),
      }));
      const garment = EMB.getGarment(project.garmentId);
      // The worksheet names the chosen hoop (manual pick or suggestion,
      // lib/hoop.js) — the operator mounts a physical hoop, not a garment.
      await exportWorksheetPDF(design, garment, effectiveHoop(project).hoop);
      // Not a stitch format — clear the encoder note so it can't linger next
      // to a message about a different download.
      lastExport = null;
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
      lastExport = null;
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
    <label class="threadbrand">
      <span>Chart</span>
      <select value={paletteId} on:change={onPaletteChange} aria-label="Thread chart">
        {#each PALETTE_INDEX as p (p.id)}
          <option value={p.id}>{p.label}</option>
        {/each}
      </select>
      {#if chartPending}<span class="threadbrand-loading">Loading chart…</span>{/if}
    </label>
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

<!-- Which format is PRE-BLESSED follows the encoder, not habit.
     DST is the industry default and stays first and primary for a project
     that exports through the service (pyembroidery convention, spec-correct).
     But when the browser's own encoder will write it — `dstUsesBrowserEncoder`,
     i.e. any project with lettering or hand-drawn shapes — DST is the one
     format we KNOW reads a quarter-turn rotated in other software, and it was
     still the filled button sitting directly above the paragraph saying so.
     The most prominent choice was the broken one. In that case PES leads
     instead: it is unaffected, it round-trips against pyembroidery, and it is
     what a home machine wants anyway.

     This changes button order and emphasis only. Nothing here touches the
     codec — the axis fix re-orients every DST EMB-Bot has ever written and is
     gated on a sew-out, which is Kent's call, not this dialog's. -->
<div class="formats">
  {#if dstUsesBrowserEncoder}
    <button class="primary" on:click={() => askThenDl("pes")}>PES</button>
    <button on:click={() => askThenDl("exp")}>EXP</button>
    <!-- The caveat rides aria-describedby, NOT the button's name: the name
         stays exactly "DST" so the control is still called what it is, and
         "click DST" still works for voice control. The asterisk is the
         sighted equivalent and is aria-hidden, since "star" announces
         nothing useful. -->
    <button class="caveat" aria-describedby="dst-encoder-note" on:click={() => askThenDl("dst")}>
      DST<span class="caveat-mark" aria-hidden="true">*</span>
    </button>
  {:else}
    <button class="primary" on:click={() => askThenDl("dst")}>DST</button>
    <button on:click={() => askThenDl("pes")}>PES</button>
    <button on:click={() => askThenDl("exp")}>EXP</button>
  {/if}
  <button on:click={() => askThenDl("svg")}>SVG</button>
  <button on:click={dlPNG}>PNG</button>
  <button on:click={dlWorksheet} disabled={worksheetBusy}>PDF worksheet</button>
</div>

<!-- PNG and the PDF worksheet are deliberately NOT gated: neither is a file a
     machine stitches, so neither can be the file that will not fit. -->
{#if pendingFmt}
  <div
    class="hg-backdrop"
    role="presentation"
    on:click={(e) => { if (e.target === e.currentTarget) closeConfirm(); }}
  >
    <div
      class="hg-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hg-title"
      tabindex="-1"
      bind:this={confirmEl}
      on:keydown={onConfirmKeydown}
    >
      <h3 id="hg-title">This design is bigger than your hoop</h3>
      <p class="hg-note">{hoopExceeds}</p>
      <p class="hg-body">
        The machine cannot stitch past the edge of the hoop — the needle would
        hit the frame. Make the design smaller, or choose a larger hoop back on
        the first step.
      </p>
      <div class="hg-btns">
        <button class="primary" on:click={closeConfirm}>Go back</button>
        <button on:click={confirmDl}>Download {pendingFmt.toUpperCase()} anyway</button>
      </div>
    </div>
  </div>
{/if}
{#if dstUsesBrowserEncoder}
  <p class="encodernote" id="dst-encoder-note" data-testid="dst-browser-encoder-note">
    <strong>* Heads up about DST:</strong> this project includes lettering or
    hand-drawn shapes, so its DST is written by EMB-Bot's own encoder. That
    file opens correctly in EMB-Bot, but other embroidery software reads it
    rotated a quarter turn and may not see the color stops. PES and EXP are
    unaffected — use one of those, or a project made only of auto-digitized
    images, if the file is going somewhere else.
  </p>
{/if}
<p>{msg}</p>
{#if lastExport && lastExport.fmt === "dst" && lastExport.via === "browser"}
  <p class="encodernote" data-testid="dst-browser-encoder-downloaded">
    That DST came from EMB-Bot's own encoder — see the note above before
    opening it in other software.
  </p>
{/if}
<p class="fontcredits-footer">
  <button type="button" class="linklike" on:click={openCredits}>Fonts: open-source — see credits</button>
</p>

<style>
  /* Backdrop/panel tokens mirror FontCredits.svelte, the leanest of the three
     hand-rolled dialogs this app already ships. */
  .hg-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--overlay);
    padding: var(--space-5);
  }

  .hg-panel {
    width: min(440px, 100%);
    background: var(--surface);
    border-radius: var(--radius-l);
    box-shadow: var(--shadow-2);
    padding: var(--space-5);
  }

  .hg-panel h3 { margin: 0 0 var(--space-3); }
  .hg-note { margin: 0 0 var(--space-3); font-weight: 600; }
  .hg-body { margin: 0 0 var(--space-4); line-height: 1.5; }
  .hg-btns { display: flex; gap: var(--space-3); flex-wrap: wrap; }
</style>
