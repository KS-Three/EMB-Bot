// PreToolUse guard: a Python interpreter given `-` as its script reads the
// program from stdin. When the Bash tool's heredoc never reaches it, Python
// 3.14 falls into _pyrepl and spins one core until killed (26 h on 2026-11-02,
// 3,320 CPU-s on 2026-11-03). Memory: bash-heredoc-python-repl-trap-2026-11-02.
// Denies `python -` (any python/py spelling, any path) in any command segment.
// Judges the parsed command word, not the text: `echo python -`,
// `git log -- python -`, `python -m x`, `python tool.py -` all pass.
const fs = require('fs');

// Drop heredoc bodies so a script piped to `cat`/`node` can mention python -.
function stripHeredocs(text) {
  const out = [];
  let end = null;
  for (const line of text.split(/\r?\n/)) {
    if (end !== null) {
      if (line.trim() === end) end = null;
      continue;
    }
    out.push(line);
    const m = /<<-?\s*(['"]?)([A-Za-z_][\w]*)\1/.exec(line);
    if (m && !/<<</.test(line)) end = m[2];
  }
  return out.join('\n');
}

// Quote-aware split into segments (on ; & | ( ) newline) of word tokens.
function segments(text) {
  const segs = [];
  let toks = [];
  let cur = '';
  let has = false;
  let q = null;
  const endTok = () => { if (has) toks.push(cur); cur = ''; has = false; };
  const endSeg = () => { endTok(); if (toks.length) segs.push(toks); toks = []; };
  for (const ch of text) {
    if (q) {
      if (ch === q) q = null; else cur += ch;
      continue;
    }
    if (ch === '"' || ch === "'") { q = ch; has = true; }
    else if (/\s/.test(ch) && ch !== '\n') endTok();
    else if (';&|()\n`'.includes(ch)) endSeg();
    else { cur += ch; has = true; }
  }
  endSeg();
  return segs;
}

const WRAPPERS = new Set(['env', 'time', 'nohup', 'exec', 'command', 'sudo', 'nice', 'timeout']);
const PY = /^(?:python(?:w)?\d*(?:\.\d+)*|py)(?:\.exe)?$/i;

function isPythonDash(toks) {
  let i = 0;
  while (i < toks.length) {
    const t = toks[i].replace(/^\$/, '');
    if (!t || /^[A-Za-z_]\w*=/.test(t) || WRAPPERS.has(t) || (/^-/.test(t) && i > 0 && WRAPPERS.has(toks[i - 1]))) i++;
    else break;
  }
  if (i >= toks.length) return false;
  const base = toks[i].split(/[\\/]/).pop();
  if (!PY.test(base)) return false;
  for (let j = i + 1; j < toks.length; j++) {
    const t = toks[j];
    if (/^\d*[<>&]/.test(t)) { if (/^\d*[<>]+$/.test(t)) j++; continue; } // redirects
    if (t === '-') return true;
    if (!t.startsWith('-')) return false;                // script file: rest are its args
    if (/^-[A-Za-z]*[mc]$/.test(t) || t === '--') return false; // -m mod / -c code
    if (/^-[WX]$/.test(t)) j++;                          // option with a separate value
  }
  return false;
}

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}
const cmd = (data.tool_input && data.tool_input.command) || '';
if (segments(stripHeredocs(cmd)).some(isPythonDash)) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        'Blocked: `python -` reads its program from stdin; if the heredoc does not arrive, ' +
        'Python 3.14 falls into its REPL and spins a core until killed (2026-11-02, 11-03). ' +
        'Write a script file in the scratchpad and run it by path.'
    }
  }));
}
process.exit(0);
