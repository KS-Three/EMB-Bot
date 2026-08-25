<script>
  import { createEventDispatcher } from "svelte";
  import ThreadPicker from "./ThreadPicker.svelte";
  import TraceImportPanel from "./TraceImportPanel.svelte";
  import Icon from "./Icon.svelte";
  import { defaultManualShape } from "../lib/project.js";
  import {
    CANVAS_W, CANVAS_H, MAX_SHAPE_POINTS,
    isValidShape, isNearStart, isDuplicateOfLast, shapeIssues, flattenShape,
    curveControlOrNull, hitTestSegmentMidpoint, curveHandlePoint, pointInShape,
    nearestSegmentIndex, insertVertexAtSegment,
  } from "../lib/manualShapes.js";

  // Manual digitizing mode (MVP slice): draw straight- or curved-line
  // polygon outlines directly on a canvas, then assign each one a stitch
  // type/color/angle by hand. Zero image analysis anywhere in this
  // component. Patch convention (see TextStep.svelte's comment for the same
  // one): every edit dispatches an "elupdate" event shaped
  // { id: element.id, patch } directly.
  export let element;
  // Test-only seam: forwarded straight through as TraceImportPanel's own
  // `workImage` prop (see that component's comment on it) so a component
  // spec can seed "already decoded an image" state for the nested trace
  // panel without faking a real file upload — jsdom has no
  // createImageBitmap/canvas decode path (see DigitizePanel.spec.js's own
  // precedent for leaving that to Playwright). The live app never passes
  // this in; TraceImportPanel manages its own working image internally once
  // mounted.
  export let traceWorkImage = null;
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  // The in-progress shape being drawn right now is ephemeral UI state, same
  // pattern ImagePanel's merge-selection uses — it's NOT part of the
  // persisted element, so it resets if this panel remounts (switching
  // elements, reloading). Only COMPLETED shapes (element.shapes) persist.
  let draft = [];
  // Sparse { [segmentIndex]: {x,y} } control-point map for `draft`'s curved
  // segments — see manualShapes.js's flattenShape doc comment. Reset in
  // lockstep with `draft` everywhere it resets (finishShape/clearDraft).
  let draftCurves = {};
  let selectedShapeId = null;
  let canvasEl;
  // Brief on-canvas hint shown when a click is dropped because the draft
  // already hit MAX_SHAPE_POINTS — cleared on a timer so it reads as a
  // transient nudge, not a persistent error banner.
  let capHint = false;
  let capHintTimer = null;
  // Whether the trace-import panel (TraceImportPanel.svelte, PR 2 of the
  // trace-an-uploaded-image feature) is mounted below the tools row —
  // ephemeral UI state, same "not part of the persisted element" category as
  // `draft`/`selectedShapeId` above.
  let traceOpen = false;

  // ---- Vertex editing for a finished shape ------------------------------
  // A selected finished shape can be dropped into "edit points" mode: drag
  // an existing vertex to a new spot, and the released position is
  // re-validated through the same shapeIssues() the draft-drawing flow
  // already uses before it's ever written back — same "drag, then patch on
  // release" shape DigitizePanel.svelte's boundary editor established
  // (see its startEditDrag/onEditPointerMove/editingId/editPoints/dragIndex),
  // reimplemented fresh here against this component's single <canvas>
  // (hit-testing a click by distance to each point) rather than
  // DigitizePanel's per-vertex SVG elements. A drag that leaves the shape
  // self-intersecting/degenerate is never patched through — editPoints stays
  // local-only and editIssues (below) surfaces the same rejection text
  // draftIssues does, so the user sees why and can keep adjusting instead of
  // having the edit silently dropped.
  const VERTEX_HIT_R = 8; // canvas-px radius for "this click/drag is on that vertex"
  let editingId = null;
  let editPoints = [];
  // editCurves mirrors draftCurves, but for the shape currently in "Edit
  // points" mode — copied from shape.curves on entry (startShapeEdit),
  // discarded on exit (stopShapeEdit), same lifecycle as editPoints.
  let editCurves = {};
  let dragIndex = null;

  // ---- Curve-handle dragging ---------------------------------------------
  // Dragging the handle at a segment's midpoint bows that segment into a
  // quadratic curve (see manualShapes.js's curveControlOrNull/
  // quadraticControlForPointOnCurve) — works identically against the
  // in-progress draft (open polyline) or a shape in vertex-edit mode
  // (closed ring); curveTarget says which point/curve-map pair
  // curveDragSeg indexes into. Only one of {dragIndex, curveDragSeg} is
  // ever non-null at a time — a pointerdown either grabs a vertex or a
  // curve handle, never both.
  let curveDragSeg = null;
  let curveDragPoint = null;
  let curveTarget = null; // "draft" | "edit"
  // Set for the one `click` event that immediately follows a curve-handle
  // drag (pointerdown -> pointerup -> click, in that order) so that click
  // doesn't ALSO get treated as "place a new draft point" at the handle's
  // location — see onCanvasClick.
  let suppressNextClick = false;

  $: shapes = element.shapes || [];
  $: selectedShape = shapes.find((s) => s.id === selectedShapeId) || null;
  // Validity is always checked against the FLATTENED geometry (curves baked
  // to points, closed=true — shapeIssues has always treated its input as a
  // closed ring for self-intersection purposes, draft or not) so a curve
  // that swings through another edge is caught exactly like a straight one
  // would be. A shape with no curved segments flattens to its own points
  // array unchanged, so this is a no-op for plain polygons.
  $: draftFlat = flattenShape(draft, draftCurves, true);
  // Only surface issues once there are enough points for them to be
  // meaningful (self-intersection/area problems don't exist below a
  // triangle) — otherwise every fresh draft would open with "Needs at
  // least 3 points," which is just the obvious starting state, not a
  // problem to report.
  $: draftIssues = draft.length >= 3 ? shapeIssues(draftFlat) : [];
  $: canFinish = draft.length >= 3 && draftIssues.length === 0;
  $: editFlat = editingId ? flattenShape(editPoints, editCurves, true) : [];
  // Same "only surface once meaningful" reasoning as draftIssues — computed
  // continuously (not just after a drag ends) so a mid-drag self-intersect
  // shows up live, the same way the draft-drawing flow already behaves.
  $: editIssues = editingId ? shapeIssues(editFlat) : [];

  function nextShapeId(list) {
    let max = 0;
    for (const s of list) {
      const m = /^s(\d+)$/.exec(s.id);
      if (m) max = Math.max(max, parseInt(m[1], 10));
    }
    return "s" + (max + 1);
  }

  function canvasPointFromEvent(e) {
    const rect = canvasEl.getBoundingClientRect();
    const scaleX = canvasEl.width / rect.width;
    const scaleY = canvasEl.height / rect.height;
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
  }

  function finishShape() {
    // Computed fresh here (not read off the reactive draftFlat) so this
    // never depends on Svelte's reactive-statement flush having already run
    // by the time a caller in the same tick invokes finishShape.
    if (!isValidShape(flattenShape(draft, draftCurves, true))) return;
    const shape = { ...defaultManualShape(nextShapeId(shapes)), points: draft, curves: draftCurves };
    patch({ shapes: [...shapes, shape] });
    draft = [];
    draftCurves = {};
    selectedShapeId = shape.id;
  }

  // TraceImportPanel hands back a finished, id-assigned shape array (see its
  // own file banner for why id assignment happens there, against THIS
  // component's live `shapes`, rather than here) — this is the one place
  // that batch ever lands in element.shapes, via exactly ONE patch (one undo
  // step for the whole batch), riding the same patch()/elupdate mechanism
  // every other edit in this file already uses. Existing shapes are never
  // touched: `shapes` is spread first, unchanged, with the new ones appended
  // after.
  function onTraced(e) {
    const newShapes = e.detail.shapes;
    patch({ shapes: [...shapes, ...newShapes] });
    traceOpen = false;
    // Anchor the batch add with an immediate selection (same mechanism the
    // sidebar list uses) — combined with de-emphasis, this gives a
    // multi-shape trace-add a visual focal point instead of N new shapes all
    // rendering at equal, unselected weight.
    if (newShapes.length) selectShape(newShapes[0].id);
  }

  function flashCapHint() {
    capHint = true;
    if (capHintTimer) clearTimeout(capHintTimer);
    capHintTimer = setTimeout(() => { capHint = false; }, 2000);
  }

  function onCanvasClick(e) {
    // Vertex-edit mode owns the canvas's pointer gestures (drag-to-move via
    // onCanvasPointerDown/Move/Up below) — a plain click while editing
    // shouldn't also drop a new draft point.
    if (editingId) return;
    // The click that immediately follows a curve-handle drag (pointerdown
    // -> pointerup -> click) shouldn't ALSO place a new point at the
    // handle's location — see suppressNextClick's declaration.
    if (suppressNextClick) {
      suppressNextClick = false;
      return;
    }
    const pt = canvasPointFromEvent(e);
    // A click on empty canvas while nothing's mid-draft selects whatever
    // finished shape is under it, instead of starting a new draft on top of
    // it — gated on draft.length === 0 so an in-progress hand-drawn shape is
    // never preempted by a select-click partway through being drawn.
    if (draft.length === 0) {
      const hitId = hitTestShapeAt(pt.x, pt.y);
      if (hitId) {
        // A click on a shape that's ALREADY selected, landing close enough
        // to its edge/line (not its interior), inserts a new vertex there
        // instead of re-selecting — see tryInsertVertexAt. Any other click
        // on a shape's body (a different shape, or the selected shape's
        // interior) keeps PR #104's plain select-click behavior unchanged.
        if (hitId === selectedShapeId && tryInsertVertexAt(hitId, pt)) return;
        selectShape(hitId);
        return;
      }
    }
    if (draft.length >= 2 && isNearStart(draft, pt.x, pt.y)) {
      finishShape();
      return;
    }
    // Same "ignore the click" precedent as the closing-radius check above:
    // a duplicate-consecutive click (double-tap jitter, not a deliberate
    // second point) or a click past the point cap just doesn't add a point.
    if (isDuplicateOfLast(draft, pt.x, pt.y)) return;
    if (draft.length >= MAX_SHAPE_POINTS) {
      flashCapHint();
      return;
    }
    draft = [...draft, pt];
  }

  // A double-click is two `click` events THEN one `dblclick`. The second
  // click lands on (or within DUP_POINT_EPS_PX of) the same point as the
  // first, so onCanvasClick's duplicate-consecutive-point dedupe already
  // drops it before this handler ever runs — nothing extra to undo here,
  // just finish with whatever's in the draft.
  function onCanvasDblClick() {
    if (editingId) return;
    finishShape();
  }

  function undoPoint() {
    // The segment between the last two anchors is going away with the
    // removed point — drop its curve entry too, or it'd silently apply to
    // whatever segment index happens to land there next.
    const removedSegIdx = draft.length - 2;
    draft = draft.slice(0, -1);
    if (removedSegIdx >= 0 && removedSegIdx in draftCurves) {
      const next = { ...draftCurves };
      delete next[removedSegIdx];
      draftCurves = next;
    }
  }
  function clearDraft() {
    draft = [];
    draftCurves = {};
  }

  function selectShape(id) {
    // Switching (or clearing) the selection always drops any in-progress
    // vertex edit — editPoints is local-only UI state tied to one shape, and
    // there's no "still editing shape A while shape B is selected" state
    // this component means to support.
    stopShapeEdit();
    selectedShapeId = selectedShapeId === id ? null : id;
  }

  function deleteShape(id) {
    if (editingId === id) stopShapeEdit();
    patch({ shapes: shapes.filter((s) => s.id !== id) });
    if (selectedShapeId === id) selectedShapeId = null;
  }

  function updateShape(id, p) {
    patch({ shapes: shapes.map((s) => (s.id === id ? { ...s, ...p } : s)) });
  }

  // ---- Vertex editing ----------------------------------------------------
  function startShapeEdit(id) {
    const shape = shapes.find((s) => s.id === id);
    if (!shape) return;
    editingId = id;
    editPoints = shape.points.map((p) => ({ ...p }));
    editCurves = { ...(shape.curves || {}) };
    dragIndex = null;
  }

  function stopShapeEdit() {
    editingId = null;
    editPoints = [];
    editCurves = {};
    dragIndex = null;
  }

  // Nearest vertex within VERTEX_HIT_R of (x, y), or -1 — this component's
  // canvas-hit-testing stand-in for DigitizePanel's per-vertex SVG elements
  // (each of which gets its own pointerdown handler there; here there's one
  // canvas, so the hit test does the same job by distance).
  function hitTestVertex(points, x, y) {
    let best = -1;
    let bestD = VERTEX_HIT_R;
    for (let i = 0; i < points.length; i++) {
      const d = Math.hypot(points[i].x - x, points[i].y - y);
      if (d <= bestD) {
        bestD = d;
        best = i;
      }
    }
    return best;
  }

  // Which finished shape (if any) sits under (x, y) — hit-tested back-to-
  // front (last-drawn/topmost shape checked first) so an overlap resolves
  // the same way the canvas visually stacks shapes. Feeds both
  // canvas-click-to-select (onCanvasClick) and the hover cursor
  // (onCanvasPointerMove) off the exact same test, so the cursor never
  // promises a click will select something it actually won't.
  function hitTestShapeAt(x, y) {
    for (let i = shapes.length - 1; i >= 0; i--) {
      const s = shapes[i];
      if (pointInShape(flattenShape(s.points, s.curves, true), x, y)) return s.id;
    }
    return null;
  }

  // The anchor-segment index of shape `id`'s edge closest to (x, y), and how
  // far — or null if (x, y) isn't within VERTEX_HIT_R of any of its edges
  // (a click/hover on the shape's plain interior, away from any line).
  // Shared by the click handler and the hover-cursor check below so they can
  // never disagree about what a click there would do.
  function edgeHitOn(id, x, y) {
    const shape = shapes.find((s) => s.id === id);
    if (!shape) return null;
    const { index, dist } = nearestSegmentIndex(shape.points, shape.curves, x, y, true);
    if (index === -1 || dist > VERTEX_HIT_R) return null;
    return { shape, index };
  }

  // Attempts the edge-click-to-insert-vertex gesture for the already-selected
  // shape `id` at canvas point `pt`: true (and a patch dispatched) once a new
  // anchor actually landed on its edge; false when the click missed every
  // edge (by more than VERTEX_HIT_R) or the shape is already at
  // MAX_SHAPE_POINTS (insertVertexAtSegment's own no-op), so the caller falls
  // back to its ordinary already-selected-shape click behavior instead.
  function tryInsertVertexAt(id, pt) {
    const hit = edgeHitOn(id, pt.x, pt.y);
    if (!hit) return false;
    const next = insertVertexAtSegment(hit.shape, hit.index, pt);
    if (next === hit.shape) return false; // at MAX_SHAPE_POINTS — no-op
    updateShape(id, { points: next.points, curves: next.curves });
    return true;
  }

  function capturePointer(e) {
    try {
      canvasEl.setPointerCapture(e.pointerId);
    } catch (err) {
      // Pointer capture is unavailable in some test/embedded environments
      // (DigitizePanel's startEditDrag notes the same) — dragging still
      // works off plain pointermove, just less robustly past the canvas
      // edge.
    }
  }

  function releasePointer(e) {
    try {
      canvasEl.releasePointerCapture(e.pointerId);
    } catch (err) {
      // See capturePointer.
    }
  }

  // The control point to store for segment `segIndex` of `points`/`curves`
  // if the user releases a curve-handle drag at `through` — null means
  // "close enough to straight, un-curve it" (see curveControlOrNull).
  function commitCurve(points, curves, segIndex, through) {
    const n = points.length;
    const a = points[segIndex];
    const c = points[(segIndex + 1) % n];
    const control = curveControlOrNull(a, c, through);
    const next = { ...curves };
    if (control) next[segIndex] = control;
    else delete next[segIndex];
    return next;
  }

  function onCanvasPointerDown(e) {
    // Reset unconditionally at the start of every gesture: a browser that
    // honors preventDefault's compatibility-event suppression (see below)
    // never fires the `click` that would otherwise clear this, so a stale
    // `true` left over from a PREVIOUS curve-handle grab could wrongly
    // swallow an unrelated future point-placement click if it weren't reset
    // here first.
    suppressNextClick = false;
    const pt = canvasPointFromEvent(e);
    if (editingId) {
      const idx = hitTestVertex(editPoints, pt.x, pt.y);
      if (idx !== -1) {
        e.preventDefault();
        dragIndex = idx;
        capturePointer(e);
        return;
      }
      const segIdx = hitTestSegmentMidpoint(editPoints, editCurves, pt.x, pt.y, true);
      if (segIdx !== -1) {
        e.preventDefault();
        curveDragSeg = segIdx;
        curveDragPoint = pt;
        curveTarget = "edit";
        capturePointer(e);
      }
      return;
    }
    // Drafting: placing a new point stays on the plain `click` handler
    // below — pointer events here only ever grab an existing segment's
    // curve handle. A pointerdown that misses every handle does nothing
    // (no preventDefault, no state change), so the click that follows
    // places a point exactly as it did before curves existed.
    if (draft.length >= 2) {
      const segIdx = hitTestSegmentMidpoint(draft, draftCurves, pt.x, pt.y, false);
      if (segIdx !== -1) {
        e.preventDefault();
        curveDragSeg = segIdx;
        curveDragPoint = pt;
        curveTarget = "draft";
        suppressNextClick = true;
        capturePointer(e);
      }
    }
  }

  function onCanvasPointerMove(e) {
    if (dragIndex != null) {
      editPoints[dragIndex] = canvasPointFromEvent(e);
      editPoints = editPoints;
      canvasEl.style.cursor = "grabbing";
      return;
    }
    if (curveDragSeg != null) {
      curveDragPoint = canvasPointFromEvent(e);
      canvasEl.style.cursor = "copy";
      return;
    }
    updateHoverCursor(canvasPointFromEvent(e));
  }

  // Canvas has no per-element CSS :hover the way DigitizePanel's SVG editor
  // does (.dgp-editor-vertex{cursor:grab}, .dgp-editor-mid{cursor:copy}) — a
  // single <canvas> here stands in for every one of those elements, so the
  // cursor has to be set from JS on every pointer move instead. Same cursor
  // vocabulary, checked in priority order (only one can apply at a time):
  //   grab      — hovering a draggable vertex (vertex-edit mode).
  //   copy      — hovering a segment's curve handle (draft or vertex-edit).
  //   cell      — hovering the ALREADY-SELECTED shape's edge/line (not its
  //               interior) — the exact spot a click would insert a new
  //               vertex at (see tryInsertVertexAt). "copy" is already
  //               spoken for by the curve handle above, so this gets its own
  //               distinct value.
  //   pointer   — hovering a finished shape's body, selectable by a click
  //               (see onCanvasClick's own draft.length === 0 gate — the
  //               cursor only offers "pointer" when a click would actually
  //               select something).
  //   crosshair — the fallback (today's implicit default, made explicit so
  //               every case funnels through this one function — otherwise
  //               a cursor set to one of the above by a previous pointermove
  //               would stick after moving off that target, since an inline
  //               style always wins over the CSS default).
  function updateHoverCursor(pt) {
    if (editingId) {
      if (hitTestVertex(editPoints, pt.x, pt.y) !== -1) {
        canvasEl.style.cursor = "grab";
        return;
      }
      if (hitTestSegmentMidpoint(editPoints, editCurves, pt.x, pt.y, true) !== -1) {
        canvasEl.style.cursor = "copy";
        return;
      }
      canvasEl.style.cursor = "crosshair";
      return;
    }
    if (draft.length >= 2 && hitTestSegmentMidpoint(draft, draftCurves, pt.x, pt.y, false) !== -1) {
      canvasEl.style.cursor = "copy";
      return;
    }
    if (draft.length === 0) {
      const hitId = hitTestShapeAt(pt.x, pt.y);
      if (hitId) {
        if (hitId === selectedShapeId && edgeHitOn(hitId, pt.x, pt.y)) {
          canvasEl.style.cursor = "cell";
          return;
        }
        canvasEl.style.cursor = "pointer";
        return;
      }
    }
    canvasEl.style.cursor = "crosshair";
  }

  // "Drag, then patch on release": a moved vertex or a bowed segment only
  // reaches element.shapes (via updateShape) if the resulting polygon is
  // still valid — an invalid drag leaves editPoints/editCurves (and the
  // live editIssues message) as the only trace, exactly like a draft that
  // hasn't been finished yet. Drafting has no such gate: draft/draftCurves
  // always take the drag result, same as a plain draft point always gets
  // added regardless of whether the shape-so-far is valid yet.
  function endVertexDrag(e) {
    if (dragIndex != null) {
      dragIndex = null;
      if (editingId && shapeIssues(flattenShape(editPoints, editCurves, true)).length === 0) {
        updateShape(editingId, { points: editPoints.map((p) => ({ ...p })) });
      }
      releasePointer(e);
      return;
    }
    if (curveDragSeg != null) {
      const seg = curveDragSeg;
      const through = curveDragPoint;
      const target = curveTarget;
      curveDragSeg = null;
      curveDragPoint = null;
      curveTarget = null;
      if (target === "draft") {
        draftCurves = commitCurve(draft, draftCurves, seg, through);
      } else if (target === "edit") {
        editCurves = commitCurve(editPoints, editCurves, seg, through);
        if (editingId && shapeIssues(flattenShape(editPoints, editCurves, true)).length === 0) {
          updateShape(editingId, {
            points: editPoints.map((p) => ({ ...p })),
            curves: { ...editCurves },
          });
        }
      }
      releasePointer(e);
    }
  }

  function onAngleInput(e) {
    if (!selectedShape) return;
    const raw = e.target.value;
    const v = raw.trim() === "" ? null : parseFloat(raw);
    updateShape(selectedShape.id, { angleDeg: Number.isFinite(v) ? v : null });
  }

  function summary(shape) {
    return `Shape ${shape.id.replace(/^s/, "")} · ${shape.stitchType === "satin" ? "Satin" : "Fill"}`;
  }

  // ---- Keyboard shortcuts ------------------------------------------------
  // Scoped to specific interactive elements — the canvas (tabindex +
  // on:keydown below) AND the shape-row/delete buttons (selecting a shape
  // by clicking its row moves DOM focus there, not to the canvas, so Delete
  // needs somewhere to fire from right after that click too) — same
  // "attach to a specific interactive element, not window" convention
  // DigitizePanel's onEditVertexKeydown uses for its per-vertex handles,
  // rather than a global window listener that would fire regardless of
  // which panel/element is on screen.
  //   Escape  — exit vertex-edit mode if active, else cancel the draft.
  //   Enter   — finish the draft (only once canFinish agrees it's sewable).
  //   Delete/
  //   Backspace — delete the selected finished shape, but ONLY when no
  //     draft is in progress and no vertex edit is in progress: a draft or
  //     an in-progress edit is unrelated state the user is actively
  //     building, and Delete's job here is never to reach past that and
  //     nuke a different, already-finished shape by surprise.
  function onCanvasKeydown(e) {
    if (e.key === "Escape") {
      if (editingId) {
        stopShapeEdit();
        e.preventDefault();
      } else if (draft.length) {
        clearDraft();
        e.preventDefault();
      }
      return;
    }
    if (e.key === "Enter") {
      if (canFinish) {
        finishShape();
        e.preventDefault();
      }
      return;
    }
    if (e.key === "Delete" || e.key === "Backspace") {
      if (selectedShapeId && draft.length === 0 && !editingId) {
        deleteShape(selectedShapeId);
        e.preventDefault();
      }
    }
  }

  // ---- Drawing ---------------------------------------------------------
  // Curved segments draw natively via quadraticCurveTo — flattening to
  // points (manualShapes.js's flattenShape) only ever happens for
  // validation and at the final shapesToRegions hand-off, never here.
  function drawShape(ctx, points, curves, closed, fillStyle, strokeStyle, lineWidth) {
    if (points.length < 2) return;
    const n = points.length;
    const segCount = closed ? n : n - 1;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 0; i < segCount; i++) {
      const c = points[(i + 1) % n];
      const control = curves && curves[i];
      if (control) ctx.quadraticCurveTo(control.x, control.y, c.x, c.y);
      else ctx.lineTo(c.x, c.y);
    }
    if (fillStyle) {
      ctx.closePath();
      ctx.fillStyle = fillStyle;
      ctx.fill();
    }
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
  }

  // The curves map to actually draw with: the committed map, with the
  // in-progress drag (if any, and if it's dragging THIS point list) applied
  // on top — so the curve visibly follows the cursor before release, same
  // "live preview" precedent onCanvasPointerMove's vertex-drag already sets.
  function liveCurvesFor(baseCurves, points, isDragTarget, dragSeg, dragPoint) {
    if (!isDragTarget || dragSeg == null) return baseCurves;
    const n = points.length;
    const a = points[dragSeg];
    const c = points[(dragSeg + 1) % n];
    const control = curveControlOrNull(a, c, dragPoint);
    const next = { ...baseCurves };
    if (control) next[dragSeg] = control;
    else delete next[dragSeg];
    return next;
  }

  // Small draggable dots at each segment's curve handle — hollow/faint when
  // the segment is still straight (a discoverable "drag me" affordance),
  // solid once curved, enlarged while actively being dragged.
  function drawCurveHandles(ctx, points, curves, closed, dragSeg) {
    const n = points.length;
    const segCount = closed ? n : n - 1;
    for (let i = 0; i < segCount; i++) {
      const a = points[i];
      const c = points[(i + 1) % n];
      const control = curves && curves[i];
      const hp = curveHandlePoint(a, c, control);
      const dragging = i === dragSeg;
      ctx.beginPath();
      ctx.arc(hp.x, hp.y, dragging ? 5 : 3.5, 0, Math.PI * 2);
      ctx.fillStyle = control ? "#4f46e5" : "rgba(79,70,229,0.35)";
      ctx.fill();
      if (dragging) {
        ctx.strokeStyle = "#4f46e5";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }

  function render(
    canvas, shapeList, draftPts, draftCrv, selectedId,
    editId, editPts, editCrv, editValid,
    dragSeg, dragPoint, dragTarget
  ) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f4f2ec";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const s of shapeList) {
      const editing = s.id === editId;
      // The shape being edited draws from the LIVE (possibly momentarily
      // invalid, mid-drag) editPts/editCrv instead of its last-persisted
      // points — everything else still only draws once it's a real
      // polygon.
      const pts = editing ? editPts : s.points;
      const liveCrv = editing
        ? liveCurvesFor(editCrv, editPts, dragTarget === "edit", dragSeg, dragPoint)
        : s.curves;
      if (!editing && !isValidShape(flattenShape(pts, liveCrv, true))) continue;
      const [r, g, b] = s.colorRgb || [20, 20, 20];
      const isSel = s.id === selectedId;
      // Once something is selected, every OTHER shape de-emphasizes to the
      // same fill-opacity/stroke-width vocabulary DigitizePanel's boundary
      // editor uses (.dgp-editor-poly's fill-opacity: 0.18) so the selected
      // shape reads as the obvious focal point instead of every shape
      // competing at equal visual weight. selectedId is falsy with nothing
      // selected, so dimmed is always false then — that path stays exactly
      // what it was before de-emphasis existed.
      const dimmed = !!selectedId && !isSel;
      const invalid = editing && !editValid;
      drawShape(
        ctx, pts, liveCrv, true,
        invalid ? "rgba(192,57,43,0.25)" : `rgba(${r},${g},${b},${dimmed ? 0.18 : 0.55})`,
        invalid ? "#c0392b" : (isSel ? "#4f46e5" : `rgb(${r},${g},${b})`),
        isSel || editing ? 3 : (dimmed ? 1 : 1.5)
      );
      if (editing) {
        drawCurveHandles(ctx, pts, liveCrv, true, dragTarget === "edit" ? dragSeg : null);
        // Draggable vertex handles instead of the centroid label — this IS
        // the "edit points" affordance.
        for (const p of pts) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
          ctx.fillStyle = "#fff";
          ctx.fill();
          ctx.strokeStyle = invalid ? "#c0392b" : "#4f46e5";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      } else if (!dimmed) {
        // Stitch-type label at the shape's centroid — dropped entirely (not
        // just faded) on a dimmed shape, since the sidebar's per-shape list
        // already shows stitch type per row; keeping it here would just be
        // redundant clutter on a shape that's already de-emphasized.
        let cx = 0, cy = 0;
        for (const p of pts) { cx += p.x; cy += p.y; }
        cx /= pts.length; cy /= pts.length;
        ctx.fillStyle = "#111";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(s.stitchType === "satin" ? "SATIN" : "FILL", cx, cy);
      }
    }

    if (draftPts.length) {
      const liveCrv = liveCurvesFor(draftCrv, draftPts, dragTarget === "draft", dragSeg, dragPoint);
      drawShape(ctx, draftPts, liveCrv, false, null, "#4f46e5", 2);
      if (draftPts.length >= 2) drawCurveHandles(ctx, draftPts, liveCrv, false, dragTarget === "draft" ? dragSeg : null);
      for (let i = 0; i < draftPts.length; i++) {
        const p = draftPts[i];
        ctx.beginPath();
        ctx.arc(p.x, p.y, i === 0 ? 5 : 3, 0, Math.PI * 2);
        ctx.fillStyle = i === 0 ? "#4f46e5" : "#fff";
        ctx.fill();
        ctx.strokeStyle = "#4f46e5";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }

  $: render(
    canvasEl, shapes, draft, draftCurves, selectedShapeId,
    editingId, editPoints, editCurves, editIssues.length === 0,
    curveDragSeg, curveDragPoint, curveTarget
  );
</script>

<div class="manualpanel">
  <p class="hint">
    Click to place points. Click near the first point (or double-click) to close the shape.
    Drag the small dot at the middle of any line to bow it into a curve — drag it back to
    the line to straighten it again. Once a shape is selected, click its edge to add a new
    point there. Draw as many shapes as you like, then pick each one's stitch type, color,
    and angle below. Escape cancels a draft, Enter finishes it, Delete removes the selected
    shape.
  </p>

  <div class="mp-canvas-wrap">
    <canvas
      bind:this={canvasEl}
      class="mp-canvas"
      width={CANVAS_W}
      height={CANVAS_H}
      tabindex="0"
      on:click={onCanvasClick}
      on:dblclick={onCanvasDblClick}
      on:pointerdown={onCanvasPointerDown}
      on:pointermove={onCanvasPointerMove}
      on:pointerup={endVertexDrag}
      on:pointercancel={endVertexDrag}
      on:pointerleave={endVertexDrag}
      on:keydown={onCanvasKeydown}
      role="img"
      aria-label="Shape drawing canvas"
    ></canvas>
    {#if capHint}
      <p class="mp-caphint" role="status">Point limit reached ({MAX_SHAPE_POINTS} max) — finish or clear this shape.</p>
    {/if}
  </div>

  {#if draftIssues.length}
    <p class="mp-draftissue" role="alert">{draftIssues.join(" ")}</p>
  {/if}
  {#if editingId && editIssues.length}
    <p class="mp-draftissue" role="alert">{editIssues.join(" ")}</p>
  {/if}

  <div class="mp-tools">
    <button type="button" on:click={undoPoint} disabled={!draft.length}>Undo point</button>
    <button type="button" on:click={clearDraft} disabled={!draft.length}>Clear shape</button>
    <button type="button" class="primary" on:click={finishShape} disabled={!canFinish}>Finish shape</button>
    <button type="button" on:click={() => (traceOpen = !traceOpen)}>Trace image…</button>
  </div>

  {#if traceOpen}
    <TraceImportPanel
      existingShapes={shapes}
      workImage={traceWorkImage}
      on:traced={onTraced}
      on:cancel={() => (traceOpen = false)}
    />
  {/if}

  {#if shapes.length}
    <ul class="mp-shapelist">
      {#each shapes as s (s.id)}
        <li>
          <button
            type="button"
            class="mp-shaperow"
            class:sel={s.id === selectedShapeId}
            on:click={() => selectShape(s.id)}
            on:keydown={onCanvasKeydown}
          >
            <span class="mp-swatch" style="background: rgb({s.colorRgb[0]},{s.colorRgb[1]},{s.colorRgb[2]})"></span>
            <span class="mp-shapename">{summary(s)}</span>
          </button>
          <button
            type="button"
            class="mp-remove"
            title="Delete shape"
            aria-label="Delete shape"
            on:click={() => deleteShape(s.id)}
            on:keydown={onCanvasKeydown}
          ><Icon name="close" size={14} /></button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mp-empty">No shapes yet — draw one above to get started.</p>
  {/if}

  {#if selectedShape}
    <div class="mp-assign">
      <h3>{summary(selectedShape)}</h3>
      <div class="mp-row">
        <span class="mp-label">Stitch type</span>
        <div class="mp-btns">
          {#each [["fill", "Fill"], ["satin", "Satin"]] as [val, label]}
            <button
              type="button"
              class="mp-btn"
              class:active={selectedShape.stitchType === val}
              on:click={() => updateShape(selectedShape.id, { stitchType: val })}
            >{label}</button>
          {/each}
        </div>
      </div>
      <div class="mp-row">
        <span class="mp-label">Points</span>
        {#if editingId === selectedShape.id}
          <button type="button" class="mp-btn active" on:click={stopShapeEdit}>Done editing</button>
        {:else}
          <button
            type="button"
            class="mp-btn"
            disabled={draft.length > 0}
            on:click={() => startShapeEdit(selectedShape.id)}
          >Edit points</button>
        {/if}
      </div>
      <div class="mp-row">
        <span class="mp-label">Color</span>
        <ThreadPicker compact rgb={selectedShape.colorRgb} on:pick={(e) => updateShape(selectedShape.id, { colorRgb: e.detail })} />
      </div>
      <label class="mp-row mp-angle">
        <span class="mp-label">Fill angle</span>
        <input
          type="number"
          step="1"
          placeholder="auto"
          value={selectedShape.angleDeg == null ? "" : selectedShape.angleDeg}
          on:input={onAngleInput}
        />
        <span class="mp-deg">° (blank = auto)</span>
      </label>
    </div>
  {/if}
</div>

<style>
  .manualpanel { display: flex; flex-direction: column; gap: 10px; }
  .hint { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
  .mp-canvas-wrap { position: relative; }
  .mp-canvas {
    width: 100%;
    max-width: 100%;
    height: auto;
    aspect-ratio: 600 / 400;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: #f4f2ec;
    cursor: crosshair;
    touch-action: none;
    display: block;
  }
  .mp-caphint {
    position: absolute;
    left: 50%;
    bottom: 10px;
    transform: translateX(-50%);
    margin: 0;
    padding: 4px 10px;
    border-radius: var(--radius-s, 8px);
    background: rgba(17, 17, 17, 0.82);
    color: #fff;
    font-size: var(--fs-xs, 12px);
    white-space: nowrap;
    pointer-events: none;
  }
  .mp-draftissue {
    font-size: var(--fs-xs, 12px);
    color: var(--danger, #c0392b);
    margin: 0;
  }
  .mp-tools { display: flex; gap: 6px; flex-wrap: wrap; }
  .mp-tools button {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .mp-tools button:disabled { opacity: 0.45; cursor: not-allowed; }
  .mp-tools button.primary {
    background: var(--accent, #4f46e5);
    color: var(--accent-ink, #fff);
    border-color: var(--accent, #4f46e5);
  }
  /* Bounded like DigitizePanel's layer list: one row per shape with no
     ceiling means a drawing with many shapes pushes the stitch-type, colour
     and angle controls below it off the panel. Rows here are ~30px, so this
     only engages on genuinely long lists. */
  .mp-shapelist {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 320px;
    overflow-y: auto;
  }
  .mp-shapelist li { display: flex; align-items: center; gap: 4px; }
  .mp-shaperow {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
    text-align: left;
  }
  .mp-shaperow.sel { border-color: var(--accent, #4f46e5); background: var(--tint, #eef0ff); }
  .mp-swatch { width: 14px; height: 14px; border-radius: 3px; border: 1px solid var(--tint-border, #ccd6fb); display: inline-block; flex: none; }
  .mp-remove { border: none; background: none; cursor: pointer; font-size: 13px; color: var(--danger, #c0392b); padding: 4px; }
  .mp-empty { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); margin: 0; }
  .mp-assign { border-top: 1px solid var(--tint-border, #ccd6fb); padding-top: 10px; margin-top: 4px; }
  .mp-assign h3 { margin: 0 0 8px; font-size: var(--fs-xs, 12px); }
  .mp-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
  .mp-label { display: block; font-size: var(--fs-xs, 12px); min-width: 70px; }
  .mp-btns { display: flex; gap: 6px; }
  .mp-btn {
    padding: 5px 10px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    background: var(--surface, #fff);
    cursor: pointer;
    font-size: var(--fs-xs, 12px);
  }
  .mp-btn.active { background: var(--accent, #4f46e5); color: var(--accent-ink, #fff); border-color: var(--accent, #4f46e5); }
  .mp-angle input {
    width: 64px;
    padding: 5px 8px;
    border: 1px solid var(--tint-border, #ccd6fb);
    border-radius: var(--radius-s, 8px);
    font-size: var(--fs-xs, 12px);
  }
  .mp-deg { font-size: var(--fs-xs, 12px); color: var(--muted, #6b7280); }
</style>
