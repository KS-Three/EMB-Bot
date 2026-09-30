# The split comb is a property of the column (2026-09-30)

**Kent's pick** after the envelope's sibling rule: Becker's letters at 100 mm
sew 5–7 mm columns straddling `SPLIT_SATIN_ABOVE_MM` (5.0), and per-leg
splitting flickered: 4,222 satin legs, 1,078 split, 122 on/off changes
(letters 1,412 legs, 73% split, 59 changes, 443 legs within ±0.5 mm of
the threshold). Per LEG: a cross and its return leg split on their own
length — the earlier "75 transitions" figure was this per-leg count on the
symmetric rails.

**Rules simulated (add-only; no leg may sew over the threshold)**: majority
of 5 neighbours 122 → 85; per-run median 103; hysteresis 35 (+402 legs).
**Shipped** `stage6_satin._comb_thresholds`: a pre-pass over the kept legs
(same skip logic as the emit loop: thin, in_bean, coincident); once a leg
> ABOVE turns the comb on it stays on while legs ≥ SPLIT_SEGMENT_MM (3.0),
both directions; each leg gets its own threshold (SEG inside the comb,
ABOVE outside); over-threshold legs keep k = ceil(len/SEG) so output is
identical for them; inf never turns it on. Seam hops between joined members
stay per leg. Measured: Becker 122 → 37 (letters 59 → 26), 8,932 → 9,333
stitches; tires 21 → 5 (+189 st), bridge 20 → 5 (+90), screenshot 8 → 3
(+40); golden_tee/enthusiast/fremont/gaulke byte-identical. Tests: the
helper on a straddling sequence; a 4.6→5.4 mm tapered bar (flickers with
the rule neutered by monkeypatch, one comb with it, rails identical).

**The pro's own Becker files comb nothing**: 5 reference DSTs, 24,108 satin
legs (study_pro.classify columns), split 1–2% up to 5.5 mm, 8% at 5.5–6,
17% at 6–7, 32% at 7–9, 78% > 9; 40 splitting columns all mixed, 734
changes. Raw-to-7 arm on our engine: 8 changes, 8,292 st (raw-to-6: 18,
8,715). Raising the threshold = a house style + a float question → sew-out
(gate 1), Kent's ruling.

**Trap**: the thread renderer barely shows mid-column penetrations — the
eye page cannot judge a comb. The strips carry a penetration-dot map under
each render (`docs/renders/split-comb-2026-09-30/`).
