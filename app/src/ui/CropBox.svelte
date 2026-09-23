<script>
  // A draggable crop rectangle over the upload preview.
  //
  // Coordinates are FRACTIONS of the image, never pixels: the service may
  // receive the customer's original file or the Studio's 1,200-px preview,
  // and a pixel rectangle would address the wrong raster (spec section 2.2).
  //
  // This component never re-encodes anything. It emits a rectangle; the crop
  // is applied server-side. Cropping by drawing to a canvas and exporting a
  // PNG is exactly the path DOCTRINE 2026-09-19/20 priced at three harms.
  let { src, crop = null, onchange = () => {} } = $props();

  let host = $state(null);
  let dragging = $state(null); // null | {handle, startX, startY, start}
  // The in-progress rectangle while a drag is live. Fix round 1 (Important
  // finding 2): `move()` used to call `onchange` on every raw pointermove,
  // and DigitizePanel's `patch()` triggers an unconditional `saveProject()`
  // on every `elupdate` -- a JSON.stringify of the whole project, including
  // the up-to-2 MB `sourcePng`. A drag was firing that full localStorage
  // write many times a second. `draft` lets the rectangle keep tracking the
  // pointer smoothly (the derived `rect` below reads it first) without
  // calling `onchange` until the drag actually ends.
  let draft = $state(null);

  const FULL = { x0: 0, y0: 0, x1: 1, y1: 1 };
  let rect = $derived(draft ?? crop ?? FULL);
  let cropped = $derived(
    rect.x0 > 0.001 || rect.y0 > 0.001 || rect.x1 < 0.999 || rect.y1 < 0.999,
  );

  const clamp = (v) => Math.min(Math.max(v, 0), 1);
  const sameRect = (a, b) => a.x0 === b.x0 && a.y0 === b.y0 && a.x1 === b.x1 && a.y1 === b.y1;

  function start(handle, e) {
    e.preventDefault();
    dragging = { handle, startX: e.clientX, startY: e.clientY, start: { ...rect } };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end, { once: true });
  }

  function move(e) {
    if (!dragging || !host) return;
    const box = host.getBoundingClientRect();
    const dx = (e.clientX - dragging.startX) / box.width;
    const dy = (e.clientY - dragging.startY) / box.height;
    const s = dragging.start;
    let next = { ...s };
    const h = dragging.handle;
    if (h === "move") {
      const w = s.x1 - s.x0, hh = s.y1 - s.y0;
      next.x0 = clamp(s.x0 + dx); next.y0 = clamp(s.y0 + dy);
      next.x1 = clamp(next.x0 + w); next.y1 = clamp(next.y0 + hh);
    } else {
      if (h.includes("w")) next.x0 = clamp(s.x0 + dx);
      if (h.includes("e")) next.x1 = clamp(s.x1 + dx);
      if (h.includes("n")) next.y0 = clamp(s.y0 + dy);
      if (h.includes("s")) next.y1 = clamp(s.y1 + dy);
    }
    if (next.x1 - next.x0 < 0.02 || next.y1 - next.y0 < 0.02) return;
    draft = next;
  }

  function end() {
    dragging = null;
    window.removeEventListener("pointermove", move);
    // Fire exactly once, on release, and only if the drag actually moved the
    // rectangle -- a click-and-release with no movement must not manufacture
    // a patch (one undo step, one re-digitize per REAL change, not per
    // gesture).
    if (draft && !sameRect(draft, crop ?? FULL)) {
      onchange(draft);
    }
    draft = null;
  }

  function reset() {
    onchange({ ...FULL });
  }
</script>

<div class="crop-host" bind:this={host}>
  <img {src} alt="Artwork preview with crop area" draggable="false" />
  <div
    class="crop-rect"
    role="group"
    aria-label="Crop area"
    style="left:{rect.x0 * 100}%; top:{rect.y0 * 100}%; width:{(rect.x1 - rect.x0) * 100}%; height:{(rect.y1 - rect.y0) * 100}%"
    onpointerdown={(e) => start("move", e)}
  >
    {#each ["nw", "ne", "sw", "se"] as h}
      <button
        type="button"
        class="handle {h}"
        aria-label="Drag {h} corner"
        onpointerdown={(e) => { e.stopPropagation(); start(h, e); }}
      ></button>
    {/each}
  </div>
</div>

<!-- Always present, not only when the box is cropped: a customer whose
     proposal is a wrong no-op must still be able to find the tool. -->
<button type="button" class="crop-reset" onclick={reset} disabled={!cropped}>
  Use whole image
</button>

<style>
  .crop-host { position: relative; display: inline-block; line-height: 0; }
  .crop-host img { max-width: 100%; height: auto; user-select: none; }
  .crop-rect {
    position: absolute;
    border: 2px solid var(--accent, #2f6fed);
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.42);
    cursor: move;
    touch-action: none;
  }
  .handle {
    position: absolute; width: 14px; height: 14px; padding: 0;
    background: #fff; border: 2px solid var(--accent, #2f6fed);
    border-radius: 2px; touch-action: none;
  }
  .handle.nw { left: -8px; top: -8px; cursor: nwse-resize; }
  .handle.ne { right: -8px; top: -8px; cursor: nesw-resize; }
  .handle.sw { left: -8px; bottom: -8px; cursor: nesw-resize; }
  .handle.se { right: -8px; bottom: -8px; cursor: nwse-resize; }
  .crop-reset { margin-top: 0.5rem; }
</style>
