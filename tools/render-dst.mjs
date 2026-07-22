// Decode a Tajima .DST and rasterize it to a PNG so we can SEE the stitch-out.
// Usage: node tools/render-dst.mjs <in.dst> <out.png> [scale]
import fs from "node:fs";
import zlib from "node:zlib";

const [, , inPath, outPath, scaleArg, colorsPath] = process.argv;
const scale = scaleArg ? parseFloat(scaleArg) : 6; // px per mm
const buf = fs.readFileSync(inPath);
// optional sidecar: JSON array of [r,g,b] per color block, for realistic thread colors
let THREAD = null;
if (colorsPath && fs.existsSync(colorsPath)) {
  try { THREAD = JSON.parse(fs.readFileSync(colorsPath, "utf8")); } catch (e) { THREAD = null; }
}

// --- header is 512 bytes ASCII ---
const header = buf.slice(0, 512).toString("latin1");
const stitchData = buf.slice(512);

// --- decode 3-byte records ---
function decodeDelta(b0, b1, b2) {
  let x = 0, y = 0;
  if (b0 & 0x80) x += 1;
  if (b0 & 0x40) x -= 1;
  if (b0 & 0x20) x += 9;
  if (b0 & 0x10) x -= 9;
  if (b0 & 0x08) y -= 9;
  if (b0 & 0x04) y += 9;
  if (b0 & 0x02) y -= 1;
  if (b0 & 0x01) y += 1;
  if (b1 & 0x80) x += 3;
  if (b1 & 0x40) x -= 3;
  if (b1 & 0x20) x += 27;
  if (b1 & 0x10) x -= 27;
  if (b1 & 0x08) y -= 27;
  if (b1 & 0x04) y += 27;
  if (b1 & 0x02) y -= 3;
  if (b1 & 0x01) y += 3;
  if (b2 & 0x20) x += 81;
  if (b2 & 0x10) x -= 81;
  if (b2 & 0x08) y -= 81;
  if (b2 & 0x04) y += 81;
  return [x, y];
}

const PAL = [
  [220, 40, 40], [40, 120, 220], [40, 170, 80], [230, 160, 30], [150, 60, 200],
  [30, 190, 190], [230, 90, 160], [120, 120, 120], [180, 140, 60], [90, 200, 40],
  [200, 60, 90], [60, 90, 200], [200, 200, 40], [40, 200, 140], [160, 60, 40],
  [100, 60, 160], [60, 160, 200], [200, 120, 200], [140, 180, 60], [80, 80, 80],
  [210, 100, 40], [40, 140, 120],
];

let x = 0, y = 0, colorIdx = 0;
const segs = []; // {x0,y0,x1,y1,jump,color}
let stitches = 0, jumps = 0, colors = 0, prevWasMove = false;
for (let i = 0; i + 2 < stitchData.length; i += 3) {
  const b0 = stitchData[i], b1 = stitchData[i + 1], b2 = stitchData[i + 2];
  if (b0 === 0 && b1 === 0 && b2 === 0xf3) break; // end
  const isJump = (b2 & 0x80) !== 0;
  const isColor = (b2 & 0x40) !== 0;
  const [dx, dy] = decodeDelta(b0, b1, b2);
  const nx = x + dx, ny = y + dy;
  if (isColor) { colorIdx++; colors++; x = nx; y = ny; continue; }
  if (isJump) { jumps++; segs.push({ x0: x, y0: y, x1: nx, y1: ny, jump: true, color: colorIdx }); }
  else { stitches++; segs.push({ x0: x, y0: y, x1: nx, y1: ny, jump: false, color: colorIdx }); }
  x = nx; y = ny;
}

// bounds (units = 0.1mm)
let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
for (const s of segs) { minX = Math.min(minX, s.x0, s.x1); maxX = Math.max(maxX, s.x0, s.x1); minY = Math.min(minY, s.y0, s.y1); maxY = Math.max(maxY, s.y0, s.y1); }
const wMM = (maxX - minX) / 10, hMM = (maxY - minY) / 10;
const pad = 10;
const W = Math.ceil(wMM * scale) + pad * 2;
const H = Math.ceil(hMM * scale) + pad * 2;

// RGBA canvas, white bg
const px = Buffer.alloc(W * H * 4, 255);
function setPx(ix, iy, r, g, b) {
  if (ix < 0 || iy < 0 || ix >= W || iy >= H) return;
  const o = (iy * W + ix) * 4;
  px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255;
}
function line(x0, y0, x1, y1, r, g, b) {
  x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;
  for (;;) {
    setPx(x0, y0, r, g, b);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x0 += sx; }
    if (e2 < dx) { err += dx; y0 += sy; }
  }
}
function tx(ux) { return pad + (ux - minX) / 10 * scale; }
function ty(uy) { return pad + (maxY - uy) / 10 * scale; } // flip Y

for (const s of segs) {
  if (s.jump) continue; // don't draw travel jumps
  const c = (THREAD && THREAD[s.color]) ? THREAD[s.color] : PAL[s.color % PAL.length];
  line(tx(s.x0), ty(s.y0), tx(s.x1), ty(s.y1), c[0], c[1], c[2]);
}

// --- minimal PNG encoder (zlib) ---
function png(width, height, rgba) {
  const raw = Buffer.alloc(height * (1 + width * 4));
  for (let yy = 0; yy < height; yy++) {
    raw[yy * (1 + width * 4)] = 0; // filter none
    rgba.copy(raw, yy * (1 + width * 4) + 1, yy * width * 4, (yy + 1) * width * 4);
  }
  const idat = zlib.deflateSync(raw, { level: 9 });
  function chunk(type, data) {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
    const t = Buffer.from(type, "latin1");
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([t, data])) >>> 0, 0);
    return Buffer.concat([len, t, data, crc]);
  }
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([sig, chunk("IHDR", ihdr), chunk("IDAT", idat), chunk("IEND", Buffer.alloc(0))]);
}
const CRC = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crc32(b) { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

fs.writeFileSync(outPath, png(W, H, px));
console.log(JSON.stringify({
  headerLine: header.slice(0, 90).replace(/\s+/g, " ").trim(),
  stitches, jumps, colorChanges: colors, colorBlocks: colorIdx + 1,
  sizeMM: [+wMM.toFixed(1), +hMM.toFixed(1)], imagePx: [W, H], out: outPath,
}));
