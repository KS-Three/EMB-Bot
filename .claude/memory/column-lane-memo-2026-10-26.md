---
name: column-lane-memo-2026-10-26
description: The Column lane rebuilt identical columns and rail pairings; a per-letter memo (`outline_cut._MEMO`) on exact keys cut stages 5-7 CPU 12% over 7 jobs (MFab hat -20%), all DSTs byte-identical
metadata:
  type: project
---

2026-10-26, follows [[digitize-speed-2026-10-26]], which put the MFab hat's
Column lane at 67 s of 141 s. On one MFab hat digitize: 779 of 2,825
`build_column` calls repeated an identical earlier call, and 941 of 1,413
`pair_rails` calls did (different pieces pair the same two rails). Counted by
`speed_dups2.py` in task 19's scratchpad, keyed exactly.

**Built:** `_MEMO` is a context variable holding one dict per letter, set in
`_letter_columns` and None elsewhere. `build_column` and `pair_rails` are
computed once per exact key: shapely WKB, float64 bytes and the cut's five
context variables. Callers get fresh copies (`_fresh` keeps each field's
type). `tests/test_column_memo.py` cuts 6 letters x 6 flag sets with and
without the memo.

**Measured:** all 7 Column-lane jobs (MFab hat and LC, Becker large and small,
Fremont, ProSeal, Tires) are DST- and preflight-identical to main 320f3372.
Stages 5-7 CPU fell 12% overall, MFab hat -20% and ProSeal -18%. That was on a
loaded laptop, main and lane alternating per job, so read the pairs.

**Left:** `rails` / `scan_stations` / `straight_axis` repeats (456 / 1,116 /
978 before the memo). Count them again with the memo on before building a
second level; most may already be gone with their parent call.

**How to apply:** a Column-lane function is only memo-safe when every context
variable its call tree reads is in the key. `_APEX_CUT` changes mid-letter
(`apex_cut_scope`), so it must stay in the key.
