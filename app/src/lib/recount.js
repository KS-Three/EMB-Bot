// The shape/colour recount shown in DigitizePanel's reading row: "N shapes, M
// colors at W mm" for the size currently chosen (Kent, 2026-11-05 -- the
// Stitchist footer's recount, counts only; no suggestion, no advice).
//
// The service half is POST /recount (stages 0-4, seconds, not /classify's
// fraction of one), so asking is deliberate: debounced so a typed width or a
// drag asks once at the end, the request for a superseded size is aborted, and
// -- the rule the row is built on -- a number is shown ONLY while it answers the
// key now on screen. A size change hides the old count at once and nothing
// stands in its place until the new answer lands: a stale count is worse than
// none.
//
// Kept apart from the Svelte file so the debounce/cancel/stale rules are tested
// without a DOM (recount.spec.js). The panel supplies what to ask and where to
// put the answer.

export const RECOUNT_DEBOUNCE_MS = 500;
export const RECOUNT_CACHE_MAX = 16;

// `onResult(key, counts)` hears every answer that is still wanted. `cache` is
// shared by the caller across mounts (ContentStep remounts the panel on every
// selection and an ask costs seconds of service CPU).
export function createRecounter({ onResult, debounceMs = RECOUNT_DEBOUNCE_MS, cache = new Map(), cacheMax = RECOUNT_CACHE_MAX }) {
  let timer = null;
  let controller = null;
  let pending = "";   // the key an ask is scheduled or in flight for
  let shown = "";     // the key the last delivered answer was for
  let gone = false;   // the service has no /recount (404): never ask again

  function stop() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    if (controller) {
      controller.abort();
      controller = null;
    }
    pending = "";
  }

  // `run(signal)` resolves to the service's counts, or null for a 404. Re-run
  // by the panel on EVERY change to the element, so the same key arriving again
  // must leave a scheduled or in-flight ask alone.
  function ask(key, run) {
    if (!key || gone) {
      stop();
      return;
    }
    if (key === pending) return;
    if (key === shown) {
      // Back to the size already answered: drop whatever a detour scheduled.
      stop();
      return;
    }
    stop();
    const hit = cache.get(key);
    if (hit) {
      shown = key;
      onResult(key, hit);
      return;
    }
    pending = key;
    timer = setTimeout(async () => {
      timer = null;
      const mine = (controller = new AbortController());
      try {
        const counts = await run(mine.signal);
        if (mine.signal.aborted) return;
        if (counts === null) {
          gone = true;
          return;
        }
        const clean = {
          shapes: Number(counts.shape_count),
          colors: Number(counts.color_count),
          sizeMm: Array.isArray(counts.size_mm) ? counts.size_mm : null,
        };
        if (!Number.isFinite(clean.shapes) || !Number.isFinite(clean.colors)) return;
        cache.set(key, clean);
        if (cache.size > cacheMax) cache.delete(cache.keys().next().value);
        shown = key;
        onResult(key, clean);
      } catch {
        // No count. The run does not depend on one.
      } finally {
        if (controller === mine) {
          controller = null;
          pending = "";
        }
      }
    }, debounceMs);
  }

  return { ask, stop };
}

// "22 shapes, 2 colors at 36.7 mm". Counts and the size they are for, nothing
// else. `widthMm` is the width the request asked for.
export function recountText(counts, widthMm) {
  if (!counts) return "";
  const n = (v, one, many) => `${v} ${v === 1 ? one : many}`;
  const w = Number(widthMm);
  const at = Number.isFinite(w) && w > 0 ? ` at ${Math.round(w * 10) / 10} mm` : "";
  return `${n(counts.shapes, "shape", "shapes")}, ${n(counts.colors, "color", "colors")}${at}`;
}
