#!/usr/bin/env node
// One-time font style tagging for the Studio font search.
//
//   node tools/tag-font-styles.mjs [--model gemma3:4b] [--force] [--only key,key]
//
// Looks at each font's static preview PNG (src/fonts/previews/<key>.png) with a
// LOCAL Ollama vision model and writes src/fonts/font-styles.json, a plain
// {key: [tag, ...]} map drawn from the fixed vocabulary below. The app only
// ever reads that committed JSON — Ollama is a build-time tool here, never a
// runtime dependency, and nothing leaves the machine.
//
// Resumable: fonts already in the file are skipped unless --force. Tags are
// model output, so review the diff by eye before committing (see the
// `reviewed` field the script leaves false).
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(root, "src", "fonts", "font-styles.json");

export const VOCAB = [
  "script", "handwritten", "brush", "serif", "sans", "slab", "block", "outline",
  "bold", "light", "rounded", "condensed", "wide", "italic", "stencil", "gothic",
  "blackletter", "western", "retro", "vintage", "modern", "formal", "elegant",
  "playful", "decorative", "ornate", "monogram", "typewriter", "military",
  "pixel", "small", "narrow-stroke", "fill-texture",
];

const args = process.argv.slice(2);
const flag = (n) => args.includes(n);
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const MODEL = opt("--model", "gemma3:4b");
const ONLY = opt("--only", "") ? opt("--only").split(",") : null;
const HOST = process.env.OLLAMA_HOST || "http://127.0.0.1:11434";

const manifest = JSON.parse(readFileSync(join(root, "src", "fonts", "manifest.json"), "utf8"));
const out = existsSync(OUT) && !flag("--force")
  ? JSON.parse(readFileSync(OUT, "utf8"))
  : { version: 1, model: MODEL, reviewed: false, fonts: {} };

function prompt(f) {
  return (
    `This image is a preview of an embroidery lettering font named "${f.name}" ` +
    `(group: ${f.group}). Describe its visual style. Choose 2 to 5 tags ONLY from ` +
    `this list: ${VOCAB.join(", ")}. Answer with JSON only: {"tags": [...]}.`
  );
}

async function tag(f) {
  const img = readFileSync(join(root, "src", "fonts", "previews", f.key + ".png")).toString("base64");
  const res = await fetch(HOST + "/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model: MODEL, stream: false, format: "json", options: { temperature: 0 },
      messages: [{ role: "user", content: prompt(f), images: [img] }],
    }),
  });
  if (!res.ok) throw new Error(`ollama ${res.status}`);
  const body = JSON.parse((await res.json()).message.content);
  const got = Array.isArray(body.tags) ? body.tags : [];
  return [...new Set(got.map((t) => String(t).toLowerCase().trim()).filter((t) => VOCAB.includes(t)))].slice(0, 5);
}

for (const f of manifest.fonts.filter((x) => x.tier === "verified")) {
  if (ONLY && !ONLY.includes(f.key)) continue;
  if (out.fonts[f.key]) continue;
  if (!existsSync(join(root, "src", "fonts", "previews", f.key + ".png"))) { out.fonts[f.key] = []; continue; }
  try {
    out.fonts[f.key] = await tag(f);
    console.log(f.key.padEnd(34), out.fonts[f.key].join(", "));
  } catch (e) {
    console.error(f.key, "FAILED", e.message);
  }
  out.model = MODEL;
  writeFileSync(OUT, JSON.stringify(out, null, 1) + "\n");
}
writeFileSync(OUT, JSON.stringify(out, null, 1) + "\n");
console.log(`wrote ${Object.keys(out.fonts).length} fonts -> ${OUT}`);
