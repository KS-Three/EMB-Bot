<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { generateAll } from "../lib/generate.js";
  import { exportDesignPreferService, exportWorksheetPDF, exportPNG, isServiceOnlyFormat } from "../lib/exporters.js";
  import { chartIdForProject } from "../lib/designChart.js";
  import { isSewable } from "../lib/flow.js";
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
  // The digitizer service's /health answer, or null when it isn't reachable
  // (App owns the probe; see its `digitizerHealth`). Needed HERE and not only
  // on the content step because JEF, XXX and VP3 have no browser encoder —
  // the service is the only thing that can write them, so those buttons have
  // to be able to say why they are unavailable instead of throwing when
  // pressed.
  export let digitizerHealth = null;
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
    // Only elements that actually SEW count. Every project is born holding an
    // empty text element (defaultProject), and a customer who uploads a logo
    // never removes it — so `every(el => el.type === "digitized")` was false
    // for essentially every real design, and this gate never fired.
    //
    // Measured 2026-09-07 by downloading from the shipped UI and decoding
    // with pystitch, the same third-party reader CI cross-validates against:
    // the app claimed 81x16 mm, and the DST a customer gets read back
    // **16.3 x 80.5 mm with 0 threads** — the quarter turn and the
    // unrecognised colour-change record of CLAUDE.md footgun 1. PES from the
    // same design read 80.5 x 16.3 with 2 threads.
    //
    // The scoping ruling is unchanged and deliberate — lettering and manual
    // designs stay on the browser encoder, the one with sew evidence behind
    // it, and a design genuinely MIXING sewable types still does too, because
    // there is no way to export part of a combined design through two
    // encoders. What changes is that a placeholder which contributes no
    // stitches no longer counts as "mixing".
    const sewable = (project.elements || []).filter(isSewable);
    return sewable.length > 0 && sewable.every((el) => el.type === "digitized");
  }

  // Encoder provenance is no longer surfaced, because it no longer changes
  // what the customer gets.
  //
  // `dstUsesBrowserEncoder` lived here from 2026-08 to 2026-09-08 and drove
  // three things: DST demoted behind PES, an asterisk on the DST button, and
  // two paragraphs saying a browser-written DST reads a quarter turn round
  // AND MIRRORED elsewhere. All of that was true and all of it is now false —
  // the codec was put right on 2026-09-08 (both record weight tables swapped;
  // byte-identical to pystitch; crossval `identity`; a rendered "FRITSCH"
  // upright at the design's own size), and the colour-change record went from
  // `0x43` to the standard `0xC3` the day before.
  //
  // PES and EXP had their own byte-framing defects, fixed 2026-08-05 (PR #58).
  // With DST joining them there is no format here whose provenance is worth a
  // warning, so the gate, the demotion, the asterisk and both notes are gone
  // together. If a future difference appears, MEASURE it and write a note
  // about that difference rather than restoring these.

  // ---- JEF (Janome) ---------------------------------------------------
  //
  // PRODUCT.md's launch checklist item 1 is "PES hardened to byte-verified +
  // JEF export", marked done because `digitizer_service/formats.py` can write
  // JEF. It could; there was no button, so a Janome owner could not export
  // anything from this app. Every other format here has a browser encoder
  // behind it, so this is the first control whose availability depends on the
  // service being up — hence a disabled state with a reason rather than a
  // button that throws.
  //
  // Which machines this product supports is a scope call — that has not
  // changed, and Kent has now MADE it (2026-09-12): XXX (Singer) and VP3
  // (Husqvarna Viking / Pfaff) ship, PEC and U01 do not. So this is no longer
  // the only service-only button; the two below are the same shape.
  //
  // The evidence is `digitizer/tools/format_roundtrip.py --detail`, which
  // reads every format back with pystitch: XXX and VP3 both come back
  // `identity` (70/70 stitches, 1/1 colour change, 1725 x 200 units) and both
  // carry the design's own thread RGB, which PES, PEC and JEF do not — they
  // snap to their chart. U01 is still the one that would need work first: its
  // colour change does not survive the round trip (1 -> 0; the stop is
  // re-encoded as two NEEDLE_SET records). Adding another is still one entry
  // in exporters.js's SERVICE_ONLY_FORMATS and one button here.
  //
  // Asked of exporters.js rather than hardcoded here, so that the day a
  // browser JEF encoder exists, removing "jef" from SERVICE_ONLY_FORMATS is
  // the whole change and this gate disappears with it.
  //
  // `jefAvailable` briefly also gated whether the DST caveat NAMED JEF as an
  // alternative — that caveat had shipped saying only "PES and EXP are
  // unaffected", written before JEF had a button and never revisited when it
  // got one, so a Janome owner was steered to two formats their machine may
  // not read and away from the one it does. Both the caveat and that sentence
  // are gone now that DST itself is correct; `jefAvailable` is back to doing
  // one job, which is enabling or disabling the button.
  $: jefAvailable = !isServiceOnlyFormat("jef") || !!digitizerHealth;
  $: jefTitle = jefAvailable
    ? "Janome JEF, written by the digitizer service"
    : "Janome JEF needs the digitizer service running — it has no in-browser encoder";

  // ---- XXX (Singer) and VP3 (Husqvarna Viking / Pfaff) -----------------
  //
  // Kent's scope call 2026-09-12, recorded in the JEF block above. Same two
  // lines per format as JEF, spelled out rather than looped: each names its
  // own brands, and a list rendered with {#each} would bury the ordering the
  // markup below is deliberately choosing.
  //
  // Named by brand in the title and by extension on the face, exactly as JEF
  // is: the button text is what voice control and a customer's own search
  // reach for, and the brand is what an owner recognises.
  //
  // VP3 gets NO asterisk and no note. Its one measured difference (a 0.1 mm
  // narrower read-back from the third colour block on, pinned there and not
  // accumulating) is documented in exporters.js and belongs in a PR body, not
  // in front of a customer — Kent's call the same day. The asterisk
  // convention on the JEF button above is for a defect that can make a
  // machine refuse the file; this is a tenth of a millimetre.
  $: xxxAvailable = !isServiceOnlyFormat("xxx") || !!digitizerHealth;
  $: xxxTitle = xxxAvailable
    ? "Singer XXX, written by the digitizer service"
    : "Singer XXX needs the digitizer service running — it has no in-browser encoder";
  $: vp3Available = !isServiceOnlyFormat("vp3") || !!digitizerHealth;
  $: vp3Title = vp3Available
    ? "Husqvarna Viking / Pfaff VP3, written by the digitizer service"
    : "Husqvarna Viking / Pfaff VP3 needs the digitizer service running — it has no in-browser encoder";

  // fontsReady gates the (necessarily synchronous, template-bound)
  // `combined` derivation below -- it starts false so the very first render
  // never runs generateAll against a possibly-missing font, then flips true
  // once the mount-time ensureFonts() resolves, which re-triggers the `$:`
  // derivation. A load failure just leaves it false forever; safeCombined's
  // own try/catch keeps returning null in that case, same as any other
  // "nothing to summarize yet" state.
  let fontsReady = false;
  onMount(() => {
    ensureFonts(fontKeysOf(project)).then(() => {
      fontsReady = true;
    }).catch(() => {
      // Font fetch failed; fontsReady stays false, so the `combined`
      // derivation returns null — the intended degrade when fonts aren't
      // available.
    });
  });

  // Deliberately NOT the shared `combined` below: this runs after the
  // download's own `ensureFonts` await, so it sees fonts the reactive
  // derivation may have been computed without, and it MUST throw with a
  // message where that one must never throw at all.
  function buildDesign() {
    const { combined: design } = generateAll(project, runtime);
    if (!design) throw new Error("Nothing to stitch yet — add some content first.");
    return design;
  }

  // ONE generated design, read by three things.
  //
  // Mirrors buildDesign() but never throws: this recomputes reactively on
  // every project/runtime change (including while nothing is ready to stitch
  // yet), so it can't surface as an error banner the way a real download
  // attempt should. `project`/`runtime` are passed as explicit args (not read
  // from closure) so Svelte's static dependency tracking on the `$:` statement
  // below actually sees them (same caveat ImagePanel.svelte documents for its
  // own reactive statements); `fontsReady` is a dependency only — it is read
  // for the re-trigger, never for a value.
  //
  // It used to be three separate calls: the "Threads" shopping list (Slice 8
  // Task 4), the hoop-exceeds gate, and — as of the JEF header note below —
  // a third. generateAll re-runs the stitch engine over every element, so a
  // third caller was the point at which paying for it once became worth the
  // one shared `$:`.
  function safeCombined(project, runtime, fontsReady) {
    try {
      return generateAll(project, runtime).combined || null;
    } catch (e) {
      return null;
    }
  }
  $: combined = safeCombined(project, runtime, fontsReady);

  // Which thread chart the summary (and PDF worksheet) names cones from --
  // shared preference with ThreadPicker, changeable right here too so a
  // shopper can flip between "generic shade names" and their actual brand's
  // catalog numbers at the moment they're writing the shopping list.
  // The brand the ENGINE snapped this design's cones out of, when a digitized
  // element carries one (`review.brandId`, set from the service's own
  // `palette[0].brand_id`). Every element in a project shares it, so the
  // first one that has it wins. See `loadPreferredPaletteId` for what a
  // generic default costs a shopper.
  const designPaletteId = chartIdForProject(project);
  let paletteId = loadPreferredPaletteId(designPaletteId);
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

  $: threadRows = ((combined && combined.colors) || []).map((c, i) => {
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
  // worksheet, and `safeCombined` for the design). Still never-throws even
  // though the generate call moved out: `effectiveHoop` reads the engine's
  // garment/hoop tables, and this runs on every project change including a
  // corrupt or half-loaded one.
  function exceedsNote(combined, project) {
    if (!combined) return "";
    try {
      const { hoop } = effectiveHoop(project);
      return hoopFitNote(combined.widthMM, combined.heightMM, hoop) || "";
    } catch (e) {
      return "";
    }
  }
  $: hoopExceeds = exceedsNote(combined, project);

  // ---- The JEF header says a hoop the design does not fit ---------------
  //
  // A JEF file carries a HOOP CODE in its header and a Janome reads it before
  // it reads a stitch. `pystitch.JefWriter.get_jef_hoop_size` derives that
  // code from the design's own bbox, correctly, until the last line:
  //
  //     if width < 1400 and height < 2000: return HOOP_140X200
  //     if width < 2000 and height < 2000: return HOOP_200X200
  //     return HOOP_110X110
  //
  // The fallthrough is HOOP_110X110 — the second SMALLEST of the five codes
  // it knows, handed to the largest designs. Measured 2026-09-07 by reading
  // the bytes back off the real /export route (digitizer/tests/
  // test_jef_hoop_code.py pins it): 199 mm declares 200x200 and fits; 201 mm
  // declares 110x110 and does not.
  //
  // Said as a persistent note beside the button rather than inside the
  // hoop-exceeds confirm, which is where this first went — because the
  // confirm does NOT open on the case that matters most. Measured the same
  // day: a 140 x 200 mm design FITS the 8x8 hoop (the app's largest) and a
  // 150 x 240 mm design FITS the 6x10 hoop, so `hoopFitNote` is silent for
  // both — and both are stamped 110 x 110. Riding the confirm would have
  // shown the caveat to the four oversize garments only and stayed quiet for
  // every design that fits a hoop the customer actually owns.
  //
  // Threshold is the writer's own test, in the writer's own units, so there
  // is no rounding sliver between what this says and what the file gets:
  // pystitch rounds the bbox to whole 0.1 mm units before comparing.
  const JEF_HOOP_UNITS_MAX = 2000; // 0.1 mm units — get_jef_hoop_size's last rung
  function overJefHoopBand(mm) {
    return isFinite(mm) && Math.round(mm * 10) >= JEF_HOOP_UNITS_MAX;
  }
  // Names only levers that exist in the product: the Size panel back on the
  // Content step, and the two formats VERIFIED to write no hoop header (grep
  // pystitch's writers: only JefWriter and PesWriter mention one, so DST and
  // EXP are clean and PES is deliberately NOT named here — its hoop bytes are
  // a constant that never described the design, and what a Brother does with
  // them is not something this repo can measure).
  function jefHoopHeaderNote(combined) {
    if (!combined) return "";
    const { widthMM: w, heightMM: h } = combined;
    if (!overJefHoopBand(w) && !overJefHoopBand(h)) return "";
    return `a JEF file records a hoop size in its header, and this design is `
      + `${w.toFixed(1)} \u00d7 ${h.toFixed(1)} mm. Over 200 mm that header is written as `
      + `110 \u00d7 110 mm \u2014 smaller than the design itself \u2014 and a Janome reads it `
      + `before it reads a stitch, so the machine may refuse the file even with a hoop `
      + `mounted that would take the design. Under 200 mm the header is correct; DST and `
      + `EXP carry no hoop header at all.`;
  }
  $: jefHoopNote = jefHoopHeaderNote(combined);

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
      // The message still names which encoder ran -- neutral provenance, not
      // a caveat. It stopped being a caveat on 2026-09-08, when the browser
      // DST codec was put right and both warning notes came out.
      msg = "Downloaded " + fmt.toUpperCase()
        + (out.via === "service" ? " (digitizer service encoder)" : " (browser encoder)");
    } catch (e) {
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
      // One palette object for both the codes and the chart name below them,
      // so the sheet can never print one chart's numbers under another
      // chart's heading.
      const palette = await loadPalette(paletteId);
      const list = palette.threads;
      design.colors = (design.colors || []).map((c) => ({
        ...c,
        name: threadLabel(nearestInList(list, [c.r, c.g, c.b])),
      }));
      const garment = EMB.getGarment(project.garmentId);
      // The worksheet names the chosen hoop (manual pick or suggestion,
      // lib/hoop.js) — the operator mounts a physical hoop, not a garment.
      // ...and the chart those codes came out of. "1375 Dark Charcoal" is
      // not a thread anyone can buy until the sheet says whose 1375 it is.
      // `hoopExceeds` is the same string the export confirm shows. The
      // worksheet is not gated on it -- printing a reference sheet is
      // harmless -- but it must SAY it, because the sheet is the document
      // that goes to the machine.
      await exportWorksheetPDF(design, garment, effectiveHoop(project).hoop, palette.label, hoopExceeds);
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

<!-- DST is the industry default and is first and primary again, on every
     project type.

     It was demoted behind PES whenever the browser's own encoder would write
     it, because that encoder was the one format we KNEW read a quarter turn
     round AND MIRRORED elsewhere — leaving the most prominent choice as the
     broken one. The codec was put right on 2026-09-08 (both weight tables
     swapped; byte-identical to pystitch, crossval reads `identity`, and a
     rendered "FRITSCH" comes back upright), so the demotion, the asterisk and
     the paragraph it pointed at have all gone with it. -->
<div class="formats">
  <button class="primary" on:click={() => askThenDl("dst")}>DST</button>
  <button on:click={() => askThenDl("pes")}>PES</button>
  <button on:click={() => askThenDl("exp")}>EXP</button>
  <!-- Same caveat convention the DST button above documents: the name stays
       exactly "JEF" so voice control and every existing query still reach it,
       the asterisk is the sighted marker and is aria-hidden, and the note
       itself rides aria-describedby. -->
  <button
    data-testid="jef-button"
    class:caveat={jefHoopNote}
    aria-describedby={jefHoopNote ? "jef-hoop-note" : undefined}
    disabled={!jefAvailable}
    title={jefTitle}
    on:click={() => askThenDl("jef")}
  >JEF{#if jefHoopNote}<span class="caveat-mark" aria-hidden="true">*</span>{/if}</button>
  <!-- Singer and Husqvarna Viking / Pfaff, shipped on Kent's 2026-09-12 scope
       call. Service-only like JEF, so the same disabled-with-a-reason
       treatment; they sit after the four that were already here and before
       SVG, because the machine formats lead and the proof formats follow. No
       asterisk on VP3 — see the script block for why its 0.1 mm is not a
       caveat. -->
  <button
    data-testid="xxx-button"
    disabled={!xxxAvailable}
    title={xxxTitle}
    on:click={() => askThenDl("xxx")}
  >XXX</button>
  <button
    data-testid="vp3-button"
    disabled={!vp3Available}
    title={vp3Title}
    on:click={() => askThenDl("vp3")}
  >VP3</button>
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
{#if jefHoopNote}
  <p class="encodernote" id="jef-hoop-note" data-testid="jef-hoop-header-note">
    <strong>* Heads up about JEF:</strong> {jefHoopNote}
  </p>
{/if}
<!-- BOTH DST caveats are gone as of 2026-09-08, and their absence is asserted
     in DownloadStep.spec.js rather than merely untested.

     They existed for one reason: the browser's own DST encoder wrote a
     private dialect, so a file it produced read a quarter turn round AND
     mirrored in anything but EMB-Bot. That codec is fixed — both record
     weight tables swapped, `encodeRecord` byte-identical to
     `pystitch.DstWriter.encode_record` across ten deltas, the crossval DST
     control reading `identity` beside PES and EXP, and a rendered "FRITSCH"
     export coming back upright at the design's own size. The colour-change
     byte went the same way on 2026-09-07 (`0x43` -> `0xC3`).

     Which encoder wrote a DST no longer changes what the customer gets, so
     the app no longer says. Leaving a warning up after its defect is fixed
     is not the safe side of the trade: it steers people off the format most
     of their machines want, and it teaches them to distrust the ones we keep.
     If a future difference reappears, MEASURE it and write a note about that
     difference — do not restore these. -->
<p>{msg}</p>
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
