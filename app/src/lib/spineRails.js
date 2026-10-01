// A hand-drawn satin column is an OPEN spine plus a drawn width (manual
// digitizing spec 2026-09-30 §6, "Amended 2026-10-01"). This turns the two
// into the pair of rails the engine sews between (`sewAs.railA` / `railB`,
// src/digitize.js) and the closed ring it treats as the column's outline.
//
// THE CONTRACT THAT MATTERS: both rails come back with the same point count,
// in the same direction, and rail A's i-th point and rail B's i-th point are
// the two ends of the cross at the spine's i-th point. The engine has no way
// to detect rails that break it — opposite-direction rails sew a bow-tie
// (measured 2026-10-01: 102 points on a curved column), coincident rails sew
// nothing — so this function is the only guard, and spineRails.spec.js pins it.
//
// Pure geometry in the caller's units (authored canvas px). No mm, no
// constants about thread: width is `widthPx` (Kent's ruling 12).

// Two spine points closer than this are the same point: they have no tangent
// between them, and a zero-length segment would yield a NaN normal.
const SAME_POINT_EPS = 1e-9;

// A miter grows without bound as a corner sharpens (half-width / cos(turn/2)).
// Capped at this many half-widths — the same reason offsetRing clamps. Both
// rails are shortened together, so the cross stays centred on the spine.
const MITER_LIMIT = 2;

// railsFromSpine(spineFlat, widthPx) -> { railA, railB, ring } | null
//
// `spineFlat` is the FLATTENED open polyline (flattenShape(points, curves,
// false)) — curves are already points here. Each vertex is offset by
// +/- widthPx / 2 along its normal: the left-hand normal of the adjacent
// segment at the two ends, and of the averaged adjacent tangents in between,
// lengthened to a true miter and clamped. Rail A is always the side
// (-t.y, t.x) of the direction of travel t; rail B the other.
//
// `ring` = rail A, then rail B walked backwards: the closed outline.
// null when the spine has under two distinct points or widthPx is not > 0.
// Consecutive coincident points are dropped first, so the rails carry one
// point per DISTINCT spine point.
export function railsFromSpine(spineFlat, widthPx) {
  if (!Array.isArray(spineFlat) || !(typeof widthPx === "number" && widthPx > 0 && isFinite(widthPx))) return null;
  const spine = [];
  for (const p of spineFlat) {
    if (!p || !isFinite(p.x) || !isFinite(p.y)) continue;
    const last = spine[spine.length - 1];
    if (last && Math.hypot(p.x - last.x, p.y - last.y) <= SAME_POINT_EPS) continue;
    spine.push(p);
  }
  const n = spine.length;
  if (n < 2) return null;

  // Unit direction of each segment i -> i+1.
  const dirs = [];
  for (let i = 0; i < n - 1; i++) {
    const dx = spine[i + 1].x - spine[i].x, dy = spine[i + 1].y - spine[i].y;
    const len = Math.hypot(dx, dy);
    dirs.push({ x: dx / len, y: dy / len });
  }

  const half = widthPx / 2;
  const railA = [], railB = [];
  for (let i = 0; i < n; i++) {
    const dIn = i > 0 ? dirs[i - 1] : dirs[0];
    const dOut = i < n - 1 ? dirs[i] : dirs[n - 2];
    let tx = dIn.x + dOut.x, ty = dIn.y + dOut.y;
    const tLen = Math.hypot(tx, ty);
    let reach = half;
    if (tLen < 1e-12) {
      // The spine doubles straight back on itself: there is no averaged
      // tangent. Keep the incoming segment's normal at the plain half-width;
      // the ring this makes folds, and columnIssues says so.
      tx = dIn.x; ty = dIn.y;
    } else {
      tx /= tLen; ty /= tLen;
      // cos(turn / 2) = averaged tangent . incoming tangent; the miter that
      // keeps both rails `half` from the spine's SEGMENTS is half / that.
      const cosHalf = tx * dIn.x + ty * dIn.y;
      reach = cosHalf > 1 / MITER_LIMIT ? half / cosHalf : half * MITER_LIMIT;
    }
    const nx = -ty * reach, ny = tx * reach;
    railA.push({ x: spine[i].x + nx, y: spine[i].y + ny });
    railB.push({ x: spine[i].x - nx, y: spine[i].y - ny });
  }
  return { railA, railB, ring: railA.concat(railB.slice().reverse()) };
}
