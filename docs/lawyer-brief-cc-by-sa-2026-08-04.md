# Brief for counsel — CC-BY-SA and compiled embroidery font binaries

**Prepared:** 2026-08-04, ready to send as-is. Source: §5 of the internal font
license audit (`docs/font-license-audit-2026-07-31.md`), updated to the
library's current post-remediation state. Booking the consult is the one step
only the owner can take (audit checklist item 11).

---

## Who we are and what the product does

EMB-Bot is a web application that generates machine-embroidery stitch files.
Customers type text; the app renders it using a library of **68 embroidery
fonts** adapted from the open-source Ink/Stitch embroidery font collection
(github.com/inkstitch/embroidery-fonts) and lets the customer download
industry-standard stitch files (DST/PES/EXP) to sew on their own machines.
First **paid** launch was gated on this question until 2026-08-04, when the ShareAlike fonts were removed (see Scope) — the consult is now optional background for a possible restore.

Each font ships as a compiled binary (our `.embf` format): satin-stitch path
coordinates mechanically derived from the Ink/Stitch vector sources —
quantized to a 0.25-unit grid, delta-encoded, packed as Int16. No creative
step occurs in the compilation; it is a lossy mechanical format conversion.

## Scope of the question

**RESOLVED BY REMOVAL 2026-08-04 — consult now OPTIONAL, kept as the restore path** (audit §9): all ShareAlike fonts were pulled from the library rather than gating launch on this question. Original scope: **13 of the then-68 fonts** under Creative Commons ShareAlike licenses:
11 × CC-BY-SA-4.0 and 2 × CC-BY-SA-2.5 (the two "Geneva" Hershey-derived
fonts). The rest of the library (51 OFL-1.1, 1 CC-BY-4.0, 2 CC0) is not part
of this question.

Attribution and notice duties are **already handled** and do not ride on your
answer: as of 2026-08-04 every font ships with its full upstream license text
(stand-alone file + embedded in the binary's metadata), a complete
author/copyright credit, and an explicit modification indication per
CC-BY-SA 4.0 §3(a)(1)(B).

## The question

Is a compiled `.embf` stitch-data binary — quantized, delta-encoded
satin-path coordinates mechanically derived from a CC-BY-SA-licensed vector
font — itself **"Adapted Material"** (CC-BY-SA 4.0 §1(a)) or a **"Derivative
Work"** (CC-BY-SA 2.5 §1(a)) that must be licensed BY-SA?

**The hinge:** 4.0 §1(a) defines Adapted Material as material modified "in a
manner requiring permission under the Copyright and Similar Rights held by
the Licensor." If the `.embf` compile takes only unprotectable elements,
ShareAlike never attaches. If it is a protected reproduction or adaptation,
§3(b) forces the whole binary under BY-SA.

## Sub-issues we want on the table

1. Does stitch-path data derived from the Ink/Stitch vector sources copy
   protectable font software/vector data, or only unprotectable letterform
   shapes? (US: typeface designs uncopyrightable — *Eltra Corp. v. Ringer*,
   37 CFR 202.1(e) — but digital font files are protected as data/programs —
   *Adobe v. Southern Software*. UK/DE protect typefaces as such.)
2. Is mechanical format conversion a mere reproduction (attribution duties
   only, license unchanged) or an adaptation (ShareAlike attaches)? Note
   4.0's format-shifting carve-out applies only to the technical-modification
   cases in §2(a)(4).
3. **The commercial exposure:** if `.embf` is BY-SA, do the DST/PES stitch
   files customers generate — and physical sew-outs — become further Adapted
   Material? Does BY-SA propagate onto customer deliverables?
4. How does the answer vary by jurisdiction, given web distribution?

## What rides on the answer (and what doesn't)

Either way — reproduction or adaptation — distribution already triggered the
attribution and notice duties, and those are shipped. Only two things ride on
your answer:

- the license **labeling** of the 13 `.embf` binaries if restored (relabel BY-SA or not);
- whether a **customer-facing note** about downstream stitch files is needed.

Worst case as we understood it: relabel the binaries BY-SA and add a customer
note — or pull the fonts from the library. The pull has since been taken
preemptively (audit §9); we would like your view on whether restoring the 13
fonts requires either of the other steps.

## One adjacent fact worth knowing

The credits screen offers each font's raw `.embf` binary for direct download.
Every binary embeds the complete upstream license text and copyright notice
in a machine-readable metadata field (the OFL explicitly blesses this
delivery channel; for CC it accompanies the URI + full text). If that
delivery mechanism changes your analysis for the CC-BY-SA fonts, flag it.
