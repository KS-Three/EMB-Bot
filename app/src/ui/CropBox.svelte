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
  // `minFrac`: the smallest width/height (as a fraction of the raster,
  // same units as `crop`) a drag is allowed to produce. Defaults to the
  // pre-2026-09-22 constant 2%; a caller whose preview raster is small
  // should pass a fraction derived from the SERVICE's pixel floor
  // (`digitizer_core/crop.py` MIN_CROP_PX = 16) instead, or a customer on a
  // small upload can drag to this default and land under 16 px on an axis
  // -- server-rejected with a message written for a programming error, and
  // it re-fires on every later param change until they widen the box
  // (finding 4, 2026-09-22 review). `DigitizePanel` computes and passes it.
  let { src, crop = null, onchange = () => {}, minFrac = 0.02 } = $props();

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
    // Pointer capture, fix round 2 (Important finding 3): without it, a drag
    // that ends without a pointerup ever reaching this component -- released
    // outside the viewport, or the gesture cancelled by the platform -- left
    // `dragging` stuck. Before round 1 that only leaked a listener with no
    // visible symptom; after round 1 it FREEZES the on-screen rectangle on
    // the abandoned position forever, because `rect` now reads `draft` first
    // and nothing ever clears it. Matches the pattern already used by the
    // three other drag handlers in this codebase (EmbroideryField.svelte,
    // ManualPanel.svelte, and DigitizePanel.svelte's own edit-drag/
    // split-drag): capture on the element that received pointerdown,
    // pointermove/up/cancel listened on an ancestor (`.crop-host` below).
    // Same try/catch fallback DigitizePanel's `startEditDrag` documents --
    // unavailable in some test/embedded environments (jsdom implements no
    // pointer-capture methods at all) -- the drag still works off the
    // container's own listeners, just without the "released outside the
    // viewport" guarantee capture buys.
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      // see comment above
    }
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
      // Clamp the DELTA, not the resulting edge (finding 7, 2026-09-22
      // review). Clamping `next.x0` and then deriving `next.x1 = next.x0 +
      // w` let x1 saturate at 1 while x0 kept advancing, so a move past the
      // right/bottom edge SHRANK the rectangle instead of stopping it --
      // moving a 0.4-wide box right by 0.5 gave [0.7, 1.0] (0.3 wide). The
      // left/top direction happened to preserve width only because x0 is
      // clamped before x1 is derived from it. Clamping dx/dy to the room
      // actually available on each side means every direction preserves
      // size.
      const cdx = Math.min(Math.max(dx, -s.x0), 1 - s.x1);
      const cdy = Math.min(Math.max(dy, -s.y0), 1 - s.y1);
      next.x0 = s.x0 + cdx; next.y0 = s.y0 + cdy;
      next.x1 = s.x1 + cdx; next.y1 = s.y1 + cdy;
    } else {
      if (h.includes("w")) next.x0 = clamp(s.x0 + dx);
      if (h.includes("e")) next.x1 = clamp(s.x1 + dx);
      if (h.includes("n")) next.y0 = clamp(s.y0 + dy);
      if (h.includes("s")) next.y1 = clamp(s.y1 + dy);
    }
    if (next.x1 - next.x0 < minFrac || next.y1 - next.y0 < minFrac) return;
    draft = next;
  }

  function endDrag() {
    // Pointerup: a completed drag commits, exactly once, and only if it
    // actually changed the rectangle -- a click-and-release with no
    // movement must not manufacture a patch (one undo step, one
    // re-digitize per REAL change, not per gesture).
    dragging = null;
    if (draft && !sameRect(draft, crop ?? FULL)) {
      onchange(draft);
    }
    draft = null;
  }

  function cancelDrag() {
    // Pointercancel (fix round 2, finding 3): the gesture ended WITHOUT a
    // pointerup ever firing here. Discard the draft rather than commit it --
    // the box must snap back to showing the last COMMITTED crop, not stay
    // frozen on the abandoned rectangle. No onchange call: nothing about
    // the crop actually changed from the customer's (or the panel's) point
    // of view.
    dragging = null;
    draft = null;
  }

  function reset() {
    onchange({ ...FULL });
  }

  // Spec section 6 asks for handles on corners AND edges; `move()` above
  // already implements edge handles correctly -- `h.includes("w")` and
  // friends handle a single axis fine for a one-letter handle name -- this
  // array is what actually emits them (finding 8, 2026-09-22 review).
  // Without it, a customer trimming only a status bar off one edge had to
  // drag two corners to do it.
  const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
  const HANDLE_LABEL = {
    nw: "nw corner", ne: "ne corner", sw: "sw corner", se: "se corner",
    n: "top edge", s: "bottom edge", e: "right edge", w: "left edge",
  };
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -- this div is not
     itself the interactive control; it is the delegation point pointer
     capture bubbles to (see `start`'s own comment). The actual controls are
     its descendants: `.crop-rect` (role="group", pointerdown starts a
     move-drag) and the eight corner/edge `<button>`s (pointerdown starts a
     resize-drag). Giving THIS wrapper its own role would be the wrong fix --
     it has no semantic role of its own to carry, only the plumbing that
     lets a capture set on a descendant reach a listener up here. -->
<div
  class="crop-host"
  bind:this={host}
  onpointermove={move}
  onpointerup={endDrag}
  onpointercancel={cancelDrag}
>
  <img {src} alt="Artwork preview with crop area" draggable="false" />
  <div
    class="crop-rect"
    role="group"
    aria-label="Crop area"
    style="left:{rect.x0 * 100}%; top:{rect.y0 * 100}%; width:{(rect.x1 - rect.x0) * 100}%; height:{(rect.y1 - rect.y0) * 100}%"
    onpointerdown={(e) => start("move", e)}
  >
    {#each HANDLES as h}
      <button
        type="button"
        class="handle {h}"
        aria-label="Drag {HANDLE_LABEL[h]}"
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
  .handle.n { left: calc(50% - 7px); top: -8px; cursor: ns-resize; }
  .handle.s { left: calc(50% - 7px); bottom: -8px; cursor: ns-resize; }
  .handle.e { right: -8px; top: calc(50% - 7px); cursor: ew-resize; }
  .handle.w { left: -8px; top: calc(50% - 7px); cursor: ew-resize; }
  .crop-reset { margin-top: 0.5rem; }
</style>
