// What the operator told us about their own shop, for the quote rows on the
// review sheet and the worksheet (2026-10-01): which machine, the speed they
// actually run it at, what a cone costs them, what an hour of the machine is
// worth. One record, this browser, every project — Kent's ruling: a shop has
// one thread price and one rate, and re-entering them per project is a chore.
// The catch that ruling accepted: a project opened on another computer shows
// no dollar rows until the prices are entered there.
//
// NOTHING HERE IS A CONSTANT OF OURS. A price is the operator's or it is
// absent, and an absent input drops its row — the same posture as
// `sewTimeMin` returning null. There is no default cone price, no default
// rate, and no currency conversion: the figure is printed in the unit it was
// typed in.
//
// Separate from machines.js on purpose. That table is BRAND GROUPS ("Brother
// / Baby Lock") mapped to the file format they read; a speed or a needle
// count exists only per MODEL, and "Tajima and other commercial" has neither.

// One model, the one whose owner asked (Kent's ruling 2026-10-01: S-1501
// first, everyone else types their own speed). Every figure carries where it
// was read; a figure nobody publishes is null, never a guess.
//
// SOURCE STANDING: smartstitch-official.com is a brand storefront whose
// ownership was not verified — it is the best page found, not a manufacturer
// datasheet. Read 2026-10-01: "Up to 1,200 SPM", caps "Up to 850 SPM", 15
// needles, 350 x 500 mm field. No page states a maximum stitch length, and
// no maker (this one, Tajima, Barudan, Melco, Happy, Brother) publishes how
// many seconds a trim or a colour change takes.
//
// `maxSpm` is the NAMEPLATE and is used only as a ceiling on what the
// operator may type. It is never the speed a quote is computed at: a machine
// does not hold its nameplate (playbook law 36), which is the whole reason
// the plan rate is 650.
export const MACHINE_PROFILES = [
  {
    id: "smartstitch_s1501",
    label: "SmartStitch S-1501",
    needles: 15,
    maxSpm: 1200,
    maxSpmCaps: 850,
    maxStitchMm: null,
    source: "https://smartstitch-official.com/products/s-1501",
  },
];

export const QUOTE_KEY = "embstudio:quote";

export function profileById(id) {
  return MACHINE_PROFILES.find((p) => p.id === id) || null;
}

const EMPTY = { profileId: null, spm: null, conePrice: null, coneM: null, hourRate: null };

function positive(v) {
  const n = typeof v === "string" && v.trim() !== "" ? Number(v) : v;
  return typeof n === "number" && isFinite(n) && n > 0 ? n : null;
}

// Whatever came in — a form's strings, a stored record from an older build,
// junk — to the one shape the rest of the code reads. A value that is not a
// positive number is null, which downstream means "row omitted".
export function cleanQuote(raw) {
  const r = raw && typeof raw === "object" ? raw : {};
  const profile = profileById(r.profileId);
  let spm = positive(r.spm);
  // A typed speed above the nameplate is not a speed that machine has.
  if (spm != null && profile && profile.maxSpm && spm > profile.maxSpm) spm = profile.maxSpm;
  return {
    profileId: profile ? profile.id : null,
    spm,
    conePrice: positive(r.conePrice),
    coneM: positive(r.coneM),
    hourRate: positive(r.hourRate),
  };
}

// Same try/catch contract as machines.js: unreadable storage is "nothing
// entered", and a failed write simply does not persist.
export function loadQuote() {
  try {
    const raw = localStorage.getItem(QUOTE_KEY);
    return raw ? cleanQuote(JSON.parse(raw)) : { ...EMPTY };
  } catch (e) {
    return { ...EMPTY };
  }
}

export function saveQuote(quote) {
  const q = cleanQuote(quote);
  try {
    if (Object.values(q).some((v) => v != null)) localStorage.setItem(QUOTE_KEY, JSON.stringify(q));
    else localStorage.removeItem(QUOTE_KEY);
  } catch (e) {
    // no storage; nothing to do
  }
  return q;
}

// "$0.03", "$12.50". Two decimals always: a thread cost is cents, and "$0"
// for 2.5 m of a cone reads as free. Under a cent says so rather than
// rounding to nothing.
export function money(v) {
  if (typeof v !== "number" || !isFinite(v) || v < 0) return null;
  if (v > 0 && v < 0.01) return "under $0.01";
  return "$" + v.toFixed(2);
}

// Top thread only. Bobbin thread is real money too, but there is no bobbin
// price input and inventing one is exactly what this file refuses to do.
export function threadCost(threadM, quote) {
  const q = quote || EMPTY;
  if (typeof threadM !== "number" || !isFinite(threadM) || threadM < 0) return null;
  if (q.conePrice == null || q.coneM == null) return null;
  return (threadM / q.coneM) * q.conePrice;
}

export function machineCost(runMin, quote) {
  const q = quote || EMPTY;
  if (typeof runMin !== "number" || !isFinite(runMin) || runMin < 0) return null;
  if (q.hourRate == null) return null;
  return (runMin / 60) * q.hourRate;
}
