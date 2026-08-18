<script>
  import { createEventDispatcher, onDestroy } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import Icon from "./Icon.svelte";
  import {
    buildDigitizeConfig,
    digitize,
    decodedFromDesignCached,
    describeWarnings,
    canonicalShapeEdits,
    editsKey,
    reviewFromJob,
    reconcileReview,
    reorderWithinLayer,
    effLayer,
    sortShapes,
    effSewOrder,
    layerSiblings,
    effRgb,
    groupIntoBlocks,
    boundaryIssues,
    mergeGroupIssues,
    splitLineIssues,
    textClusterIds,
    textClusterMembers,
    textClusterSeed,
  } from "../lib/digitizer.js";
  import { loadPalette, nearestInList } from "../lib/threads.js";

  // Editor panel for an auto-digitized artwork element (build step 10).
  // The element stores the source image (processing size, PNG base64), the
  // digitizing params (service field names), and the BAKED result Design —
  // see project.js's defaultDigitizedElement. This panel owns the review
  // loop: upload -> params -> Digitize -> poll -> result lands on the
  // element; a param change with a result in hand re-digitizes automatically
  // (the service's job cache makes an unchanged re-ask free).
  export let element;
  export let project; // garmentId rides into the config (fabric preset service-side)
  export let health = null; // /health payload or null; App owns the probe

  const d = createEventDispatcher();

  // Processing size (long edge). The pipeline needs nowhere near the
  // original resolution ("2000 px across is plenty" — service limits), and
  // this base64 lives in localStorage with the project, so smaller is a
  // feature: at 1200 px a flat-color logo PNG is typically well under 500 KB.
  const PROCESS_MAX_PX = 1200;
  // Storage guard on the stored base64 itself (localStorage isn't infinite —
  // same reasoning as DesignPanel's 1 MB DST cap).
  const MAX_SOURCE_B64 = 2_000_000;

  let error = "";
  let phase = "idle"; // idle | submitting | queued | running
  let fileBusy = false;
  let rerunWanted = false;
  let destroyed = false;
  onDestroy(() => {
    destroyed = true;
  });

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // ---- upload ---------------------------------------------------------------

  async function loadImage(file) {
    if (typeof createImageBitmap === "function") {
      try {
        return await createImageBitmap(file);
      } catch (e) {
        // fall through to the <img> + object URL fallback
      }
    }
    const url = URL.createObjectURL(file);
    try {
      return await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("Could not read this image file."));
        img.src = url;
      });
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function onFile(e) {
    const file = e.currentTarget.files && e.currentTarget.files[0];
    e.currentTarget.value = ""; // re-selecting the same file must re-fire change
    if (!file) return;
    error = "";
    fileBusy = true;
    try {
      const img = await loadImage(file);
      const iw = img.width, ih = img.height;
      const scale = Math.min(1, PROCESS_MAX_PX / (Math.max(iw, ih) || 1));
      const w = Math.max(1, Math.round(iw * scale));
      const h = Math.max(1, Math.round(ih * scale));
      const cv = document.createElement("canvas");
      cv.width = w;
      cv.height = h;
      cv.getContext("2d").drawImage(img, 0, 0, w, h);
      const dataUrl = cv.toDataURL("image/png");
      const b64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      if (b64.length > MAX_SOURCE_B64) {
        error = "That image is too heavy to save with the design — the limit is about 1.5 MB after downscaling. Simplify or shrink it and try again.";
        return;
      }
      // New artwork resets everything the old artwork produced — including
      // the layer list and its edits, which are keyed to the OLD art's
      // shape ids and would only produce SHAPE_EDIT_UNKNOWN_ID noise here.
      patch({
        sourcePng: b64, name: file.name, result: null, warnings: [], blockColors: {}, sizeMm: null,
        review: null, shapeOverrides: {}, deletedShapeIds: [], appliedEdits: null,
        mergeGroups: [], splitLines: {},
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
  async function runDigitize(el) {
    if (!el.sourcePng || !health) return;
    if (phase !== "idle") {
      rerunWanted = true; // a change landed mid-flight; run again after
      return;
    }
    error = "";
    phase = "submitting";
    try {
      const cfg = buildDigitizeConfig(el, project);
      const job = await digitize(el.sourcePng, cfg, {
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
        warnings: job.warnings || [],
        review: reconcileReview(el.review, reviewFromJob(job.review), el.deletedShapeIds),
        preflight: job.preflight || null,
        appliedEdits: editsKey({
          deleted_shape_ids: cfg.deleted_shape_ids,
          shape_overrides: cfg.shape_overrides,
          merge_shape_ids: cfg.merge_shape_ids,
          split_shapes: cfg.split_shapes,
        }),
      });
    } catch (err) {
      if (!destroyed) error = String((err && err.message) || err);
    } finally {
      if (!destroyed) {
        phase = "idle";
        if (rerunWanted) {
          rerunWanted = false;
          runDigitize(element);
        }
      }
    }
  }

  // Param changes re-digitize automatically once a result exists (the review
  // loop); before the first result the Digitize button is the explicit start.
  // Same prev-value guard pattern as ImagePanel's re-flatten.
  let prevParamsJson = JSON.stringify(element.params);
  $: {
    const now = JSON.stringify(element.params);
    if (now !== prevParamsJson) {
      prevParamsJson = now;
      if (element.result) runDigitize(element);
    }
  }

  // Shape edits restitch on their own, after a pause (Kent's call,
  // 2026-08-13). Before this, a hand edit on the canvas moved the outline and
  // left the stitches where they were until "Apply layer changes" was pressed
  // — correct, but it made the canvas editor feel like it was drawing on a
  // photograph rather than editing a design.
  //
  // Debounced rather than immediate because a restitch is a full stage 0-7
  // service run: measured 0.65s on simple line art but ~10-14s on a real
  // photograph, with no useful cache (the job key folds shape_overrides into
  // the config, so every edit is a guaranteed miss). Firing per drag would
  // queue a 10s run behind every nudge. Waiting for the user to STOP means
  // ten adjustments cost one run, not ten.
  const RESTITCH_IDLE_MS = 2000;
  let restitchTimer = 0;
  let prevEditsKey = editsKey(canonicalShapeEdits(element));
  $: {
    const k = editsKey(canonicalShapeEdits(element));
    if (k !== prevEditsKey) {
      prevEditsKey = k;
      // `health` gates it: with no service there is nothing to restitch to,
      // and the existing "saved with the design, applied next time you
      // digitize" branch already covers that honestly.
      if (element.result && health) scheduleRestitch();
    }
  }

  function scheduleRestitch() {
    clearTimeout(restitchTimer);
    restitchTimer = setTimeout(() => {
      restitchTimer = 0;
      runDigitize(element);
    }, RESTITCH_IDLE_MS);
  }

  onDestroy(() => clearTimeout(restitchTimer));

  function setParam(key, value) {
    patch({ params: { ...element.params, [key]: value } });
  }

  // ---- derived view state ---------------------------------------------------

  $: pending = phase !== "idle";
  $: statusLine =
    phase === "running" ? "Digitizing your art…" :
    phase === "queued" ? "Waiting for the digitizer — another job is running…" :
    phase === "submitting" ? "Sending your art…" : "";

  $: decoded = element.result ? decodedFromDesignCached(element.result) : null;
  $: warningLines = describeWarnings(element.warnings);
  // BACKGROUND_ENCLOSED gets its own live, actionable banner (below, next to
  // unstitchedRows) instead of this generic list -- showing both would just
  // repeat the same fact once as a static server message and once as a count
  // that tracks the user's own restores.
  $: otherWarningLines = warningLines.filter((w) => w.code !== "BACKGROUND_ENCLOSED");

  // Resize honesty (Kent's rule, same as DesignPanel): the field's resize
  // handles SCALE baked stitches, they don't re-digitize — density changes
  // with size. Unlike a .dst import, here the fix is one click away:
  // re-digitize at the resized width.
  $: rotation = element.rotationDeg || 0;
  $: nativeWidthNow = rotatedWidth(decoded, rotation);
  $: scaleFactor = decoded && element.sizeMm ? element.sizeMm / Math.max(0.1, nativeWidthNow) : 1;
  $: resized = Math.abs(scaleFactor - 1) > 0.02;

  function rotatedWidth(dec, deg) {
    if (!dec) return 0.1;
    const rot = ((deg % 360) + 360) % 360;
    if (rot === 0 || rot === 180) return dec.widthMM;
    if (rot === 90 || rot === 270) return dec.heightMM;
    const rad = (rot * Math.PI) / 180;
    return Math.abs(dec.widthMM * Math.cos(rad)) + Math.abs(dec.heightMM * Math.sin(rad));
  }

  // "Re-digitize at N mm": make the dragged size the new digitize target.
  // The params patch triggers the auto re-run; sizeMm clears in the same
  // patch so the fresh native-size stitches aren't immediately re-scaled.
  function redigitizeAtSize(el) {
    const target = Math.round(el.sizeMm * 10) / 10;
    patch({ params: { ...el.params, target_width_mm: target }, sizeMm: null });
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
  ];

  $: overrides = element.shapeOverrides || {};
  $: deletedIds = element.deletedShapeIds || [];
  $: reviewShapes = (element.review && element.review.shapes) || [];
  $: orderedShapes = sortShapes(reviewShapes, overrides);
  $: knownIds = new Set(reviewShapes.map((s) => s.id));
  $: unmatchedCount = new Set(
    [...Object.keys(overrides), ...deletedIds].filter((sid) => !knownIds.has(sid))
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

  // The Sequencer view's color blocks: `sewableShapes` grouped by effLayer,
  // in sew order (the same list moveShape's up/down buttons walk, just
  // collapsed one row per color instead of one row per shape) — a block IS
  // one color's whole run before the machine changes thread. Dead/hidden/
  // unstitched shapes don't have a real place in the sew sequence, so they
  // never appear here even though they're still in the plain Layers list.
  $: sequencerBlocks = groupIntoBlocks(sewableShapes, overrides);

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

  function rowName(row) {
    return row.threadNumber ? "#" + row.threadNumber : "Shape";
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
    for (const sid of Object.keys(overrides)) if (knownIds.has(sid)) keep[sid] = overrides[sid];
    patch({
      shapeOverrides: keep,
      deletedShapeIds: deletedIds.filter((sid) => knownIds.has(sid)),
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
    <span class="dgp-upload-btn">{element.sourcePng ? "Replace artwork…" : "Auto Digitize Image"}</span>
    <input type="file" accept="image/png,image/jpeg,image/webp,image/*" on:change={onFile} disabled={fileBusy} />
  </label>
  {#if fileBusy}<p class="dgp-note">Reading the image…</p>{/if}

  {#if !element.sourcePng}
    <p class="dgp-note">
      Upload flat art — a logo, a mark, lettering as an image — and it comes back as stitches you
      can place like any other element. Clean, solid colors digitize best; photos and gradients
      won't sew cleanly. PNG with a transparent background and sharp, non-anti-aliased edges
      digitizes best — a bigger image sews sharper than a small one.
    </p>
  {:else}
    <div class="dgp-src">
      <img
        class="dgp-thumb"
        src={"data:image/png;base64," + element.sourcePng}
        alt={element.name || "Artwork"}
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

    <div class="dgp-params">
      <label class="dgp-param">
        <span>Stitch width</span>
        <input
          type="number"
          min="10"
          max="400"
          step="1"
          value={element.params.target_width_mm}
          on:change={(e) => setParam("target_width_mm", Math.max(10, parseFloat(e.currentTarget.value) || 80))}
        />
        <span class="dgp-unit">mm</span>
      </label>
      <label class="dgp-param">
        <span>Colors (max {element.params.max_colors})</span>
        <input
          type="range"
          min="2"
          max="12"
          step="1"
          value={element.params.max_colors}
          on:input={(e) => setParam("max_colors", parseInt(e.currentTarget.value, 10))}
        />
      </label>
      <label class="dgp-checkline">
        <input
          type="checkbox"
          checked={element.params.satin}
          on:change={(e) => setParam("satin", e.currentTarget.checked)}
        />
        Satin for thin shapes
      </label>
      <label class="dgp-checkline">
        <input
          type="checkbox"
          checked={element.params.detail_layer}
          on:change={(e) => setParam("detail_layer", e.currentTarget.checked)}
        />
        Detail lines for photos
      </label>
      <label class="dgp-param">
        <span>Fill angle</span>
        <select
          value={element.params.fill_angle_deg == null ? "auto" : String(element.params.fill_angle_deg)}
          on:change={onAngleChange}
        >
          {#each FILL_ANGLES as a}
            <option value={a.value == null ? "auto" : String(a.value)}>{a.label}</option>
          {/each}
        </select>
      </label>
      <label class="dgp-param">
        <span>Border</span>
        <select
          value={element.params.border}
          on:change={(e) => setParam("border", e.currentTarget.value)}
        >
          <option value="off">None</option>
          <option value="auto">Auto (satin where it fits)</option>
          <option value="bean">Bean (light outline)</option>
        </select>
      </label>
    </div>

    <button
      type="button"
      class="dgp-run"
      disabled={pending || !health}
      on:click={() => runDigitize(element)}
    >
      {pending ? "Digitizing…" : element.result ? "Digitize again" : "Digitize"}
    </button>
    {#if statusLine}<p class="dgp-status" role="status">{statusLine}</p>{/if}
    {#if error}<p class="dgp-error" role="alert">{error}</p>{/if}

    {#if element.result}
      <p class="dgp-stats">
        {element.result.stitchCount.toLocaleString()} stitches ·
        {element.result.widthMM.toFixed(0)}×{element.result.heightMM.toFixed(0)} mm ·
        {element.result.colorCount} color{element.result.colorCount === 1 ? "" : "s"}
      </p>

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
      {#if otherWarningLines.length}
        <ul class="dgp-warnings">
          {#each otherWarningLines as w (w.code + w.text)}
            <li>{w.text}</li>
          {/each}
        </ul>
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
          on:click={() => redigitizeAtSize(element)}
        >
          Re-digitize at {element.sizeMm.toFixed(0)} mm
        </button>
      {/if}

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
                  Color sequence ({sequencerBlocks.length} block{sequencerBlocks.length === 1 ? "" : "s"})
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
              {@const members = clusterMembers(clusterId)}
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
          <ol class="dgp-layerlist">
            {#each orderedShapes as row, i (row.id)}
              {@const dead = deletedIds.includes(row.id)}
              {@const stitched = effStitched(row, overrides)}
              {@const unstitched = !dead && !stitched}
              {@const clusterHidden = unstitched && isClusterHidden(row, textConversions)}
              <!-- Was excluded by default (an enclosed-background region)
                   AND is currently sewing — i.e. the user restored it. Shown
                   as a small badge plus an undo, so restoring stays a
                   reversible toggle rather than a one-way door. -->
              {@const restoredEnclosed = !dead && stitched && row.stitched === false}
              {@const boundaryEdited = !dead && !unstitched &&
                !!(overrides[row.id] && overrides[row.id].boundary_override)}
              {@const mergedInfo = !dead && !unstitched ? mergedFromInfo(row.id) : null}
              {@const splitInfo = !dead && !unstitched ? splitFromInfo(row.id) : null}
              {@const textCand = !dead && !unstitched && !!row.textCandidate}
              {@const rgb = effRgb(row, overrides)}
              {@const tier = effTier(row, overrides)}
              {@const siblings = dead || unstitched ? [] : layerSiblings(row, sewableShapes, overrides)}
              {@const siblingIdx = siblings.findIndex((r) => r.id === row.id)}
              <li class="dgp-layer" class:dead class:unstitched>
                {#if !dead && !unstitched}
                  <label class="dgp-mergecheck" title="Select for merge">
                    <input
                      type="checkbox"
                      checked={mergeSelection.includes(row.id)}
                      on:change={() => toggleMergeSelect(row.id)}
                      aria-label={"Select " + rowName(row) + " for merge"}
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
                      <ThreadPicker {rgb} compact on:pick={(e) => recolorShape(row.id, e.detail)} />
                      <span class="dgp-lname">{rowName(row)}</span>
                      <span class="dgp-larea">{fmtArea(row.areaMm2)}</span>
                      <span class="dgp-ltier tier-{tier || 'none'}">{tier || "not sewn"}</span>
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
                        aria-label="Stitch type"
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
                          aria-label="Fill angle"
                        >
                          {#each SHAPE_ANGLES as a}
                            <option value={a.value == null ? "auto" : String(a.value)}>{a.label}</option>
                          {/each}
                        </select>
                        <select
                          class="dgp-lsel"
                          value={overrideUnderlay(row, overrides)}
                          on:change={(e) => setShapeUnderlay(row.id, e.currentTarget.value)}
                          aria-label="Underlay style"
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
                        aria-label="Border"
                      >
                        <option value="default">Design ({element.params.border})</option>
                        <option value="off">No border</option>
                        <option value="auto">Auto border</option>
                        <option value="bean">Bean border</option>
                      </select>
                    </div>
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
                      aria-label="Sew earlier"
                      on:click={() => moveShape(row, -1)}
                    ><Icon name="arrowUp" size={12} /></button>
                    <button
                      type="button"
                      class="dgp-lbtn"
                      disabled={i === orderedShapes.length - 1}
                      title="Sew later"
                      aria-label="Sew later"
                      on:click={() => moveShape(row, 1)}
                    ><Icon name="arrowDown" size={12} /></button>
                    {#if siblings.length > 1}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        disabled={siblingIdx <= 0}
                        title="Sew earlier within this color"
                        aria-label="Sew earlier within this color"
                        on:click={() => moveShapeWithinLayer(row, -1)}
                      ><Icon name="chevron" size={12} class="dgp-caret-up" /></button>
                      <button
                        type="button"
                        class="dgp-lbtn"
                        disabled={siblingIdx < 0 || siblingIdx === siblings.length - 1}
                        title="Sew later within this color"
                        aria-label="Sew later within this color"
                        on:click={() => moveShapeWithinLayer(row, 1)}
                      ><Icon name="chevron" size={12} /></button>
                    {/if}
                    {#if restoredEnclosed}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Mark as not sewn again (enclosed area)"
                        aria-label="Mark as not sewn again"
                        on:click={() => unrestoreStitching(row.id)}
                      ><Icon name="exclude" size={12} /></button>
                    {/if}
                    {#if mergedInfo}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Undo this merge (the original shapes come back)"
                        aria-label="Undo merge"
                        on:click={() => undoMerge(row.id)}
                      ><Icon name="revert" size={12} /></button>
                    {:else if splitInfo}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Undo this split (the original shape comes back)"
                        aria-label="Undo split"
                        on:click={() => undoSplit(row.id)}
                      ><Icon name="revert" size={12} /></button>
                    {:else}
                      <button
                        type="button"
                        class="dgp-lbtn"
                        title="Cut this shape into two"
                        aria-label="Split shape"
                        on:click={() => startSplitEdit(row)}
                      ><Icon name="scissors" size={12} /></button>
                    {/if}
                    <button
                      type="button"
                      class="dgp-lbtn"
                      title="Edit this shape's boundary"
                      aria-label="Edit shape boundary"
                      on:click={() => startBoundaryEdit(row)}
                    ><Icon name="edit" size={12} /></button>
                    <button
                      type="button"
                      class="dgp-lbtn"
                      title="Hide this shape (restorable)"
                      aria-label="Hide this shape"
                      on:click={() => deleteShape(row.id)}
                    ><Icon name="close" size={12} /></button>
                  {/if}
                </div>
              </li>
            {/each}
          </ol>
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
              <p class="dgp-note">Restitching on its own in a moment — or apply now.</p>
            {:else}
              <p class="dgp-queued">
                The digitizer isn't running — these layer changes are saved with the design and
                apply the next time you digitize.
              </p>
            {/if}
          {/if}
        </div>
      {:else if health}
        <p class="dgp-note">Digitize again to get an editable layer list for this result.</p>
      {/if}

      <div class="dgp-blocks">
        <span class="dgp-blocks-label">Thread per color</span>
        {#each Array.from({ length: (element.result.colors || []).length }) as _, i}
          <div class="dgp-block">
            <span class="dgp-block-n">{blockName(element, i)}</span>
            <ThreadPicker rgb={blockRgb(element, i)} compact on:pick={(e) => pickBlock(i, e.detail)} />
          </div>
        {/each}
      </div>

      <label class="letterspacing">
        <span>Rotation</span>
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
</div>

<style>
  .digipanel { margin-top: 4px; }
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
  .dgp-upload:focus-within .dgp-upload-btn {
    outline: 2px solid var(--accent, #4f46e5);
    outline-offset: 1px;
  }
  .dgp-note { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 8px 0 0; }
  .dgp-src { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
  .dgp-thumb {
    width: 56px;
    height: 56px;
    object-fit: contain;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: #fff;
  }
  .dgp-srcname { font-size: var(--fs-xs, 12px); color: var(--muted, #667); word-break: break-all; }
  .dgp-offline {
    margin-top: 10px;
    padding: 8px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    font-size: var(--fs-xs, 12px);
  }
  .dgp-offline p { margin: 0 0 6px; }
  .dgp-cmd code { font-size: 11px; }
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
  .dgp-param input[type="number"] { width: 70px; }
  .dgp-param input[type="range"] { flex: 1; }
  .dgp-unit { color: var(--muted, #667); }
  .dgp-checkline { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs, 12px); }
  .dgp-run {
    margin-top: 12px;
    padding: 7px 16px;
    border: 1px solid var(--accent, #4f46e5);
    border-radius: var(--radius-s, 6px);
    background: var(--accent, #4f46e5);
    color: #fff;
    cursor: pointer;
    font-size: var(--fs-s, 13px);
  }
  .dgp-run:disabled { opacity: 0.6; cursor: default; }
  .dgp-status { font-size: var(--fs-xs, 12px); color: var(--muted, #667); margin: 6px 0 0; }
  .dgp-error { font-size: var(--fs-xs, 12px); color: var(--danger, #b3261e); margin: 6px 0 0; }
  .dgp-stats { font-size: var(--fs-xs, 12px); margin: 10px 0 0; }
  .dgp-warnings {
    margin: 8px 0 0;
    padding-left: 18px;
    font-size: var(--fs-xs, 12px);
    color: var(--warn-text, #8a6d1a);
  }
  .dgp-warnings li { margin-top: 2px; }
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
  .dgp-resize { font-size: var(--fs-xs, 12px); color: var(--warn-text, #8a6d1a); margin: 8px 0 6px; }
  .dgp-blocks { margin-top: 10px; }
  .dgp-blocks-label { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
  .dgp-block { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
  .dgp-block-n { font-size: var(--fs-xs, 12px); min-width: 130px; }
  .dgp-layers { margin-top: 12px; }
  .dgp-layers-head { display: flex; align-items: baseline; gap: 8px; }
  .dgp-layers-title { font-size: var(--fs-xs, 12px); font-weight: 600; }
  .dgp-layers-order { font-size: 11px; color: var(--muted, #667); }
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
    font-size: 11px;
    text-align: left;
  }
  /* `chevron` points down at rest -- that's the "open" reading, so the
     closed (▸) state is the one that needs a rotate; same reuse-one-icon,
     rotate-in-CSS convention Icon.svelte's own comment documents. */
  .dgp-seq-caret { flex: none; color: var(--muted, #667); transition: transform 0.15s ease; }
  .dgp-seq-caret-closed { transform: rotate(-90deg); }
  .dgp-seq-title { flex: 1; font-weight: 600; }
  .dgp-seq-trims { color: var(--muted, #667); white-space: nowrap; }
  .dgp-seq-trims.heavy { color: var(--warn-text, #8a6d1a); font-weight: 600; }
  .dgp-seq-list { list-style: none; margin: 4px 0 0; padding: 0; }
  .dgp-seq-block {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    border-top: 1px solid var(--tint-border, #ccd6fb);
    font-size: 11px;
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
  .dgp-seq-btns { display: flex; gap: 2px; flex: none; }
  .dgp-layerlist { list-style: none; margin: 6px 0 0; padding: 0; }
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
  .dgp-ltier-unstitched {
    color: var(--warn-text, #8a6d1a);
    border-color: var(--warn-text, #8a6d1a);
  }
  .dgp-lbadge {
    font-size: 10px;
    color: var(--muted, #667);
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: 8px;
    padding: 1px 5px;
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
  .dgp-lname { font-size: var(--fs-xs, 12px); font-weight: 600; }
  .dgp-larea { font-size: 11px; color: var(--muted, #667); }
  .dgp-ltier {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 1px 5px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: 8px;
    color: var(--muted, #667);
  }
  .dgp-lsel { font-size: 11px; max-width: 110px; }
  .dgp-lbtns { display: flex; flex-direction: column; gap: 2px; flex: none; }
  .dgp-lbtn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px 6px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: 11px;
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
  .dgp-editor-title { font-size: var(--fs-xs, 12px); font-weight: 600; margin: 0 0 4px; }
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
