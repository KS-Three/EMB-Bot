// Generate a flat spot-color test logo (transparent bg) to validate digitizing.
import fs from "node:fs";
import { encodePNG } from "./png.mjs";
const W = 512, H = 512;
const px = new Uint8ClampedArray(W * H * 4); // all zero => transparent
const set = (x, y, c) => { if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2]; px[o + 3] = 255; };
const NAVY = [22, 42, 92], RED = [198, 32, 46], WHITE = [245, 245, 245], GOLD = [225, 170, 30];
const cx = 256, cy = 236;
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
  const dx = x - cx, dy = y - cy, r = Math.hypot(dx, dy);
  if (r <= 190) set(x, y, RED);            // broad disc -> fill
  if (r <= 216 && r >= 194) set(x, y, NAVY); // thin ring -> satin
}
// white bold chevron (two thick triangles) in center -> fill
function tri(ax, ay, bx, by, cx2, cy2, col) {
  const minx = Math.min(ax, bx, cx2), maxx = Math.max(ax, bx, cx2), miny = Math.min(ay, by, cy2), maxy = Math.max(ay, by, cy2);
  const sign = (px1, py1, px2, py2, px3, py3) => (px1 - px3) * (py2 - py3) - (px2 - px3) * (py1 - py3);
  for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
    const d1 = sign(x, y, ax, ay, bx, by), d2 = sign(x, y, bx, by, cx2, cy2), d3 = sign(x, y, cx2, cy2, ax, ay);
    const neg = d1 < 0 || d2 < 0 || d3 < 0, pos = d1 > 0 || d2 > 0 || d3 > 0;
    if (!(neg && pos)) set(x, y, col);
  }
}
tri(200, 170, 256, 300, 256, 190, WHITE);
tri(312, 170, 256, 300, 256, 190, WHITE);
// gold horizontal bar near bottom -> thin+wide -> satin
for (let y = 300; y <= 322; y++) for (let x = 130; x <= 382; x++) set(x, y, GOLD);
fs.writeFileSync("scratch_flat.png", encodePNG(W, H, px));
console.log("wrote scratch_flat.png " + W + "x" + H);
