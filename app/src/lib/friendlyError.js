// friendlyError.js — one place that turns "what the browser threw" into a
// sentence a customer can act on.
//
// Every failure a customer can hit in the Studio used to be shown by
// rendering `err.message` verbatim: fetch's own "Failed to fetch", an
// AbortSignal's "The operation was aborted due to timeout", a FastAPI 422's
// "[object Object]", a service traceback. None of those says what happened or
// what to do. Callers pass the error and WHERE it happened; the answer is
// always a plain sentence that says both.
//
// The rule that keeps this honest: a message that is already a plain
// sentence (the service's own `detail` lines, UNREADABLE, "Nothing to stitch
// yet") is passed through untouched, because it names the real cause better
// than anything generic could. Only transport failures, timeouts and
// technical-looking text are replaced.

export const OFFLINE_DIGITIZE =
  "Couldn’t reach the digitizer service, so nothing was digitized. Make sure it’s running " +
  "(python -m digitizer_service, in the digitizer folder), then press Auto Digitize Image again. " +
  "Your artwork and settings are saved.";

export const TIMEOUT_DIGITIZE =
  "Digitizing took too long, so it was stopped. Crop the artwork tighter or use a simpler image, " +
  "then press Auto Digitize Image again.";

export const FAILED_DIGITIZE =
  "Digitizing didn’t work on this image. Press Auto Digitize Image to try again; if it keeps " +
  "failing, crop the artwork tighter or use a simpler image.";

export const TOO_LARGE_DIGITIZE =
  "That image is too large for the digitizer. Shrink it or crop it tighter, replace the artwork, " +
  "then press Auto Digitize Image again.";

export const BAD_UPLOAD =
  "Couldn’t open that file. PNG, JPEG, WebP, GIF, BMP and SVG all work — export a PDF, AI or " +
  "EPS logo as one of those first, then choose it again.";

// Fetch rejects with a bare TypeError whose text differs per browser.
const NETWORK_RE = /failed to fetch|networkerror|network request failed|load failed|fetch failed|econnrefused|connection refused|err_connection/i;
const TIMEOUT_RE = /timed? ?out|aborted due to timeout/i;

// Does this look like something a person wrote for a person, rather than an
// exception's text, a stack, a JSON blob or a status code?
export function isPlainSentence(msg) {
  if (typeof msg !== "string") return false;
  const m = msg.trim();
  if (m.length < 8 || m.length > 300) return false;
  if (/[\r\n]/.test(m)) return false;
  if (/traceback|exception|\[object|\bundefined\b|\bnull\b|\bNaN\b|errno|\.py\b|\.js\b|\bat \S+:\d+|0x[0-9a-f]{4,}/i.test(m)) return false;
  if (/^\s*[\[{<]/.test(m)) return false;
  if (/^[A-Za-z]*(Error|Exception)\b/.test(m)) return false;
  if (/^The digitizer service answered \d+\.?$/.test(m)) return false;   // httpDetail's no-detail fallback
  return /[a-z]{3,} [a-z]{2,}/i.test(m);   // at least two real words
}

export function isNetworkError(err) {
  if (!err) return false;
  if (err.kind === "unreachable") return true;
  if (err.name === "AbortError" || err.name === "TimeoutError") return false;
  const msg = String(err.message || err);
  return err instanceof TypeError ? NETWORK_RE.test(msg) || msg.length < 40 : NETWORK_RE.test(msg);
}

export function isTimeoutError(err) {
  if (!err) return false;
  if (err.kind === "timeout") return true;
  if (err.name === "TimeoutError" || err.name === "AbortError") return true;
  return TIMEOUT_RE.test(String(err.message || ""));
}

// context: "digitize" | "upload" | "export" — what the customer was doing.
// `what` (export only) names the thing being made: "DST file", "PNG preview".
export function friendlyError(err, context, what) {
  const raw = err && typeof err === "object" ? String(err.message || "") : String(err || "");
  const plain = isPlainSentence(raw) ? raw.trim() : "";

  if (context === "digitize") {
    if (isNetworkError(err)) return OFFLINE_DIGITIZE;
    if (isTimeoutError(err)) return TIMEOUT_DIGITIZE;
    if (err && err.status === 413 && !plain) return TOO_LARGE_DIGITIZE;
    return plain || FAILED_DIGITIZE;
  }

  if (context === "upload") {
    return plain || BAD_UPLOAD;
  }

  if (context === "export") {
    const thing = what || "file";
    if (isNetworkError(err)) {
      return `Couldn’t make the ${thing} because the digitizer service isn’t answering. ` +
        "Start it (python -m digitizer_service, in the digitizer folder), then try again.";
    }
    if (isTimeoutError(err)) {
      return `Making the ${thing} took too long. Try again; if it keeps happening, use a smaller design.`;
    }
    return plain || `Couldn’t make the ${thing}. Try again; if it keeps happening, pick a different file format.`;
  }

  return plain || "Something went wrong. Try again.";
}
