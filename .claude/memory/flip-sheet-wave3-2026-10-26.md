---
name: flip-sheet-wave3-2026-10-26
description: Flip sheet wave 3 -- twelve flags built OFF since 10-24 rendered OFF|ON|pro, grouped by flag with a LAYOUT/FABRIC kind and st/tr/cc tables; cfg.extra rows; three flags read inert or near-inert at this engine
metadata:
  type: project
---

2026-10-26, follow-on to [[flip-sheet-wave2-2026-10-24]]. `tools/flip_sheet_renders.py`
gained a `kind` per FLAGS row (LAYOUT default, FABRIC on the four sew-out-card
flags), `sets: {"extra": {...}}` for `cfg.extra` keys (the service parser refuses
`extra`, so `config_extra` lays it on the parsed config for one digitize),
colour changes per cell, and a page grouped by flag with an OFF/ON/pro table.
Kinds agree with `tools/flag_ledger` (#1111) on every wave-3 flag; the ledger
also reads `cut_every_jump` and `sew_enclosed_white` as HELD, a kind the sheet
does not carry.

**Trap:** `import digitizer_service.app` returns the FastAPI OBJECT (the package
attribute shadows the submodule); use `importlib.import_module("digitizer_service.app")`
to patch `_parse_config`.

**Trap:** OFF cells are keyed by the HEAD sha AT EACH CELL, so merging main or
committing mid-run splits one sheet across engines. Rows added after a merge
run at the new sha (`absorb_fragments`, `small_text_bay_mouth` at a1aea825;
the rest ab06d3d7); the md's engine column says which.

Read at this engine (trims are pystitch TRIM records, OFF -> ON, pro):
- `keyline_fold_slivers` MFab hat 37 -> 25, LC 46 -> 24 (pro 19 / 20), on arm d2.
- `absorb_fragments` MFab hat 40 -> 26, LC 52 -> 34 (pro 19 / 20), on arm w1.
- `monoline_script_satin` **INERT on Tires**: byte-identical, the script word
  still sews fill (20 fill runs, 2 satin). Wave 2 read 10 -> 24 trims, so
  something since 10-24 changed what `monoline_stroke` matches. Look before
  Kent rules on it.
- `fill_section_travel` Fremont 28 -> 28 trims, travel runs 153 -> 153 (#1091
  read 51 -> 41 on its own base). `small_text_bay_mouth` 3 stitches on
  Fremont, and the census reads EST and 1895 as dropped in both arms.
- No change, as the PRs predicted: `outline_loop_mitre` on Bridge (line-art
  guard) and `fine_bars_satin` on MFab and Bridge.

**How to apply:** a row's OFF moves with main, so quote a flag's effect from
the sheet at a named engine, never from its PR's measurement; and when a row
reads byte-identical where its PR measured a change, report it as a finding
before the flip, not as "no visible difference".
