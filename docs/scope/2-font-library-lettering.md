# Area 2 — Font library & lettering

**Part of [`MASTER_SCOPE.md`](../../MASTER_SCOPE.md)** — this is the detail
for one capability area. The live one-line verdict (Status / Confidence /
what is next) is in MASTER_SCOPE; this file is the supporting record.

**Claim discipline:** a claim here should carry a `(verb date — source)`
pointer — `confirmed` = checked against code or a passing test, `measured` =
a number was produced, `suspected` = neither. Much of this file predates that
rule and is **not yet annotated**; anything unannotated is unverified until
someone checks it. Test counts, stitch counts and corpus grades written here
were snapshots when written — do not quote one as a current baseline.
Dated narrative belongs in [`../scope-history.md`](../scope-history.md).

---

The 55-font pre-digitized satin library, browser UI, EMBF binary format, the
add-font QC/tier pipeline, and Text mode. Expandable — but every addition is
gated by the license rule below (Kent: don't risk copyright infringement if
this ever sells).

**Status:** Implemented (library/UI/format itself) — license remediation
**resolved 2026-08-04** (audit items 1–10 + 12, plus items 1–3's pulls
followed by the full 13-font ShareAlike removal, PR #16; see the
cross-cutting item above). The item-11 lawyer consult is no longer a
launch gate — it's an optional restore path now.

**Confidence:**
- Library/tech: **High.** `src/fontbin.js` (EMBF codec), `manifest.json` +
  55 `.embf` files (72 → 68 after the audit pulls → 55 after the 2026-08-04
  ShareAlike removal), lazy loading,
  `FontBrowser.svelte`/credits UI, and the QC/tier pipeline
  (`tools/qc-font.mjs`, `tools/build-embf.mjs`, `tools/font-license.mjs`,
  `tools/patch-embf-licenses.mjs`) all exist and pass the engine suite.
- License compliance: **High — the open legal question was resolved by
  removal (Kent's call, 2026-08-04).** All 13 ShareAlike fonts pulled
  (audit §9); the remaining 55 are 52 OFL-1.1 + 1 CC-BY-4.0 + 2 CC0, zero
  ShareAlike. Full license texts ship three ways (sidecar file, served
  `/fonts/<key>.LICENSE.txt`, embedded in each binary), attributions are
  complete notices, guard tests pin it. The item-11 lawyer consult is now
  OPTIONAL — kept as the restore path for the 13
  (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`), no longer launch-gating.

**Open issues:** the item-11 consult is optional now, not blocking (above).
`EMB-Bot-standalone.html` (which embedded a pre-audit inlined font registry)
is **deleted, 2026-08-04, Kent's call** — the live `satin-fonts.js` residual
was already closed the same day (audit §10), so no pre-audit font list
ships anywhere now. On
the tech side: the font-editing round deferred condensed/expanded width and
mixed per-letter size (both risk uneven satin distortion) — minor, not
blocking.

**Next step:** font-library expansion is unblocked — the license gate is
resolved by removal (PR #16 + #17, both merged), and the add-font skill's
compliance note is backed by guard tests. Booking the lawyer consult (send
`docs/lawyer-brief-cc-by-sa-2026-08-04.md` as-is) is now purely optional,
Kent's call, only relevant if he wants the 13 pulled ShareAlike fonts back.
