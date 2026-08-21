// Shared font-license text utilities — audit items 4, 8, 9 of
// docs/font-license-audit-2026-07-31.md.
//
// Used by BOTH tools/build-embf.mjs (future rebuilds from scratch_ink/) and
// tools/patch-embf-licenses.mjs (the in-place library fix for checkouts
// without scratch_ink/). Keeping the logic here means the two paths cannot
// drift: a rebuild and a patch produce the same attribution + licenseId for
// the same license text.
//
// History of the extraction defect this replaces (audit item 4): the old
// build took the FIRST LINE of the font's `license` blob as the attribution.
// Two separate bugs compounded:
//   1. Upstream LICENSE files mostly use bare-CR (old-Mac) line endings; the
//      original /\r?\n/ split never fired, so "first line" degenerated to
//      the whole blob truncated mid-word. (Fixed earlier with a
//      /\r\n|\r|\n/ split — that part of the audit's item-4 wording was
//      already done.)
//   2. Even with correct splitting, first-LINE extraction drops names that
//      sit on the next physical line — apex_simple_AGS's license reads
//      "…adapted for Ink/Stitch by \r Françoise Lapierre Baillet \r and is
//      licensed…", so the credit ended at "by". The fix is first-PARAGRAPH
//      extraction (join lines to the first blank line / separator), plus an
//      appended upstream copyright line when the paragraph lacks one — the
//      OFL requires the copyright notice to travel with every copy, and the
//      attribution string is the user-visible notice.

// license id from the font's license text. NOTE (dejavufont lesson, audit
// §7): this matches the ADAPTER's header claim before any license body
// further down the blob — a font whose header says "CC-BY-SA" over a
// non-CC body will be mislabeled. Fine for the shipped set (all 68 sidecars
// verified consistent 2026-08-04); do not trust it blindly on new fonts.
export function licenseId(text) {
  const t = String(text || "");
  if (/GNU General Public License|GPL/i.test(t)) return "GPL-3.0";
  if (/SIL Open Font License|OFL/i.test(t)) return "OFL-1.1";
  // NonCommercial / NoDerivatives Creative Commons variants, checked BEFORE
  // the plain CC-BY branches below. "CC-BY-NC-SA 4.0" does not match the
  // CC-BY-SA pattern (the NC sits between BY and SA), so it fell through to
  // bare CC-BY and returned "CC-BY-4.0" — an ALLOWED_LICENSES id — which
  // would let a NonCommercial font into a build meant to be sold. Found
  // 2026-08-21 on upstream PRs #75/#76/#77 (fornow, rigart, therese), all
  // labeled "CC-BY-NC-SA4 .0"; no shipped font is affected. NC is fatal to a
  // paid product and ND forbids the .embf adaptation outright, so both
  // return ids deliberately outside ALLOWED_LICENSES.
  const ccMods = /CC[- ]BY((?:[- ](?:NC|ND|SA)\b){1,3})/i.exec(t);
  const isNC = /\bNonCommercial\b/i.test(t) || (ccMods && /\bNC\b/i.test(ccMods[1]));
  const isND = /\bNoDerivat(?:ive|ion)s?\b|\bNoDerivs\b/i.test(t) ||
               (ccMods && /\bND\b/i.test(ccMods[1]));
  if (isNC || isND) {
    // tolerate the "4 .0" spacing seen in the upstream files
    const m = /CC[- ]BY(?:[- ](?:NC|ND|SA))+[^\d]{0,10}(\d)\s*\.\s*(\d)/i.exec(t);
    const ver = m ? m[1] + "." + m[2] : "4.0";
    const sa = ccMods && /\bSA\b/i.test(ccMods[1]) ? "SA-" : "";
    return "CC-BY-" + (isNC ? "NC-" : "") + (isND ? "ND-" : "") + sa + ver;
  }
  if (/CC[- ]BY[- ]SA/i.test(t)) {
    const m = /CC[- ]BY[- ]SA[^\d]{0,10}(\d\.\d)/i.exec(t);
    return "CC-BY-SA-" + (m ? m[1] : "4.0");
  }
  if (/CC[- ]BY/i.test(t)) {
    const m = /CC[- ]BY[^\d]{0,10}(\d\.\d)/i.exec(t);
    return "CC-BY-" + (m ? m[1] : "4.0");
  }
  if (/public domain|CC0/i.test(t)) return "CC0";
  return "SEE-LICENSE-FILE";
}

// Repair classic UTF-8-read-as-Latin-1 double encoding ("Marie-FranÃ§oise"
// → "Marie-Françoise"). Conservative: only rewrites when the text carries
// the unmistakable two-byte signature (Ã/Â followed by a continuation-range
// char) AND the repaired form round-trips to strictly fewer replacement
// chars. Clean text (including legitimate 'Ã' glyph names in kerning
// tables — real accented letters, NOT mojibake) passes through untouched
// because a lone Ã followed by a plain ASCII letter doesn't match.
export function fixMojibake(s) {
  const str = String(s || "");
  if (!/[ÂÃ][-¿]/.test(str)) return str;
  try {
    const bytes = Uint8Array.from([...str].map((c) => c.charCodeAt(0) & 0xff));
    const fixed = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return fixed;
  } catch {
    return str; // not actually double-encoded — leave it alone
  }
}

// Strip personal email addresses from a USER-FACING attribution string
// (audit item 9, auberge_marif: "strip personal email from user-facing
// credit; keep full notice in LICENSE file"). Applied generally: the full
// sidecar keeps every notice verbatim; the credit line doesn't need to
// republish anyone's inbox. Removes "(x@y.z)" parentheticals whole, then
// bare addresses.
export function stripEmails(s) {
  return String(s || "")
    .replace(/\(\s*[^()]*@[^()]*\)/g, "")
    .replace(/[\w.+-]+@[\w-]+(\.[\w-]+)+/g, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([,.;)])/g, "$1")
    .trim();
}

const SEPARATOR = /^[-=_*—–]{3,}\s*$/;
const BODY_HEADING = /^(SIL\s+)?OPEN FONT LICENSE\b|^Open Font License\s*$|^PREAMBLE\s*$|^License for\b|^original font license:/i;

// The user-visible attribution: first paragraph of the license text (the
// upstream convention is "This font X has been adapted for Ink/Stitch by Y
// and is licensed under …"), plus — when that paragraph carries no
// copyright notice of its own — the first upstream "Copyright …" line found
// in the rest of the blob, including any "with Reserved Font Name" line(s)
// glued to it. HTML entities are decoded, emails stripped, mojibake
// repaired. No truncation: the full sentence ships (manifest bytes are
// cheap; a cut-off legal notice is not).
export function extractAttribution(fullText) {
  const norm = fixMojibake(String(fullText || ""))
    .replace(/&quot;/g, '"').replace(/&amp;/g, "&")
    .replace(/\r\n|\r/g, "\n");
  const lines = norm.split("\n").map((l) => l.trim());

  // first paragraph: skip leading blank lines (several upstream files open
  // with one, which used to erase the whole adapter credit), then take lines
  // up to the first blank line, separator, or license-body heading
  let start = 0;
  while (start < lines.length && !lines[start]) start++;
  const para = [];
  for (let i = start; i < lines.length; i++) {
    const l = lines[i];
    if (!l || SEPARATOR.test(l) || BODY_HEADING.test(l)) break;
    para.push(l);
  }
  let attribution = para.join(" ").replace(/\s{2,}/g, " ").trim();
  const rest = lines.slice(start + para.length);

  // If the paragraph names no license, append the first sentence that does
  // (medium_font-style files open with a bare copyright line and put the
  // "licensed under the SIL Open Font License" sentence in the next
  // paragraph — the old extractor cut that sentence off at a colon).
  if (!/licens/i.test(attribution)) {
    const li = rest.findIndex((l) => /licens/i.test(l) && !BODY_HEADING.test(l));
    if (li >= 0) {
      const sentence = rest[li].split(/(?<=\.)\s+/).find((s) => /licens/i.test(s));
      if (sentence) attribution = (attribution ? attribution + " " : "") + sentence.trim();
    }
  }

  // Append the first upstream copyright notice if the paragraph lacks one.
  // The notice must look like a real one — "Copyright (c) …" / "Copyright
  // 2017 …" — so the OFL body's own wrapped "copyright statement(s)." line
  // and "Copyright and Licensing:" headings never qualify.
  if (!/copyright|\(c\)|©/i.test(attribution)) {
    const ci = rest.findIndex((l) => /^copyright\s*(\(c\)|©|\d{4})|^©\s/i.test(l));
    if (ci >= 0) {
      let notice = rest[ci];
      // a notice can wrap onto following "with Reserved Font Name …" lines
      for (let j = ci + 1; j < rest.length; j++) {
        if (/^with\s+Reserved\s+Font\s+Name/i.test(rest[j])) notice += " " + rest[j];
        else break;
      }
      attribution = (attribution ? attribution + " " : "") + notice.trim();
    }
  }

  // upstream cosmetic fix: "Bris,and is licensed" — missing space after comma
  return stripEmails(attribution).replace(/,(?=[A-Za-z])/g, ", ");
}

// Hand-maintained overrides for fonts whose license text cannot yield a
// correct credit mechanically (audit item 9's "hand-check" list). Keys are
// font keys; values replace the extracted attribution entirely. The full
// sidecar LICENSE.txt still ships verbatim alongside — these are only the
// user-visible credit lines.
export const ATTRIBUTION_OVERRIDES = {
  // Audit §2: "credit Schneider + ship required Hershey acknowledgement".
  // Schneider's name appears nowhere in the upstream LICENSE blob (only the
  // TECFA/EduTechWiki cite URL), so extraction can't produce it. The 1967
  // Hershey acknowledgement text itself ships in full in the sidecar
  // LICENSE.txt and the .embf-embedded license.
  geneva_simple:
    "Adapted for Ink/Stitch by Daniel K. Schneider (TECFA, University of Geneva); " +
    "based on the Hershey fonts originally created by Dr. A. V. Hershey while working " +
    "at the U.S. National Bureau of Standards. Licensed CC-BY-SA 2.5; see the license " +
    "file for the required Hershey acknowledgements.",
  geneva_rounded:
    "Adapted for Ink/Stitch by Daniel K. Schneider (TECFA, University of Geneva); " +
    "based on the Hershey fonts originally created by Dr. A. V. Hershey while working " +
    "at the U.S. National Bureau of Standards. Licensed CC-BY-SA 2.5; see the license " +
    "file for the required Hershey acknowledgements.",
};

// One call that does the whole job for a font: full text in, manifest
// fields out.
export function deriveLicenseFields(key, fullText) {
  return {
    licenseId: licenseId(fullText),
    attribution: ATTRIBUTION_OVERRIDES[key] || extractAttribution(fullText),
  };
}
