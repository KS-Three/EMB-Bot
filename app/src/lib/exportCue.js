// The tail of the Download step's "Saved ..." line: what the read-back said about
// the file(s) the customer just asked for (Kent 2026-11-05: every export is
// re-read, and a mismatch blocks the download -- so a save that DID happen was
// read back, unless the format has no reader).
//
// Honest by construction: "verified" is only ever said from a read-back result
// that says `verified: true`. A result that is missing (the service's headers
// were not readable) or says `verified: false` (SVG is a picture; a build
// without readback.js) is reported as "not re-read", never rounded up; a read
// that skipped checks (the service reader cannot give some back for XXX / VP3)
// says how many. A confirmation on the export the customer just asked for, not
// a quality readout: no warning styling, no new row
// (no-warnings-reaches-readouts, Kent 2026-10-02).

const plural = (k, one, many) => Number(k).toLocaleString("en-US") + " " + (k === 1 ? one : many);
const isVerified = (rb) => !!rb && rb.verified === true;
const skippedOf = (rb) => (isVerified(rb) && Array.isArray(rb.skipped) ? rb.skipped.length : 0);

// One file: " - re-read and verified: 2,459 stitches, 2 colour changes" or
// " - not re-read (<why>)". `readback` is the export result's `readback`.
export function singleCue(readback) {
  if (isVerified(readback)) {
    const facts = [];
    if (Number.isFinite(readback.stitches)) facts.push(plural(readback.stitches, "stitch", "stitches"));
    if (Number.isFinite(readback.colors)) facts.push(plural(readback.colors, "colour change", "colour changes"));
    const skipped = skippedOf(readback);
    return " - re-read and verified" + (facts.length ? ": " + facts.join(", ") : "")
      + (skipped ? " (" + plural(skipped, "check", "checks") + " this format cannot give back skipped)" : "");
  }
  const why = readback && readback.reason ? " (" + readback.reason + ")" : "";
  return " - not re-read" + why;
}

// The archive: `items` is [{ format, readback }] for every stitch format in it.
// All fully verified -> " - 7 stitch files re-read and verified"; otherwise the
// count that were read, then the ones that were not (or only partly), by name.
export function zipCue(items) {
  const list = items || [];
  if (!list.length) return "";
  const read = list.filter((i) => isVerified(i.readback));
  const partly = read.filter((i) => skippedOf(i.readback));
  const none = list.filter((i) => !isVerified(i.readback));
  if (read.length === list.length && !partly.length) return " - " + list.length + " stitch files re-read and verified";
  const notes = [];
  if (none.length) notes.push(none.map((i) => i.format.toUpperCase()).join(", ") + " not re-read");
  if (partly.length) notes.push(partly.map((i) => i.format.toUpperCase()).join(", ") + " with some checks skipped");
  return " - " + read.length + " of " + list.length + " stitch files re-read and verified (" + notes.join("; ") + ")";
}
