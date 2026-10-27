# `cutEveryJump` on typed lettering, OFF beside ON (2026-10-27)

"Fritsch's Stitches" at 50 mm on `hat_front` (a cap: glyphs sew centre-out),
three library fonts, drawn from each DST's own records by
`node tools/lettering-uncut-jumps.mjs --fonts medium_font,jersey_15,mai_en_fleur
--texts "Fritsch's Stitches" --sizes 50 --garments hat_front --renders <dir>`.
Not sewn. The flag is built OFF; Kent's ruling 2026-10-26 puts it on sew-out
card v8 as an OFF-beside-ON arm with the Python lane's `cut_every_jump`.

- Thread is dark; a move with the needle up is light grey.
- **OFF (left)**: every uncut move (one or two jump records, a float no
  machine cuts) is a thick red line.
- **ON (right)**: every cut the flag added is a blue ring; every hop it sewed
  needle-down instead (buried under later thread, or walked on sewn thread) is
  a thick green line. ON leaves no red: 0 uncut moves in each file.

| font | OFF uncut | OFF trims | ON buried | ON walked | ON cut | ON trims |
|---|---|---|---|---|---|---|
| medium_font (the Studio's default) | 3 | 15 | 0 | 0 | 3 | 18 |
| jersey_15 | 60 | 16 | 2 | 3 | 55 | 71 |
| mai_en_fleur | 307 | 34 | 0 | 0 | 307 | 341 |

Most hops lie between letters or between a letter's parts on bare cloth, so
they are cut; each cut costs a lock either side (8 stitches). mai_en_fleur's
307 are inside its letters (304 of them): at 50 mm its glyphs come apart
into many short pieces joined by needle-down travel (772 travel spans to 47
satin). 66 of its hops lie on that travel thread, but travel is not cover
(as in the Python pass: a connector may itself lie on bare cloth), so every
one is cut. How the font comes apart at this size is a question of its own.
