// The Studio's side of closed-loop sew-out calibration
// (docs/sewout-calibration-brief-2026-09-30.md, phase 4): download the
// calibration card in the customer's machine format, send a photo of the
// sewn card, get a draft profile back. Every number comes from the service
// (digitizer_core/calibration/profile.py); this file only carries it. The
// profile the customer accepts lands on `project.fabricProfile`, which
// adjusts the garment's preset in both engines (src/fabrics.js, fabrics.py).
import { digitizerUrl } from "./digitizer.js";

// The machine formats the card is offered in — the Download step's own six,
// in its order. All service-written here, even DST: the card is built by
// the service so the file the customer sews and the reference their photo
// is compared against are one object.
export const CARD_FORMATS = ["dst", "pes", "exp", "jef", "vp3", "xxx"];

// First download builds the card service-side (~15 s); a read is 10-20 s.
const CARD_TIMEOUT_MS = 90000;
const READ_TIMEOUT_MS = 120000;

async function detail(r) {
  try {
    const body = await r.json();
    if (body && body.detail) return String(body.detail);
  } catch {
    // fall through
  }
  return "The digitizer service answered " + r.status + ".";
}

export async function fetchCalibrationInfo(fetchFn = globalThis.fetch) {
  const r = await fetchFn(digitizerUrl() + "/calibration/info");
  if (!r.ok) throw new Error(await detail(r));
  return r.json();
}

// -> { bytes, filename, mime, widthMm, heightMm }, the same shape
// exportViaService returns so download.js's triggerDownload takes it as is.
export async function downloadCalibrationCard(format, fetchFn = globalThis.fetch) {
  const fmt = String(format || "dst").toLowerCase();
  if (!CARD_FORMATS.includes(fmt)) throw new Error("Unknown card format: " + fmt);
  const r = await fetchFn(digitizerUrl() + "/calibration/card?format=" + encodeURIComponent(fmt), {
    signal: AbortSignal.timeout(CARD_TIMEOUT_MS),
  });
  if (!r.ok) throw new Error(await detail(r));
  const bytes = await r.blob();
  const cd = (r.headers && r.headers.get("Content-Disposition")) || "";
  const m = /filename="([^"]+)"/.exec(cd);
  return {
    bytes,
    filename: m ? m[1] : `EMBBOT_CALIBRATION_CARD_V2.${fmt}`,
    mime: (r.headers && r.headers.get("Content-Type")) || "application/octet-stream",
    widthMm: Number((r.headers && r.headers.get("X-Design-Width-Mm")) || 0) || null,
    heightMm: Number((r.headers && r.headers.get("X-Design-Height-Mm")) || 0) || null,
  };
}

// `photo` is a File/Blob. The garment picks the preset the draft adjusts —
// the same lookup the engine makes (fabrics.py GARMENT_FABRIC).
export async function readCalibrationPhoto(photo, garmentId, fetchFn = globalThis.fetch) {
  const form = new FormData();
  form.append("photo", photo, (photo && photo.name) || "card.jpg");
  if (garmentId) form.append("garment_id", garmentId);
  const r = await fetchFn(digitizerUrl() + "/calibration/read", {
    method: "POST",
    body: form,
    signal: AbortSignal.timeout(READ_TIMEOUT_MS),
  });
  if (!r.ok) throw new Error(await detail(r));
  return r.json();
}

// The reading's feature rows the panel shows, in the order a person reads
// the card: the wide satin bars (pull-in across, push along), the fill
// squares (cloth showing through), the seam pairs (bare gap). Lock bars and
// words stay out — the lock is a tug test and the words are OCR when
// tesseract exists, neither a number the profile uses.
export function readingRows(reading) {
  const feats = (reading && reading.features) || [];
  const rows = [];
  for (const f of feats) {
    if (f.role === "bar" && /^satin-/.test(f.name)) {
      rows.push({
        kind: "satin", name: f.name.replace("satin-", "") + " column",
        pullIn: f.d_height_mm == null ? null : -f.d_height_mm,
        push: f.d_width_mm,
        note: f.note || "",
      });
    } else if (f.role === "square") {
      rows.push({
        kind: "fill", name: f.name.replace("fill-", "") + " fill",
        showThrough: f.d_coverage == null ? null : -f.d_coverage,
        pullIn: f.d_width_mm == null ? null : -f.d_width_mm,
        note: f.note || "",
      });
    }
  }
  const seams = (reading && reading.seam_gap_delta_mm) || {};
  for (const rung of Object.keys(seams)) {
    rows.push({ kind: "seam", name: `${rung} mm underlap seam`, gap: seams[rung] });
  }
  return rows;
}

export function fmtMm(v, digits = 2) {
  if (v == null || !Number.isFinite(v)) return "—";
  const s = v.toFixed(digits);
  return (v > 0 ? "+" : "") + s + " mm";
}

export function fmtPct(v) {
  if (v == null || !Number.isFinite(v)) return "—";
  return Math.round(v * 100) + "%";
}
