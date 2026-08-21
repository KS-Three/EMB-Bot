# External font hunt — everything outside upstream, 2026-08-21

**Question:** are there free, commercially-sellable Ink/Stitch lettering fonts —
**any stitch type** — anywhere outside `inkstitch/embroidery-fonts`?

**Answer: effectively no. Ink/Stitch is a monoculture.** Two genuinely new fonts
exist in the entire searchable world. One is a 5-glyph abandoned demo. The other
(`Terminus`) is importable but needs three decisions, all Kent's (§2).

Method: 20 agents across 9 blind search angles (forks, GitHub-wide code search,
community repos, non-GitHub forges, issue/PR surfaces, the open web + Wayback,
adjacent tools, non-Latin communities, non-satin communities), then adversarial
per-candidate verification requiring a real clone and a verbatim license quote.
59 raw leads → 32 unique non-upstream → 12 verified.

Companion to `docs/font-expansion-research-2026-08-21.md` (the *upstream* sweep,
which is where all 15 fonts actually added on 2026-08-21 came from).

## 1. The census that settles it

`horiz_adv_x_space` is a key present in essentially every Ink/Stitch `font.json`
and almost nothing else on earth. Across **all of GitHub** it returns **16
files**. Eleven are upstream, Ink/Stitch tooling, or EMB-Bot itself. The
non-upstream remainder is **exactly four `font.json` files** — three in
`UncleJey/inkstitchFonts`, one in `Godan/japanese-fonts-for-stitch`.

Five independent fingerprints (`satin_column`, `fill_method`,
`cross_stitch_method`, `bean_stitch_repeats`, `horiz_adv_x_space`) converge on
the same tiny repo set. That is what "monoculture" means here, measured rather
than asserted.

**Independent non-satin Ink/Stitch lettering fonts: zero.** Searching
`inkstitch:cross_stitch_method` GitHub-wide returns 9 files, all upstream.
Applique and motif: same. `bean_stitch_repeats` outside upstream returns exactly
one font, which is upstream's own `nick_ainley` redistributed.

## 2. `Terminus` — the one real candidate

`github.com/inkstitch/inkstitch` PR **#2034** (bkmgit), **closed unmerged**
2024-04-17, path `fonts/inkstitch_terminus_ttf/`. Verified here by direct fetch,
build and QC — not taken on an agent's word:

| | |
|---|---|
| License | **OFL-1.1**, Benson Muite adaptation; original from `files.ax86.net/terminus-ttf` — a real primary source, not an aggregator listing |
| Glyphs | 100 — full A–Z, a–z, 0–9 |
| Satin | 146 columns, genuine hand-authored |
| Stitches | **736** at a 40 mm target — it works |
| Gap filled | the 142 contain **no monospace face at all** |

**Three decisions before it could ship, all Kent's:**

1. **It carries a Reserved Font Name.** The LICENSE declares
   `Reserved Font Name "Terminus Font"`, and `font.json` currently reads
   `"Ink/Stitch Terminus TTF"` — which still contains the reserved word. OFL §3
   requires a rename for a Modified Version, exactly as upstream did for
   Sortefax→Initials and Shojumaru→Manga Impact.
2. **QC fails it as-is**: `missing/invalid sizeMm` (its `font.json` has no
   `size` key at all, so nothing tells us how large it is meant to sew — a
   physical property, so ROADMAP gate 1 bars us from inventing one), plus
   1/52 letter glyphs stitching as nothing.
3. **Upstream declined it on QUALITY, not licence.** The maintainer called the
   potrace-derived outlines "somewhat ugly," and Terminus TTF published a better
   trace in April 2023 that the PR never picked up. Shipping a font the source
   project rejected is a judgement call. Re-tracing from the current upstream
   TTF would likely beat the PR geometry.

## 3. `m_plus_stitch` — confirmed real, not viable

`github.com/Godan/japanese-fonts-for-stitch`, `custom_fonts/m_plus_stitch/`.
Verbatim 93-line **OFL-1.1** from the M+ FONTS Project, no Reserved Font Name,
60 real `inkstitch:satin_column` attributes, valid `font.json`. Genuinely new —
no hiragana anywhere upstream.

**But it is 5 glyphs, not 10.** The small kana ぁぃぅぇぉ are scaled duplicates of
あいうえお — identical satin path counts and identical per-path subpath structure.
Five hiragana out of ~46, no katakana, no kanji, no Latin. **You cannot set a
single Japanese word with it.** One commit, 2024-07-26; its README promised full
hiragana "within August" and nothing followed.

**Provenance flag if it is ever revisited:** the repo also ships
`ipaex-gothic.sfd` under the **IPA Font License** (not on our approved list),
containing exactly the same 10 codepoints, and the stitch SVG's
`sodipodi:docname` is `IPAexGothic.svg`. The exculpatory reading is stronger —
the 4.6 MB `mplus_stroke.svg` is a purpose-built M+ centerline extraction, which
is what you trace satin rails from, while the IPA `.sfd` has no centerlines — but
that is inference, not an author statement. **Never vendor `ipaex-gothic.sfd`.**

Verdict: log as confirmed-real, non-viable. Do not re-mine.

## 4. Near-misses — do not re-mine these either

**Right format, wrong licence:**

- **`makeitlabs/makeit-inkstitch-font`** — the best-engineered non-upstream font
  in existence (90 glyphs, full Latin + umlauts, 208 satin columns, three
  underlay types, populated kerning). **Zero licence files**, verified four ways.
  Also a corporate logo mark whose own `font.json` admits derivation from Arial
  Rounded MT (Monotype, proprietary). Untouchable twice over.
- **`UncleJey/inkstitchFonts`** — 3 fonts, and Cyrillic is a real gap for us.
  All three fail: `Cirilic_old` (151 glyphs, 656 satin columns — the largest
  non-upstream font anywhere) states its base typeface is «распространяемый без
  лицензии», *distributed without a licence*; `Colleege` is a DaFont freeware
  blurb; `NickAlery` is upstream's `nick_ainley`, which upstream declares
  CC-BY-SA (banned).
- **lowtechlinux.com "Colleege"** — real font, 179 satin columns, 36 glyphs.
  Its LICENSE.txt in full: *"Based on freeware font 'College Slab' available at
  DaFont.com."* No grant from the adapter on his own derivative either.

**Right licence, wrong format:**

- **`derdanielmoin/inkstich-fonts-addons`** — genuine OFL-1.1, but legacy
  `embroider_*` attributes and no `font.json`. Moot anyway: upstream already
  ships `pacificlo`/`pacificlo_tiny` from the same Pacifico face with 120 glyphs.
- **EduTech Wiki Hershey typefaces** — the only real bean/fill lettering data
  found outside upstream. Fails twice: legacy `embroider_*` namespace with no
  GlyphLayers or `font.json`, and the wiki default is **CC BY-NC-SA 3.0** — NC
  and SA both banned.

## 5. The one lead worth a decision: Hershey vector fonts

`techninja/hersheytextjs` — 23 faces including **Cyrillic, Greek, Japanese and
blackletter**. Glyph data declared **public domain**, MIT wrapper; each glyph is
already a path plus an advance width.

This is the only unblocked route to Cyrillic/Greek/Japanese coverage anywhere,
and Hershey faces are single-stroke, which is precisely what the run/bean
lettering path added on 2026-08-21 stitches.

**But it collides with ROADMAP gate 1, and that is not a detail.** Hershey data
carries geometry and nothing else — no `running_stitch_length_mm`, no bean
repeats, because it was never embroidery data. The whole design of the run
lettering path is that a run stitches *only* when the font's own author supplied
a length. Importing Hershey means choosing a stitch length for 23 faces with no
digitizer's judgement behind it, on fabric no one has tested. That is exactly
the physical constant the gate exists to refuse.

Not a blocker to record; a decision to put to Kent explicitly. Options are to
take a sew-out and set the constant with evidence, or leave Hershey alone.

## 6. Searched and empty — do not repeat this sweep

- **Forks:** all 6 forks of `embroidery-fonts` enumerated. Three are pinned to
  upstream SHA `6f83b54d` with zero divergence. **`dgswilkins`' 16 "new"
  directories are a trap** — they are *pre-rename* spellings of fonts already in
  the 142, proven by matching `original_font` fields (`lobster_AGS`↔`stebor_AGS`,
  `sortefaxXL`↔`initials_XL`, `espresso_*`↔`caffeine_*`, `baumans_FI`↔
  `bathaus_FI`, `namskout_*`↔`kum_tsoan_*`, `abril`↔`mai_en_fleur`). This
  matches the independent finding in the upstream sweep's history dig.
- **PR/issue surface — enumerated, not sampled.** All 73 PR refs in
  `embroidery-fonts` and all **1591** in `inkstitch/inkstitch` fetched and
  diffed against merge-base. 131 distinct `fonts/` directory names; subtracting
  everything that ever existed in main history leaves 7 → 2 path artifacts, 2
  pre-rename spellings, 2 that re-landed as `violin_serif`/`chicken_scratch`
  (PR #2531 → #2703, a textbook false positive disproved by glyph-set diff), and
  1 = Terminus.
- **Non-GitHub forges:** GitLab.com, framagit, Codeberg, SourceHut, Bitbucket,
  SourceForge, ~30 Gitea/Forgejo instances, ~16 self-hosted GitLabs, Gitee — all
  empty.
- **BX/PES/DST font shops** — pre-stitched binaries, not vector sources, and
  mostly personal-use-only. Structurally unusable, not merely unlicensed.

## 7. Conclusion

The library grew 55 → 70 on 2026-08-21, and **every one of those 15 fonts came
from a repository we already had**. They were unlocked by fixing a NonCommercial
licence-detection hole and a satin-only lettering path — not by finding anything
new on the internet.

There is no external supply. Growth from here comes from the levers in
`docs/font-expansion-research-2026-08-21.md` §8 — chiefly the fill/cross-stitch
lettering path (17 more fonts already licensed and on disk) — or from
commissioning new digitizing.
