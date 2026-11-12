// The launch starter pack (PRODUCT.md launch item 3): twelve CC0 /
// public-domain designs shipped as static files in public/starter/, listed by
// its manifest.json (docs/starter-pack-2026-11-10.md; guarded by
// test/starter-pack.test.js). This module is everything the Studio knows
// about it: read the manifest, fetch one design's .dst, and add it to the
// project.
//
// Nothing here talks to the digitizer service. The files are static and the
// DST is decoded in the browser, so the pack works with the service down.
//
// A starter design is an ORDINARY import: its bytes go through
// designFilePatch (lib/designImport.js), the same function DesignPanel's file
// picker uses, and land on a plain "design" element. The one thing added is a
// thread colour per block (lib/starterThreads.js), because a DST carries none.
//
// Deliberately not read from the manifest: preflight_grade / preflight_score.
// Kent's ruling: nothing about the pack is shown to the customer as a warning
// (LETTERING_TOO_SMALL and GROUND_SEWN false-fire on these designs).
import { addElement, updateElement, withoutBlankStarter } from "./project.js";
import { designFilePatch } from "./designImport.js";
import { STARTER_THREADS } from "./starterThreads.js";

// Document-relative, never "/starter/…": the bundle is built with base "./"
// (see lib/assetPaths.spec.js for what an absolute path cost the fonts).
const DIR = "starter/";

// "Art by Jon Phillips · CC0" -- the provenance line shown where a design is
// picked. Both halves are the manifest's own words: `author` as the art's
// source page credits it, `license` as that page states it.
export function creditLine(entry) {
  return `Art by ${entry.author} · ${entry.license}`;
}

// The manifest's designs, reduced to what the picker and the insert need.
// Throws on a file that is not the pack's manifest, so a wrong response (an
// HTML error page served with 200) fails loudly instead of listing nothing.
export function starterDesigns(manifest) {
  if (!manifest || !Array.isArray(manifest.designs)) throw new Error("Starter pack manifest is unreadable");
  return manifest.designs.map((d) => ({
    id: d.id,
    title: d.title,
    theme: d.theme,
    artUrl: DIR + d.art,
    dstUrl: DIR + d.dst,
    credit: creditLine(d),
    sourceUrl: d.source_page_url,
  }));
}

// One fetch per page load. A failure is not cached, so reopening the picker
// tries again.
let packPromise = null;
export function loadStarterPack(fetchFn = fetch) {
  if (!packPromise) {
    packPromise = fetchFn(DIR + "manifest.json")
      .then((res) => {
        if (!res.ok) throw new Error(`Starter pack manifest: HTTP ${res.status}`);
        return res.json();
      })
      .then(starterDesigns)
      .catch((err) => {
        packPromise = null;
        throw err;
      });
  }
  return packPromise;
}

// Block index -> [r, g, b], the shape a design element's `blockColors` takes.
export function starterBlockColors(id) {
  const out = {};
  (STARTER_THREADS[id] || []).forEach((rgb, i) => {
    out[i] = [rgb[0], rgb[1], rgb[2]];
  });
  return out;
}

// Fetches one design's .dst and returns the element patch for it: exactly
// what importing that file by hand produces, named by the manifest's title
// and with the pack's thread colours filled in.
export async function loadStarterPatch(design, fetchFn = fetch) {
  const res = await fetchFn(design.dstUrl);
  if (!res.ok) throw new Error(`Starter design ${design.id}: HTTP ${res.status}`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  return { ...designFilePatch(bytes, design.title), blockColors: starterBlockColors(design.id) };
}

// Adds the design to the project as a new, selected "design" element, in ONE
// project change: App records it once, so it is one undo step. On a fresh
// project the untouched blank text box is dropped first, as an artwork upload
// does (withoutBlankStarter), so the design is not filed beside a
// "Text · empty" row. Pure.
export function addStarterDesign(project, patch, hoopWmm) {
  const added = addElement(withoutBlankStarter(project), "design", hoopWmm);
  return updateElement(added, added.selectedId, patch);
}
