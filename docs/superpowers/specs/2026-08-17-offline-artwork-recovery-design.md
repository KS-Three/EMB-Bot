# Offline-artwork recovery — design

**Date:** 2026-08-17 · **Scope:** the "+ Artwork" tile's losing branch leaves
a dead end with no explanation and no recovery, confirmed live 2026-08-17.

## Problem

`App.onAddElement` (`app/src/App.svelte:363-369`) routes the Content step's
single "+ Artwork" tile to a `digitized` or `image` element based on
`digitizerHealth` at the moment of the click:

```js
const resolved = type === "artwork"
  ? (digitizerHealth ? "digitized" : "image")
  : type;
```

This routing rule is intentional and out of scope here — the problem is what
happens on the losing branch:

1. `image` elements have no digitize path. `ImagePanel.svelte` never
   references the digitizer at all.
2. Element type is frozen at creation. Starting the service afterwards
   changes nothing for an existing element.
3. Nothing in `ImagePanel` explains this or offers recovery.
   `DigitizePanel.svelte:1099` has a "Check again" button, but it's only
   reachable from a `digitized` element — the one the user doesn't have.

By construction, every `image` element that exists today came from this one
losing branch — the field context-menu (`EmbroideryField.svelte:1656-1663`)
only offers `manual`/`shape`, and templates only seed `text`. So there is no
need to distinguish "stranded" image elements from ordinary ones: every
`image` element is, structurally, one of these.

## Design

### Model — `convertImageToDigitized(project, id)`, in `lib/project.js`

New function beside `addElement`/`addSeededTextElement` (the file's existing
pattern for "new element shape, specific caller"):

```js
export function convertImageToDigitized(project, id) {
  const el = project.elements.find((e) => e.id === id);
  if (!el || el.type !== "image") return project;
  const next = {
    ...defaultDigitizedElement(id),
    offsetXMm: el.offsetXMm,
    offsetYMm: el.offsetYMm,
  };
  return {
    ...project,
    elements: project.elements.map((e) => (e.id === id ? next : e)),
  };
}
```

- **Replaces in place** (`.map`, not remove+append) — array position is sew
  order; appending would silently reorder the stitch-out.
- **Carries only `offsetXMm`/`offsetYMm`.** Not `sizeMm`: `addElement`
  already leaves a fresh `digitized` element's `sizeMm` at `null` so stitches
  render at their generated size (`project.js:285`); no result exists yet at
  convert time, so `null` is the honest value here too.
  `defaultDigitizedElement`'s other defaults (`params`, empty `result`, etc.)
  apply unchanged.
- **Drops** `nColors`, `removeBg`, `threadRgb`, `underlay`, `_hasImage` —
  meaningless on the digitized lane.
- **No-op** (returns `project` unchanged) if `id` doesn't exist or isn't an
  `image` element. Not an error path a UI button can trigger, but keeps the
  function safe to call.
- **`id` is preserved.** `runtime.flats[id]`/`workImages[id]` (App-owned,
  in-memory, keyed by element id) become stale for what is now a live
  `digitized` element — App must drop both in the same step (see below), or
  a later re-upload landing on a reused id could inherit dead pixels (the
  same hazard `onRemoveElement` already guards against,
  `App.svelte:423-438`).

Undo: `persist()` records one history step, same as every other element
edit. Restoring the `image` element via undo won't restore its pixels —
`runtime.flats`/`workImages` aren't part of history — but this is an
existing, already-handled limitation: `truthHasImage` (`App.svelte:102`)
already re-truths `_hasImage` against what `runtime` actually holds after
any snapshot restore. No new mechanism needed.

### UI — `ImagePanel.svelte`

New `health` prop (name matches `DigitizePanel`'s existing prop), plus three
pieces stacked under the upload box:

1. **Standing line, unconditional on `health`:** "This artwork uses the
   browser's built-in engine, not the auto-digitizer service." Phrased as
   what the element *is*, not a historical claim about why it was created —
   stays accurate even if a future path other than today's losing branch
   ever produces an `image` element.
2. **Gated on `health`:**
   - down: a standalone **"Check again"** button (capitalized, its own
     control — matches `DigitizePanel`'s `dgp-check` button convention, not
     `ContentStep`'s mid-sentence lowercase link), dispatching
     `checkservice`. No extra sentence beyond the standing line above it —
     the standing line already covers "why"; the down state only needs to
     offer the action. This is the actual fix for point 3 above: today
     nothing in `ImagePanel` can trigger a recheck at all, so a user sitting
     on this exact panel after starting the service has no way to find out
     without navigating away and back.
   - up: the sentence "Digitizer is running now." followed by a standalone
     **"Convert to auto-digitized"** button.
3. **Inline confirm, only when `element._hasImage` is true** (the existing
   flag `onFlat` already maintains and `truthHasImage` already re-truths —
   reused rather than re-derived from the `workImage` prop). Clicking
   "Convert to auto-digitized" swaps the button row for the sentence "This
   replaces your uploaded art and colors — you'll pick the file again."
   followed by two buttons, **"Convert anyway"** and **"Cancel"** — only
   "Convert anyway" dispatches `convert`. No art loaded → the first click on
   "Convert to auto-digitized" dispatches `convert` immediately, no confirm
   step.

   No `window.confirm()` or modal component: neither exists anywhere in this
   codebase today (checked `App.svelte`, `ProjectsDrawer.svelte` — element
   and project deletion both happen with no confirmation at all). An inline
   swap matches the codebase's existing inline-banner convention
   (`.dgp-offline`, `.digitize-offline`) instead of introducing a new UI
   pattern for one button.

`ImagePanel` dispatches `convert` and `checkservice` id-less — same
convention as its existing `image`/`flat` events: App always applies them to
`project.selectedId`, which is safe because only the selected element's
panel is ever mounted (`ContentStep.svelte`'s `{#key el.id}` block).

`ContentStep.svelte` gains `health={digitizerHealth}` on its `ImagePanel`
instance (mirrors its existing `DigitizePanel` binding) and bubbles
`on:convert`/`on:checkservice` through to `App`, same shape as its existing
`DigitizePanel` wiring.

### Wiring — `App.svelte`

```js
function clearRuntimeImage(id) {
  if (id in runtime.flats || id in runtime.workImages) {
    const flats = { ...runtime.flats };
    const workImages = { ...runtime.workImages };
    delete flats[id];
    delete workImages[id];
    runtime = { flats, workImages };
  }
}

function onConvertImage() {
  const id = project.selectedId;
  project = convertImageToDigitized(project, id);
  clearRuntimeImage(id);
  persist();
}
```

`clearRuntimeImage` is extracted from `onRemoveElement`'s existing inline
block (`App.svelte:429-436`), which switches to calling it too — two call
sites now share it verbatim, which is enough to justify pulling it out
without over-abstracting.

`ContentStep`'s single mount point (`App.svelte:709`) gets
`on:convert={onConvertImage}` beside its existing
`on:checkservice={checkDigitizer}`.

### Error handling

None new. `convertImageToDigitized` is synchronous and cannot fail (a bad id
or wrong type is a no-op, not an error). The actual `/digitize` call only
happens later, through `DigitizePanel`'s existing upload flow, which already
owns its own `try`/`catch` and offline state (`DigitizePanel.svelte:88-123`,
`:1092-1101`).

Considered and dismissed: `digitizerHealth` flipping down between the
Convert button rendering and being clicked. Worst case, the user lands on
`DigitizePanel`'s normal "Choose artwork" prompt (which doesn't check health
— `DigitizePanel.svelte:1075`), then sees the existing offline block once
they upload. No broken state; no guard needed in `onConvertImage`.

## Effect on existing behavior

None outside the `image` element type. The routing rule in `onAddElement` is
unchanged. `ContentStep`'s existing prospective banner (`!digitizerHealth` →
"Artwork will be placed but not auto-digitized…",
`ContentStep.svelte:207-217`) is unchanged — it's about the *next* click on
the Artwork tile, a separate concern from an *existing* element's own panel.

## Testing

- `project.spec.js`: `convertImageToDigitized` — no-op on missing id, no-op
  on a non-`image` element, replaces in place (array position/sew order
  unchanged), preserves `offsetXMm`/`offsetYMm`, drops
  `nColors`/`removeBg`/`threadRgb`/`underlay`/`_hasImage`, lands `sizeMm:
  null`.
- `ImagePanel.spec.js` (new — following `DigitizePanel.spec.js`'s harness
  pattern: Svelte 5's `$on` doesn't work on a mounted instance, so a real
  wrapper `.svelte` that listens with `on:convert`/`on:checkservice` is the
  only way to observe a dispatched event, per that file's own note):
  - standing line always renders, regardless of `health`.
  - `health={false}`: check-again button renders and dispatches
    `checkservice`; no convert button.
  - `health={true}`: convert button renders.
  - convert click with `element._hasImage: false` dispatches `convert`
    immediately.
  - convert click with `element._hasImage: true` shows the inline confirm
    first; `convert` only dispatches after the second ("Convert anyway")
    click; "Cancel" dismisses with no dispatch.
- Not covered here, same carve-out `DigitizePanel.spec.js` already states:
  the real upload → digitize → poll flow after conversion. That's exercised
  by the existing Playwright e2e coverage for the normal `digitized`-element
  path once an element reaches that state.

## Non-goals

- Does not change the routing rule in `onAddElement` (Kent's call, explicitly
  out of scope per this doc's origin).
- Does not persist source art for `image` elements to enable a no-re-pick
  convert. `image` elements only ever hold a 480px alpha-cut working image
  (`WORK_MAX_PX`, `lib/flatten.js:2`) in memory; `digitized` elements want a
  1200px PNG (`PROCESS_MAX_PX`, `DigitizePanel.svelte:47`). Carrying the
  smaller source across would feed the pipeline art at roughly 40% of the
  resolution it expects. Re-picking the file costs one extra click and gets
  the sharp source the auto-digitizer actually wants.
