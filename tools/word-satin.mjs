// Render a WORD from a pre-digitized font library to validate layout+kerning.
// Usage: TEXT="GENEVA" FONT=src/fonts/geneva_simple.json node tools/word-satin.mjs out.png
import fs from "node:fs";
import { createRequire } from "module";
import { encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
global.window = global;
const SF = require("../src/satinfont.js");

const TEXT = process.env.TEXT || "GENEVA";
const FONT = process.env.FONT || "src/fonts/geneva_simple.json";
const EMMM = +(process.env.EMMM || 18);
const OUT = process.argv[2] || "scratch_word.png";
const font = JSON.parse(fs.readFileSync(FONT, "utf8"));

const { runs, bbox } = SF.layoutText(font, TEXT, { emMm: EMMM, pxPerMm: 10, spacingMm: 0.4, pullCompMm: 0.2 });
const travels = [];

const pad = 24, sc = 1;
const W = Math.ceil((bbox.x1 - bbox.x0) * sc) + pad * 2, H = Math.ceil((bbox.y1 - bbox.y0) * sc) + pad * 2;
const px = new Uint8ClampedArray(W * H * 4); for (let i = 0; i < px.length; i += 4) { px[i] = px[i + 1] = px[i + 2] = 255; px[i + 3] = 255; }
const TX = (x) => pad + (x - bbox.x0) * sc, TY = (y) => pad + (y - bbox.y0) * sc;
function set(x, y, r, g, b) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; }
function line(x0, y0, x1, y1, r, g, b) { x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx - dy; for (; ;) { set(x0, y0, r, g, b); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 > -dy) { e -= dy; x0 += sx; } if (e2 < dx) { e += dx; y0 += sy; } } }
// underlay (green) then satin (blue)
for (const run of runs) { if (run.kind !== "underlay") continue; const p = run.pts; for (let k = 0; k + 1 < p.length; k++) line(TX(p[k].x), TY(p[k].y), TX(p[k + 1].x), TY(p[k + 1].y), 30, 170, 30); }
for (const run of runs) { if (run.kind !== "satin") continue; const p = run.pts; for (let k = 0; k + 1 < p.length; k += 2) { const a = p[k], b = p[k + 1]; line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 20, 80, 210); } }
fs.writeFileSync(OUT, encodePNG(W, H, px));
console.log(JSON.stringify({ text: TEXT, runs: runs.length, satin: runs.filter((r) => r.kind === "satin").length, widthMm: +((bbox.x1 - bbox.x0) / 10).toFixed(1), heightMm: +((bbox.y1 - bbox.y0) / 10).toFixed(1), out: OUT }));
