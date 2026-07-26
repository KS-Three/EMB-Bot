// Compact hand-written inline SVG line-art, one per garment id (Slice 8 Task
// 3). Each icon: viewBox 0 0 48 48, `currentColor` strokes (~2.5 wide), fill
// none, plus exactly ONE small accent detail carrying `class="acc"` — styled
// via `var(--accent)` in theme.css — so garment tiles read as icon-over-label
// instead of text-only buttons. Kept as plain template-string exports (not
// .svg asset files) so GarmentStep can inline them directly with `{@html}`
// without an extra asset-loading/fetch step; every string stays comfortably
// under ~600 bytes (checked at authoring time — hand-counted paths, not a
// generator), so there's no bundle-size concern in shipping all 10 inline.
//
// Silhouettes intentionally read as simple/recognizable rather than
// photorealistic: a cap profile, a polo with a small chest mark, a tee back
// with a big center print, a folded beanie, a tapered sleeve, a tote with
// handles, a jacket back with a center seam, a shield patch with a star, a
// folded/striped towel, and a rolled blanket.
export const GARMENT_ART = {
  hat_front: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 27 Q6 9 24 9 Q42 9 42 27"/><path d="M3 29 Q24 36 45 29"/><path class="acc" d="M24 9 L24 27"/></svg>`,

  left_chest: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8 L8 14 L11 20 L15 17 L15 40 L33 40 L33 17 L37 20 L40 14 L32 8 L27 11 L21 11 Z"/><path d="M21 11 L24 15 L27 11"/><rect class="acc" x="19" y="22" width="6" height="6" rx="1"/></svg>`,

  full_back: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8 L8 14 L11 20 L15 17 L15 40 L33 40 L33 17 L37 20 L40 14 L32 8 L27 9 Q24 11 21 9 Z"/><rect class="acc" x="17" y="20" width="14" height="14" rx="2"/></svg>`,

  beanie: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 26 Q9 8 24 8 Q39 8 39 26 L39 30 L9 30 Z"/><path d="M9 22 L39 22"/><circle class="acc" cx="24" cy="6" r="2.4"/></svg>`,

  sleeve: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 10 L40 6 L36 16 L30 39 L18 37 L14 18 Z"/><path d="M16 33 L32 35"/><path class="acc" d="M14 14 L34 10"/></svg>`,

  tote: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 18 L10 42 L38 42 L38 18 Z"/><path d="M16 18 L16 10 Q16 6 20 6 L28 6 Q32 6 32 10 L32 18"/><rect class="acc" x="19" y="26" width="10" height="8" rx="1"/></svg>`,

  jacket_back: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 10 L7 16 L10 22 L14 19 L12 42 L36 42 L34 19 L38 22 L41 16 L34 10 L28 13 L20 13 Z"/><path d="M20 13 L24 17 L28 13"/><path class="acc" d="M24 17 L24 42"/></svg>`,

  patch: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M24 6 L40 12 L40 24 Q40 36 24 43 Q8 36 8 24 L8 12 Z"/><path class="acc" d="M24 16 L26.5 22 L33 22 L27.5 26 L29.5 33 L24 29 L18.5 33 L20.5 26 L15 22 L21.5 22 Z"/></svg>`,

  towel: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="10" width="34" height="28" rx="2"/><path d="M7 18 L41 18 M7 30 L41 30"/><rect class="acc" x="7" y="20" width="34" height="4"/></svg>`,

  blanket: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 10 L36 10 Q42 10 42 24 Q42 38 36 38 L14 38 Q8 38 8 24 Q8 10 14 10 Z"/><path d="M8 24 Q14 24 14 16 Q14 10 8 12"/><path class="acc" d="M8 24 Q14 24 14 32 Q14 38 8 36"/></svg>`,
};

// Defensive fallback for any garment id without hand-drawn art above — EMB's
// GARMENTS list currently covers exactly the 10 keys in GARMENT_ART, but this
// keeps GarmentStep from rendering a blank icon slot if that ever drifts.
const FALLBACK_ART = `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="30" height="30" rx="4"/><path class="acc" d="M9 24 L39 24"/></svg>`;

export function garmentArt(id) {
  return GARMENT_ART[id] || FALLBACK_ART;
}
