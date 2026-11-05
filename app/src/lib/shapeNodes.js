// The Studio's side of sparse smooth nodes (spec 2026-11-04-sparse-smooth-nodes-
// design.md, PR 2). `sparseNodes.js` is the pure geometry; this is the little
// glue that has no Svelte in it either, so it can be tested without a browser.
//
// `shapeOverrides[sid].nodes = { shell: [{ i, kind }], holes: [[{ i, kind }]] }`,
// `i` an index into the ring the Studio shows for that shape. Nodes are Studio
// state only: `canonicalShapeEdits` never emits them (a test pins that).

import { seedNodes, isValidNodes } from "./sparseNodes.js";
import { boundaryIssues } from "./digitizer.js";
import { fieldMmToOutlineMm, splitRingKey, ringKey } from "./shapeOverlay.js";

// Seeds are a pure function of the ring, and the field redraws on every pointer
// move, so the O(n^2) farthest-pair search in `seedNodes` runs once per ring
// shape (keyed by a cheap signature), not once per frame.
const SEED_CACHE = new Map();
const SEED_CACHE_MAX = 4000;

function ringSignature(ring) {
  let sx = 0, sy = 0;
  for (const [x, y] of ring) { sx += x; sy += y; }
  const last = ring[ring.length - 1] || [0, 0];
  return `${ring.length}|${sx.toFixed(5)}|${sy.toFixed(5)}|${ring[0] ? ring[0][0].toFixed(5) : ""}|${last[1].toFixed(5)}`;
}

/** `seedNodes`, memoized on the ring's signature. Returns a fresh copy. */
export function seedNodesCached(ring) {
  const key = ringSignature(ring);
  let hit = SEED_CACHE.get(key);
  if (!hit) {
    if (SEED_CACHE.size >= SEED_CACHE_MAX) SEED_CACHE.clear();
    hit = seedNodes(ring);
    SEED_CACHE.set(key, hit);
  }
  return hit.map((n) => ({ i: n.i, kind: n.kind }));
}

/**
 * A cheap fingerprint of a ring: vertex count plus the first and last edge as a
 * share of the perimeter (rounded to 1e-5). Similarity-invariant, so the service
 * ring a commit sees and the field-mm ring the Studio shows agree. A closing
 * duplicate vertex is ignored (as `outlineOf` does). Stored in `nodes.fp`, it
 * lets a later show notice that the ring under the node indices is not the one
 * they were made against (a re-digitize that kept the shape id).
 */
export function ringFingerprint(ring) {
  let pts = ring || [];
  const n0 = pts.length;
  if (n0 >= 2 && Math.abs(pts[0][0] - pts[n0 - 1][0]) < 1e-6 && Math.abs(pts[0][1] - pts[n0 - 1][1]) < 1e-6) pts = pts.slice(0, n0 - 1);
  const n = pts.length;
  if (n < 2) return String(n);
  const edge = (i) => Math.hypot(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1]);
  let per = 0;
  for (let i = 0; i < n; i++) per += edge(i);
  if (!(per > 0)) return String(n);
  const r = (v) => (Math.round((v / per) * 1e5) / 1e5).toFixed(5);
  return `${n}:${r(edge(0))}:${r(edge(n - 1))}`;
}

/**
 * The node lists a shape shows: the STORED ones when `entry.nodes` is valid for
 * every ring and the hole count matches, else fresh seeds for every ring (spec
 * section 2: an invalid entry is ignored and re-seeded). Seeds are never
 * written here; the first node edit commits them with the polygon.
 *
 * @param entry  shapeOverrides[sid] (or undefined)
 * @param shell  the shell ring shown ([[x, y], ...])
 * @param holes  the hole rings shown, in index order
 * @returns { shell, holes, stored }
 */
export function nodesForShape(entry, shell, holes = []) {
  const n = entry && entry.nodes;
  const stored = !!n && isValidNodes(n.shell, shell)
    && Array.isArray(n.holes) && n.holes.length === holes.length
    && holes.every((h, k) => isValidNodes(n.holes[k], h))
    && fingerprintsMatch(n.fp, shell, holes);
  if (stored) {
    return {
      stored: true,
      shell: n.shell.map((x) => ({ i: x.i, kind: x.kind })),
      holes: n.holes.map((l) => l.map((x) => ({ i: x.i, kind: x.kind }))),
    };
  }
  return { stored: false, shell: seedNodesCached(shell), holes: holes.map((h) => seedNodesCached(h)) };
}

/** True once the pointer has travelled `px` or more from the press: a click is not a drag. */
export function pastClickDeadZone(start, cur, px) {
  return Math.hypot(cur.x - start.x, cur.y - start.y) >= px;
}

// No `fp` (a hand-built entry) is trusted on range alone; one that is there must match.
function fingerprintsMatch(fp, shell, holes) {
  if (!fp) return true;
  if (fp.shell !== ringFingerprint(shell)) return false;
  return Array.isArray(fp.holes) && fp.holes.length === holes.length && holes.every((h, k) => fp.holes[k] === ringFingerprint(h));
}

/** How a node draws: a corner is a square, a smooth node the existing disc. */
export function nodeMarker(kind) {
  return kind === "corner" ? "square" : "disc";
}

/**
 * Which span a polygon EDGE `j` (vertex j -> j+1) lies in: the span that starts
 * at the last node at or before j (wrapping to the last node when j precedes
 * the first one).
 */
export function spanOfEdge(nodes, j) {
  let k = -1;
  for (let m = 0; m < nodes.length; m++) if (nodes[m].i <= j) k = m;
  return k < 0 ? nodes.length - 1 : k;
}

/**
 * Attach node lists to field-mm outlines. `outlines` is
 * `shapeOutlinesInFieldMm`'s output ({ id, key, ring?, points }); the result is
 * the same array with `nodes` on every entry (a hole's list at its `ring`
 * index). `overrides` is `el.shapeOverrides`.
 */
export function withNodes(outlines, overrides) {
  const holesOf = new Map();
  for (const o of outlines) {
    if (o.ring == null) continue;
    if (!holesOf.has(o.id)) holesOf.set(o.id, []);
    holesOf.get(o.id)[o.ring] = o.points;
  }
  const perShape = new Map();
  for (const o of outlines) {
    if (o.ring != null || perShape.has(o.id)) continue;
    const holes = (holesOf.get(o.id) || []).filter(Boolean);
    perShape.set(o.id, nodesForShape(overrides && overrides[o.id], o.points, holes));
  }
  return outlines.map((o) => {
    const got = perShape.get(o.id);
    if (!got) return o;
    return { ...o, nodes: o.ring == null ? got.shell : got.holes[o.ring] || null };
  });
}

/**
 * The overrides a set of edited rings turns into (moved out of
 * EmbroideryField.svelte so Simplify-deletes-nodes can be unit tested).
 * `live` is Map<ringKey, ring in field mm> (a shell is its shape id, a hole
 * `<id>#h<k>`); `removed` is Map<shapeId, Set<holeIndex>> of holes deleted
 * outright. Per touched shape: `boundary_override` from the shell when the
 * SHELL moved, `holes_override` from ALL its current holes when a hole did,
 * `boundaryIssues` on every touched shape; one refusal drops the gesture.
 * `liveNodes` (Map<ringKey, node list>) is passed only by the node editor: it
 * writes `nodes` ({ shell, holes }) from the live lists, else from
 * `basis.nodesById` (how seeds are committed with the first node edit). Any
 * other writer passes null and `nodes` is deleted from the entry.
 * -> { cur } | { error, sid, cur: null }
 */
export function ringEditOverrides(el, basis, live, removed = null, liveNodes = null) {
  if (!basis || !basis.rows || !basis.bboxMm) return { error: "" , sid: null, cur: null };
  const gone = removed || new Map();
  if (!live.size && !gone.size) return { cur: null };
  const cur = { ...(el.shapeOverrides || {}) };
  const touched = new Map();   // sid -> { shell, holes: Map<k, pts> }
  const note = (sid) => {
    if (!touched.has(sid)) touched.set(sid, { shell: null, holes: new Map() });
    return touched.get(sid);
  };
  for (const [key, pts] of live) {
    const { shapeId, ring } = splitRingKey(key);
    const t = note(shapeId);
    if (ring === "exterior") t.shell = pts;
    else t.holes.set(ring, pts);
  }
  for (const sid of gone.keys()) note(sid);
  const toService = (pts) => fieldMmToOutlineMm(pts, basis.rows, basis.bboxMm, basis.rotationDeg);
  for (const [sid, t] of touched) {
    const row = basis.rows.find((r) => r && r.id === sid) || {};
    const entry = { ...(cur[sid] || {}) };
    let shellService = null;
    if (t.shell) {
      shellService = toService(t.shell);
      if (!shellService) return { error: "", sid, cur: null };
    } else if (Array.isArray(entry.boundary_override)) {
      shellService = entry.boundary_override;
    } else {
      shellService = row.outlineFull || null;
    }
    const holeEdited = t.holes.size > 0 || (gone.get(sid) && gone.get(sid).size > 0);
    const sendHoles = holeEdited || Array.isArray(entry.holes_override);
    let holes = null;
    const holeNodes = [];   // node lists of the holes that survive, in order
    if (sendHoles || (shellService && (Array.isArray(row.holesFull) && row.holesFull.length))) {
      const base = Array.isArray(entry.holes_override) ? entry.holes_override : (row.holesFull || []);
      const drop = gone.get(sid) || new Set();
      holes = [];
      base.forEach((h, k) => {
        if (drop.has(k)) return;
        const hk = ringKey(sid, k);
        holeNodes.push((liveNodes && liveNodes.get(hk)) || (basis.nodesById && basis.nodesById.get(hk)) || null);
        if (t.holes.has(k)) {
          const s = toService(t.holes.get(k));
          holes.push(s || h);
        } else holes.push(h);
      });
    }
    const issues = boundaryIssues(shellService, holes);
    if (issues.length) return { error: issues[0], sid, cur: null };
    if (t.shell) entry.boundary_override = shellService.map(([x, y]) => [x, y]);
    if (sendHoles) entry.holes_override = (holes || []).map((r) => r.map(([x, y]) => [x, y]));
    const shellNodes = liveNodes ? (liveNodes.get(sid) || (basis.nodesById && basis.nodesById.get(sid)) || null) : null;
    if (shellNodes && holeNodes.every(Boolean)) {
      entry.nodes = {
        shell: shellNodes.map((n) => ({ i: n.i, kind: n.kind })),
        holes: holeNodes.map((l) => l.map((n) => ({ i: n.i, kind: n.kind }))),
        fp: { shell: ringFingerprint(shellService), holes: (holes || []).map((h) => ringFingerprint(h)) },
      };
    } else delete entry.nodes;
    cur[sid] = entry;
  }
  return { cur };
}

/**
 * Discard: the fields Reshape snapshotted on entry, put back. Returns only the
 * keys that differ (so nothing changed = no patch). `nodes` ride inside
 * `shapeOverrides`, which is why Discard restores them.
 */
export function discardPatch(el, start, keys) {
  const patch = {};
  for (const k of keys) if (el[k] !== start[k]) patch[k] = start[k];
  return patch;
}
