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
  //
  // During a drag the rectangle is LIVE LOCAL state; `onchange` fires once, on
  // pointerup, so a drag is one edit (one undo step, one restitch) rather than
  // a patch per pointermove. A pointercancel discards the drag instead.
  let { src, crop = null, onchange = () => {} } = $props();

  let host = $state(null);
  let dragging = $state(null); // null | {handle, startX, startY, start}
  let live = $state(null); // the rectangle being dragged, or null

  const FULL = { x0: 0, y0: 0, x1: 1, y1: 1 };
  let rect = $derived(live ?? crop ?? FULL);
  let cropped = $derived(
    rect.x0 > 0.001 || rect.y0 > 0.001 || rect.x1 < 0.999 || rect.y1 < 0.999,
  );

  const clamp = (v) => Math.min(Math.max(v, 0), 1);

  function start(handle, e) {
    e.preventDefault();
    const s = { ...rect };
    dragging = { handle, startX: e.clientX, startY: e.clientY, start: s };
    live = s;
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end, { once: true });
    window.addEventListener("pointercancel", cancel, { once: true });
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
      next.x0 = Math.min(Math.max(s.x0 + dx, 0), 1 - w);
      next.y0 = Math.min(Math.max(s.y0 + dy, 0), 1 - hh);
      next.x1 = next.x0 + w;
      next.y1 = next.y0 + hh;
    } else {
      if (h.includes("w")) next.x0 = clamp(s.x0 + dx);
      if (h.includes("e")) next.x1 = clamp(s.x1 + dx);
      if (h.includes("n")) next.y0 = clamp(s.y0 + dy);
      if (h.includes("s")) next.y1 = clamp(s.y1 + dy);
    }
    if (next.x1 - next.x0 < 0.02 || next.y1 - next.y0 < 0.02) return;
    live = next;
  }

  function detach() {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", end);
    window.removeEventListener("pointercancel", cancel);
  }

  function end() {
    const s = dragging && dragging.start;
    const next = live;
    dragging = null;
    live = null;
    detach();
    if (s && next && (next.x0 !== s.x0 || next.y0 !== s.y0 || next.x1 !== s.x1 || next.y1 !== s.y1)) {
      onchange(next);
    }
  }

  // A CANCELLED gesture (the browser took the pointer: a scroll or pinch
  // won, the pen left range, a system dialog) discards the drag: the box snaps
  // back to where it was and nothing is emitted. Committing it instead would
  // restitch on a rectangle the customer never let go of. Without this the
  // drag stayed live -- no pointerup ever arrives after a pointercancel -- so
  // the box followed the next pointermove until some later click ended it.
  function cancel() {
    dragging = null;
    live = null;
    detach();
  }

  // An unmount mid-drag must not leave window listeners behind.
  $effect(() => detach);

  function reset() {
    onchange({ ...FULL });
  }

  const HANDLES = [
    ["nw", "top-left corner"], ["ne", "top-right corner"],
    ["sw", "bottom-left corner"], ["se", "bottom-right corner"],
    ["n", "top edge"], ["s", "bottom edge"], ["w", "left edge"], ["e", "right edge"],
  ];
</script>

<div class="crop-host" bind:this={host}>
  <img class="dgp-thumb" {src} alt="Artwork preview with crop area" draggable="false" />
  <div
    class="crop-rect"
    role="group"
    aria-label="Crop area"
    style="left:{rect.x0 * 100}%; top:{rect.y0 * 100}%; width:{(rect.x1 - rect.x0) * 100}%; height:{(rect.y1 - rect.y0) * 100}%"
    onpointerdown={(e) => start("move", e)}
  >
    {#each HANDLES as [h, label]}
      <button
        type="button"
        class="handle {h}"
        aria-label="Drag {label}"
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
  .crop-host { position: relative; display: inline-block; line-height: 0; overflow: hidden; }
  /* max-height bounds a tall upload (a 554 x 1200 phone screenshot, the main
     use case, was ~650 px tall and pushed the panel's controls below the
     fold). width:auto keeps the aspect; the host is inline-block with
     line-height 0, so it shrink-wraps the SCALED image and the percentage
     rectangle above stays on the picture. */
  .crop-host img { display: block; max-width: 100%; max-height: 320px; width: auto; height: auto; user-select: none; }
  .crop-rect {
    position: absolute;
    box-sizing: border-box;
    border: 2px solid var(--accent, #2f6fed);
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.42);
    cursor: move;
    touch-action: none;
  }
  /* Every handle sits INSIDE the box, so .crop-host's overflow:hidden (which
     contains the shadow above) never clips one at the image edge. */
  .handle {
    position: absolute; width: 14px; height: 14px; padding: 0;
    background: #fff; border: 2px solid var(--accent, #2f6fed);
    border-radius: 2px; touch-action: none; box-sizing: border-box;
  }
  .handle.nw { left: 0; top: 0; cursor: nwse-resize; }
  .handle.ne { right: 0; top: 0; cursor: nesw-resize; }
  .handle.sw { left: 0; bottom: 0; cursor: nesw-resize; }
  .handle.se { right: 0; bottom: 0; cursor: nwse-resize; }
  .handle.n { left: calc(50% - 7px); top: 0; cursor: ns-resize; }
  .handle.s { left: calc(50% - 7px); bottom: 0; cursor: ns-resize; }
  .handle.w { top: calc(50% - 7px); left: 0; cursor: ew-resize; }
  .handle.e { top: calc(50% - 7px); right: 0; cursor: ew-resize; }
  .crop-reset { margin-top: 0.5rem; }
</style>
