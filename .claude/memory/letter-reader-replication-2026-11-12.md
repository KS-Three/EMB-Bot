---
name: letter-reader-replication-2026-11-12
description: Letter-fault reader replication 11-12/13: pre-registered (frozen #1389 reader, digest b5211fb9); Kent sat the 9-logo kit `defect-marks-1112` 11-13: frozen rule selects letter pins on 2 items (needs 5) = no verdict; not replicated, not refuted
metadata:
  type: project
---

Follows [[letter-fault-reader-2026-11-11]] and [[defect-marks-sitting-2-2026-11-11]].

**Pre-registration first** (`docs/defect-marks-2026-11-12/letter-reader-replication-preregistration.md`,
own commit): reader frozen as merged in `79fa7646` (detection AST digest
`b5211fb9…`, pinned by `tests/test_letter_reader_replication.py`), pin rule
unchanged, 3 mm, `chance_area` null, pass line = at least 5 items with pins
AND item-bootstrap lower bound > 0 both with all pins and with rule-4 (bare,
inherited) pins dropped; LOO decides fragile vs robust. Candidate-pick null
not available: this reader writes no candidate set.

**Held-out data:** none usable. 11-10 is the fit set; 11-11 gives 30 pins on
one item. Power of a new sitting (simulated from the 6 fit items): 9 items
with pins -> P(shown) 0.76 at the first effect, 0.43 at half, false 0.04.

**Prepared:** the nine `testdata/art/commons_lettering/` logos (public
domain, never pinned; Kent saw them as pairs 11-02), 80 mm left chest, kit
`eye_pairs_out/defect-marks-1112` (launch.json port 8738), driver
`docs/defect-marks-2026-11-12/build_kit.py`, scorer `score_replication.py`.

**How to apply:** after Kent sits it, score from a checkout at the kit's tree
with `score_replication.py`; do not pool 11-10/11-11 pins into it, do not add
pins the rule does not select. Write-up: `docs/letter-reader-replication-2026-11-12.md`.

**Result (sat 2026-11-13, scored same day):** no verdict. 60 pins on 8 items
(1 "Nothing wrong"), but the closure rule selects 1 pin on each of 2 items
(`bukit_asam` hit 1/1, `n_sync` 0 flags, miss): chance-corrected +0.446,
CI95 [0.00, 0.81], under the 5-item floor. The pre-registration expected
about 5 of 9 items to carry letter pins; 2 did. His pins on lettering are
about flat/straight edges, smooth curves, baseline alignment and stitch-type
changes, not closure. Record: `docs/defect-marks-2026-11-12/SITTING.md`
(marks sha256 `12e74bff…`, byte copy of his file).

**Why it matters:** a closure-only reader will keep hitting the item floor on
logos at 80 mm; another sitting of the same kind is unlikely to decide it.
