<script>
  import { createEventDispatcher, onDestroy, onMount, tick } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import Icon from "./Icon.svelte";
  import { tip } from "../lib/tip.js";
  import { markDigitizeBusy } from "../lib/digitizeBusy.js";
  import { isCapPieceId } from "../lib/capPieces.js";
  import {
    buildDigitizeConfig,
    digitize,
    decodedFromDesignCached,
    describeWarnings,
    SILENT_WARNINGS,
    ATTENTION_WARNINGS,
    canonicalShapeEdits,
    editsKey,
    configKey,
    resizedTargetWidth,
    reviewFromJob,
    reconcileReview,
    reorderWithinLayer,
    effLayer,
    sortShapes,
    effSewOrder,
    layerSiblings,
    effRgb,
    groupIntoBlocks,
    machineBlocksForRows,
    boundaryIssues,
    mergeGroupIssues,
    splitLineIssues,
    textClusterIds,
    textClusterMembers,
    textClusterSeed,
    remapBlockColors,
    stitchWidthGroupRows,
    STITCH_WIDTH_MIN_MM,
    STITCH_WIDTH_MAX_MM,
    spoolCount } from "../lib/digitizer.js";
  import {
    appliedBorders,
    borderRequestPending,
    borderSummaryText,
    borderTally,
    edgeCapState,
    edgeCapSummaryText,
    indexRuns,
    shapeBorderState } from "../lib/borderMenu.js";
  import { loadPalette, nearestInList } from "../lib/threads.js";
  import { loadImage, rasterSize, isVectorFile, uploadPlan, downscaleForService, pngDimensionsFromBase64 } from "../lib/rasterize.js";
  import CropBox from "./CropBox.svelte";
  import { proposeCrop } from "../lib/cropProposal.js";
  import { getSource, putSource, sourceKeyFor, sourceStoreAvailable } from "../lib/sourceStore.js";

  // Editor panel for an auto-digitized artwork element (build step 10).
  // The element stores the source image (processing size, PNG base64), the
  // digitizing params (service field names), and the BAKED result Design —
  // see project.js's defaultDigitizedElement. This panel owns the review
  // loop: upload -> params -> "Auto Digitize Image" -> poll -> result lands
  // on the element. Nothing runs on its own (Kent 2026-10-05): every run is
  // that button, and it goes transparent whenever the element has moved on
  // from the config the result on the canvas was digitized with.
  export let element;
  export let project; // garmentId rides into the config (fabric preset service-side)
  export let health = null; // /health payload or null; App owns the probe
  // Canvas -> list (2026-09-30): the shape under the pointer on the field,
  // and the one selected there. The matching row highlights, and a
  // selection opens the list and scrolls its row into view (revealRow,
  // below the list state). The list -> canvas half is the rows' own
  // mouseenter/mouseleave ("shapehover") and the name button ("shapeselect"),
  // which App routes to the field.
  export let hoverShapeId = null;
  export let selectedShapeId = null;
  // A file picked BEFORE this element existed: "Upload file" opens the OS
  // file browser first and App only adds the element once something is
  // chosen, so the File arrives here as a prop and is ingested on mount.
  // "fileconsumed" tells App to drop it, so a remount cannot ingest it twice.
  export let pendingFile = null;

  const d = createEventDispatcher();

  // PREVIEW size (long edge) — since 2026-09-20 this canvas is what the
  // panel SHOWS and saves with the project, not what it sends. It used to be
  // both, and the pipeline read a raster the customer never made: resampled
  // at Chrome's default smoothing, its RGB under transparency rewritten by
  // the canvas (DOCTRINE 2026-09-19/20; nine logos 503 -> 609 trims). The
  // file's own bytes now go to /digitize (lib/rasterize.js `uploadPlan`) and
  // live in IndexedDB (lib/sourceStore.js). This base64 lives in localStorage
  // with the project, so smaller is a feature: at 1200 px a flat-color logo
  // PNG is typically well under 500 KB.
  const PROCESS_MAX_PX = 1200;
  // Set when a digitize had to send the preview because the original's bytes
  // are gone (cleared site data, another browser): the two digitize
  // differently, so the panel says which one this result came from.
  let sourceNote = "";
  // Storage guard on the stored base64 itself (localStorage isn't infinite —
  // same reasoning as DesignPanel's 1 MB DST cap).
  const MAX_SOURCE_B64 = 2_000_000;

  let error = "";
  let phase = "idle"; // idle | submitting | queued | running
  let fileBusy = false;
  let destroyed = false;
  onDestroy(() => {
    destroyed = true;
  });

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // ---- upload ---------------------------------------------------------------

  function onFile(e) {
    const file = e.currentTarget.files && e.currentTarget.files[0];
    e.currentTarget.value = ""; // re-selecting the same file must re-fire change
    if (file) ingestFile(file);
  }

  onMount(() => {
    if (!pendingFile) return;
    const file = pendingFile;
    d("fileconsumed");
    ingestFile(file);
  });

  async function ingestFile(file) {
    error = "";
    fileBusy = true;
    try {
      const img = await loadImage(file);
      // A vector renders AT the work size, not at whatever default size the
      // browser gave it — see lib/rasterize.js for the measurement.
      const { w, h } = rasterSize(img, PROCESS_MAX_PX, { vector: isVectorFile(file) });
      const cv = document.createElement("canvas");
      cv.width = w;
      cv.height = h;
      cv.getContext("2d").drawImage(img, 0, 0, w, h);
      // Propose a crop from the preview we already drew. Measuring this
      // canvas is fine; SENDING it is the 2026-09-19/20 regression.
      let crop = null;
      try {
        const px = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height);
        crop = proposeCrop(px, (element.params && element.params.target_width_mm) || 80);
      } catch {
        crop = null; // tainted canvas or no 2d context: no proposal, no crash
      }
      const dataUrl = cv.toDataURL("image/png");
      const b64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      if (b64.length > MAX_SOURCE_B64) {
        error = "That image is too heavy to save with the design — the limit is about 1.5 MB after downscaling. Simplify or shrink it and try again.";
        return;
      }
      // The file itself is what digitizes, when the service can decode it and
      // it is within the service's limits; its bytes go to IndexedDB so a
      // re-digitize after a reload sends the same thing. A store that refuses
      // (private window, storage blocked) is not a failed upload — the preview
      // path still works, it is just the pre-2026-09-20 result.
      let sourceFile = null;
      const plan = uploadPlan(file, img, health && health.limits);
      if (plan.asIs && sourceStoreAvailable()) {
        try {
          const bytes = new Uint8Array(await file.arrayBuffer());
          // Asked again WITH the bytes: a JPEG the browser rotated on decode
          // stays on the canvas path (uploadPlan's "orientation").
          if (uploadPlan(file, img, health && health.limits, bytes).asIs) {
            const key = await sourceKeyFor(bytes);
            const type = file.type || plan.type || "";
            await putSource(key, { bytes, type, name: file.name });
            sourceFile = { key, type, size: bytes.length, width: img.width, height: img.height };
          }
        } catch {
          sourceFile = null;
        }
      }
      // Over the service's byte or pixel limit: send the 2,800-px decode it
      // would have made anyway, not the 1,200-px preview (rasterize.js).
      if (!sourceFile && (plan.reason === "bytes" || plan.reason === "pixels") && sourceStoreAvailable()) {
        try {
          const lim = { max_upload_bytes: 12 * 1024 * 1024, ...((health && health.limits) || {}) };
          const small = await downscaleForService(img, lim.max_upload_bytes);
          if (small) {
            const key = await sourceKeyFor(small.bytes);
            await putSource(key, { bytes: small.bytes, type: "image/png", name: file.name });
            sourceFile = { key, type: "image/png", size: small.bytes.length, width: small.width, height: small.height };
          }
        } catch {
          sourceFile = null;
        }
      }
      sourceNote = "";
      // New artwork resets everything the old artwork produced — including
      // the layer list and its edits, which are keyed to the OLD art's
      // shape ids and would only produce SHAPE_EDIT_UNKNOWN_ID noise here.
      patch({
        sourcePng: b64, sourceFile, crop, name: file.name, result: null, warnings: [], blockColors: {}, sizeMm: null,
        review: null, shapeOverrides: {}, deletedShapeIds: [], appliedEdits: null,
        appliedConfig: null, mergeGroups: [], splitLines: {},
      });
    } catch (err) {
      error = String((err && err.message) || err);
    } finally {
      fileBusy = false;
    }
  }

  // ---- digitize -------------------------------------------------------------

  // `el` is passed explicitly (never closed over) so a re-run always reads
  // the element as it is NOW — the blockRgb(element, i) lesson from
  // DesignPanel applies to async work too.
  // Findings that have a KNOB behind them, in the language of the outcome
  // rather than the language of the control. Item 8 asked for presets — "the
  // panel offers knobs where the user has a job" — and Kent's 2026-09-02 call
  // was that they belong AFTER the run, not before it: the panel was
  // deliberately moved away from asking anything up front ("can't we just
  // upload a photo and the tool AUTOMATICALLY recognizes what needs to be
  // done?", 2026-08-30), and a preset picker answered before upload
  // re-introduces exactly that.
  //
  // So this is not a preset list. It is the quality report's own findings,
  // each paired with the one adjustment that addresses it — the app already
  // computes "31 trims" and "sews below readable size"; what was missing was
  // an action.
  //
  // ONE OF THESE BUTTONS RESTS ON A MISQUOTE, and it is recorded here rather
  // than quietly removed. This comment used to read: *"`LETTERING_TOO_SMALL`'s
  // own message ends 'Enlarging helps', and until now nothing offered to
  // enlarge it."* On the day that was written (1c20ec9, 2026-09-02) the
  // message ALREADY read "Enlarging helps BUT DOES NOT FULLY CLEAR IT: the
  // smallest shapes regenerate at any size. Remove or simplify the smallest
  // lettering." The quote stopped at the word where the sentence reverses, and
  // the action it justified ("make it bigger") is not the action the message
  // ends on ("remove or simplify"). Not drift -- wrong on the day it was
  // written, and a truthful substring, which is why no checker catches it.
  //
  // `preflight.py`'s own docstring carries the measurement: over 92.5 -> 220 mm
  // the flagged COUNT falls 38 -> 13 while the median flagged column stays FLAT
  // near 0.8 mm, because segmentation keeps generating sub-millimetre shapes as
  // the design grows. The documented root cause is per-stroke satin routing
  // (`docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`), which is
  // scale-invariant. So enlarging is a real knob that moves a real number, and
  // it is NOT the cure either finding describes.
  //
  // MEASURED, 2026-09-06 (`digitizer/tools/enlarge_cure.py`) -- the ten corpus
  // fixtures that fire STITCHES_TOO_SHORT at 80 mm, swept through one press
  // (100 mm) and two (125 mm):
  //
  //   * one press CLEARED the finding on 1 of 10; two presses on 4 of 10;
  //   * it made the number WORSE on 3 of 10 -- photo_dof_meadow 0.36 -> 0.58
  //     -> 0.71, worse at every press; logo_bridge_bar 0.30 -> 0.36;
  //     photo_sunset_backlit 0.65 -> 0.66;
  //   * the satin SHAPE count rose on EVERY fixture (2 -> 9, 42 -> 71), which
  //     is "the smallest shapes regenerate at any size" seen from the other
  //     side: enlarging buys new small shapes as fast as it widens the ones
  //     already there.
  //
  // Read no grade claim into that. Several checks move with size at once, and
  // 5 of the 10 sit on the clamped score floor where nothing registers either
  // way (`digitizer/tools/floor_depth.py`).
  //
  // Left in place, not removed. The button does what its LABEL says, and
  // whether a one-in-ten remedy earns one is a product call -- Kent's, not a
  // session's. The numbers are here so it is an informed one.
  //
  // DELIBERATELY SHORT, and the omissions are the honest part. Most findings
  // have no knob that helps and get nothing rather than a button that does
  // something adjacent: TRIM_HEAVY's lever is `chain_links`, frozen by gate 1;
  // DENSITY_STACKED has no exposed density control; PHOTO_RESOLUTION_LOW needs
  // better artwork, not a setting. Offering a plausible-looking button there
  // would be worse than silence, because it would be tried.
  //
  // Nothing here contradicts a standing ruling: no fix sets `border: "auto"`
  // (DOCTRINE: +60% stitches and WORSE on a photo), none sets `forced_class`
  // (no Studio control does since 2026-09-30, and forcing flat measured
  // worse on textured logo art before that), and none turns on
  // `edge_cap`, which Kent reserved per design and which no sew-out has
  // settled.
  const FIX_FOR = {
    COLOR_STOPS_HEAVY: {
      label: "Use fewer colors",
      // The slider's own floor is 2; step down by two so one press is a real
      // move rather than a nudge nobody can see in the result.
      next: (p) => ({ max_colors: Math.max(2, (p.max_colors || 6) - 2) }),
      spent: (p) => `${p.max_colors} → ${Math.max(2, (p.max_colors || 6) - 2)} colors`,
    },
    LETTERING_TOO_SMALL: {
      label: "Make it bigger",
      next: (p, f) => ({ target_width_mm: namedOrStep(p, f) }),
      spent: (p, f) => `${Math.round(p.target_width_mm)} → ${namedOrStep(p, f)} mm wide`,
    },
    // Same cure as above, and deduped below so two findings never offer the
    // same button twice.
    STITCHES_TOO_SHORT: {
      label: "Make it bigger",
      next: (p) => ({ target_width_mm: Math.min(400, Math.round((p.target_width_mm || 80) * 1.25)) }),
      spent: (p) => `${Math.round(p.target_width_mm)} → ${Math.min(400, Math.round((p.target_width_mm || 80) * 1.25))} mm wide`,
    },
    // The same cure again (2026-09-10, quality review item 11): the check
    // reads the lettering back off the RENDER and warns when the thread no
    // longer says what the artwork says. Its own remedy line is "Make the
    // lettering bigger or simpler", and size is the half this panel owns —
    // the other half is the artwork, which no button here can change.
    LETTERING_ILLEGIBLE: {
      label: "Make it bigger",
      next: (p, f) => ({ target_width_mm: namedOrStep(p, f) }),
      spent: (p, f) => `${Math.round(p.target_width_mm)} → ${namedOrStep(p, f)} mm wide`,
    },
    // The tight-gaps finding (2026-09-30, Kent's pick) NAMES the width at
    // which its headline shape's gaps clear the fabric's pull plus the
    // thread, so its button jumps straight there instead of stepping 25%:
    // one press clears THAT shape by construction (arithmetic on its
    // polygon; the design can still segment new small shapes at the larger
    // size, which the finding states per shape and never as a promise).
    // Two size buttons would confuse, so `offeredFixes` keeps ONE per
    // parameter and lets the larger target win when this and a 25% step
    // both apply. Without a named width (no shapes in the payload) it takes
    // the same 25% step as the others.
    SATIN_GAPS_TIGHT: {
      label: "Make it bigger",
      next: (p, f) => ({ target_width_mm: namedOrStep(p, f) }),
      spent: (p, f) => `${Math.round(p.target_width_mm)} → ${namedOrStep(p, f)} mm wide`,
    },
  };

  // The width a finding names, capped at the 400 mm ceiling; the 25% step
  // when the payload names none. Two findings name one: SATIN_GAPS_TIGHT's
  // headline shape (`extra.shapes[0].clear_width_mm`, the shape with the most
  // closed gap), and the lettering findings' `extra.traced_at_mm` (2026-09-30:
  // the width at which the prep's grid could trace lettering a low-resolution
  // source lost -- present only when the source sits under the prep floor,
  // where a bigger design gives the tracer more pixels; absent, the step).
  function namedOrStep(p, f) {
    const extra = (f && f.extra) || {};
    const shapes = Array.isArray(extra.shapes) ? extra.shapes : [];
    const fromShape = shapes.length ? shapes[0].clear_width_mm : null;
    const named = typeof fromShape === "number" && fromShape > 0 ? fromShape
                : typeof extra.traced_at_mm === "number" && extra.traced_at_mm > 0 ? extra.traced_at_mm : null;
    const w = named != null ? named : (p.target_width_mm || 80) * 1.25;
    return Math.min(400, Math.round(w));
  }

  function offeredFixes(el) {
    const found = (el && el.preflight && el.preflight.findings) || [];
    const params = (el && el.params) || {};
    const out = [];
    for (const f of found) {
      const fix = FIX_FOR[f.code];
      if (!fix) continue;
      const patch = fix.next(params, f);
      // A fix already at its limit is not offered: "Make it bigger" on a
      // design already at 400 mm would do nothing and cost a full re-digitize.
      const key = Object.keys(patch)[0];
      if (params[key] === patch[key]) continue;
      const offer = { label: fix.label, patch, spent: fix.spent(params, f), why: f.message };
      // ONE button per parameter: findings with the same cure never offer it
      // twice, and when one names a width (SATIN_GAPS_TIGHT) while another
      // steps 25%, the larger target is the one press that serves both.
      const i = out.findIndex((o) => Object.keys(o.patch)[0] === key);
      if (i < 0) out.push(offer);
      else if (key === "target_width_mm" && patch[key] > out[i].patch[key]) out[i] = offer;
    }
    return out;
  }
  $: fixes = offeredFixes(element);

  function applyFix(fix) {
    // Straight through setParam, so it takes the same auto-re-digitize path a
    // knob does and lands as one undo step.
    for (const [k, v] of Object.entries(fix.patch)) setParam(k, v);
  }

  // The five figures a person compares across a re-digitize. Null when there
  // is nothing to compare against -- a first digitize is not "unchanged", it
  // is the baseline, and saying "+0 stitches" there would be a lie dressed as
  // information. Drawn from both sources because neither carries all five:
  // trims live only on the job envelope, score/grade only on preflight.
  function runSnapshot(el) {
    if (!el || !el.result) return null;
    const m = (el.preflight && el.preflight.metrics) || {};
    const st = el.stats || {};
    const snap = {
      stitch_count: el.result.stitchCount,
      color_changes: m.color_changes ?? st.color_changes ?? null,
      trims: typeof st.trims === "number" ? st.trims : null,
      score: el.preflight ? el.preflight.score : null,
      grade: el.preflight ? el.preflight.grade : null,
    };
    return snap;
  }

  // What moved since the last run. Returns [] when nothing did, and the
  // caller renders "no change" for that -- which is the most useful answer
  // this line gives: it means the setting you just changed did nothing to the
  // stitches, and without it a re-digitize that changed nothing is
  // indistinguishable from one that changed everything.
  //
  // Signs are stated from the operator's side, not the engine's: FEWER trims
  // and FEWER stops are wins, so they read as "-6 trims" and the reader does
  // not have to know which direction is good. No colouring on that basis
  // though -- "fewer stitches" is not automatically better (it can mean
  // coverage was lost), so this reports the movement and declines to grade it.
  function runDelta(el) {
    const prev = el && el.priorRun;
    if (!prev || !el.result) return [];
    const m = (el.preflight && el.preflight.metrics) || {};
    const st = el.stats || {};
    const out = [];
    const push = (was, now, one, many) => {
      if (typeof was !== "number" || typeof now !== "number" || was === now) return;
      const d = now - was;
      out.push(`${d > 0 ? "+" : "\u2212"}${Math.abs(d).toLocaleString()} ${Math.abs(d) === 1 ? one : many}`);
    };
    push(prev.stitch_count, el.result.stitchCount, "stitch", "stitches");
    push(prev.color_changes, m.color_changes ?? st.color_changes, "thread change", "thread changes");
    push(prev.trims, typeof st.trims === "number" ? st.trims : undefined, "trim", "trims");
    if (el.preflight && prev.grade && prev.grade !== el.preflight.grade) {
      out.push(`${prev.grade} \u2192 ${el.preflight.grade}`);
    }
    return out;
  }
  $: changed = runDelta(element);
  $: hasPrior = !!(element && element.priorRun && element.result);

  // What goes to the service: the customer's file while its bytes are still
  // here, else the preview PNG — and the panel says so, because the two
  // digitize differently (DOCTRINE 2026-09-19/20: the preview is resampled and
  // its RGB under transparency rewritten).
  async function imageToSend(el) {
    if (el.sourceFile && el.sourceFile.key) {
      let rec = null;
      try {
        rec = await getSource(el.sourceFile.key);
      } catch {
        rec = null;   // a store that will not read is a missing original, not a failed digitize
      }
      if (rec) {
        sourceNote = "";
        return { bytes: rec.bytes, type: rec.type || el.sourceFile.type || "", name: el.name || rec.name || "art" };
      }
      sourceNote = "Digitized from the saved preview — the original file is no longer stored in this browser, and the preview sews a little differently. Replace the artwork with the original for the full result.";
    }
    return el.sourcePng;
  }

  async function runDigitize(el) {
    // The button is disabled while a run is in flight, and "Apply layer
    // changes" with it, so a second call can only be a stray one.
    if (!el.sourcePng || !health || phase !== "idle") return;
    error = "";
    phase = "submitting";
    try {
      // A field resize is a Design width change (resizedTargetWidth): the
      // run digitizes at the dragged width, and the landing patch below
      // makes that the design's own width instead of a scale on top of it.
      const resizeTarget = resizedTargetWidth(el, nativeWidthOf(el));
      const cfg = buildDigitizeConfig(withTargetWidth(el, resizeTarget), project);
      // The preview path is synchronous here on purpose: it is the
      // pre-2026-09-20 flow tick for tick, so nothing about restitch timing
      // moved for an element with no stored original.
      const image = el.sourceFile && el.sourceFile.key ? await imageToSend(el) : el.sourcePng;
      const job = await digitize(image, cfg, {
        onState: (s) => {
          if (!destroyed) phase = s === "running" ? "running" : "queued";
        },
        isCancelled: () => destroyed,
      });
      if (destroyed || !job) return;
      // One patch = one undo step (App.persist snapshots per elupdate).
      // `appliedEdits` records the edits THIS result was digitized with —
      // taken from the submitted cfg, not the live element, so an edit made
      // mid-flight still reads as pending afterwards. The review is
      // reconciled so shapes the user deleted keep a struck-through,
      // restorable row (the fresh review no longer contains them).
      patch({
        result: job.design,
        // The new palette is not the old one, and blockColors is keyed by
        // palette INDEX -- so a per-block thread override has to be carried
        // across by the colour it was chosen for, or it lands on whatever
        // thread now occupies that index. See remapBlockColors for the
        // measurement (a white block exporting as the navy picked for red).
        blockColors: remapBlockColors(
          (el.result && el.result.colors) || [],
          el.blockColors,
          (job.design && job.design.colors) || [],
        ),
        warnings: job.warnings || [],
        review: reconcileReview(
          el.review,
          reviewFromJob(job.review, job.stats && job.stats.blocks),
          el.deletedShapeIds,
        ),
        preflight: job.preflight || null,
        // The service has always returned these (thread metres total and
        // per colour, trims, jumps, colour changes) and the Studio has always
        // dropped them: `result` keeps job.design, not the stats beside it. The
        // review step's shopping list is the first thing to want them.
        stats: job.stats || null,
        // Item 10: keep what the LAST run produced, because this line is the
        // only moment the old numbers still exist -- one statement later they
        // are gone. Read off `el`, the pre-patch element, not off `element`,
        // which a mid-flight edit may already have moved on.
        priorRun: runSnapshot(el),
        appliedEdits: editsKey({
          deleted_shape_ids: cfg.deleted_shape_ids,
          shape_overrides: cfg.shape_overrides,
          merge_shape_ids: cfg.merge_shape_ids,
          split_shapes: cfg.split_shapes,
        }),
        // From the SUBMITTED cfg for the same reason: a setting changed while
        // this run was in flight is not in these stitches, and the button
        // has to come back transparent for it.
        appliedConfig: configKey(cfg),
        ...resizeLanding(el, element, resizeTarget),
      });
    } catch (err) {
      if (!destroyed) error = String((err && err.message) || err);
    } finally {
      if (!destroyed) phase = "idle";
    }
  }

  // NOTHING RE-RUNS ON ITS OWN (Kent's ruling 2026-10-05, replacing his
  // 2026-08-13 "shape edits restitch after a pause" and 2026-08-30 "new
  // artwork digitizes itself"). Four watchers used to live here -- params,
  // a new `sourcePng`, shape edits behind a 2 s debounce, and the crop box --
  // each starting a run. Every run is now the "Auto Digitize Image" button,
  // and what those watchers knew is one comparison instead: the config this
  // element would send NOW against the one its result was digitized with.
  //
  // `appliedConfig` is on the element, not in this component, because
  // ContentStep remounts the panel per selection: a local flag would forget
  // an unapplied change the moment the user clicked another element and back.
  // A project saved before the field existed has a result and no key; it is
  // taken as current as it loads (`mountKey`), since there is nothing to
  // compare it with and a saved design opening "out of date" would be a lie.
  // `hasPendingEdits` (below, off `appliedEdits`) still catches that
  // project's unapplied shape edits.
  const mountKey = configKey(buildDigitizeConfig(element, project));
  // Read against the width a field resize asks for (resizedTargetWidth), so
  // a corner drag turns the button transparent like a typed Design width.
  // `mountKey` stays on the raw element: a project saved resized and never
  // re-run opens transparent, which is the truth about its stitches.
  $: currentKey = configKey(buildDigitizeConfig(withTargetWidth(element, resizeTarget), project));
  $: stale =
    !!element.result &&
    (currentKey !== (element.appliedConfig || mountKey) || hasPendingEdits);

  // The crop box's drag floor, sized to the raster it shows. The service
  // refuses a crop under `digitizer_core/crop.py` MIN_CROP_PX (16) on either
  // axis, and CropBox's own 2% is under that on any preview narrower than
  // 800 px. Read off `sourcePng`'s PNG header, so it survives a reload
  // without a second persisted field. The preview is never larger than the
  // original, so a floor that holds on the preview holds on either raster
  // the service may be sent.
  const CROP_MIN_PX = 16;
  $: cropMinFrac = (() => {
    const dim = pngDimensionsFromBase64(element.sourcePng);
    if (!dim) return 0.02;
    return Math.min(0.5, Math.max(0.02, CROP_MIN_PX / Math.min(dim.width, dim.height)));
  })();

  function setParam(key, value) {
    patch({ params: { ...element.params, [key]: value } });
  }

  // ---- derived view state ---------------------------------------------------

  $: pending = phase !== "idle";
  // The field shows the pinwheel while this run is in flight (lib/digitizeBusy).
  // Keyed by the element the panel is showing; a switch to another element
  // mid-run clears the old id rather than leaving its pinwheel up.
  let busyId = null;
  $: {
    const id = element && element.id;
    if (busyId != null && busyId !== id) markDigitizeBusy(busyId, false);
    busyId = id;
    markDigitizeBusy(id, pending);
  }
  onDestroy(() => markDigitizeBusy(busyId, false));
  // A run in flight OR a change the button has not been pressed for. Both
  // mean the same thing to anything READING the stitch plan — what is on the
  // canvas is the previous request.
  $: restitching = pending || stale;
  $: statusLine =
    phase === "running" ? "Digitizing your art…" :
    phase === "queued" ? "Waiting for the digitizer — another job is running…" :
    phase === "submitting" ? "Sending your art…" : "";

  $: decoded = element.result ? decodedFromDesignCached(element.result) : null;
  $: warningLines = describeWarnings(element.warnings);
  // Three reasons a warning does not reach this list, and only the first is
  // about presentation:
  //
  //   BACKGROUND_ENCLOSED owns its own live, actionable banner (below, next to
  //   unstitchedRows). Showing both would repeat one fact as a static server
  //   message and again as a count that tracks the user's own restores.
  //
  //   SILENT_WARNINGS (digitizer.js) is engine telemetry and internal
  //   diagnostics -- "982 superpixels, 32 after merging", "chart-restricted
  //   weighted k-medoids" -- which fired on 20 of 26 corpus fixtures each,
  //   the two most frequent codes in the whole corpus, straight into this
  //   list. Nothing in them is actionable by the person who uploaded art.
  //
  //   An empty `text` is a translator declining THIS instance: SHAPES_LEFT_
  //   UNSEWN returns "" when every unsewn shape is enclosed background,
  //   because the banner above already said so and said it better. Measured
  //   2026-09-07: on all 10 fixtures that emit it, BACKGROUND_ENCLOSED emits
  //   too.
  //
  // `warningLines` itself keeps every code -- the classification readout
  // below switches on codes there, so filtering upstream would silently
  // disable it.
  $: otherWarningLines = warningLines.filter(
    (w) => w.code !== "BACKGROUND_ENCLOSED" && !SILENT_WARNINGS.has(w.code)
           && w.text);
  // And of what survives, most is the engine saying what it decided rather
  // than anything to act on. A real logo at 80 mm produced TEN lines in one
  // flat list on 2026-09-07 and exactly one of them asked for anything --
  // ten equal bullets read as ten faults in the customer's artwork. The ones
  // that ask stay in the list; the rest go behind a disclosure that says how
  // many there are, so nothing is hidden and nothing is shouted.
  $: attentionLines = otherWarningLines.filter((w) => ATTENTION_WARNINGS.has(w.code));
  $: noteLines = otherWarningLines.filter((w) => !ATTENTION_WARNINGS.has(w.code));

  // ---- what stage 0 made of the art ----------------------------------------
  //
  // Stage 0 classifies every job on its own (flat / gradient / photo_subject /
  // photo_scene) and reports the answer as a CLASSIFIED_* warning; stage
  // 1.25 adds PHOTO_DETECTED when the file's camera header or a face says
  // the art is a photograph (buildDigitizeConfig asks for that detection on
  // every job). The panel STATES the reading in plain words. It asks nothing
  // and offers no correction -- Kent, 2026-09-30: "get rid of the 'it's flat
  // art' / 'it's a photo' check boxes when uploading a photo, logo or
  // ANYTHING ... just automatically recognize what it is, and how it needs to
  // be digitized." That was the second time he asked (2026-08-30: "IDK what
  // ANY of that even means"); the first time the question moved from a
  // pre-upload quiz to a one-click correction on this row, and the
  // correction is what went on 2026-09-30.
  //
  // So there is no `isPhoto` any more: a saved project that still carries it
  // is read as if it did not (buildDigitizeConfig never sends it).
  //
  // The FLAT correction came back the same evening, also Kent's call, after
  // his Instagram icon read as shaded artwork and sewed badly with no way to
  // say otherwise. It is one button on a TONAL reading ("Sew as flat art",
  // writes `params.forced_class = "flat"`) and, on a design that used it, a
  // sentence saying so plus the way back. It is an ordinary digitize param:
  // changing element.params re-digitizes through the params-changed block,
  // so neither control calls runDigitize itself. Stage 0 still misroutes
  // real logos (ROADMAP phase 2); fixing the routing is still the fix.
  //
  // `warningLines` is read INLINE here, not through a `hasCode(...)` helper:
  // these are legacy `$:` statements, whose dependencies are collected
  // syntactically, so a helper would leave this tracking only the (never
  // reassigned) function and the reading would freeze at its first value.
  //
  // Order matters for honesty: the sentence names the TIER the art is sewing
  // in, and stage 0's class decides that. Stage 1.25's PHOTO_DETECTED does
  // not move the tier -- it turns the photographic machinery on (palette
  // bind, depth sequencing) -- so it only gets its own sentence when the
  // class said nothing tonal, and that sentence promises solid regions, not
  // shading. The warning line beside it names WHICH signal fired.
  // Only "flat" counts: any other stored value is a pre-09-30 leftover that
  // buildDigitizeConfig does not send, so the row must not claim it either.
  $: forcedFlat = !!(element.params && element.params.forced_class === "flat");
  $: artRead =
    // The user's own word outranks whatever the engine read, and has to key
    // on the stored param: once it takes effect the art classifies flat and
    // the CLASSIFIED_* warning that offered it is gone.
    forcedFlat ? "forced" :
    // A face routed the design flat (Kent's ruling 2026-09-30): the class IS
    // flat and no CLASSIFIED_* warning exists, so this can lead without
    // shadowing anything; it leads so the sentence names the reason.
    warningLines.some((w) => w.code === "FACE_ROUTED_FLAT") ? "face" :
    warningLines.some((w) => w.code === "CLASSIFIED_PHOTO_SUBJECT" || w.code === "CLASSIFIED_PHOTO_SCENE") ? "photo" :
    warningLines.some((w) => w.code === "CLASSIFIED_GRADIENT") ? "gradient" :
    warningLines.some((w) => w.code === "PHOTO_DETECTED") ? "detected" :
    warningLines.some((w) => w.code === "CLASSIFICATION_UNCERTAIN") ? "unsure" :
    "flat";
  // Whether the art is photographic or shaded content. `detail_layer` reads
  // its lines off the source raster, which is worth offering there and not
  // on a flat logo (Kent's call, 2026-08-30) -- so the control rides this
  // row rather than sitting in the params list beside stitch width. A
  // detected photograph counts even when its tier is flat.
  $: tonalLane = artRead === "photo" || artRead === "gradient" || artRead === "detected"
    || artRead === "face";
  // Flat is offered where the art is sewing down a tonal lane and flat is a
  // real alternative. Not on "face" (already flat) and not on a flat reading.
  $: offerFlat = artRead === "photo" || artRead === "gradient" || artRead === "detected";

  // Back to automatic REMOVES the key rather than nulling it: the params
  // have to come back identical to a design that never set it, or the
  // service's job cache key differs and the revert pays for a run the cache
  // already holds.
  function useAutomatic() {
    const { forced_class, ...rest } = element.params || {};
    patch({ params: rest });
  }

  // Resize honesty (Kent's rule, same as DesignPanel): the field's resize
  // handles SCALE baked stitches, they don't re-digitize — density changes
  // with size. Unlike a .dst import, here the fix is the run button: the
  // dragged width IS the design width until the next run (resizedTargetWidth),
  // so the button goes transparent, Design width shows it, and a run lands
  // the stitches at it.
  $: rotation = element.rotationDeg || 0;
  $: nativeWidthNow = rotatedWidth(decoded, rotation);
  $: scaleFactor = decoded && element.sizeMm ? element.sizeMm / Math.max(0.1, nativeWidthNow) : 1;
  $: resizeTarget = resizedTargetWidth(element, decoded ? nativeWidthNow : 0);
  $: resized = resizeTarget != null;

  function rotatedWidth(dec, deg) {
    if (!dec) return 0.1;
    const rot = ((deg % 360) + 360) % 360;
    if (rot === 0 || rot === 180) return dec.widthMM;
    if (rot === 90 || rot === 270) return dec.heightMM;
    const rad = (rot * Math.PI) / 180;
    return Math.abs(dec.widthMM * Math.cos(rad)) + Math.abs(dec.heightMM * Math.sin(rad));
  }

  // The same width for any element, not only the one on screen — runDigitize
  // is handed the element it was clicked for.
  function nativeWidthOf(el) {
    const dec = el && el.result ? decodedFromDesignCached(el.result) : null;
    return dec ? rotatedWidth(dec, el.rotationDeg || 0) : 0;
  }

  function withTargetWidth(el, target) {
    return target == null ? el : { ...el, params: { ...el.params, target_width_mm: target } };
  }

  // What a landing run writes for a resize it was sent with. Until
  // 2026-10-08 "Re-digitize at N mm" cleared `sizeMm` and set the width and
  // waited for an automatic re-run the 2026-10-05 ruling had removed: the
  // design jumped BACK to its old size on the canvas and nothing ran. Now the
  // run itself carries the width, and only on landing does the scale go.
  // Compared against the live element so an edit made mid-flight survives: a
  // newly typed width is kept, and a second drag keeps its scale (re-read
  // against the new result, so the button stays transparent for it).
  function resizeLanding(sent, live, target) {
    if (target == null) return {};
    const out = {};
    const sentW = sent.params && sent.params.target_width_mm;
    const liveW = live.params && live.params.target_width_mm;
    if (sentW === liveW) out.params = { ...live.params, target_width_mm: target };
    if (live.sizeMm === sent.sizeMm) out.sizeMm = null;
    return out;
  }

  // A typed width replaces a dragged one: the scale goes with it, or the drag
  // would keep overriding the number in the box.
  function setDesignWidth(v) {
    if (resized) patch({ params: { ...element.params, target_width_mm: v }, sizeMm: null });
    else setParam("target_width_mm", v);
  }

  // Same explicit-argument pattern as DesignPanel's blockRgb.
  function blockRgb(el, i) {
    const o = (el.blockColors || {})[i];
    if (o) return o;
    const c = ((el.result && el.result.colors) || [])[i] || { r: 0, g: 0, b: 0 };
    return [c.r || 0, c.g || 0, c.b || 0];
  }

  function blockName(el, i) {
    const c = ((el.result && el.result.colors) || [])[i];
    return (c && c.name) || "Color " + (i + 1);
  }

  function pickBlock(i, rgb) {
    patch({ blockColors: { ...(element.blockColors || {}), [i]: rgb } });
  }

  // Thread per color lists SPOOLS, not sew blocks (2026-09-30). The design
  // edge re-loads a cone, so a two-spool logo sews three blocks, and the
  // list named "1720 Not Quite Red" twice — a customer reading it as what to
  // buy buys a spool they have (the same rule the summary and the review's
  // shopping list already follow: a colour is a cone to buy). Grouped by
  // the cone's name and colour; a pick applies to every block of that
  // spool, since on the machine they are one spool.
  $: spoolRows = spoolGroups(element);
  function spoolGroups(el) {
    const colors = (el.result && el.result.colors) || [];
    const groups = new Map();
    colors.forEach((c, i) => {
      const key = blockName(el, i) + "|" + [c.r || 0, c.g || 0, c.b || 0].join(",");
      if (!groups.has(key)) groups.set(key, { name: blockName(el, i), first: i, blocks: [] });
      groups.get(key).blocks.push(i);
    });
    return [...groups.values()];
  }
  function pickSpool(g, rgb) {
    const next = { ...(element.blockColors || {}) };
    for (const i of g.blocks) next[i] = rgb;
    patch({ blockColors: next });
  }

  const FILL_ANGLES = [
    { value: null, label: "Auto (per shape)" },
    { value: 0, label: "0°" },
    { value: 30, label: "30°" },
    { value: 45, label: "45°" },
    { value: 60, label: "60°" },
    { value: 90, label: "90°" },
    { value: 135, label: "135°" },
  ];

  function onAngleChange(e) {
    const v = e.currentTarget.value;
    setParam("fill_angle_deg", v === "auto" ? null : parseFloat(v));
  }

  // ---- the Layers list (shape-layers contract v1) ---------------------------
  //
  // One row per shape, keyed by shape_id — the engine's assign_shape_ids
  // re-derives the same id from the same content, which is what makes these
  // survive a re-digitize (not match_shape_ids, which is unwired). Edits
  // accumulate on the
  // element (shapeOverrides / deletedShapeIds) and only restitch on Apply —
  // the review payload the rows render from is the LAST job's, so live-
  // editing it would show stitches that don't exist yet.

  // Collapsed by default: the Sequencer is a secondary view over the same
  // data the Layers list already shows (one row per color block instead of
  // one row per shape) — opt-in so it doesn't push the primary list down
  // for anyone who never opens it.
  let sequencerOpen = false;

  // Same reasoning one level up: the per-shape rows are the panel's DEEPEST
  // control surface and its least-used one, so they open on request rather
  // than on arrival. `{#key el.id}` in ContentStep remounts this component per
  // element, so this resets when you switch designs -- which is what you want,
  // since "I was editing shapes" does not carry from one artwork to another.
  let layersOpen = false;
  let layerListEl = null;
  // Three tabs once there is a result (2026-09-30, the last item of Kent's
  // design review): Settings — what you turn and what the run said;
  // Shapes — the Layers list and its editors; Threads — the spools. One
  // column had grown to 1,738px at 1440x900 with all of it stacked, and the
  // customer's question ("what do I change?") was buried under the expert's
  // list. Resets with the panel, which `{#key el.id}` remounts per element.
  let tab = "settings";
  // A shape picked on the canvas is found in the list: open it if it was
  // closed, then bring the row into view. `nearest` so a row already on
  // screen does not jump, and a row the user just clicked (which also
  // arrives here, via App) is a no-op. Matched by walking the rows rather
  // than an attribute selector so an id needs no escaping.
  $: if (selectedShapeId) revealRow(selectedShapeId);
  async function revealRow(id) {
    tab = "shapes";
    layersOpen = true;
    await tick();
    if (!layerListEl) return;
    for (const li of layerListEl.querySelectorAll("[data-shape-id]")) {
      if (li.dataset.shapeId === String(id)) {
        if (typeof li.scrollIntoView === "function") li.scrollIntoView({ block: "nearest" });
        return;
      }
    }
  }

  // What the design-level border setting is called in a per-shape row's
  // "Design (...)" option. null is the automatic default and has no bare word
  // of its own, so it gets one here rather than rendering "Design ()".
  function borderLabel(v) {
    return v == null ? "automatic" : v;
  }

  const SHAPE_ANGLES = [{ value: null, label: "Auto angle" }, ...FILL_ANGLES.slice(1)];

  // Underlay style (shape-layers contract v1): fabrics.py's own vocabulary,
  // "none" included. Fill/contour-classified shapes only — a satin shape's
  // underlay is a separate, fabric-driven knob this override does not touch
  // (digitizer_core/config.py's shape_overrides docstring), so the control
  // only shows for tier === "fill" below, same as the fill-angle dropdown.
  const SHAPE_UNDERLAYS = [
    { value: null, label: "Auto underlay" },
    { value: "none", label: "None" },
    { value: "edge_run", label: "Edge run" },
    { value: "center_run", label: "Center run" },
    { value: "edge_lattice", label: "Edge + lattice" },
    { value: "edge_zigzag", label: "Edge + zigzag" },
    { value: "double_lattice", label: "Double lattice" },
    { value: "zigzag", label: "Zigzag" },
    { value: "cross_tatami", label: "Crossing pass (pro)" },
  ];

  $: overrides = element.shapeOverrides || {};
  $: deletedIds = element.deletedShapeIds || [];
  $: reviewShapes = (element.review && element.review.shapes) || [];
  $: orderedShapes = sortShapes(reviewShapes, overrides);
  $: knownIds = new Set(reviewShapes.map((s) => s.id));
  $: unmatchedCount = new Set(
    [...Object.keys(overrides), ...deletedIds].filter((sid) => !knownIds.has(sid) && !isCapPieceId(sid))
  ).size;
  // Pending = the element's canonical edits differ from the ones the current
  // result was digitized with. Canonical on both sides, so a toggled-then-
  // untoggled edit reads as "nothing pending", exactly like the job cache.
  $: hasPendingEdits =
    reviewShapes.length > 0 &&
    editsKey(canonicalShapeEdits(element)) !== (element.appliedEdits || editsKey({}));

  // The shapes a within-layer reorder may touch: not hidden, not sitting out
  // as an unstitched enclosed area — the same live subset the up/down
  // buttons render for.
  $: sewableShapes = orderedShapes.filter(
    (r) => !deletedIds.includes(r.id) && effStitched(r, overrides)
  );

  // ---- borders, as SEWN rather than as asked for ---------------------------
  //
  // Everything else in this panel about borders is the REQUEST — the two
  // selects and the per-row one write `params.border` / `shapeOverrides[sid]
  // .border`, and until now the panel read those straight back and called it
  // the answer. The engine declines: a satin-tiered shape never gets a border,
  // a shape too narrow for a column gets a bean run, a narrower one gets
  // nothing. `design.runs` (contract 2026-09-15) is the read-back; lib/
  // borderMenu.js turns it into states, and NULL when the payload has no runs,
  // which every line below renders as "requested" rather than "sewn".
  //
  // Recomputed only when the result, the review or the overrides change — the
  // walk is over runs (hundreds), not stitches (tens of thousands), and the
  // stitch records it does touch are only the edge cap's own span.
  $: runIndex = indexRuns(element.result, knownIds);
  $: appliedBorderSet = appliedBorders(element.appliedEdits);
  $: borderCounts = borderTally({
    rows: sewableShapes,
    overrides,
    designBorder: element.params.border,
    index: runIndex,
  });
  $: borderLine = borderSummaryText(borderCounts, element.params.border);
  $: edgeCap = edgeCapState({
    mode: element.params.edge_cap,
    warnings: element.warnings,
    index: runIndex,
  });
  $: edgeCapLine = edgeCapSummaryText(edgeCap);

  // One row's border state. `row.tier` deliberately, not `effTier` — this is
  // about what the CURRENT stitches did, and effTier folds in a forced tier
  // that has not been stitched yet.
  function borderStateFor(row) {
    return shapeBorderState({
      shapeId: row.id,
      entry: overrides[row.id],
      designBorder: element.params.border,
      index: runIndex,
      tier: row.tier,
      pending: borderRequestPending(appliedBorderSet, row.id, overrides[row.id]),
    });
  }

  // The Sequencer view's color blocks: `sewableShapes` grouped by effLayer,
  // in sew order (the same list moveShape's up/down buttons walk, just
  // collapsed one row per color instead of one row per shape) — a block IS
  // one color's whole run before the machine changes thread. Dead/hidden/
  // unstitched shapes don't have a real place in the sew sequence, so they
  // never appear here even though they're still in the plain Layers list.
  $: sequencerBlocks = groupIntoBlocks(sewableShapes, overrides);

  // The machine's own cone list — `stats.blocks`, one per sewn block in sew
  // order (service contract 2026-09-04). The rows above are what the user
  // REORDERS (one per colour layer); this is what the operator LOADS, and the
  // two differ on a gradient: a blend-tier layer sews as one block per
  // accepted shade, four or five threads under one swatch. The header says
  // so, and a row that sews as several threads lists them. Empty on a job
  // from before the field existed, which leaves the header as it was.
  $: machineBlocks =
    element.stats && Array.isArray(element.stats.blocks) ? element.stats.blocks : [];

  // Server-computed, read-only (preflight.py's own report) — surfaced here
  // rather than left buried in `element.preflight`, since block-boundary
  // trims are exactly what the Sequencer view lets a user reason about and
  // Ember's equivalent panel has no counterpart for at all. null (not 0)
  // when no job has run preflight yet, so the header can tell "clean" apart
  // from "never checked" the same way the rest of this field does.
  $: trimsPer1000 = (element.preflight && element.preflight.metrics
    ? element.preflight.metrics.trims_per_1000
    : null);
  $: trimHeavy = !!(element.preflight && element.preflight.findings || []).some(
    (f) => f.code === "TRIM_HEAVY"
  );

  // Whether the shape sews at all — DISTINCT from `dead` (a user hid it):
  // this is the digitizer's own BACKGROUND_ENCLOSED default (contract v1.1,
  // reviewFromJob's `stitched`), which an override can restore or re-skip.
  // An override wins outright; absent one, the row's own default applies
  // (`true` when the server predates the field, same reading reviewFromJob
  // gives it).
  function effStitched(row, ov) {
    const e = ov[row.id] || {};
    if (typeof e.stitched === "boolean") return e.stitched;
    return row.stitched !== false;
  }

  // The tier the shape will sew as: a forced tier wins; otherwise the tier
  // the engine's plan actually emitted (review.tier — read off the plan, not
  // re-derived). null = the shape produced no stitches.
  function effTier(row, ov) {
    const e = ov[row.id] || {};
    return e.tier && e.tier !== "auto" ? e.tier : row.tier;
  }

  function overrideTier(row, ov) {
    const e = ov[row.id] || {};
    return e.tier || "auto";
  }

  function overrideAngle(row, ov) {
    const e = ov[row.id] || {};
    return e.fill_angle_deg == null ? "auto" : String(e.fill_angle_deg);
  }

  // Per-shape border override (shape_overrides[sid].border, contract v1 —
  // engine-supported since the landing commit, this select is its first UI).
  // Unlike tier, "auto" is a REAL override value here, not the no-override
  // spelling: it forces the border decision back on for one shape even when
  // the design-wide Border param is "off" (canonicalShapeEdits keeps it, the
  // service applies it — _BORDER_VALUES in digitizer_service/app.py). So the
  // no-override sentinel is its own word, "default" = sew the design-wide
  // Border setting.
  function overrideBorder(row, ov) {
    const e = ov[row.id] || {};
    return e.border == null ? "default" : e.border;
  }

  function setShapeBorder(sid, v) {
    setOverride(sid, { border: v === "default" ? null : v });
  }

  // Per-shape underlay-style override (shape_overrides[sid].underlay_style,
  // shape-layers contract v1). Unlike border, it has no "auto" override
  // spelling of its own — absence of the key IS "use the design setting" —
  // so "auto" is only ever the no-override sentinel here.
  function overrideUnderlay(row, ov) {
    const e = ov[row.id] || {};
    return e.underlay_style == null ? "auto" : e.underlay_style;
  }

  // Per-shape stitch width (shape_overrides[sid].stitch_width_mm, contract
  // v1.8). The engine measures every column-shaped shape, gives the letters
  // of a detected word one shared width, and reports all of it in
  // `row.stitchWidth` (reviewFromJob). The input here holds the OVERRIDE
  // only; empty means "auto", and the placeholder shows what auto sews so
  // the user has a starting number rather than a blank box.
  //
  // A shape in a word takes its edit for the WHOLE word by default —
  // Kent's rule (2026-09-29): letters that belong together must not sew at
  // varying widths. `wordScope` holds the ids the user has narrowed to
  // "this shape only"; absent means the word.
  let wordScope = new Set();
  // Ids are content-derived, so a scope narrowed on one design could
  // otherwise outlive it and land on another design's shape.
  let wordScopeFor = null;
  $: if (element && element.id !== wordScopeFor) {
    wordScopeFor = element.id;
    wordScope = new Set();
  }

  function overrideStitchWidth(row, ov) {
    const e = ov[row.id] || {};
    return typeof e.stitch_width_mm === "number" ? e.stitch_width_mm : null;
  }

  // The rows one edit reaches: the shape's word unless narrowed.
  function stitchWidthTargets(row) {
    const rows = wordScope.has(row.id) ? [row] : stitchWidthGroupRows(sewableShapes, row);
    return rows.length ? rows : [row];
  }

  function setShapeStitchWidth(row, raw) {
    const txt = String(raw == null ? "" : raw).trim();
    let v = null;
    if (txt !== "") {
      v = Math.round(parseFloat(txt) * 100) / 100;
      if (!Number.isFinite(v)) return;
      v = Math.min(STITCH_WIDTH_MAX_MM, Math.max(STITCH_WIDTH_MIN_MM, v));
    }
    // One element patch for the whole word = one undo step, one restitch.
    const cur = { ...(element.shapeOverrides || {}) };
    for (const r of stitchWidthTargets(row)) {
      const entry = { ...(cur[r.id] || {}) };
      if (v == null) delete entry.stitch_width_mm;
      else entry.stitch_width_mm = v;
      if (Object.keys(entry).length) cur[r.id] = entry;
      else delete cur[r.id];
    }
    patch({ shapeOverrides: cur });
  }

  function toggleWordScope(row) {
    const next = new Set(wordScope);
    if (next.has(row.id)) next.delete(row.id);
    else next.add(row.id);
    wordScope = next;
  }

  function fmtMm(v) {
    return typeof v === "number" ? (Math.round(v * 100) / 100).toFixed(2) : "";
  }

  // The sentence under the input: what auto measured and chose, and
  // whether the engine could honour the last request in full.
  function stitchWidthNote(row, ov) {
    const w = row.stitchWidth;
    if (!w) return "";
    const parts = [];
    if (w.group) {
      const n = stitchWidthGroupRows(sewableShapes, row).length;
      parts.push(n > 1 ? `shared by ${n} shapes in this word` : "in a word");
    }
    // A shape the plan sews as a RUN is a bean on its own outline, with no
    // column and no pull — its number is the artwork stroke, and the way to
    // a satin column is a width. Everything else reads the sewn column.
    if (row.tier === "run" && typeof w.artMm === "number") {
      parts.push(`${fmtMm(w.artMm)} mm stroke, sewn as a thin run — set a width for a satin column`);
    } else if (typeof w.measuredMm === "number") {
      parts.push(`measured ${fmtMm(w.measuredMm)} mm`);
    }
    if (w.source === "group" || w.source === "floor") parts.push(`evened to ${fmtMm(w.sewnMm)} mm`);
    if (w.limited) parts.push("kept short of the request so a counter or gap stays open");
    if (w.skipReason === "gap_or_hole_would_close") parts.push("could not widen: a gap or counter would close");
    else if (w.skipReason === "would_split_or_vanish") parts.push("could not narrow that far");
    else if (w.skipReason === "below_fabric_pull") parts.push("this fabric's pull alone sews wider than that");
    else if (w.skipReason === "hand_edited_outline") parts.push("outline was hand-edited, auto left it alone");
    return parts.join(" · ");
  }

  function rowName(row) {
    return row.threadNumber ? "#" + row.threadNumber : "Shape";
  }

  // The accessible name for every control in ONE shape row.
  //
  // rowName() alone is the thread number, which every shape in a colour
  // shares — on a two-colour logo that left 29 merge checkboxes with 2
  // distinct names between them, and 27 controls each called just "Stitch
  // type". Nothing said WHICH shape a control acted on, so the list was
  // unusable by screen reader and unaddressable by voice ("click Sew later"
  // was ambiguous 27 ways).
  //
  // The ordinal leads because it is the part a person can say out loud and
  // the only part guaranteed unique; the thread number and area follow
  // because they are what the row shows on screen, so what is heard matches
  // what is seen.
  function rowLabel(row, i, total) {
    const parts = [`shape ${i + 1} of ${total}`];
    if (row.threadNumber) parts.push("thread #" + row.threadNumber);
    const area = fmtArea(row.areaMm2);
    if (area) parts.push(area);
    return parts.join(", ");
  }

  function fmtArea(a) {
    if (a == null) return "";
    return (a >= 100 ? Math.round(a) : a.toFixed(1)) + " mm²";
  }

  // Tiny outline thumbnail: the stored review keeps a decimated outline per
  // shape (thinOutline), scaled here into a 24-box. Image-space mm is y-down
  // and so is SVG, so no flip — the thumb matches the artwork.
  function thumbPath(row) {
    const pts = row.outline || [];
    if (pts.length < 3) return "";
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [x, y] of pts) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    const s = 20 / Math.max(maxX - minX, maxY - minY, 0.001);
    const ox = (24 - (maxX - minX) * s) / 2;
    const oy = (24 - (maxY - minY) * s) / 2;
    return (
      pts
        .map(
          ([x, y], i) =>
            (i ? "L" : "M") + ((x - minX) * s + ox).toFixed(1) + " " + ((y - minY) * s + oy).toFixed(1)
        )
        .join(" ") + " Z"
    );
  }

  // Merge fields into one shape's override entry; null (and tier "auto")
  // clears a field, an emptied entry disappears entirely. Every call is one
  // element patch = one undo step (App's 500 ms coalescing merges rapid
  // clicks, same as any slider).
  function setOverride(sid, fields) {
    const cur = { ...(element.shapeOverrides || {}) };
    const entry = { ...(cur[sid] || {}), ...fields };
    for (const k of Object.keys(entry)) {
      if (entry[k] == null || (k === "tier" && entry[k] === "auto")) delete entry[k];
    }
    if (Object.keys(entry).length) cur[sid] = entry;
    else delete cur[sid];
    patch({ shapeOverrides: cur });
  }

  function setShapeTier(sid, v) {
    setOverride(sid, { tier: v === "auto" ? null : v });
  }

  function setShapeAngle(sid, v) {
    setOverride(sid, { fill_angle_deg: v === "auto" ? null : parseFloat(v) });
  }

  function setShapeUnderlay(sid, v) {
    setOverride(sid, { underlay_style: v === "auto" ? null : v });
  }

  // Recolor: ThreadPicker hands back an rgb; the engine wants an index into
  // the chart of the job's brand. The app's brand lists and the service's
  // chart_data are generated from the same source in the same order
  // (digitizer_core/threads.py points back at threadBrandsIndex.js), so
  // nearest-in-the-brand-list IS the chart index. rgb rides along app-side
  // for the swatch; canonicalShapeEdits strips it before the wire.
  async function recolorShape(sid, rgb) {
    const brand = (element.review && element.review.brandId) || "isacord";
    try {
      const pal = await loadPalette(brand);
      if (pal.id !== brand) throw new Error("chart mismatch");
      const n = nearestInList(pal.threads, rgb);
      setOverride(sid, { thread_index: n.index, rgb: [...n.rgb] });
    } catch (e) {
      error = "Couldn't match that color to the job's thread chart (" + brand + ").";
    }
  }

  function deleteShape(sid) {
    if (deletedIds.includes(sid)) return;
    patch({ deletedShapeIds: [...deletedIds, sid] });
  }

  function restoreShape(sid) {
    patch({ deletedShapeIds: deletedIds.filter((id) => id !== sid) });
  }

  // Restore-equivalent for a `stitched: false` (BACKGROUND_ENCLOSED) row:
  // an explicit override, not deletedShapeIds — the shape was never hidden
  // by the user, so restoring it is never a matter of un-hiding it.
  function restoreStitching(sid) {
    setOverride(sid, { stitched: true });
  }

  // Send an override-restored shape back to the digitizer's own default
  // (clearing the key, not forcing `false` — same "auto" convention as
  // setShapeTier/setShapeAngle) — for a user who restored one by mistake.
  function unrestoreStitching(sid) {
    setOverride(sid, { stitched: null });
  }

  // "Sew earlier/later" ACROSS layers, within what the integer layer field
  // can express: join the adjacent row's layer when it differs; when the
  // neighbour already shares this layer, step past the whole group instead
  // — order WITHIN a layer is a SEPARATE control (moveShapeWithinLayer,
  // sew_order, contract v1.2) below, not this one.
  function moveShape(row, dir) {
    const rows = orderedShapes;
    const i = rows.findIndex((r) => r.id === row.id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= rows.length) return;
    const mine = effLayer(row, overrides);
    const theirs = effLayer(rows[j], overrides);
    let target = theirs !== mine ? theirs : mine + dir;
    // Joining a layer places the shape by its emitted sew position WITHIN
    // that layer, which can re-sort it right back where it was (measured in
    // the live probe: a restored shape "moved earlier" into the last block
    // and stayed visually last). If the join wouldn't move the row, step
    // past the neighbour's whole layer instead — a click always moves.
    const test = { ...overrides, [row.id]: { ...(overrides[row.id] || {}), layer: target } };
    if (sortShapes(reviewShapes, test).findIndex((r) => r.id === row.id) === i) {
      target = theirs + dir;
    }
    setOverride(row.id, { layer: target });
  }

  // "Sew earlier/later" WITHIN one color layer (contract v1.2): reorders the
  // shapes sharing `row`'s effective layer via the sew_order override —
  // distinct from moveShape above, which moves a shape to a DIFFERENT layer.
  // The whole layer's order is committed at once (reorderWithinLayer's
  // contract), one patch = one undo step, the same as every other edit here.
  function moveShapeWithinLayer(row, dir) {
    const siblingIds = layerSiblings(row, sewableShapes, overrides).map((r) => r.id);
    const next = reorderWithinLayer(siblingIds, row.id, dir);
    if (!next) return;
    const cur = { ...(element.shapeOverrides || {}) };
    for (const sid of Object.keys(next)) {
      cur[sid] = { ...(cur[sid] || {}), sew_order: next[sid] };
    }
    patch({ shapeOverrides: cur });
  }

  // Sequencer view: "sew this whole color earlier/later" — moves every
  // shape in one block past every shape in the adjacent block in one step.
  // Unlike moveShape (one row, which has to decide whether it's JOINING an
  // existing group or stepping past it), swapping two whole blocks' layer
  // numbers is unambiguous: each block keeps its own internal sew_order
  // untouched, only which layer integer it carries changes. One patch = one
  // undo step, the same convention every other edit in this panel follows.
  function moveBlock(layer, dir) {
    const layers = sequencerBlocks.map((b) => b.layer);
    const i = layers.indexOf(layer);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= layers.length) return;
    const other = layers[j];
    const cur = { ...(element.shapeOverrides || {}) };
    for (const row of sewableShapes) {
      const rl = effLayer(row, overrides);
      if (rl === layer) cur[row.id] = { ...(cur[row.id] || {}), layer: other };
      else if (rl === other) cur[row.id] = { ...(cur[row.id] || {}), layer };
    }
    patch({ shapeOverrides: cur });
  }

  // A stale edit (the art changed under it — e.g. a re-digitize at a new
  // width regenerates shape ids) keeps its warning until the user clears it;
  // silently dropping a user's edit is the one thing this panel never does.
  function clearUnmatched() {
    const keep = {};
    for (const sid of Object.keys(overrides)) if (knownIds.has(sid) || isCapPieceId(sid)) keep[sid] = overrides[sid];
    patch({
      shapeOverrides: keep,
      deletedShapeIds: deletedIds.filter((sid) => knownIds.has(sid) || isCapPieceId(sid)),
    });
  }

  // ---- boundary edit mode (shape-layers contract v1.4) ----------------------
  //
  // Reshape one shape's outline on a small SVG canvas of its own: drag a
  // vertex, click an edge midpoint to add one, right-click a vertex to
  // remove it. Purely local UI state — never part of `element` — until
  // "Save boundary" merges the result into shapeOverrides through the exact
  // same setOverride/Apply-layer-changes flow every other edit here uses.
  // The mm/y-down coordinate space is the review payload's own (outline_mm),
  // so the SVG viewBox needs no flip — same reasoning as thumbPath above.
  let editingId = null;
  let editPoints = [];
  let dragIndex = null;
  let svgEl;

  $: editIssues = editingId ? boundaryIssues(editPoints) : [];
  $: editViewBox = fitViewBox(editPoints);
  $: editHandleR = Math.max(editViewBox.w, editViewBox.h) / 45;
  $: editMidpoints = editPoints.map((p, i) => {
    const q = editPoints[(i + 1) % editPoints.length];
    return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
  });

  function fitViewBox(pts) {
    if (!pts || !pts.length) return { minX: -5, minY: -5, w: 10, h: 10 };
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [x, y] of pts) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    const w = Math.max(maxX - minX, 0.001);
    const h = Math.max(maxY - minY, 0.001);
    const pad = Math.max(w, h) * 0.18 + 0.5;
    return { minX: minX - pad, minY: minY - pad, w: w + pad * 2, h: h + pad * 2 };
  }

  function round3(v) {
    return Math.round(v * 1000) / 1000;
  }

  // Continue from a PENDING (not yet applied) hand edit if one is already
  // sitting in shapeOverrides — same "resume where you left off" reading
  // every other control here has (overrideAngle/overrideTier read the
  // pending value the same way) — else the shape's current outline, which
  // already reflects the last APPLIED boundary_override if there was one.
  function startBoundaryEdit(row) {
    cancelSplitEdit(); // the two editors replace the same list view; only one at a time
    const ov = overrides[row.id] || {};
    const pending = Array.isArray(ov.boundary_override) && ov.boundary_override.length >= 3
      ? ov.boundary_override
      : null;
    const src = pending || row.outlineFull || row.outline || [];
    editingId = row.id;
    editPoints = src.map((p) => [p[0], p[1]]);
    dragIndex = null;
  }

  function cancelBoundaryEdit() {
    editingId = null;
    editPoints = [];
    dragIndex = null;
  }

  function saveBoundaryEdit() {
    if (!editingId || editIssues.length) return;
    setOverride(editingId, { boundary_override: editPoints.map(([x, y]) => [x, y]) });
    editingId = null;
    editPoints = [];
    dragIndex = null;
  }

  // Undo a previous hand edit back to the digitizer's own outline for this
  // shape (the "auto" convention every other override control uses).
  function resetBoundaryEdit() {
    if (!editingId) return;
    setOverride(editingId, { boundary_override: null });
    editingId = null;
    editPoints = [];
    dragIndex = null;
  }

  function svgPointIn(el, evt) {
    if (!el) return [0, 0];
    const pt = el.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    const ctm = el.getScreenCTM();
    if (!ctm) return [0, 0];
    const p = pt.matrixTransform(ctm.inverse());
    return [p.x, p.y];
  }

  function svgPoint(evt) {
    return svgPointIn(svgEl, evt);
  }

  function startEditDrag(e, i) {
    e.preventDefault();
    dragIndex = i;
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch (err) {
      // Pointer capture is unavailable in some test/embedded environments;
      // dragging still works off plain pointermove, just less robustly at
      // the edge of the SVG.
    }
  }

  function onEditPointerMove(e) {
    if (dragIndex == null) return;
    const [x, y] = svgPoint(e);
    editPoints[dragIndex] = [round3(x), round3(y)];
    editPoints = editPoints;
  }

  function endEditDrag() {
    dragIndex = null;
  }

  function addEditVertex(i) {
    const n = editPoints.length;
    const a = editPoints[i];
    const b = editPoints[(i + 1) % n];
    const mid = [round3((a[0] + b[0]) / 2), round3((a[1] + b[1]) / 2)];
    editPoints = [...editPoints.slice(0, i + 1), mid, ...editPoints.slice(i + 1)];
  }

  // Floor matches the server's MIN_BOUNDARY_POINTS (regions.py) — a click
  // that would cross it is simply ignored, not an error state.
  function removeEditVertex(e, i) {
    e.preventDefault();
    if (editPoints.length <= 3) return;
    editPoints = editPoints.filter((_, idx) => idx !== i);
    if (dragIndex === i) dragIndex = null;
  }

  // Keyboard equivalents for the two drag/click-only interactions above —
  // every handle here is a real tabbable element (role="button", tabindex
  // 0), not just a pointer target.
  function nudgeStep(vb) {
    return Math.max(vb.w, vb.h) / 200;
  }
  function nudgeStepMm() {
    return nudgeStep(editViewBox);
  }

  function onEditVertexKeydown(e, i) {
    const step = nudgeStepMm();
    const [x, y] = editPoints[i];
    if (e.key === "ArrowLeft") { e.preventDefault(); editPoints[i] = [round3(x - step), y]; editPoints = editPoints; }
    else if (e.key === "ArrowRight") { e.preventDefault(); editPoints[i] = [round3(x + step), y]; editPoints = editPoints; }
    else if (e.key === "ArrowUp") { e.preventDefault(); editPoints[i] = [x, round3(y - step)]; editPoints = editPoints; }
    else if (e.key === "ArrowDown") { e.preventDefault(); editPoints[i] = [x, round3(y + step)]; editPoints = editPoints; }
    else if (e.key === "Delete" || e.key === "Backspace") { removeEditVertex(e, i); }
  }

  function onEditMidKeydown(e, i) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      addEditVertex(i);
    }
  }

  // ---- shape identity edits (contract v1.5): merge and split ----------------
  //
  // The other half of the shape-recognition gap `boundary_override` (above)
  // did not touch: that reshapes ONE shape's outline, this changes the SET of
  // shapes. Both ride the exact same setOverride-adjacent pattern the rest of
  // this panel uses — local UI state until a save action merges the result
  // into an ELEMENT field (`mergeGroups` / `splitLines`, siblings of
  // `shapeOverrides`), which only restitches through the existing "Apply
  // layer changes" flow. `canonicalShapeEdits`/`editsKey` (digitizer.js)
  // already fold both fields into the same pending-edit diff every other
  // override here drives off, so no new Apply-button wiring is needed.

  // -- merge: select 2+ same-thread rows, then commit as one group ----------
  let mergeSelection = [];

  function toggleMergeSelect(id) {
    mergeSelection = mergeSelection.includes(id)
      ? mergeSelection.filter((s) => s !== id)
      : [...mergeSelection, id];
  }

  $: mergeSelectedRows = orderedShapes.filter((r) => mergeSelection.includes(r.id));
  $: mergeIssues = mergeSelection.length ? mergeGroupIssues(mergeSelectedRows) : [];

  function commitMerge() {
    if (mergeIssues.length || mergeSelection.length < 2) return;
    const ids = [...mergeSelection].sort();
    const key = JSON.stringify(ids);
    const existing = element.mergeGroups || [];
    if (existing.some((g) => JSON.stringify([...g].sort()) === key)) {
      mergeSelection = [];
      return;
    }
    patch({ mergeGroups: [...existing, ids] });
    mergeSelection = [];
  }

  function clearMergeSelection() {
    mergeSelection = [];
  }

  // A merged/split row's provenance comes from the LAST APPLIED job's own
  // warnings (`SHAPES_MERGED_BY_USER`/`SHAPE_SPLIT_BY_USER`, `groups` extra),
  // not from re-deriving the deterministic id here — the server already did
  // the work and said exactly which sources produced which result id.
  function mergedFromInfo(rowId) {
    const w = (element.warnings || []).find((x) => x.code === "SHAPES_MERGED_BY_USER");
    const groups = (w && w.groups) || [];
    return groups.find((g) => g.into === rowId) || null;
  }

  function splitFromInfo(rowId) {
    const w = (element.warnings || []).find((x) => x.code === "SHAPE_SPLIT_BY_USER");
    const groups = (w && w.groups) || [];
    return groups.find((g) => (g.into || []).includes(rowId)) || null;
  }

  // Undo an APPLIED merge: remove the stored source-id group so the next
  // Apply regenerates the original shapes instead of re-merging them — the
  // same "auto" convention (clear the override, don't invert it) every other
  // control here uses.
  function undoMerge(rowId) {
    const info = mergedFromInfo(rowId);
    if (!info) return;
    const key = JSON.stringify([...info.from].sort());
    patch({
      mergeGroups: (element.mergeGroups || []).filter(
        (g) => JSON.stringify([...g].sort()) !== key
      ),
    });
  }

  function undoSplit(rowId) {
    const info = splitFromInfo(rowId);
    if (!info) return;
    const lines = { ...(element.splitLines || {}) };
    delete lines[info.from];
    patch({ splitLines: lines });
  }

  // -- split: drag a two-point cut line across one shape's outline ----------
  let splitId = null;
  let splitLine = [[0, 0], [0, 0]];
  let splitDragIndex = null;
  let splitSvgEl;

  $: splitRow = splitId ? orderedShapes.find((r) => r.id === splitId) : null;
  $: splitOutline = splitRow ? splitRow.outlineFull || splitRow.outline || [] : [];
  $: splitIssues = splitId ? splitLineIssues(splitOutline, splitLine) : [];
  $: splitViewBox = fitViewBox(splitOutline);

  function startSplitEdit(row) {
    cancelBoundaryEdit(); // the two editors replace the same list view; only one at a time
    mergeSelection = [];
    const existing = (element.splitLines || {})[row.id];
    if (existing && existing.length === 2) {
      splitLine = existing.map((p) => [p[0], p[1]]);
    } else {
      const outline = row.outlineFull || row.outline || [];
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const [x, y] of outline) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
      const cy = (minY + maxY) / 2;
      const pad = Math.max(maxX - minX, 0.001) * 0.2;
      // A horizontal line through the centroid, spanning past both edges —
      // a sane starting cut for a roughly-convex shape (already valid, so
      // Save works immediately); a concave shape may need a drag to fix it,
      // same as the boundary editor's own "start from what's there" reading.
      splitLine = [[minX - pad, cy], [maxX + pad, cy]];
    }
    splitId = row.id;
    splitDragIndex = null;
  }

  function cancelSplitEdit() {
    splitId = null;
    splitLine = [[0, 0], [0, 0]];
    splitDragIndex = null;
  }

  function saveSplitEdit() {
    if (!splitId || splitIssues.length) return;
    patch({
      splitLines: { ...(element.splitLines || {}), [splitId]: splitLine.map((p) => [p[0], p[1]]) },
    });
    splitId = null;
    splitLine = [[0, 0], [0, 0]];
    splitDragIndex = null;
  }

  // Undo a PENDING (not yet applied) cut, same "auto" convention as
  // `resetBoundaryEdit` — clears the override rather than inverting it.
  function resetSplitEdit() {
    if (!splitId) return;
    const lines = { ...(element.splitLines || {}) };
    delete lines[splitId];
    patch({ splitLines: lines });
    splitId = null;
    splitLine = [[0, 0], [0, 0]];
    splitDragIndex = null;
  }

  function startSplitDrag(e, i) {
    e.preventDefault();
    splitDragIndex = i;
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch (err) {
      // Same graceful fallback as the boundary editor's own drag handler.
    }
  }

  function onSplitPointerMove(e) {
    if (splitDragIndex == null) return;
    const [x, y] = svgPointIn(splitSvgEl, e);
    splitLine[splitDragIndex] = [round3(x), round3(y)];
    splitLine = splitLine;
  }

  function endSplitDrag() {
    splitDragIndex = null;
  }

  function onSplitKeydown(e, i) {
    const step = nudgeStep(splitViewBox);
    const [x, y] = splitLine[i];
    if (e.key === "ArrowLeft") { e.preventDefault(); splitLine[i] = [round3(x - step), y]; splitLine = splitLine; }
    else if (e.key === "ArrowRight") { e.preventDefault(); splitLine[i] = [round3(x + step), y]; splitLine = splitLine; }
    else if (e.key === "ArrowUp") { e.preventDefault(); splitLine[i] = [x, round3(y - step)]; splitLine = splitLine; }
    else if (e.key === "ArrowDown") { e.preventDefault(); splitLine[i] = [x, round3(y + step)]; splitLine = splitLine; }
  }

  // ---- text-cluster detection: badge, convert-to-text, undo (Step 6b) ------
  //
  // `textCandidate`/`textClusterId` (reviewFromJob's mapping, straight off
  // the wire) mark a shape as a member of a server-detected "looks like
  // text" cluster — several rows can share one cluster id, so "Convert to
  // text" is a per-CLUSTER action, not a per-row one. It lives in its own
  // bar above the layer list (the `.dgp-mergebar` "act on a group" template),
  // not a per-row button: unlike a merge selection, cluster membership is
  // implicit in the data, not something the user assembles by clicking
  // checkboxes, and the action must stay reachable even once a member row
  // moves into the "unstitched" branch (stitched:false, set on convert) --
  // which renders no per-row badges/buttons at all.
  //
  // Rows are drawn from `reviewShapes` filtered only by `deletedIds` (a
  // user's own hide), NOT by `orderedShapes`/`sewableShapes` — a converted
  // cluster's members are unstitched by design and must still resolve for
  // the undo control below.
  $: liveReviewShapes = reviewShapes.filter((r) => !deletedIds.includes(r.id));
  $: visibleClusterIds = textClusterIds(liveReviewShapes);
  $: textConversions = element.textConversions || {};

  // A row whose cluster has already been converted to text: its
  // `stitched:false` (set by onConvertClusterToText, App.svelte) is a
  // permanent hide belonging to THIS feature, not the BACKGROUND_ENCLOSED
  // default -- restoring it through the enclosed-area machinery below would
  // silently un-hide a shape a different feature already replaced with a
  // real text element, producing a visible duplicate on Apply. Shared by
  // both the bulk banner (unstitchedRows) and the per-row "unstitched"
  // branch in the layer list.
  function isClusterHidden(row, conversions) {
    return row.textClusterId != null && conversions[row.textClusterId] != null;
  }

  function clusterMembers(clusterId) {
    return textClusterMembers(liveReviewShapes, clusterId);
  }

  // Computes the seed patch from the cluster's own member rows (bbox/color;
  // see textClusterSeed's own doc for exactly what it derives and what it
  // punts on) and dispatches `converttotext` — App.svelte's
  // `onConvertClusterToText` (already merged, Step 6a) does the rest: adds
  // the seeded text element AND hides these member shapes
  // (`stitched: false`) on this element in one coordinated project update.
  function convertClusterToText(clusterId) {
    const members = clusterMembers(clusterId);
    if (!members.length) return;
    const seed = textClusterSeed(members, liveReviewShapes);
    d("converttotext", {
      seed,
      clusterId,
      sourceElementId: element.id,
      memberShapeIds: members.map((r) => r.id),
    });
  }

  // Undo an applied conversion: mirrors undoMerge/undoSplit's button-swap,
  // but provenance is pure Studio-side state (element.textConversions,
  // Step 6a) rather than re-parsed from the last applied job's warnings --
  // no server round-trip is needed to know what to undo. `removeelement`
  // already exists (ContentStep.svelte's row-remove button / App.svelte's
  // onRemoveElement) and takes a plain element id, so it's reused as-is.
  // The override-clearing uses the SAME "delete the key, don't invert it"
  // convention `unrestoreStitching`/setOverride use -- inlined across all of
  // the cluster's members and combined with the textConversions removal into
  // ONE patch() call, the same "whole-group, one patch" discipline
  // moveShapeWithinLayer already established (looping setOverride calls here
  // would have each one build its shapeOverrides object off the same stale
  // `element` prop and clobber the others' changes).
  function undoTextConversion(clusterId) {
    const conversions = { ...textConversions };
    const textElementId = conversions[clusterId];
    if (!textElementId) return;
    delete conversions[clusterId];

    const shapeOverrides = { ...(element.shapeOverrides || {}) };
    for (const row of clusterMembers(clusterId)) {
      const entry = { ...(shapeOverrides[row.id] || {}) };
      delete entry.stitched;
      if (Object.keys(entry).length) shapeOverrides[row.id] = entry;
      else delete shapeOverrides[row.id];
    }
    patch({ shapeOverrides, textConversions: conversions });
    d("removeelement", textElementId);
  }

  // ---- bulk enclosed-area restore (warnings banner CTA) ---------------------
  //
  // Every row currently held unstitched by the BACKGROUND_ENCLOSED default,
  // EXCLUDING a text-cluster member a user has deliberately converted to text
  // (isClusterHidden above -- restoring one would silently duplicate the
  // shape under the new text element). Same one-patch discipline as
  // undoTextConversion above: looping setOverride here would have each call
  // build off the same stale `element` prop and clobber the others.
  $: unstitchedRows = orderedShapes.filter(
    (r) =>
      !deletedIds.includes(r.id) &&
      !effStitched(r, overrides) &&
      !isClusterHidden(r, textConversions)
  );

  function pluralize(n, one, many) {
    return n === 1 ? one : many.replace("{n}", String(n));
  }

  function restoreAllUnstitched() {
    const shapeOverrides = { ...(element.shapeOverrides || {}) };
    for (const row of unstitchedRows) {
      shapeOverrides[row.id] = { ...(shapeOverrides[row.id] || {}), stitched: true };
    }
    patch({ shapeOverrides });
  }
</script>

<div class="digipanel">
  <label class="dgp-upload">
    <span class="dgp-upload-btn" class:dgp-upload-cta={!element.sourcePng}
      >{element.sourcePng ? "Replace file…" : "Upload file"}</span
    >
    <input type="file" accept="image/png,image/jpeg,image/webp,image/*" on:change={onFile} disabled={fileBusy} />
  </label>
  {#if fileBusy}<p class="dgp-note">Reading the image…</p>{/if}
  <!-- Directly under the upload control, and OUTSIDE the `element.sourcePng`
       branch below.
       It used to live beside the Digitize button, which is in the `{:else}`
       arm — so it could only ever render once artwork had already loaded. A
       file that FAILS to load never sets `sourcePng`, so `onFile` set this
       message and the template had no way to show it: measured 2026-09-07 by
       dropping a .txt on a fresh panel, which set `error` and rendered the
       unchanged empty state. The one case where the user has nothing on
       screen and most needs telling was the one case that stayed silent, and
       a failed REPLACE — where they can already see their artwork — was the
       only case that spoke. -->
  {#if error}<p class="dgp-error" role="alert">{error}</p>{/if}
  {#if sourceNote}<p class="dgp-note" data-testid="source-note">{sourceNote}</p>{/if}

  {#if !element.sourcePng}
    <p class="dgp-note">
      Drop in any image — a logo, a mark, lettering, a photo. Then press Auto Digitize
      Image: it reads the artwork itself and picks how to sew it; afterwards it says what it
      made of the art so you can correct it if it read it wrong. Solid-color art still sews
      best — photos and gradients are newer ground and come back rougher. A bigger image sews
      sharper than a small one, and a PNG with a transparent background and sharp,
      non-anti-aliased edges digitizes cleanest.
    </p>
  {:else}
    <div class="dgp-src">
      <CropBox
        src={"data:image/png;base64," + element.sourcePng}
        crop={element.crop}
        onchange={(c) => patch({ crop: c })}
        minFrac={cropMinFrac}
      />
      <span class="dgp-srcname">{element.name || "Artwork"}</span>
    </div>

    {#if !health}
      <div class="dgp-offline">
        <p>
          The digitizer service isn't running, so digitizing is off.
          {#if element.result}Your stitched result is saved with the design and still sews and exports.{/if}
        </p>
        <p class="dgp-cmd">Start it: <code>python -m digitizer_service</code> in the digitizer folder.</p>
        <button type="button" class="dgp-check" on:click={() => d("checkservice")}>Check again</button>
      </div>
    {/if}

    <!-- Above the settings, not under them: nothing runs until this is
         pressed, and under seven controls it sat below the fold at 1440x900
         with a freshly uploaded file and no sign of what to do next. -->
    <!-- The ONE way a run starts. Solid before the first run and while the
         result matches the settings; transparent once anything it was
         digitized with has changed (Kent 2026-10-05: "so I know I need to
         select Auto Digitize again"). The sentence under it says the same
         thing in words, because an outline alone tells a screen reader
         nothing and tells a first-time user very little. -->
    <button
      type="button"
      class="dgp-run"
      class:dgp-run-stale={stale && !pending}
      data-stale={stale ? "true" : "false"}
      disabled={pending || !health}
      on:click={() => runDigitize(element)}
    >
      {pending ? "Digitizing…" : "Auto Digitize Image"}
    </button>
    {#if statusLine}<p class="dgp-status" role="status">{statusLine}</p>{/if}
    {#if stale && !pending && health}
      <p class="dgp-status" role="status" data-testid="digitize-stale">
        {#if resized}
          Resized to {resizeTarget.toFixed(0)} mm — the stitches are only scaled until you press
          Auto Digitize Image to restitch at that width.
        {:else}
          Changed since the last run — press Auto Digitize Image to restitch.
        {/if}
      </p>
    {/if}

    <div class="dgp-params">
      <!-- Every setting carries `use:tip` (lib/tip.js) with its key in
           lib/settingHelp.js — hover the label or focus the control and the
           three-line help shows. The "?" is a generated glyph on an empty,
           aria-hidden element, so the label's text is unchanged. -->
      <label class="dgp-param" use:tip={"designWidth"}>
        <!-- Renamed from "Stitch width" 2026-09-29: this is the DESIGN's
             width. "Stitch width" now means the per-shape satin column, in
             the Edit shapes list below, and one word cannot mean both. -->
        <span>Design width<i class="tipmark" aria-hidden="true"></i></span>
        <input
          type="number"
          min="10"
          max="400"
          step="1"
          value={resizeTarget ?? element.params.target_width_mm}
          on:change={(e) => setDesignWidth(Math.min(400, Math.max(10, parseFloat(e.currentTarget.value) || 80)))}
        />
        <span class="dgp-unit">mm</span>
      </label>
      <label class="dgp-param" use:tip={"colors"}>
        <span>Colors (max {element.params.max_colors})<i class="tipmark" aria-hidden="true"></i></span>
        <input
          type="range"
          min="2"
          max="12"
          step="1"
          value={element.params.max_colors}
          on:input={(e) => setParam("max_colors", parseInt(e.currentTarget.value, 10))}
        />
      </label>
      <label class="dgp-checkline" use:tip={"satinThin"}>
        <input
          type="checkbox"
          checked={element.params.satin}
          on:change={(e) => setParam("satin", e.currentTarget.checked)}
        />
        Satin for thin shapes<i class="tipmark" aria-hidden="true"></i>
      </label>
      <!-- Off by default on purpose: on real lettering the per-letter reading
           is a smooth chain, not a step (digitizer_core/stitchwidth.py), so
           the word's median is a guess. The always-on half is per shape, in
           Edit shapes: every measured column shows its width, and "whole
           word" writes one width to every letter. -->
      <label class="dgp-checkline" use:tip={"evenWidths"}>
        <input
          type="checkbox"
          checked={!!element.params.stitch_width_auto}
          on:change={(e) => setParam("stitch_width_auto", e.currentTarget.checked)}
        />
        Even out lettering widths<i class="tipmark" aria-hidden="true"></i>
      </label>
      <label class="dgp-param" use:tip={"fillAngle"}>
        <span>Fill angle<i class="tipmark" aria-hidden="true"></i></span>
        <select
          value={element.params.fill_angle_deg == null ? "auto" : String(element.params.fill_angle_deg)}
          on:change={onAngleChange}
        >
          {#each FILL_ANGLES as a}
            <option value={a.value == null ? "auto" : String(a.value)}>{a.label}</option>
          {/each}
        </select>
      </label>
      <label class="dgp-param" use:tip={"border"}>
        <span>Border<i class="tipmark" aria-hidden="true"></i></span>
        <select
          value={element.params.border ?? ""}
          on:change={(e) => setParam("border", e.currentTarget.value || null)}
        >
          <!-- The empty value is the null sentinel: it sends no `border` at
               all, so the service picks per artwork class -- `significant` on
               a photo, off elsewhere. It is first and it is the default
               because that per-class answer is the measured-good one, and
               until 2026-09-02 the Studio's unconditional "off" made it
               unreachable. -->
          <option value="">Automatic (by artwork)</option>
          <option value="off">None</option>
          <option value="auto">Auto (satin where it fits)</option>
          <option value="bean">Bean (light outline)</option>
        </select>
      </label>
      <!-- The DESIGN's outer edge, not each shape's (that is Border, above).
           Kent's first sew-out: every tatami row in the background ended in
           open air, because the silhouette is the union of several shapes and
           no per-shape border rides it. Toggleable on purpose — bean and
           satin read very differently on cloth and the choice is his, per
           design. -->
      <label class="dgp-param" use:tip={"designEdge"}>
        <span>Design edge<i class="tipmark" aria-hidden="true"></i></span>
        <select
          value={element.params.edge_cap}
          on:change={(e) => setParam("edge_cap", e.currentTarget.value)}
        >
          <option value="none">Leave open</option>
          <option value="bean">Bean cap (light outline)</option>
          <option value="satin">Satin cap (full column)</option>
        </select>
      </label>

      <!-- What the two selects above ACTUALLY produced, read off the stitch
           plan (design.runs) rather than off the request. Kent, 2026-09-15:
           "easier to identify when a satin border is or isn't generated and
           what it looks like going back and forth between satin border
           on/off". Both selects can be declined by the engine — a satin-tiered
           shape never takes a border, a narrow one takes a bean run or
           nothing, and the design edge finds nothing to sew on a small design
           — and none of that was visible anywhere before this block.

           It sits directly under the two controls that cause it, not in the
           warnings list, for the same reason the artwork-reading row does:
           this is the sentence you read while deciding, and the counts are
           what MOVE when the toggle does. On a payload with no `runs` the
           wording says "requested" and never "sewn" (borderMenu.js). -->
      {#if element.result}
        <div class="dgp-borders" class:dgp-borders-stale={restitching}>
          <p class="dgp-bline">
            <span class="dgp-bkey">Borders</span>
            <span
              title={borderCounts.verified
                ? "Read off the stitch plan: which shapes actually have a border on them, and how it sewed. “Not generated” means you asked for one and the engine added none — usually a shape too narrow to hold an outline. Open Edit shapes to see which."
                : "This design was stitched before the Studio could read back which runs sewed, so this is the request, not the cloth."}
            >{borderLine}</span>
          </p>
          <p class="dgp-bline">
            <span class="dgp-bkey">Design edge</span>
            <span title={edgeCap.title}>{edgeCapLine}</span>
          </p>
          {#if restitching}
            <p class="dgp-bnote">{pending ? "Restitching — these" : "These"} read the previous stitch plan.</p>
          {/if}
        </div>
      {/if}
    </div>

    <!-- What the art was read as, in plain words. Sits with the params, not
         down in the warnings list, because the reading decides what the
         params list even shows (the detail-lines option below). It hangs off
         the last run, since before it there is nothing to report -- except
         a design SET to flat, whose row stands with or without a result,
         because the reading it would hang off is gone once the override
         takes effect. One correction, on a tonal reading only. -->
    {#if forcedFlat || element.result}
      <div class="dgp-read" use:tip={"photoReading"}>
        <p class="dgp-read-text">
          {#if artRead === "forced"}
            You set this to flat art, so it's sewing as solid color regions.
          {:else if artRead === "face"}
            A face was found, so it's sewing as flat art: solid color regions with an outline.
          {:else if artRead === "photo"}
            Read as a photo, so it's sewing with shaded thread.
          {:else if artRead === "gradient"}
            Read as shaded artwork, so it's sewing in blended thread shades.
          {:else if artRead === "detected"}
            Read as a photograph, sewing as solid color regions.
          {:else if artRead === "unsure"}
            Couldn't tell what this artwork is, so it's sewing as flat art.
          {:else}
            Read as flat art, sewing as solid color regions.
          {/if}
        </p>
        {#if artRead === "forced"}
          <button type="button" class="dgp-read-btn" on:click={useAutomatic}>
            Use automatic detection
          </button>
        {:else if offerFlat}
          <button
            type="button"
            class="dgp-read-btn"
            on:click={() => setParam("forced_class", "flat")}
          >
            Sew as flat art
          </button>
        {/if}
        {#if tonalLane}
          <label class="dgp-checkline dgp-read-opt">
            <input
              type="checkbox"
              checked={element.params.detail_layer}
              on:change={(e) => setParam("detail_layer", e.currentTarget.checked)}
            />
            Add fine detail lines
          </label>
        {/if}
      </div>
    {/if}

    {#if element.result}
      <p class="dgp-stats">
        {element.result.stitchCount.toLocaleString()} stitches ·
        {element.result.widthMM.toFixed(0)}×{element.result.heightMM.toFixed(0)} mm ·
        {spoolCount(element.result)} color{spoolCount(element.result) === 1 ? "" : "s"}
      </p>
      <!-- "Since last run" sits with the stats, above the tabs: a re-run
           can be started from any of them (Apply on Shapes, a spool on
           Threads), and its outcome should be read where you are. -->
      {#if hasPrior}
        <p class="dgp-delta" role="status" data-testid="digitize-delta">
          {#if changed.length}
            Since last run: {changed.join(" · ")}
          {:else}
            Since last run: no change to stitches, threads or trims.
          {/if}
        </p>
      {/if}
      <!-- The run's warnings too: a layer edit that no longer matches a
           shape, a background that was hard to separate. Whatever tab you
           are on, these are not to be missed. -->
      {#if attentionLines.length}
        <ul class="dgp-warnings">
          {#each attentionLines as w (w.code + w.text)}
            <li>{w.text}</li>
          {/each}
        </ul>
      {/if}

      <!-- The tabs (see `tab` in the script). The stats line, the delta and
           the warnings above are common to all three; everything below
           belongs to one. The counts are aria-hidden so the tabs' names stay
           the plain words. -->
      <div class="dgp-tabs" role="tablist" aria-label="Digitize panel">
        <button type="button" role="tab" class="dgp-tab" class:dgp-tab-on={tab === "settings"} aria-selected={tab === "settings"} on:click={() => (tab = "settings")}>Settings</button>
        <button type="button" role="tab" class="dgp-tab" class:dgp-tab-on={tab === "shapes"} aria-selected={tab === "shapes"} on:click={() => (tab = "shapes")}>
          Shapes{#if reviewShapes.length}<span class="dgp-tab-count" aria-hidden="true">{reviewShapes.length}</span>{/if}
        </button>
        <button type="button" role="tab" class="dgp-tab" class:dgp-tab-on={tab === "threads"} aria-selected={tab === "threads"} on:click={() => (tab = "threads")}>
          Threads<span class="dgp-tab-count" aria-hidden="true">{spoolRows.length}</span>
        </button>
      </div>

      {#if tab === "settings"}

      <!-- Item 10: a re-digitize used to replace the design in place with
           nothing to compare against, so a knob you turned and a knob you
           imagined turning looked identical. `role="status"` because this
           appears as the RESULT of an action the user just took. -->
      <!-- Item 8, in the shape Kent chose 2026-09-02: outcome language, AFTER
           the run, with the knobs still underneath. Not a preset picker —
           that would re-introduce the pre-upload question he had removed. -->
      {#if fixes.length}
        <div class="dgp-fixes" data-testid="digitize-fixes">
          {#each fixes as fix}
            <button type="button" class="dgp-fix" on:click={() => applyFix(fix)}
                    title={fix.why}>
              {fix.label}
              <span class="dgp-fix-cost">{fix.spent}</span>
            </button>
          {/each}
        </div>
      {/if}

      {/if}

      {#if tab === "shapes"}
      {#if unstitchedRows.length}
        <div class="dgp-enclosed-banner" role="alert">
          <p class="dgp-enclosed-banner-text">
            {pluralize(
              unstitchedRows.length,
              "1 enclosed area was left unstitched by default, like the hole in an O. If it's meant to be part of the design and not a real gap, sew it.",
              "{n} enclosed areas were left unstitched by default, like the hole in an O. If they're meant to be part of the design and not real gaps, sew them."
            )}
          </p>
          <button type="button" class="dgp-enclosed-banner-btn" on:click={restoreAllUnstitched}>
            Sew all {unstitchedRows.length}
          </button>
        </div>
      {/if}
      {/if}

      {#if tab === "settings"}
      {#if noteLines.length}
        <details class="dgp-notes">
          <summary>{noteLines.length} note{noteLines.length === 1 ? "" : "s"} about how this was digitized</summary>
          <ul>
            {#each noteLines as w (w.code + w.text)}
              <li>{w.text}</li>
            {/each}
          </ul>
        </details>
      {/if}

      {#if resized}
        <p class="dgp-resize">
          Resized to {(scaleFactor * 100).toFixed(0)}% — the stitches scale, so thread density
          changes with size. Re-digitize at this size to regenerate them for it.
        </p>
        <button
          type="button"
          class="dgp-resizefix"
          disabled={pending || !health}
          on:click={() => runDigitize(element)}
        >
          Re-digitize at {resizeTarget.toFixed(0)} mm
        </button>
      {/if}
      {/if}

      {#if tab === "shapes"}
      {#if reviewShapes.length}
        <div class="dgp-layers">
          <div class="dgp-layers-head">
            <span class="dgp-layers-title">Layers</span>
            <!-- TOP SEWS FIRST — chosen, labeled, and here is why: an
                 operator reads the machine's color-change sheet top-to-
                 bottom in the order the needle runs, and the service's
                 review arrives in that same order. Graphics-app z-order
                 (bottom sews first) would put "first on the fabric" at the
                 BOTTOM of a list that is entirely about sewing sequence. -->
            <span class="dgp-layers-order">top sews first</span>
          </div>

          {#if sequencerBlocks.length > 1}
            <div class="dgp-sequencer">
              <button
                type="button"
                class="dgp-seq-toggle"
                aria-expanded={sequencerOpen}
                on:click={() => (sequencerOpen = !sequencerOpen)}
              >
                <Icon
                  name="chevron"
                  size={12}
                  class={"dgp-seq-caret" + (sequencerOpen ? "" : " dgp-seq-caret-closed")}
                />
                <span class="dgp-seq-title">
                  Color sequence ({sequencerBlocks.length} block{sequencerBlocks.length === 1 ? "" : "s"}{machineBlocks.length > sequencerBlocks.length ? `, ${machineBlocks.length} threads on the machine` : ""})
                </span>
                {#if trimsPer1000 != null}
                  <span class="dgp-seq-trims" class:heavy={trimHeavy}>
                    {trimsPer1000}/1000 trims{trimHeavy ? " — heavy" : ""}
                  </span>
                {/if}
              </button>
              {#if sequencerOpen}
                <ol class="dgp-seq-list">
                  {#each sequencerBlocks as block, i (block.layer)}
                    {@const shades = machineBlocksForRows(machineBlocks, block.rows)}
                    <li class="dgp-seq-block">
                      <span
                        class="dgp-seq-swatch"
                        style="background: rgb({block.rgb[0]},{block.rgb[1]},{block.rgb[2]})"
                      ></span>
                      <span class="dgp-seq-thread">{block.threadNumber || "—"}</span>
                      <span class="dgp-seq-count">{block.rows.length} shape{block.rows.length === 1 ? "" : "s"}</span>
                      <span class="dgp-seq-span">
                        {#if block.sewIndexMin != null}
                          #{block.sewIndexMin}{block.sewIndexMax > block.sewIndexMin ? `–${block.sewIndexMax}` : ""}
                        {/if}
                      </span>
                      {#if shades.length > 1}
                        <!-- Unkeyed: the same cone can head two blocks of one
                             layer (two regions re-snapped onto it), and a
                             duplicate key crashes the block. -->
                        <span class="dgp-seq-shades" title="This color sews as {shades.length} threads">
                          sews as
                          {#each shades as cone}
                            <span class="dgp-seq-shade">
                              <span
                                class="dgp-seq-swatch dgp-seq-swatch-sm"
                                style="background: rgb({cone.rgb[0]},{cone.rgb[1]},{cone.rgb[2]})"
                              ></span>{cone.number}
                            </span>
                          {/each}
                        </span>
                      {/if}
                      <span class="dgp-seq-btns">
                        <button
                          type="button"
                          class="dgp-lbtn"
                          title="Sew this color earlier"
                          aria-label="Sew this color earlier"
                          disabled={i === 0}
                          on:click={() => moveBlock(block.layer, -1)}
                        ><Icon name="arrowUp" size={12} /></button>
                        <button
                          type="button"
                          class="dgp-lbtn"
                          title="Sew this color later"
                          aria-label="Sew this color later"
                          disabled={i === sequencerBlocks.length - 1}
                          on:click={() => moveBlock(block.layer, 1)}
                        ><Icon name="arrowDown" size={12} /></button>
                      </span>
                    </li>
                  {/each}
                </ol>
              {/if}
            </div>
          {/if}
          {#if editingId}
            {@const editingRow = orderedShapes.find((r) => r.id === editingId)}
            <div class="dgp-editor">
              <p class="dgp-editor-title">
                Editing boundary — {editingRow ? rowName(editingRow) : "shape"}
              </p>
              <p class="dgp-note">
                Drag a point to move it (arrow keys nudge a focused point). Click — or press Enter
                on — a small dot on an edge to add a point there. Right-click, or press Delete, on
                a point to remove it.
              </p>
              <svg
                bind:this={svgEl}
                class="dgp-editor-svg"
                role="application"
                aria-label="Boundary editor — drag, add or remove points to reshape this shape"
                viewBox="{editViewBox.minX} {editViewBox.minY} {editViewBox.w} {editViewBox.h}"
                on:pointermove={onEditPointerMove}
                on:pointerup={endEditDrag}
                on:pointercancel={endEditDrag}
                on:pointerleave={endEditDrag}
              >
                <polygon
                  points={editPoints.map((p) => p.join(",")).join(" ")}
                  class="dgp-editor-poly"
                  class:invalid={editIssues.length > 0}
                />
                {#each editMidpoints as m, i (i + "-mid-" + editPoints.length)}
                  <circle
                    cx={m[0]}
                    cy={m[1]}
                    r={editHandleR * 0.55}
                    class="dgp-editor-mid"
                    role="button"
                    tabindex="0"
                    aria-label="Add a point on this edge"
                    on:click={() => addEditVertex(i)}
                    on:keydown={(e) => onEditMidKeydown(e, i)}
                  />
                {/each}
                {#each editPoints as p, i (i + "-pt-" + editPoints.length)}
                  <circle
                    cx={p[0]}
                    cy={p[1]}
                    r={editHandleR}
                    class="dgp-editor-vertex"
                    role="button"
                    tabindex="0"
                    aria-label="Drag to move this point; right-click or Delete to remove it"
                    on:pointerdown={(e) => startEditDrag(e, i)}
                    on:contextmenu={(e) => removeEditVertex(e, i)}
                    on:keydown={(e) => onEditVertexKeydown(e, i)}
                  />
                {/each}
              </svg>
              {#if editIssues.length}
                <ul class="dgp-editor-issues" role="alert">
                  {#each editIssues as issue}<li>{issue}</li>{/each}
                </ul>
              {/if}
              <div class="dgp-editor-btns">
                <button type="button" class="dgp-lbtn" on:click={cancelBoundaryEdit}>Cancel</button>
                {#if overrides[editingId] && overrides[editingId].boundary_override}
                  <button type="button" class="dgp-lbtn" on:click={resetBoundaryEdit}>Reset to auto</button>
                {/if}
                <button
                  type="button"
                  class="dgp-apply"
                  disabled={editIssues.length > 0}
                  on:click={saveBoundaryEdit}
                >
                  Save boundary
                </button>
              </div>
            </div>
          {:else if splitId}
            <div class="dgp-editor">
              <p class="dgp-editor-title">
                Splitting shape — {splitRow ? rowName(splitRow) : "shape"}
              </p>
              <p class="dgp-note">
                Drag either end of the line (arrow keys nudge a focused end) so it crosses the
                shape once, edge to edge — everything on each side becomes its own new shape.
              </p>
              <svg
                bind:this={splitSvgEl}
                class="dgp-editor-svg"
                role="application"
                aria-label="Split editor — drag the line's ends to choose where this shape is cut"
                viewBox="{splitViewBox.minX} {splitViewBox.minY} {splitViewBox.w} {splitViewBox.h}"
                on:pointermove={onSplitPointerMove}
                on:pointerup={endSplitDrag}
                on:pointercancel={endSplitDrag}
                on:pointerleave={endSplitDrag}
              >
                <polygon
                  points={splitOutline.map((p) => p.join(",")).join(" ")}
                  class="dgp-editor-poly"
                />
                <line
                  x1={splitLine[0][0]} y1={splitLine[0][1]}
                  x2={splitLine[1][0]} y2={splitLine[1][1]}
                  class="dgp-split-line"
                  class:invalid={splitIssues.length > 0}
                />
                {#each splitLine as p, i (i)}
                  <circle
                    cx={p[0]}
                    cy={p[1]}
                    r={Math.max(splitViewBox.w, splitViewBox.h) / 45}
                    class="dgp-editor-vertex"
                    role="button"
                    tabindex="0"
                    aria-label={i === 0 ? "Drag this end of the cut line" : "Drag the other end of the cut line"}
                    on:pointerdown={(e) => startSplitDrag(e, i)}
                    on:keydown={(e) => onSplitKeydown(e, i)}
                  />
                {/each}
              </svg>
              {#if splitIssues.length}
                <ul class="dgp-editor-issues" role="alert">
                  {#each splitIssues as issue}<li>{issue}</li>{/each}
                </ul>
              {/if}
              <div class="dgp-editor-btns">
                <button type="button" class="dgp-lbtn" on:click={cancelSplitEdit}>Cancel</button>
                {#if (element.splitLines || {})[splitId]}
                  <button type="button" class="dgp-lbtn" on:click={resetSplitEdit}>Remove cut</button>
                {/if}
                <button
                  type="button"
                  class="dgp-apply"
                  disabled={splitIssues.length > 0}
                  on:click={saveSplitEdit}
                >
                  Save cut
                </button>
              </div>
            </div>
          {:else}
          {#if mergeSelection.length}
            <div class="dgp-mergebar">
              <span>{mergeSelection.length} selected for merge</span>
              {#if mergeIssues.length}
                <span class="dgp-mergeissue">{mergeIssues[0]}</span>
              {/if}
              <button
                type="button"
                class="dgp-lbtn"
                disabled={mergeIssues.length > 0}
                on:click={commitMerge}
              >
                Merge {mergeSelection.length} shapes
              </button>
              <button type="button" class="dgp-lbtn" on:click={clearMergeSelection}>Clear</button>
            </div>
          {/if}
          {#if visibleClusterIds.length}
            {#each visibleClusterIds as clusterId (clusterId)}
              <!-- textClusterMembers(liveReviewShapes, ...) directly, NOT the
                   clusterMembers(clusterId) wrapper: an {@const} tracks only
                   what it textually names, and this each is keyed by
                   clusterId -- a string that by definition never changes for a
                   surviving block. So the wrapper's read of liveReviewShapes
                   was invisible and the member list was computed once, ever.
                   Delete one member row from a 4-shape "looks like text"
                   cluster and the banner kept saying "4 shapes" while the
                   cluster really had 3. Found 2026-08-26. The two other
                   clusterMembers() callers are event handlers, where reading
                   the closure is correct. -->
              {@const members = textClusterMembers(liveReviewShapes, clusterId)}
              {@const convertedId = textConversions[clusterId]}
              <div class="dgp-mergebar">
                <span>"looks like text" · {members.length} shape{members.length === 1 ? "" : "s"}</span>
                {#if convertedId}
                  <button
                    type="button"
                    class="dgp-lbtn"
                    on:click={() => undoTextConversion(clusterId)}
                  >
                    Undo — remove text element
                  </button>
                {:else}
                  <button
                    type="button"
                    class="dgp-lbtn"
                    on:click={() => convertClusterToText(clusterId)}
                  >
                    Convert to text
                  </button>
                {/if}
              </div>
            {/each}
          {/if}
          <!-- Closed by default. On a two-colour logo this list is 235
               buttons, 59 selects and 29 checkboxes -- 329 controls, 2,148 px
               of content in a 741 px viewport -- and fourteen of its rows are
               the individual letters of one wordmark. For a product whose
               premise is that anyone can use it, that is the moment the
               promise breaks. Everything a person needs BEFORE editing shapes
               one at a time now sits above this: the stitch/size/colour
               summary, the trim-density readout, and "Convert to text", which
               is the correct answer to those fourteen letter rows.
               Same idiom as the Sequencer toggle above, deliberately -- a
               plain button with aria-expanded and an {#if}-gated body, because
               this app has no <details> anywhere and one disclosure pattern is
               enough. -->
          <button
            type="button"
            class="dgp-seq-toggle"
            aria-expanded={layersOpen}
            on:click={() => (layersOpen = !layersOpen)}
          >
            <Icon
              name="chevron"
              size={12}
              class={"dgp-seq-caret" + (layersOpen ? "" : " dgp-seq-caret-closed")}
            />
            <span class="dgp-seq-title">
              Edit shapes ({orderedShapes.length})
            </span>
          </button>
          {#if layersOpen}
          <ol class="dgp-layerlist" bind:this={layerListEl}>
            {#each orderedShapes as row, i (row.id)}
              <!-- One name per row, reused by every control in it, so a
                   screen reader and a voice command can both tell the rows
                   apart. See rowLabel(). -->
              {@const rowAria = rowLabel(row, i, orderedShapes.length)}
              {@const dead = deletedIds.includes(row.id)}
              {@const stitched = effStitched(row, overrides)}
              {@const unstitched = !dead && !stitched}
              {@const clusterHidden = unstitched && isClusterHidden(row, textConversions)}
              <!-- Was excluded by default (an enclosed-background region)
                   AND is currently sewing — i.e. the user restored it. Shown
                   as a small badge plus an undo, so restoring stays a
                   reversible toggle rather than a one-way door. -->
              {@const restoredEnclosed = !dead && stitched && row.stitched === false}
              <!-- A restored enclosed row whose colour is a flattening
                   artifact (contract v1.7, reviewFromJob's
                   enclosedColourUnknown): the RGB it carries is whatever the
                   exporter flattened under the transparency — usually the
                   enclosing shape's own colour — so sewing it silently would
                   turn e.g. a Gray letter interior solid black. Marked until
                   the user picks a real thread (recolorShape writes
                   thread_index; unrestoring clears it the other way). -->
              {@const needsColour = restoredEnclosed && row.enclosedColourUnknown === true &&
                !(overrides[row.id] && typeof overrides[row.id].thread_index === "number")}
              {@const boundaryEdited = !dead && !unstitched &&
                !!(overrides[row.id] && overrides[row.id].boundary_override)}
              {@const mergedInfo = !dead && !unstitched ? mergedFromInfo(row.id) : null}
              {@const splitInfo = !dead && !unstitched ? splitFromInfo(row.id) : null}
              {@const textCand = !dead && !unstitched && !!row.textCandidate}
              {@const rgb = effRgb(row, overrides)}
              {@const tier = effTier(row, overrides)}
              {@const siblings = dead || unstitched ? [] : layerSiblings(row, sewableShapes, overrides)}
              {@const siblingIdx = siblings.findIndex((r) => r.id === row.id)}
              <li
                class="dgp-layer"
                class:dead
                class:unstitched
                class:dgp-layer-hover={hoverShapeId === row.id}
                class:dgp-layer-sel={selectedShapeId === row.id}
                data-shape-id={row.id}
                on:mouseenter={() => d("shapehover", row.id)}
                on:mouseleave={() => d("shapehover", null)}
              >
                {#if !dead && !unstitched}
                  <label class="dgp-mergecheck" title="Select for merge">
                    <input
                      type="checkbox"
                      checked={mergeSelection.includes(row.id)}
                      on:change={() => toggleMergeSelect(row.id)}
                      aria-label={"Select " + rowAria + " for merge"}
                    />
                  </label>
                {/if}
                <svg class="dgp-lthumb" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d={thumbPath(row)}
                    fill="rgb({rgb[0]},{rgb[1]},{rgb[2]})"
                    fill-opacity="0.9"
                    stroke="currentColor"
                    stroke-opacity="0.35"
                    stroke-width="0.6"
                  />
                </svg>
                <div class="dgp-lmain">
                  <div class="dgp-lrow">
                    {#if dead}
                      <span class="dgp-lname">{rowName(row)}</span>
                      <span class="dgp-larea">{fmtArea(row.areaMm2)}</span>
                      <span class="dgp-ltier">hidden</span>
                    {:else if unstitched}
                      <span class="dgp-lname">{rowName(row)}</span>
                      <span class="dgp-larea">{fmtArea(row.areaMm2)}</span>
                      {#if clusterHidden}
                        <span
                          class="dgp-ltier dgp-ltier-unstitched"
                          title="This shape was replaced by a converted text element. Use “Undo — remove text element” on the text-cluster bar above to bring it back, not a restore here."
                        >hidden — converted to text</span>
                      {:else}
                        <span
                          class="dgp-ltier dgp-ltier-unstitched"
                          title="The digitizer found this as an enclosed area the same color as the background (like the hole in an O) and left it unstitched by default."
                        >not sewn — enclosed area</span>
                      {/if}
                    {:else}
                      <ThreadPicker {rgb} compact name={rowAria} on:pick={(e) => recolorShape(row.id, e.detail)} />
                      <!-- The name is the row's handle onto the canvas: click
                           it and the field selects this shape, the amber
                           outline showing which one. Only a sewing row gets
                           this — a hidden or deleted shape has no outline to
                           show and a Delete armed on it would be a surprise. -->
                      <button
                        type="button"
                        class="dgp-lname dgp-lname-btn"
                        title="Show this shape on the canvas"
                        aria-label={"Show " + rowAria + " on the canvas"}
                        on:click={() => d("shapeselect", row.id)}
                      >{rowName(row)}</button>
                      <span class="dgp-larea">{fmtArea(row.areaMm2)}</span>
                      <span class="dgp-ltier tier-{tier || 'none'}">{tier || "not sewn"}</span>
                      <!-- The border this row actually has on it (borderMenu
                           .js's shapeBorderState), beside the tier badge
                           because the two answer the same question about the
                           same shape: what is on the cloth. Silent when
                           nothing asked for a border — the select right below
                           already says that, and a badge per row saying "no"
                           is how a list becomes unreadable. -->
                      {@const bst = borderStateFor(row)}
                      {#if bst.label}
                        <span class="dgp-lbadge dgp-lborder dgp-lborder-{bst.tone}" title={bst.title}>
                          {bst.label}
                        </span>
                      {/if}
                      {#if needsColour}
                        <span
                          class="dgp-lbadge dgp-lbadge-needscolor"
                          title="This area was a transparent hole in the artwork, so the color it shows was inherited from whatever the file flattened underneath it — not a real choice. Pick its thread with the color swatch on this row."
                        >pick a color</span>
                      {/if}
                      {#if restoredEnclosed}
                        <span
                          class="dgp-lbadge"
                          title="This was an enclosed background area the digitizer left unstitched by default; you restored it."
                        >restored</span>
                      {/if}
                      {#if boundaryEdited}
                        <span class="dgp-lbadge" title="This shape's outline was hand-edited.">
                          edited outline
                        </span>
                      {/if}
                      {#if mergedInfo}
                        <span
                          class="dgp-lbadge"
                          title={"Merged from " + mergedInfo.from.length + " shapes on the review screen."}
                        >merged from {mergedInfo.from.length}</span>
                      {/if}
                      {#if splitInfo}
                        <span class="dgp-lbadge" title="One of two shapes cut from the same original shape.">
                          split shape
                        </span>
                      {/if}
                      {#if textCand}
                        <span
                          class="dgp-lbadge"
                          title="A classical-CV pass flagged this shape as part of a cluster that looks like text (no character recognition — it can be wrong). Use the &quot;Convert to text&quot; action above the list to replace it with a real, typed text element."
                        >looks like text</span>
                      {/if}
                    {/if}
                  </div>
                  {#if !dead && !unstitched}
                    <div class="dgp-lrow">
                      <select
                        class="dgp-lsel"
                        value={overrideTier(row, overrides)}
                        on:change={(e) => setShapeTier(row.id, e.currentTarget.value)}
                        aria-label={"Stitch type — " + rowAria}
                        use:tip={"shapeTier"}
                      >
                        <option value="auto">Auto{row.tier ? " (" + row.tier + ")" : ""}</option>
                        <option value="satin">Satin</option>
                        <option value="fill">Fill</option>
                        <option value="run">Run</option>
                        <option value="sketch">Sketch</option>
                        <option value="streamline">Streamline</option>
                        <option value="crosshatch">Cross-hatch</option>
                        <option value="wave">Wave</option>
                        <option value="chevron">Chevron</option>
                        <option value="brick">Brick</option>
                      </select>
                      {#if tier === "fill"}
                        <select
                          class="dgp-lsel"
                          value={overrideAngle(row, overrides)}
                          on:change={(e) => setShapeAngle(row.id, e.currentTarget.value)}
                          aria-label={"Fill angle — " + rowAria}
                          use:tip={"shapeAngle"}
                        >
                          {#each SHAPE_ANGLES as a}
                            <option value={a.value == null ? "auto" : String(a.value)}>{a.label}</option>
                          {/each}
                        </select>
                        <select
                          class="dgp-lsel"
                          value={overrideUnderlay(row, overrides)}
                          on:change={(e) => setShapeUnderlay(row.id, e.currentTarget.value)}
                          aria-label={"Underlay style — " + rowAria}
                          use:tip={"shapeUnderlay"}
                        >
                          {#each SHAPE_UNDERLAYS as u}
                            <option value={u.value == null ? "auto" : u.value}>{u.label}</option>
                          {/each}
                        </select>
                      {/if}
                      <select
                        class="dgp-lsel"
                        value={overrideBorder(row, overrides)}
                        on:change={(e) => setShapeBorder(row.id, e.currentTarget.value)}
                        aria-label={"Border — " + rowAria}
                        use:tip={"shapeBorder"}
                      >
                        <option value="default">Design ({borderLabel(element.params.border)})</option>
                        <option value="off">No border</option>
                        <option value="auto">Auto border</option>
                        <option value="bean">Bean border</option>
                      </select>
                    </div>
                    <!-- Stitch width (contract v1.8): only where the engine
                         measured a column. A fill region has no column to
                         size, so the control is absent rather than disabled
                         there; the tier select above is that shape's lever. -->
                    {#if row.stitchWidth && tier !== "fill"}
                      {@const swOverride = overrideStitchWidth(row, overrides)}
                      {@const swGroupN = stitchWidthGroupRows(sewableShapes, row).length}
                      <div class="dgp-lrow dgp-lwidth" data-testid="stitch-width-row">
                        <label class="dgp-lwidth-label">
                          <span>Stitch width</span>
                          <input
                            type="number"
                            class="dgp-lwidth-input"
                            min={STITCH_WIDTH_MIN_MM}
                            max={STITCH_WIDTH_MAX_MM}
                            step="0.1"
                            placeholder={"auto " + fmtMm(row.stitchWidth.autoMm)}
                            value={swOverride == null ? "" : swOverride}
                            aria-label={"Stitch width — " + rowAria}
                            use:tip={"stitchWidth"}
                            on:change={(e) => setShapeStitchWidth(row, e.currentTarget.value)}
                          />
                          <span class="dgp-unit">mm</span>
                        </label>
                        {#if swOverride != null}
                          <button
                            type="button"
                            class="dgp-lbtn dgp-lwidth-auto"
                            title={swGroupN > 1 && !wordScope.has(row.id) ? "Back to the engine's own width, for the whole word" : "Back to the engine's own width"}
                            on:click={() => setShapeStitchWidth(row, "")}
                          >Auto</button>
                        {/if}
                        {#if swGroupN > 1}
                          <label class="dgp-lwidth-scope" use:tip={"wholeWord"}>
                            <input
                              type="checkbox"
                              checked={!wordScope.has(row.id)}
                              on:change={() => toggleWordScope(row)}
                              aria-label={"Whole word — " + rowAria}
                            />
                            whole word
                          </label>
                        {/if}
                        <span class="dgp-lwidth-note">{stitchWidthNote(row, overrides)}</span>
                      </div>
                    {/if}
                  {/if}
                </div>
                <div class="dgp-lbtns">
                  {#if dead}
                    <button type="button" class="dgp-lbtn dgp-restore" on:click={() => restoreShape(row.id)}>
                      Restore
                    </button>
                  {:else if unstitched && !clusterHidden}
                    <button
                      type="button"
                      class="dgp-lbtn dgp-restore"
                      title="Sew this enclosed area"
                      on:click={() => restoreStitching(row.id)}
                    >
                      Sew it
                    </button>
                  {:else if !unstitched}
                    <button
                      type="button"
                      class="dgp-lbtn"
                      disabled={i === 0}
                      title="Sew earlier"
                      aria-label={"Sew earlier — " + rowAria}
                      on:click={() => moveShape(row, -1)}
                    ><Icon name="arrowUp" size={12} /></button>
                    <button
                      type="button"
                      class="dgp-lbtn"
                      disabled={i === orderedShapes.length - 1}
                      title="Sew later"
                      aria-label={"Sew later — " + rowAria}
                      on:click={() => moveShape(row, 1)}
                    ><Icon name="arrowDown" size={12} /></button>
                    {#if siblings.length > 1}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        disabled={siblingIdx <= 0}
                        title="Sew earlier within this color"
                        aria-label={"Sew earlier within this color — " + rowAria}
                        on:click={() => moveShapeWithinLayer(row, -1)}
                      ><Icon name="chevron" size={12} class="dgp-caret-up" /></button>
                      <button
                        type="button"
                        class="dgp-lbtn"
                        disabled={siblingIdx < 0 || siblingIdx === siblings.length - 1}
                        title="Sew later within this color"
                        aria-label={"Sew later within this color — " + rowAria}
                        on:click={() => moveShapeWithinLayer(row, 1)}
                      ><Icon name="chevron" size={12} /></button>
                    {/if}
                    {#if restoredEnclosed}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Mark as not sewn again (enclosed area)"
                        aria-label={"Mark as not sewn again — " + rowAria}
                        on:click={() => unrestoreStitching(row.id)}
                      ><Icon name="exclude" size={12} /></button>
                    {/if}
                    {#if mergedInfo}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Undo this merge (the original shapes come back)"
                        aria-label={"Undo merge — " + rowAria}
                        on:click={() => undoMerge(row.id)}
                      ><Icon name="revert" size={12} /></button>
                    {:else if splitInfo}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Undo this split (the original shape comes back)"
                        aria-label={"Undo split — " + rowAria}
                        on:click={() => undoSplit(row.id)}
                      ><Icon name="revert" size={12} /></button>
                    {:else}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Cut this shape into two"
                        aria-label={"Split shape — " + rowAria}
                        on:click={() => startSplitEdit(row)}
                      ><Icon name="scissors" size={12} /></button>
                    {/if}
                    <button
                      type="button"
                      class="dgp-lbtn"
                      title="Edit this shape's boundary"
                      aria-label={"Edit shape boundary — " + rowAria}
                      on:click={() => startBoundaryEdit(row)}
                    ><Icon name="edit" size={12} /></button>
                    <button
                      type="button"
                      class="dgp-lbtn"
                      title="Hide this shape (restorable)"
                      aria-label={"Hide this shape — " + rowAria}
                      on:click={() => deleteShape(row.id)}
                    ><Icon name="close" size={12} /></button>
                  {/if}
                </div>
              </li>
            {/each}
          </ol>
          {/if}
          {/if}

          {#if unmatchedCount}
            <p class="dgp-unmatched">
              {unmatchedCount} layer edit{unmatchedCount === 1 ? "" : "s"} point at shapes that are
              no longer in the art.
              <button type="button" class="dgp-lbtn dgp-clearun" on:click={clearUnmatched}>Clear them</button>
            </p>
          {/if}

          {#if hasPendingEdits}
            {#if health}
              <button
                type="button"
                class="dgp-apply"
                disabled={pending}
                on:click={() => runDigitize(element)}
              >
                {pending ? "Digitizing…" : "Apply layer changes"}
              </button>
            {:else}
              <p class="dgp-queued">
                The digitizer isn't running — these layer changes are saved with the design and
                apply the next time you digitize.
              </p>
            {/if}
          {/if}
        </div>
      {:else if health}
        <p class="dgp-note">Press Auto Digitize Image again to get an editable layer list for this result.</p>
      {/if}
      {/if}

      {#if tab === "threads"}
      <div class="dgp-blocks">
        <span class="dgp-blocks-label">Thread per color</span>
        {#each spoolRows as g (g.first)}
          <div class="dgp-block">
            <span class="dgp-block-n">{g.name}</span>
            {#if g.blocks.length > 1}
              <span class="dgp-block-note">loaded {g.blocks.length} times</span>
            {/if}
            <ThreadPicker rgb={blockRgb(element, g.first)} compact on:pick={(e) => pickSpool(g, e.detail)} />
          </div>
        {/each}
      </div>
      {/if}

      {#if tab === "settings"}
      <label class="letterspacing" use:tip={"rotation"}>
        <span>Rotation<i class="tipmark" aria-hidden="true"></i></span>
        <input
          type="range"
          min="0"
          max="360"
          step="1"
          value={rotation}
          on:input={(e) => patch({ rotationDeg: parseInt(e.currentTarget.value, 10) })}
        />
        <span class="label">{rotation}°</span>
      </label>
      {/if}
    {/if}
  {/if}
</div>

<style>
  .digipanel { margin-top: 4px; }
  /* The three tabs: a hairline underline strip, the lit one in ink with a
     2px accent rule — the same segmented language as the hoop picker and
     the view segments, laid flat because it heads a column. */
  .dgp-tabs {
    display: flex;
    gap: var(--space-4, 16px);
    margin: 12px 0 10px;
    border-bottom: 1px solid var(--border, #e2e5eb);
  }
  .dgp-tab {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 2px 8px;
    margin-bottom: -1px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: none;
    color: var(--muted, #616875);
    font: inherit;
    font-size: var(--fs-sm, 14px);
    font-weight: var(--fw-medium, 500);
    cursor: pointer;
  }
  .dgp-tab:hover { color: var(--ink, #1c1f26); }
  .dgp-tab-on { color: var(--ink, #1c1f26); border-bottom-color: var(--accent, #4f46e5); font-weight: var(--fw-medium, 500); }
  .dgp-tab-count {
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--fill, #f4f4f4);
    color: var(--muted, #616875);
    font-size: var(--fs-2xs, 11px);
    font-weight: var(--fw-medium, 500);
  }
  .dgp-tab-on .dgp-tab-count { background: var(--tint, #eef0ff); color: var(--accent, #4f46e5); }
  .dgp-block-note { font-size: var(--fs-xs, 11px); color: var(--muted, #616875); }
  .dgp-upload { display: inline-block; cursor: pointer; }
  .dgp-upload input[type="file"] {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    overflow: hidden;
  }
  .dgp-upload-btn {
    display: inline-block;
    padding: 6px 12px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    font-size: var(--fs-xs, 12px);
  }
  /* Primary only while it is the panel's sole action (no artwork yet). */
  .dgp-upload-cta {
    padding: 10px 20px;
    min-height: 40px;
    border: 2px solid var(--accent, #4f46e5);
    border-radius: var(--radius-s, 8px);
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    font-weight: var(--fw-medium, 500);
    font-size: var(--fs-sm, 14px);
  }
  .dgp-upload:hover .dgp-upload-cta {
    background: var(--accent-dark, #4338ca);
    border-color: var(--accent-dark, #4338ca);
  }

  .dgp-upload:focus-within .dgp-upload-btn {
    outline: 2px solid var(--accent, #4f46e5);
    outline-offset: 1px;
  }
  .dgp-note {
    font-size: var(--fs-xs, 12px);
    line-height: var(--lh-body, 1.6);
    color: var(--muted, #6b7280);
    margin: 8px 0 0;
  }
  .dgp-src { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; margin-top: 10px; }
  .dgp-srcname { font-size: var(--fs-xs, 12px); color: var(--muted, #667); word-break: break-all; }
  .dgp-offline {
    margin-top: 10px;
    padding: 8px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    font-size: var(--fs-xs, 12px);
  }
  .dgp-offline p { margin: 0 0 6px; }
  .dgp-cmd code { font-size: var(--fs-xs, 0.6875rem); }
  .dgp-check,
  .dgp-resizefix {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .dgp-params { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
  .dgp-param { display: flex; align-items: center; gap: 8px; font-size: var(--fs-xs, 12px); }
  .dgp-param > span:first-child { min-width: 96px; }
  .dgp-param input[type="range"] { flex: 1; }

  /* Bare OS widgets otherwise -- a grey system dropdown and a hairline text
     box sitting directly under the app's 2px-bordered, 8px-radius controls.
     Matches theme.css's `.unitselect`/`.sizeinput` treatment (this file is
     component-scoped, so the rule cannot be shared, only mirrored). The
     panel-level selects also stretch to a common edge instead of each
     sizing to its own longest option, which is why "Auto (per shape)" and
     "None" used to end at different x. */
  .dgp-param select,
  .dgp-param input[type="number"] {
    padding: 4px 6px;
    border: 2px solid var(--border, #e2e5eb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    color: var(--ink, #1c1f26);
    font: inherit;
    font-size: var(--fs-xs, 12px);
  }
  .dgp-param select { flex: 1; min-width: 0; cursor: pointer; }
  .dgp-param input[type="number"] { width: 70px; }
  .dgp-param select:hover { border-color: var(--ink, #171a20); }
  .dgp-param input[type="number"]:focus { border-color: var(--accent, #4f46e5); }
  .dgp-unit { color: var(--muted, #667); }
  .dgp-checkline { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs, 12px); }
  .dgp-run {
    margin-top: 12px;
    padding: 10px 20px;
    min-height: 40px;
    border: 2px solid var(--accent, #4f46e5);
    border-radius: var(--radius-s, 8px);
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    cursor: pointer;
    font-weight: var(--fw-medium, 500);
    font-size: var(--fs-sm, 14px);
  }
  .dgp-run:hover:not(:disabled) {
    background: var(--accent-dark, #4338ca);
    border-color: var(--accent-dark, #4338ca);
  }
  .dgp-run:disabled { opacity: 0.6; cursor: default; }
  /* Out of date: the fill goes, the outline and the label keep the accent. */
  .dgp-run.dgp-run-stale {
    background: transparent;
    color: var(--accent, #4f46e5);
  }
  .dgp-run.dgp-run-stale:hover:not(:disabled) {
    background: var(--tint, rgba(79, 70, 229, 0.08));
    border-color: var(--accent, #4f46e5);
  }
  .dgp-status { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 6px 0 0; }
  .dgp-error { font-size: var(--fs-xs, 12px); color: var(--danger, #b3261e); margin: 6px 0 0; }
  .dgp-fixes {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
  .dgp-fix {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    padding: 4px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius-s);
    background: var(--surface);
    cursor: pointer;
    font-size: 12px;
  }
  .dgp-fix-cost { color: var(--muted); }

  .dgp-delta {
    margin: 2px 0 0;
    font-size: 12px;
    color: var(--muted, #6f685c);
  }

  .dgp-stats { font-size: var(--fs-xs, 12px); margin: 10px 0 0; }
  .dgp-warnings {
    margin: 8px 0 0;
    padding-left: 18px;
    font-size: var(--fs-xs, 12px);
    color: var(--warn-text, #8a6d1a);
  }
  .dgp-warnings li { margin-top: 2px; }
  /* Notes are the engine's own account of what it did: present, countable,
     and quiet. Muted rather than --warn-text, because nothing in here is a
     warning about the customer's artwork. */
  .dgp-notes {
    margin: 8px 0 0;
    font-size: var(--fs-xs, 12px);
    color: var(--muted, #6f685c);
  }
  .dgp-notes summary { cursor: pointer; }
  .dgp-notes ul { margin: 4px 0 0; padding-left: 18px; }
  .dgp-notes li { margin-top: 2px; }
  /* Louder than .dgp-warnings on purpose (Kent's own diagnosis of the
     Instagram-icon complaint: the per-shape "Sew it" restore already existed
     but was easy to miss as a dim list line) -- a bordered, actionable box
     instead of another <li>, same --warn-text vocabulary as everything else
     in this file rather than a new color invented for one banner. */
  .dgp-enclosed-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 8px 0 0;
    padding: 8px 10px;
    border: 1px solid var(--warn-text, #8a6d1a);
    border-radius: var(--radius-s, 6px);
    background: var(--warn-bg, #fdf6e3);
  }
  .dgp-enclosed-banner-text {
    flex: 1;
    margin: 0;
    font-size: var(--fs-xs, 12px);
    color: var(--warn-text, #8a6d1a);
  }
  .dgp-enclosed-banner-btn {
    flex-shrink: 0;
    padding: 5px 10px;
    border: 1px solid var(--warn-text, #8a6d1a);
    border-radius: var(--radius-s, 6px);
    background: var(--warn-text, #8a6d1a);
    color: #fff;
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
    white-space: nowrap;
  }
  /* The reading row STATES what the engine read: nothing is wrong and
     nothing needs chasing, and it stays for the life of the design. So it
     takes .dgp-check's quiet surface/tint vocabulary rather than warning
     yellow, and its one button (the flat switch, back 2026-09-30) is quiet
     too. Still a box, so the detail-lines option reads as part of it. */
  .dgp-read {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin: 10px 0 0;
    padding: 8px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
  }
  .dgp-read-text {
    flex: 1 1 auto;
    margin: 0;
    font-size: var(--fs-xs, 12px);
    color: var(--muted, #667);
  }
  /* The detail-lines option takes the row's own width and sits on its own
     line under the sentence, in the same colour so it reads as part of the
     row rather than inheriting the panel default through the container. */
  .dgp-read-opt {
    flex: 1 1 100%;
    color: var(--muted, #667);
  }
  .dgp-read-btn {
    flex-shrink: 0;
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    color: inherit;
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
    white-space: nowrap;
  }
  .dgp-resize { font-size: var(--fs-xs, 12px); color: var(--warn-text, #8a6d1a); margin: 8px 0 6px; }
  .dgp-blocks { margin-top: 10px; }
  .dgp-blocks-label { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
  .dgp-block { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
  .dgp-block-n { font-size: var(--fs-xs, 12px); min-width: 130px; }
  .dgp-layers { margin-top: 12px; }
  .dgp-layers-head { display: flex; align-items: baseline; gap: 8px; }
  .dgp-layers-title { font-size: var(--fs-xs, 12px); font-weight: var(--fw-medium, 500); }
  .dgp-layers-order { font-size: var(--fs-2xs, 0.6875rem); color: var(--muted, #667); }
  .dgp-sequencer { margin-top: 6px; }
  .dgp-seq-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 4px 6px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-2xs, 0.6875rem);
    text-align: left;
  }
  /* `chevron` points down at rest -- that's the "open" reading, so the
     closed (▸) state is the one that needs a rotate; same reuse-one-icon,
     rotate-in-CSS convention Icon.svelte's own comment documents. */
  .dgp-seq-caret { flex: none; color: var(--muted, #667); }
  @media (prefers-reduced-motion: no-preference) {
    .dgp-seq-caret { transition: transform 150ms ease; }
  }
  .dgp-seq-caret-closed { transform: rotate(-90deg); }
  .dgp-seq-title { flex: 1; font-weight: var(--fw-medium, 500); }
  .dgp-seq-trims { color: var(--muted, #667); white-space: nowrap; }
  .dgp-seq-trims.heavy { color: var(--warn-text, #8a6d1a); font-weight: var(--fw-medium, 500); }
  .dgp-seq-list { list-style: none; margin: 4px 0 0; padding: 0; }
  .dgp-seq-block {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    border-top: 1px solid var(--tint-border, #ccd6fb);
    font-size: var(--fs-xs, 0.6875rem);
  }
  .dgp-seq-swatch {
    width: 12px;
    height: 12px;
    flex: none;
    border-radius: 3px;
    border: 1px solid var(--tint-border, #ccd6fb);
  }
  .dgp-seq-thread { flex: none; min-width: 40px; color: var(--muted, #667); }
  .dgp-seq-count { flex: 1; }
  .dgp-seq-span { flex: none; color: var(--muted, #667); }
  .dgp-seq-shades {
    flex: 1 1 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 2px 8px;
    padding-left: 22px;
    font-size: 0.85em;
    color: var(--muted, #667);
  }
  .dgp-seq-shade { display: inline-flex; align-items: center; gap: 3px; }
  .dgp-seq-swatch-sm { width: 9px; height: 9px; }
  .dgp-seq-btns { display: flex; gap: 2px; flex: none; }
  /* Bounded, with its own scroll. One shape per row and no ceiling meant a
     31-shape logo pushed everything after the list -- thread-per-color,
     rotation, and the whole Size panel -- more than three screens down the
     panel, and shape count scales with artwork complexity, so a busy logo is
     worse. Capping the list keeps the panel a fixed, navigable length no
     matter what the artwork contains. Nothing is hidden: every row stays in
     the DOM, and scroll chaining still carries the wheel on to the panel
     once the list reaches its end. */
  .dgp-layerlist {
    list-style: none;
    margin: 6px 0 0;
    padding: 0;
    max-height: 420px;
    overflow-y: auto;
    /* The cap only helps if the list LOOKS like a scroll region -- otherwise
       the rows just stop and the 25 shapes below them are invisible. A frame
       plus the same cover/shadow gradient pair .panel-body uses says both
       "this is its own box" and "there is more in it". */
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background:
      linear-gradient(var(--surface, #fff) 30%, var(--surface-fade, rgba(255, 255, 255, 0))),
      linear-gradient(var(--surface-fade, rgba(255, 255, 255, 0)), var(--surface, #fff) 70%) 0 100%,
      radial-gradient(farthest-side at 50% 0, rgba(15, 23, 42, 0.13), transparent),
      radial-gradient(farthest-side at 50% 100%, rgba(15, 23, 42, 0.13), transparent) 0 100%;
    background-repeat: no-repeat;
    background-color: var(--surface, #fff);
    background-size: 100% 24px, 100% 24px, 100% 8px, 100% 8px;
    background-attachment: local, local, scroll, scroll;
  }
  /* The frame now supplies the outer edges, so the first/last row's own
     rules would double them up. */
  .dgp-layerlist > .dgp-layer:first-child { border-top: none; }
  .dgp-layerlist > .dgp-layer:last-child { border-bottom: none; }
  .dgp-layer {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    padding: 6px 4px;
    border-top: 1px solid var(--tint-border, #ccd6fb);
  }
  .dgp-layer:last-child { border-bottom: 1px solid var(--tint-border, #ccd6fb); }
  .dgp-layer.dead .dgp-lname,
  .dgp-layer.dead .dgp-larea { text-decoration: line-through; }
  .dgp-layer.dead { opacity: 0.6; }
  /* Unstitched-by-default (BACKGROUND_ENCLOSED) rows are dimmed like a
     hidden row so the list reads "not fully active" at a glance, but
     deliberately NOT struck through — this isn't something the user
     removed, so it shouldn't look removed. */
  .dgp-layer.unstitched { opacity: 0.75; }
  /* The list and the canvas point at the same shape (2026-09-30): a row
     under the pointer here, or whose shape is under the pointer there, takes
     the hover ground; the selected shape's row takes the tint with an
     accent edge, the list's twin of the amber outline on the field. */
  .dgp-layer:hover,
  .dgp-layer-hover { background: var(--fill, #f4f4f4); }
  .dgp-layer-sel,
  .dgp-layer-sel:hover { background: var(--tint, #eef0ff); box-shadow: inset 3px 0 0 var(--accent, #4f46e5); }
  .dgp-lname-btn {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font-family: inherit;
    line-height: inherit;
    text-align: left;
    cursor: pointer;
  }
  .dgp-lname-btn:hover { color: var(--accent, #4f46e5); text-decoration: underline; }
  .dgp-ltier-unstitched {
    color: var(--warn-text, #8a6d1a);
    border-color: var(--warn-text, #8a6d1a);
  }
  .dgp-lbadge {
    font-size: var(--fs-2xs, 0.6875rem);
    color: var(--muted, #667);
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: 8px;
    padding: 1px 5px;
  }

  /* The border badges. Three weights, and the ONE that has to stand out is
     "the engine declined" -- that is the state Kent cannot see today and the
     only one that wants a decision. A sewn border is reassurance and stays
     quiet; a bean border is a downgrade worth noticing but not an alarm.
     Colour here is chrome, never thread: the canvas is where thread colour is
     judged, and recolouring a stitch to signal structure would break that.

     Every colour is an EXISTING theme.css token. There is no success/ok token
     in the palette and this is not the place to invent one: theme.css's own
     header records what happened last time this file asked for names that were
     never defined (--warn-text/--warn-bg x23, silently taking a hardcoded
     olive fallback while the rest of the app used --warn). So "sewn" reads in
     the accent family, which the app already spends on affirmative state. */
  .dgp-lborder { white-space: nowrap; }
  .dgp-lborder-ok {
    color: var(--accent);
    border-color: var(--tint-border);
    background: var(--tint);
  }
  .dgp-lborder-note {
    color: var(--warn-text);
    border-color: var(--warn-text);
    background: var(--warn-bg);
  }
  .dgp-lborder-quiet {
    color: var(--muted);
    border-color: var(--border);
    background: var(--fill);
  }
  .dgp-lborder-warn {
    color: var(--danger);
    border-color: var(--danger);
    background: var(--surface);
  }

  /* The design-level readout under the two border selects. Deliberately plain
     -- it is a status line, not a warning: on a healthy design every border
     asked for is on the cloth and this should read as calmly as the stitch
     count does. */
  .dgp-borders {
    margin-top: 2px;
    padding: 6px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius-s, 6px);
    background: var(--fill);
  }
  .dgp-borders-stale { opacity: 0.6; }
  .dgp-bline {
    margin: 0;
    font-size: var(--fs-xs);
    line-height: var(--lh-snug, 1.4);
    color: var(--ink);
  }
  .dgp-bline + .dgp-bline { margin-top: 3px; }
  .dgp-bkey {
    display: inline-block;
    min-width: 76px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: var(--tracking-wide);
  }
  .dgp-bnote {
    margin: 4px 0 0;
    font-size: var(--fs-xs);
    color: var(--muted);
  }
  /* The needs-colour marker (contract v1.7): warning-tinted like the
     enclosed-areas banner, since it flags the same class of silent wrong
     output — a colour nobody chose. */
  .dgp-lbadge-needscolor {
    color: var(--warn-text, #8a6d1a);
    border-color: var(--warn-text, #8a6d1a);
    background: var(--warn-bg, #fdf6e3);
  }
  .dgp-lthumb {
    width: 24px;
    height: 24px;
    flex: none;
    margin-top: 2px;
    color: var(--muted, #667);
  }
  .dgp-lmain { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
  .dgp-lrow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .dgp-lname { font-size: var(--fs-xs, 12px); font-weight: var(--fw-medium, 500); }
  .dgp-larea { font-size: var(--fs-2xs, 0.6875rem); color: var(--muted, #667); }
  .dgp-ltier {
    font-size: var(--fs-2xs, 0.6875rem);
    text-transform: uppercase;
    letter-spacing: var(--tracking-wide, 0.08em);
    padding: 1px 5px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: 8px;
    color: var(--muted, #667);
  }
  .dgp-lsel {
    font-size: var(--fs-2xs, 0.6875rem);
    max-width: 110px;
    padding: 2px 4px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    color: var(--ink, #1c1f26);
    cursor: pointer;
  }
  .dgp-lsel:hover { border-color: var(--ink, #171a20); }
  .dgp-lwidth { gap: 6px; }
  .dgp-lwidth-label { display: inline-flex; align-items: center; gap: 4px; font-size: var(--fs-2xs, 0.6875rem); }
  .dgp-lwidth-input {
    /* 84px, not 64: the placeholder is "auto 2.08" and a number input keeps
       a spinner on the right, so 64 clipped it to "auto 2.0" on the first
       drive (2026-09-30). Sized for "auto 12.34" plus the spinner. */
    width: 84px;
    padding: 2px 4px;
    font-size: var(--fs-2xs, 0.6875rem);
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    color: var(--ink, #1c1f26);
  }
  .dgp-lwidth-input:focus { border-color: var(--accent, #4f46e5); outline: none; }
  .dgp-lwidth-auto { width: auto; padding: 0 6px; }
  .dgp-lwidth-scope { display: inline-flex; align-items: center; gap: 3px; font-size: var(--fs-2xs, 0.6875rem); cursor: pointer; }
  .dgp-lwidth-note { font-size: var(--fs-xs, 0.6875rem); color: var(--ink-soft, #5c6270); flex-basis: 100%; }
  /* A 4-wide grid, not a 1-wide column. These seven 26x18 buttons were
     stacked vertically, which made `.dgp-lbtns` 26px wide and 138px TALL --
     and since it is the tallest child of `.dgp-layer`, it set every row's
     height. Measured: rows were 151px while their actual content
     (`.dgp-lmain`) was 54px, so ~97px of every row was empty space held open
     by a column of icons, and a 31-shape logo produced a 4,234px list. A
     wrapped grid puts the same buttons in 2 rows of ~110px, which the
     content beside them already covers. `repeat(4, auto)` also handles the
     dead/unstitched branches, where the only child is one wide text button
     ("Restore" / "Sew it"): it lands in column 1 and sizes to its content
     while the empty columns collapse. */
  .dgp-lbtns {
    display: grid;
    grid-template-columns: repeat(4, auto);
    gap: 2px;
    flex: none;
    justify-content: end;
    align-content: start;
  }
  .dgp-lbtn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px 6px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 11px);
    line-height: 1.3;
  }
  .dgp-lbtn:disabled { opacity: 0.4; cursor: default; }
  /* `chevron` points down at rest -- the within-layer "later" nudge button
     reuses it as-is, "earlier" rotates it to point up. Same rotate-in-CSS
     reuse as the sequencer caret above, kept as its own rule since it
     rotates unconditionally rather than toggling with component state. */
  .dgp-caret-up { transform: rotate(180deg); }
  .dgp-restore { white-space: nowrap; }
  .dgp-unmatched {
    font-size: var(--fs-xs, 12px);
    color: var(--warn-text, #8a6d1a);
    margin: 8px 0 0;
  }
  .dgp-clearun { margin-left: 4px; }
  .dgp-apply {
    margin-top: 10px;
    padding: 6px 14px;
    border: 1px solid var(--accent, #4f46e5);
    border-radius: var(--radius-s, 6px);
    background: var(--accent, #4f46e5);
    color: #fff;
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .dgp-apply:disabled { opacity: 0.6; cursor: default; }
  .dgp-queued {
    font-size: var(--fs-xs, 12px);
    color: var(--warn-text, #8a6d1a);
    margin: 8px 0 0;
  }
  .dgp-editor { margin-top: 6px; }
  .dgp-editor-title { font-size: var(--fs-xs, 12px); font-weight: var(--fw-medium, 500); margin: 0 0 4px; }
  .dgp-editor-svg {
    width: 100%;
    height: 220px;
    margin-top: 6px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    touch-action: none;
  }
  .dgp-editor-poly {
    fill: var(--accent, #4f46e5);
    fill-opacity: 0.18;
    stroke: var(--accent, #4f46e5);
    stroke-width: 0.6;
    vector-effect: non-scaling-stroke;
  }
  .dgp-editor-poly.invalid {
    fill: var(--danger, #b3261e);
    fill-opacity: 0.14;
    stroke: var(--danger, #b3261e);
  }
  .dgp-editor-vertex {
    fill: var(--accent, #4f46e5);
    stroke: #fff;
    stroke-width: 0.4;
    vector-effect: non-scaling-stroke;
    cursor: grab;
  }
  .dgp-editor-mid {
    fill: var(--surface, #fff);
    stroke: var(--muted, #667);
    stroke-width: 0.3;
    vector-effect: non-scaling-stroke;
    opacity: 0.6;
    cursor: copy;
  }
  .dgp-editor-mid:hover { opacity: 1; }
  .dgp-editor-issues {
    margin: 6px 0 0;
    padding-left: 18px;
    font-size: var(--fs-xs, 12px);
    color: var(--danger, #b3261e);
  }
  .dgp-editor-btns { display: flex; gap: 8px; align-items: center; margin-top: 8px; flex-wrap: wrap; }
  .dgp-split-line {
    stroke: var(--danger, #b3261e);
    stroke-width: 0.5;
    vector-effect: non-scaling-stroke;
  }
  .dgp-split-line.invalid { stroke-dasharray: 1.2 0.8; }
  .dgp-mergecheck { display: flex; align-items: center; margin-top: 4px; flex: none; }
  .dgp-mergebar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin: 6px 0;
    padding: 6px 8px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    font-size: var(--fs-xs, 12px);
  }
  .dgp-mergeissue { color: var(--warn-text, #8a6d1a); }
</style>
