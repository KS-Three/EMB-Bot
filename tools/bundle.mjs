// tools/bundle.mjs
//
// Bundles EMB-Bot.html + src/*.js into a single portable EMB-Bot-standalone.html.
//
// What it does:
//   - Reads EMB-Bot.html.
//   - Finds every LOCAL script tag, i.e. <script src="src/XXX.js"></script>
//     (src starting with "src/"), and replaces it in place with an inline
//     <script> containing that file's contents read verbatim from disk.
//     Original order is preserved.
//   - Leaves the CDN <script src="https://..."> tags (opentype.js, jsPDF)
//     untouched as remote references -- the standalone file still needs
//     internet access to fetch those (and the Google-Fonts URLs inside
//     src/fonts.js), it just no longer needs the src/ folder on disk.
//   - Writes the result to EMB-Bot-standalone.html.
//
// Usage: node tools/bundle.mjs   (run from anywhere -- paths are resolved
// relative to this file's location, not the current working directory)

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const HTML_IN = join(ROOT, "EMB-Bot.html");
const HTML_OUT = join(ROOT, "EMB-Bot-standalone.html");

// Matches a <script ...src="src/XXX.js"...></script> tag (or single-quoted
// src). The src value must literally start with "src/" and end in ".js",
// which is what makes this LOCAL-only: a CDN tag like
//   <script src="https://cdn.jsdelivr.net/npm/jspdf@2/..."></script>
// starts with "https:", not "src/", so it can never match this pattern and
// is left completely alone. [^>]* (a negated character class, not a dot)
// is used around the src attribute so this also matches across newlines
// and regardless of what other attributes / attribute order the tag has.
const LOCAL_SCRIPT_RE =
  /<script\b[^>]*\bsrc\s*=\s*(["'])(src\/[^"'>]+\.js)\1[^>]*>\s*<\/script>/g;

function main() {
  if (!existsSync(HTML_IN)) {
    throw new Error("Cannot find " + HTML_IN);
  }
  const html = readFileSync(HTML_IN, "utf8");

  const inlined = [];
  const missing = [];

  const result = html.replace(LOCAL_SCRIPT_RE, (fullMatch, _quote, srcPath) => {
    const abs = join(ROOT, srcPath);
    if (!existsSync(abs)) {
      missing.push(srcPath);
      return fullMatch; // leave the tag as-is so the problem stays visible
    }
    const code = readFileSync(abs, "utf8");
    inlined.push(srcPath);
    return "<script>\n/* inlined: " + srcPath + " */\n" + code + "\n</script>";
  });

  if (missing.length) {
    throw new Error(
      "Aborting -- referenced local script(s) not found on disk: " +
        missing.join(", ")
    );
  }
  if (inlined.length === 0) {
    throw new Error(
      "Aborting -- no local src/*.js <script> tags were found/matched in " +
        HTML_IN + ". Check LOCAL_SCRIPT_RE against the actual markup."
    );
  }

  // Sanity check 1: no local src/ script reference should remain.
  const stillLocal = result.match(/<script\b[^>]*\bsrc\s*=\s*["']src\/[^"']*["']/g);
  if (stillLocal) {
    throw new Error(
      "Bundle still references local script(s), inlining incomplete: " +
        stillLocal.join(", ")
    );
  }

  // Sanity check 2: the remote CDN scripts must still be present untouched.
  const cdnTags =
    result.match(/<script\b[^>]*\bsrc\s*=\s*["']https?:\/\/[^"']+["'][^>]*>\s*<\/script>/g) ||
    [];

  writeFileSync(HTML_OUT, result, "utf8");

  const rel = (p) => p.replace(ROOT, ".").replace(/\\/g, "/");

  console.log("Bundled " + rel(HTML_IN) + " -> " + rel(HTML_OUT));
  console.log("");
  console.log("Inlined " + inlined.length + " local script(s):");
  for (const p of inlined) console.log("  - " + p);
  console.log("");
  console.log("Left " + cdnTags.length + " remote CDN script(s) untouched:");
  for (const t of cdnTags) {
    const m = t.match(/src\s*=\s*["']([^"']+)["']/);
    console.log("  - " + (m ? m[1] : t));
  }
  console.log("");
  console.log("Wrote " + rel(HTML_OUT) + " (" + result.length.toLocaleString() + " bytes)");
}

main();
