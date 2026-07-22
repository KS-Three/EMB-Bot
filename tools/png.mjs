// Minimal PNG decoder (8-bit, non-interlaced; color types 0/2/3/4/6) + box downscale.
import fs from "node:fs";
import zlib from "node:zlib";

export function decodePNG(path) {
  const buf = fs.readFileSync(path);
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  for (let i = 0; i < 8; i++) if (buf[i] !== sig[i]) throw new Error("not a PNG");
  let off = 8, width = 0, height = 0, bitDepth = 0, colorType = 0;
  const idat = [];
  let plte = null, trns = null;
  while (off < buf.length) {
    const len = buf.readUInt32BE(off); const type = buf.toString("latin1", off + 4, off + 8);
    const data = buf.slice(off + 8, off + 8 + len);
    if (type === "IHDR") {
      width = data.readUInt32BE(0); height = data.readUInt32BE(4);
      bitDepth = data[8]; colorType = data[9];
      if (data[12] !== 0) throw new Error("interlaced PNG not supported");
    } else if (type === "PLTE") plte = data;
    else if (type === "tRNS") trns = data;
    else if (type === "IDAT") idat.push(data);
    else if (type === "IEND") break;
    off += 12 + len;
  }
  if (bitDepth !== 8) throw new Error("only 8-bit PNG supported, got " + bitDepth);
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const channels = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[colorType];
  if (!channels) throw new Error("unsupported color type " + colorType);
  const bpp = channels;
  const stride = width * bpp;
  const cur = Buffer.alloc(height * stride);
  const paeth = (a, b, c) => { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); return pa <= pb && pa <= pc ? a : pb <= pc ? b : c; };
  let ri = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[ri++];
    for (let x = 0; x < stride; x++) {
      const rawv = raw[ri++];
      const a = x >= bpp ? cur[y * stride + x - bpp] : 0;
      const b = y > 0 ? cur[(y - 1) * stride + x] : 0;
      const c = (x >= bpp && y > 0) ? cur[(y - 1) * stride + x - bpp] : 0;
      let v;
      switch (filter) {
        case 0: v = rawv; break;
        case 1: v = rawv + a; break;
        case 2: v = rawv + b; break;
        case 3: v = rawv + ((a + b) >> 1); break;
        case 4: v = rawv + paeth(a, b, c); break;
        default: throw new Error("bad filter " + filter);
      }
      cur[y * stride + x] = v & 0xff;
    }
  }
  // expand to RGBA
  const rgba = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < width * height; i++) {
    let r, g, b, alpha = 255;
    if (colorType === 6) { r = cur[i * 4]; g = cur[i * 4 + 1]; b = cur[i * 4 + 2]; alpha = cur[i * 4 + 3]; }
    else if (colorType === 2) { r = cur[i * 3]; g = cur[i * 3 + 1]; b = cur[i * 3 + 2]; }
    else if (colorType === 0) { r = g = b = cur[i]; }
    else if (colorType === 4) { r = g = b = cur[i * 2]; alpha = cur[i * 2 + 1]; }
    else if (colorType === 3) { const idx = cur[i]; r = plte[idx * 3]; g = plte[idx * 3 + 1]; b = plte[idx * 3 + 2]; if (trns && idx < trns.length) alpha = trns[idx]; }
    rgba[i * 4] = r; rgba[i * 4 + 1] = g; rgba[i * 4 + 2] = b; rgba[i * 4 + 3] = alpha;
  }
  return { width, height, rgba };
}

// Encode RGBA (Uint8-ish) to a PNG buffer.
export function encodePNG(width, height, rgba) {
  const raw = Buffer.alloc(height * (1 + width * 4));
  for (let y = 0; y < height; y++) {
    raw[y * (1 + width * 4)] = 0;
    for (let x = 0; x < width * 4; x++) raw[y * (1 + width * 4) + 1 + x] = rgba[y * width * 4 + x];
  }
  const idat = zlib.deflateSync(raw, { level: 6 });
  const CRC = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  const crc32 = (b) => { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0); const t = Buffer.from(type, "latin1"); const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([t, data])), 0); return Buffer.concat([len, t, data, crc]); };
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([sig, chunk("IHDR", ihdr), chunk("IDAT", idat), chunk("IEND", Buffer.alloc(0))]);
}

// Box-average downscale to a target longest side.
export function downscale(img, longSide) {
  const { width: W, height: H, rgba } = img;
  const s = longSide / Math.max(W, H);
  const w = Math.max(1, Math.round(W * s)), h = Math.max(1, Math.round(H * s));
  const out = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    const y0 = Math.floor(y / h * H), y1 = Math.max(y0 + 1, Math.floor((y + 1) / h * H));
    for (let x = 0; x < w; x++) {
      const x0 = Math.floor(x / w * W), x1 = Math.max(x0 + 1, Math.floor((x + 1) / w * W));
      let r = 0, g = 0, b = 0, a = 0, n = 0;
      for (let yy = y0; yy < y1; yy++) for (let xx = x0; xx < x1; xx++) {
        const o = (yy * W + xx) * 4; r += rgba[o]; g += rgba[o + 1]; b += rgba[o + 2]; a += rgba[o + 3]; n++;
      }
      const o = (y * w + x) * 4;
      out[o] = r / n; out[o + 1] = g / n; out[o + 2] = b / n; out[o + 3] = a / n;
    }
  }
  return { width: w, height: h, rgba: out };
}
