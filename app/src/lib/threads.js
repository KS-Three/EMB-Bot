// threads.js — a curated, generic (no brand names) 56-shade embroidery
// thread palette (Slice 8 Task 4) + a Euclidean-nearest-color lookup.
//
// Consumed by ThreadPicker.svelte (the grid of pickable swatches) and by
// DownloadStep's "Threads" summary (mapping a combined design's raw stitch
// colors onto the closest named shade so a shopper knows what to buy).
//
// Every entry is { name, rgb: [r,g,b] }. Names are deliberately generic (no
// manufacturer/brand names) so the list stays useful regardless of which
// actual thread brand a shop stocks -- rgb values are hand-picked, sensible
// approximations of each shade, not sampled from any particular catalog.
import { THREAD_BRANDS } from "./threadBrands.js";

export const THREADS = [
  // Whites / creams
  { name: "Snow White", rgb: [255, 255, 255] },
  { name: "Natural White", rgb: [250, 247, 240] },
  { name: "Cream", rgb: [245, 235, 205] },
  { name: "Ivory", rgb: [255, 244, 214] },

  // Yellows
  { name: "Lemon", rgb: [255, 244, 79] },
  { name: "Sunflower", rgb: [255, 205, 30] },
  { name: "Gold", rgb: [212, 175, 55] },
  { name: "Old Gold", rgb: [168, 134, 58] },

  // Oranges
  { name: "Tangerine", rgb: [255, 130, 35] },
  { name: "Burnt Orange", rgb: [204, 85, 0] },
  { name: "Rust", rgb: [166, 74, 34] },

  // Reds
  { name: "Scarlet", rgb: [230, 40, 30] },
  { name: "Cherry", rgb: [186, 20, 40] },
  { name: "Crimson", rgb: [153, 0, 40] },
  { name: "Wine", rgb: [114, 28, 44] },

  // Pinks
  { name: "Blush", rgb: [244, 194, 194] },
  { name: "Rose", rgb: [224, 120, 140] },
  { name: "Hot Pink", rgb: [255, 60, 150] },
  { name: "Magenta", rgb: [200, 30, 130] },

  // Purples
  { name: "Lavender", rgb: [186, 166, 214] },
  { name: "Violet", rgb: [140, 90, 180] },
  { name: "Royal Purple", rgb: [98, 44, 140] },
  { name: "Plum", rgb: [90, 45, 80] },

  // Blues
  { name: "Baby Blue", rgb: [173, 209, 235] },
  { name: "Sky", rgb: [90, 170, 220] },
  { name: "Royal Blue", rgb: [30, 80, 180] },
  { name: "Navy", rgb: [25, 40, 90] },
  { name: "Midnight", rgb: [15, 22, 48] },

  // Teals
  { name: "Aqua", rgb: [70, 200, 195] },
  { name: "Turquoise", rgb: [30, 170, 170] },
  { name: "Teal", rgb: [10, 110, 110] },

  // Greens
  { name: "Mint", rgb: [150, 220, 180] },
  { name: "Kelly Green", rgb: [30, 140, 60] },
  { name: "Emerald", rgb: [15, 120, 80] },
  { name: "Forest", rgb: [25, 80, 45] },
  { name: "Olive", rgb: [95, 100, 45] },

  // Browns
  { name: "Tan", rgb: [190, 155, 110] },
  { name: "Caramel", rgb: [160, 105, 55] },
  { name: "Chocolate", rgb: [90, 55, 35] },
  { name: "Espresso", rgb: [55, 35, 25] },

  // Neutrals
  { name: "Silver Grey", rgb: [190, 192, 196] },
  { name: "Dove Grey", rgb: [160, 160, 160] },
  { name: "Steel", rgb: [110, 116, 122] },
  { name: "Charcoal", rgb: [60, 60, 64] },
  { name: "Black", rgb: [15, 15, 17] },

  // Accents -- rounding the wheel out to 56 named shades.
  { name: "Coral", rgb: [255, 110, 90] },
  { name: "Peach", rgb: [255, 190, 150] },
  { name: "Mustard", rgb: [200, 160, 40] },
  { name: "Sage", rgb: [140, 155, 120] },
  { name: "Denim", rgb: [65, 95, 135] },
  { name: "Burgundy", rgb: [90, 20, 35] },
  { name: "Eggplant", rgb: [70, 35, 60] },
  { name: "Slate", rgb: [90, 105, 120] },
  { name: "Khaki", rgb: [170, 160, 110] },
  { name: "Copper", rgb: [180, 100, 60] },
  { name: "Bronze", rgb: [140, 100, 50] },
];

// Euclidean nearest-neighbor lookup in RGB space. Returns { name, rgb, index }
// for whichever THREADS entry is closest to `rgb` -- scanning in order and
// only replacing the best match on a STRICTLY smaller squared distance means
// an exact match (distance 0) always wins deterministically, and ties
// between two equidistant shades resolve to whichever comes first in
// THREADS.
export function nearestThread(rgb) {
  return nearestInList(THREADS, rgb);
}

// Same Euclidean-nearest scan as nearestThread, over ANY thread list (the
// generic THREADS or a brand catalog's .threads). Entries may carry a `code`
// (manufacturer catalog number); it's passed through when present so callers
// can render "1902 Poinsettia" style labels.
export function nearestInList(list, rgb) {
  const [r, g, b] = rgb;
  let bestIndex = 0;
  let bestDist = Infinity;
  for (let i = 0; i < list.length; i++) {
    const t = list[i];
    const dr = r - t.rgb[0];
    const dg = g - t.rgb[1];
    const db = b - t.rgb[2];
    const dist = dr * dr + dg * dg + db * db;
    if (dist < bestDist) {
      bestDist = dist;
      bestIndex = i;
    }
  }
  const best = list[bestIndex];
  return { name: best.name, code: best.code || "", rgb: best.rgb, index: bestIndex };
}

// Every selectable palette: the generic Studio list first (default), then the
// real manufacturer charts from threadBrands.js (generated, see
// tools/build-threads.mjs). Shape is uniform -- { id, label, threads } with
// threads entries { name, code?, rgb } -- so pickers can treat them all alike.
export const PALETTES = [
  { id: "studio", label: "Studio basics", threads: THREADS },
  ...THREAD_BRANDS,
];

export function paletteById(id) {
  return PALETTES.find((p) => p.id === id) || PALETTES[0];
}

// App-wide "which thread chart does this shop stitch with" preference,
// shared by ThreadPicker (where it's set) and DownloadStep's thread summary/
// PDF worksheet (where it decides which brand's codes appear). Storage
// failures (private mode, disabled) just mean "studio" every session.
export const PALETTE_STORAGE_KEY = "embstudio:threadPalette";

export function loadPreferredPaletteId() {
  try {
    const id = localStorage.getItem(PALETTE_STORAGE_KEY);
    return PALETTES.some((p) => p.id === id) ? id : "studio";
  } catch (e) {
    return "studio";
  }
}

export function savePreferredPaletteId(id) {
  try {
    localStorage.setItem(PALETTE_STORAGE_KEY, id);
  } catch (e) {
    // Non-persistent is fine; the session still works.
  }
}

// Case-insensitive name/code filter for the brand picker's search box.
// Pure + tested; an empty/whitespace query returns the list untouched.
export function filterThreads(list, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return list;
  return list.filter(
    (t) => t.name.toLowerCase().includes(q) || (t.code || "").toLowerCase().includes(q)
  );
}
