// Bringing a saved project's artwork back.
//
// An `image` element's pixels are owned by App's `runtime`, which is
// deliberately not persisted. `element.sourcePng` (added 2026-09-07) is the
// durable copy; this module turns it back into the two runtime entries the
// rest of the app already knows how to consume — the working image and its
// flattened palette — so a reload is indistinguishable from having just
// uploaded the file.
//
// Why here and not in ImagePanel: the panel mounts only on the Content step
// with that element selected, and the embroidery field is visible on EVERY
// step. Rehydrating in the panel left a reloaded project showing an empty
// field until the user happened to click Content — and worse, `_hasImage`
// would be false meanwhile, so the Review step would have called a design
// with real artwork in it empty. The load path is the only place that is
// true for every step at once.
//
// `decode` and `flatten` are injected rather than imported so the ORDERING
// and STATE MERGING here — the parts that actually go wrong — are testable
// without a canvas. App passes the real implementations.

/** Elements whose saved artwork is not yet in runtime. */
export function pendingImageRehydrations(project, runtime) {
  const have = (runtime && runtime.workImages) || {};
  return ((project && project.elements) || []).filter(
    (el) => el && el.type === "image" && el.sourcePng && !have[el.id]);
}

/**
 * Decode each pending element and publish it as it lands.
 *
 * Sequential, not Promise.all: decoding is fast and the alternative is N
 * canvases alive at once on a machine that may already be short of memory —
 * and publishing each as it finishes means a two-element project shows its
 * first piece of artwork without waiting for the second.
 *
 * `token()` lets the caller abandon a run that a project switch has
 * overtaken: it is checked before every publish, so a stale decode can never
 * write into the new project's runtime. Returns a summary rather than
 * throwing — one unreadable record must not stop the others coming back.
 */
export async function rehydrateImages(project, runtime, opts) {
  const { decode, flatten, onImage, onFlat, onError, token = () => true } = opts;
  const pending = pendingImageRehydrations(project, runtime);
  const done = [];
  const failed = [];
  for (const el of pending) {
    if (!token()) return { done, failed, abandoned: true };
    try {
      const workImage = await decode(el.sourcePng);
      if (!token()) return { done, failed, abandoned: true };
      onImage(el.id, workImage);
      onFlat(el.id, flatten(workImage, el.nColors, el.removeBg));
      done.push(el.id);
    } catch (err) {
      failed.push(el.id);
      if (onError) onError(el.id, err);
    }
  }
  return { done, failed, abandoned: false };
}
