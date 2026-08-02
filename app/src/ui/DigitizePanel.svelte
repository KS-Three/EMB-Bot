<script>
  import { createEventDispatcher, onDestroy } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import {
    buildDigitizeConfig,
    digitize,
    decodedFromDesignCached,
    describeWarnings,
    canonicalShapeEdits,
    editsKey,
    reviewFromJob,
    reconcileReview,
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
        appliedEdits: editsKey({
          deleted_shape_ids: cfg.deleted_shape_ids,
          shape_overrides: cfg.shape_overrides,
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
  // One row per shape, keyed by shape_id (content-derived ids survive a
  // re-digitize via the engine's match_shape_ids). Edits accumulate on the
  // element (shapeOverrides / deletedShapeIds) and only restitch on Apply —
  // the review payload the rows render from is the LAST job's, so live-
  // editing it would show stitches that don't exist yet.

  const SHAPE_ANGLES = [{ value: null, label: "Auto angle" }, ...FILL_ANGLES.slice(1)];

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

  // Effective layer: the user's explicit sew-order override, else the layer
  // the engine assigned (one per thread), else last. Rows sort by it, then
  // by the emitted sew position — the list IS the sew order.
  function effLayer(row, ov) {
    const e = ov[row.id] || {};
    if (Number.isInteger(e.layer)) return e.layer;
    if (row.layer != null) return row.layer;
    return row.sewIndex == null ? 1e9 : row.sewIndex;
  }

  function sortShapes(shapes, ov) {
    return [...shapes].sort(
      (a, b) =>
        effLayer(a, ov) - effLayer(b, ov) ||
        (a.sewIndex == null ? 1e9 : a.sewIndex) - (b.sewIndex == null ? 1e9 : b.sewIndex) ||
        (a.id < b.id ? -1 : 1)
    );
  }

  function effRgb(row, ov) {
    const e = ov[row.id] || {};
    return e.rgb || row.rgb || [136, 136, 136];
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

  // "Sew earlier/later", within what the integer layer field can express:
  // join the adjacent row's layer when it differs; when the neighbour
  // already shares this layer, step past the whole group instead — order
  // WITHIN a layer belongs to the machine's pathing (stage 6 nearest-
  // neighbour), not to this list, and pretending otherwise would show an
  // order the file won't sew.
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
</script>

<div class="digipanel">
  <label class="dgp-upload">
    <span class="dgp-upload-btn">{element.sourcePng ? "Replace artwork…" : "Choose artwork…"}</span>
    <input type="file" accept="image/png,image/jpeg,image/webp,image/*" on:change={onFile} disabled={fileBusy} />
  </label>
  {#if fileBusy}<p class="dgp-note">Reading the image…</p>{/if}

  {#if !element.sourcePng}
    <p class="dgp-note">
      Upload flat art — a logo, a mark, lettering as an image — and it comes back as stitches you
      can place like any other element. Clean, solid colors digitize best; photos and gradients
      won't sew cleanly.
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

      {#if warningLines.length}
        <ul class="dgp-warnings">
          {#each warningLines as w (w.code + w.text)}
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
          <ol class="dgp-layerlist">
            {#each orderedShapes as row, i (row.id)}
              {@const dead = deletedIds.includes(row.id)}
              {@const rgb = effRgb(row, overrides)}
              {@const tier = effTier(row, overrides)}
              <li class="dgp-layer" class:dead>
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
                    {:else}
                      <ThreadPicker {rgb} compact on:pick={(e) => recolorShape(row.id, e.detail)} />
                      <span class="dgp-lname">{rowName(row)}</span>
                      <span class="dgp-larea">{fmtArea(row.areaMm2)}</span>
                      <span class="dgp-ltier tier-{tier || 'none'}">{tier || "not sewn"}</span>
                    {/if}
                  </div>
                  {#if !dead}
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
                      {/if}
                    </div>
                  {/if}
                </div>
                <div class="dgp-lbtns">
                  {#if dead}
                    <button type="button" class="dgp-lbtn dgp-restore" on:click={() => restoreShape(row.id)}>
                      Restore
                    </button>
                  {:else}
                    <button
                      type="button"
                      class="dgp-lbtn"
                      disabled={i === 0}
                      title="Sew earlier"
                      aria-label="Sew earlier"
                      on:click={() => moveShape(row, -1)}
                    >↑</button>
                    <button
                      type="button"
                      class="dgp-lbtn"
                      disabled={i === orderedShapes.length - 1}
                      title="Sew later"
                      aria-label="Sew later"
                      on:click={() => moveShape(row, 1)}
                    >↓</button>
                    <button
                      type="button"
                      class="dgp-lbtn"
                      title="Hide this shape (restorable)"
                      aria-label="Hide this shape"
                      on:click={() => deleteShape(row.id)}
                    >✕</button>
                  {/if}
                </div>
              </li>
            {/each}
          </ol>

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
              <p class="dgp-note">Layer changes restitch only when you apply them.</p>
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
  .dgp-resize { font-size: var(--fs-xs, 12px); color: var(--warn-text, #8a6d1a); margin: 8px 0 6px; }
  .dgp-blocks { margin-top: 10px; }
  .dgp-blocks-label { display: block; font-size: var(--fs-xs, 12px); margin-bottom: 4px; }
  .dgp-block { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
  .dgp-block-n { font-size: var(--fs-xs, 12px); min-width: 130px; }
  .dgp-layers { margin-top: 12px; }
  .dgp-layers-head { display: flex; align-items: baseline; gap: 8px; }
  .dgp-layers-title { font-size: var(--fs-xs, 12px); font-weight: 600; }
  .dgp-layers-order { font-size: 11px; color: var(--muted, #667); }
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
    padding: 2px 6px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 6px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: 11px;
    line-height: 1.3;
  }
  .dgp-lbtn:disabled { opacity: 0.4; cursor: default; }
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
</style>
