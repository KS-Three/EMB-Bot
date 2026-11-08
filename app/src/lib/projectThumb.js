// Project thumbnails for the "My designs" drawer.
//
// A saved project carries its baked stitches only inside its "digitized"
// elements (`element.result`, the service's Design verbatim). This module
// joins those into one design, draws it with preview.js's renderRealistic
// onto an offscreen 96 px canvas, and keeps the PNG data URL in a cache keyed
// by the project's SAVED REVISION (`id:updatedAt` from the registry index --
// saveProject bumps updatedAt on every write, so a changed design misses and
// an unchanged one never redraws). The cache is module-level: closing and
// reopening the drawer draws nothing new.
//
// A project with no stitches here (text-only, manual shapes, imported DST --
// those regenerate in App rather than being stored) yields null and the
// drawer keeps its placeholder; null is cached too so it is not re-derived.

import { renderRealistic } from "./preview.js";
import { combineDesigns } from "./combine.js";
import { loadProject } from "./projects.js";

export const THUMB_PX = 96;
const THUMB_PAD = 6;
const MAX_ENTRIES = 120;

const cache = new Map(); // revision key -> data URL | null (no stitches)

export function thumbKey(id, updatedAt) {
  return id + ":" + (updatedAt || 0);
}

function hasSewn(d) {
  const s = d && d.stitches;
  if (!Array.isArray(s)) return false;
  for (let i = 0; i < s.length; i++) if (s[i].type === "stitch") return true;
  return false;
}

// The project's stitches as one Design, or null when it has none to draw.
export function projectDesign(project) {
  const els = (project && project.elements) || [];
  const parts = [];
  for (const el of els) {
    if (el && el.type === "digitized" && hasSewn(el.result)) parts.push(el.result);
  }
  if (parts.length === 0) return null;
  return parts.length === 1 ? parts[0] : combineDesigns(parts);
}

// At 96 px a 20k-stitch design has ~200 stitches per pixel, and the renderer
// pays per stitch. Drop each SEWN stitch that lands within MIN_STEP_PX of the
// last one kept (colour, trim and jump records are always kept, so the
// thread path, colour blocks and travel are untouched). The span index no
// longer describes the shortened array, so the copy carries none and the
// renderer falls back to drawing everything as ordinary stitching.
const MIN_STEP_PX = 0.7;

export function thinForThumb(design) {
  const src = design.stitches;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i < src.length; i++) {
    const s = src[i];
    if (s.type === "color" || s.type === "end") continue;
    if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y;
  }
  const span = Math.max(1, maxX - minX, maxY - minY);
  const step = (span / (THUMB_PX - 2 * THUMB_PAD)) * MIN_STEP_PX; // DST units
  if (!(step > 0) || src.length < 2000) return design;
  const step2 = step * step;
  const out = [];
  let lx = 0, ly = 0, have = false;
  for (let i = 0; i < src.length; i++) {
    const s = src[i];
    if (s.type !== "stitch") { out.push(s); have = false; continue; }
    const last = i === src.length - 1 || src[i + 1].type !== "stitch";
    if (have) {
      const dx = s.x - lx, dy = s.y - ly;
      if (dx * dx + dy * dy < step2 && !last) continue;
    }
    out.push(s); lx = s.x; ly = s.y; have = true;
  }
  const { runs: _runs, ...rest } = design;
  return { ...rest, stitches: out };
}

// Draws `design` at THUMB_PX and returns a PNG data URL (or null if the
// environment cannot make a canvas).
export function drawThumb(design) {
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = THUMB_PX;
  canvas.height = THUMB_PX;
  renderRealistic(canvas, thinForThumb(design), { pad: THUMB_PAD });
  return canvas.toDataURL("image/png");
}

// Cached thumbnail for one registry entry. `load` is injectable for specs.
export function getThumb(entry, load = loadProject) {
  const key = thumbKey(entry.id, entry.updatedAt);
  if (cache.has(key)) {
    const hit = cache.get(key);
    cache.delete(key); // refresh LRU order
    cache.set(key, hit);
    return hit;
  }
  let url = null;
  try {
    const design = projectDesign(load(entry.id));
    url = design ? drawThumb(design) : null;
  } catch (e) {
    url = null;
  }
  cache.set(key, url);
  while (cache.size > MAX_ENTRIES) cache.delete(cache.keys().next().value);
  return url;
}

export function clearThumbCache() {
  cache.clear();
}
