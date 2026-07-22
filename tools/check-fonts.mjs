// Verifies every URL in src/fonts.js FONTS resolves (HTTP 200-ish) so the
// browser can actually fetch+parse each font at runtime. Retries transient
// network errors before counting a URL as failed -- the sandbox's outbound
// network can be flaky, and a single ENOTFOUND/ECONNRESET is not proof a URL
// is dead.
//
// Usage: node tools/check-fonts.mjs

import fontsModule from "../src/fonts.js";

const { FONTS } = fontsModule;

const RETRIES = 3;
const RETRY_DELAY_MS = 500;
const TIMEOUT_MS = 15000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function headOrRangedGet(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    let res = await fetch(url, { method: "HEAD", signal: controller.signal });
    if (res.status === 405 || res.status === 501) {
      // Some CDNs/mirrors don't support HEAD; fall back to a ranged GET so we
      // don't download the whole file just to check it exists.
      res = await fetch(url, {
        method: "GET",
        headers: { Range: "bytes=0-0" },
        signal: controller.signal,
      });
    }
    return res;
  } finally {
    clearTimeout(timer);
  }
}

async function checkUrl(url) {
  let lastErr = null;
  for (let attempt = 1; attempt <= RETRIES; attempt++) {
    try {
      const res = await headOrRangedGet(url);
      if (res.ok || res.status === 206) {
        return { ok: true, status: res.status };
      }
      // Non-2xx/206: treat as a real failure, but still allow retries in case
      // of transient 5xx from the CDN.
      lastErr = new Error("HTTP " + res.status);
      if (res.status >= 400 && res.status < 500) break; // 4xx won't fix itself
    } catch (err) {
      lastErr = err;
    }
    if (attempt < RETRIES) await sleep(RETRY_DELAY_MS * attempt);
  }
  return { ok: false, error: lastErr };
}

async function main() {
  let pass = 0;
  let fail = 0;
  const failures = [];

  for (const font of FONTS) {
    const result = await checkUrl(font.url);
    if (result.ok) {
      pass++;
      console.log("PASS  " + font.family + "  (" + font.url + ")");
    } else {
      fail++;
      const reason = result.error ? result.error.message || String(result.error) : "unknown";
      failures.push({ family: font.family, url: font.url, reason });
      console.log("FAIL  " + font.family + "  (" + font.url + ")  -- " + reason);
    }
  }

  console.log("");
  console.log("PASS " + pass + " / FAIL " + fail + "  (of " + FONTS.length + " total)");
  if (failures.length) {
    console.log("");
    console.log("Failed families:");
    for (const f of failures) {
      console.log("  - " + f.family + ": " + f.reason);
    }
  }

  process.exitCode = fail > 0 ? 1 : 0;
}

main();
