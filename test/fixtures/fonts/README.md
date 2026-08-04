# Test-fixture fonts — NOT shipped

These font JSONs are TEST FIXTURES ONLY. They were pulled from the shipping
library (manifest/bin/previews) in the 2026-08-04 ShareAlike removal
(font-license audit §9) but remain here because large parts of the engine
and app test suites use them as their measured reference fonts, and
re-deriving dozens of pinned geometric assertions against a different font
would trade real regression coverage for license tidiness the tests don't
need: repo-internal fixture use with the full license text alongside is
ordinary CC-BY-SA-compliant reuse — the open ShareAlike question (see
docs/lawyer-brief-cc-by-sa-2026-08-04.md) is about DISTRIBUTING compiled
binaries to customers, which these files no longer are.

Do not add these back to src/fonts/ — that directory is shipped-only, and
test/embf-guard.test.js's shipped-font invariants depend on that meaning.
