#!/usr/bin/env node
// PreToolUse guard: deleting or moving a lane under .claude/worktrees/ can
// destroy another lane's live, uncommitted work — see CLAUDE.md footgun 2 and
// memory `worktree-add-empty-var-wipes-cwd`.
//
// It judges the TARGET of each destructive verb, not the command text. The
// first version denied any command that both named `.claude/worktrees/` and
// contained rm/rmdir/rd/del/mv as a word anywhere, which caught scratchpad
// cleanups, a JS variable called `mv`, and prose (measured 2026-10-03: 1.6%
// of a wrong-root session's shell calls, every sampled one a false positive).
//
// How it decides, per simple command (split on newlines ; && || | & and
// subshell parens, quote-aware, heredoc bodies parsed line by line):
//
//   verbs   rm rmdir rd del erase unlink Remove-Item ri | mv move Move-Item mi
//           Rename-Item ren rni | git worktree remove|move | git clean |
//           find … -delete / -exec rm | xargs rm | bash -c / cmd /c /
//           powershell -Command / eval (re-lexed)
//   paths   resolved against the effective cwd: the hook payload's `cwd`,
//           updated by `cd`/`pushd`/`Set-Location` and `git -C` earlier in the
//           same command; `VAR=…`, `export`, `$name = …`, `for v in …` earlier
//           in the command; `~`, `$HOME`, `$PWD`, `$env:X` and the hook's own
//           environment; Git Bash `/c/…`, WSL `/mnt/c/…`, `C:\…`, globs.
//   deny    (1) the `.claude/worktrees` directory itself or a glob over it;
//           (2) a lane root (`.claude/worktrees/<name>`), or `rm -rf .`/`*`
//               inside one;
//           (3) a path INSIDE a lane when the command is not running inside
//               that same lane (OWN_LANE policy below);
//           (4) an ancestor that holds the lanes (`rm -rf <repo>`,
//               `rm -rf .claude`) — probed on disk, read-only;
//           (5) a target the hook cannot resolve (a variable set in an
//               earlier tool call, `$(…)`, `$_`, xargs stdin) when the command
//               text ALSO names `.claude/worktrees/` — failing closed there
//               is the old guard's behaviour on exactly its true positives;
//           (6) `git worktree add` with no path or a bare unresolvable one,
//               run from inside a lane — the 2026-08-31 incident.
//   allow   everything else, including a relative delete under an unknown
//           cwd that neither climbs (`..`) nor names a lane: the only way
//           that reaches a lane is a cwd that is exactly `.claude/worktrees`.
//
// OWN_LANE — Kent's ruling 2026-10-04 (PR #629): what to do with a target that
// sits INSIDE a lane when the command is running inside that same lane
// (payload cwd or a `cd` earlier in the command).
//   'allow'      Kent's pick, the default: a session cleaning its own lane (`rm vt.log`,
//                `rm -rf redcheck`) is routine; the lane root stays denied.
//   'files-only' allow when the target is an existing file; deny a directory.
//   'deny'       deny everything under .claude/worktrees/ regardless of cwd.
// Set EMB_WORKTREE_GUARD_OWN_LANE to override (the tests do).
//
// Tests: test/worktree-guard.test.js (pipe-tests: stdin JSON → stdout JSON).
// Replay over real transcripts: tools/replay-worktree-guard.mjs.
'use strict';
const fs = require('fs');
const path = require('path');

const OWN_LANE = process.env.EMB_WORKTREE_GUARD_OWN_LANE || 'allow';

const WORKTREES_TEXT = /\.claude[\\/]+worktrees[\\/]?/i;

const REMOVE_VERBS = new Set(['rm', 'rmdir', 'rd', 'del', 'erase', 'unlink', 'remove-item', 'ri']);
const MOVE_VERBS = new Set(['mv', 'move', 'move-item', 'mi']);
const RENAME_VERBS = new Set(['rename-item', 'rni', 'ren', 'rename']);
const CMD_ONLY_VERBS = new Set(['rd', 'del', 'erase', 'move', 'ren', 'rename']); // `/s`-style flags
const CD_VERBS = new Set(['cd', 'chdir', 'pushd', 'set-location', 'sl', 'push-location']);
const POP_VERBS = new Set(['popd', 'pop-location']);
const WRAPPERS = new Set(['sudo', 'doas', 'command', 'exec', 'nice', 'nohup', 'time', 'builtin', 'env', 'timeout', 'ionice']);
const ASSIGN_VERBS = new Set(['export', 'local', 'declare', 'readonly', 'typeset']);
const RESERVED = new Set(['do', 'then', 'else', 'elif', 'if', 'while', 'until', '!', '{', '}', 'done', 'fi', 'esac', 'function']);
const FIND_FILTERS = new Set(['-name', '-iname', '-path', '-ipath', '-regex', '-iregex', '-type', '-mtime', '-mmin', '-newer', '-size', '-empty', '-user', '-perm', '-maxdepth', '-mindepth']);
const PS_VALUE_PARAMS = new Set(['-filter', '-include', '-exclude', '-erroraction', '-warningaction', '-informationaction', '-errorvariable', '-warningvariable', '-outvariable', '-newname']);

// ---------------------------------------------------------------- lexer ----

// A token is {parts, quoted, raw}: parts are strings, {var: NAME}, {home: true}
// or {sub: true} (command substitution / subexpression — never resolvable).
function lex(text, dialect, out) {
  out = out || [];
  const ps = dialect === 'ps' || dialect === 'cmd'; // backslash is a path separator, not an escape
  const n = text.length;
  let i = 0;
  let words = [];
  let parts = [];
  let raw = '';
  let inWord = false;
  let quoted = false;
  let expectRedirectTarget = false;
  let expectHeredocDelim = false;
  const pendingHeredocs = [];

  const push = (s) => {
    inWord = true;
    raw += typeof s === 'string' ? s : s.raw || '';
    if (typeof s === 'string') {
      const last = parts[parts.length - 1];
      if (typeof last === 'string') parts[parts.length - 1] = last + s;
      else parts.push(s);
    } else {
      parts.push(s);
    }
  };
  const endWord = () => {
    if (!inWord) return;
    const tok = { parts, quoted, raw };
    parts = [];
    raw = '';
    inWord = false;
    quoted = false;
    if (expectHeredocDelim) {
      expectHeredocDelim = false;
      pendingHeredocs.push(literalText(tok));
      return;
    }
    if (expectRedirectTarget) {
      expectRedirectTarget = false;
      return;
    }
    words.push(tok);
  };
  const endCmd = () => {
    endWord();
    if (words.length) out.push({ type: 'cmd', words });
    words = [];
  };
  const atCmdStart = () => !inWord && words.length === 0;

  // Skip a balanced (...) / `...` region starting after the opener; returns
  // the inner text and leaves i after the closer.
  const readBalanced = (open, close) => {
    let depth = 1;
    let q = null;
    const start = i;
    while (i < n) {
      const c = text[i];
      if (q) {
        if (c === '\\' && q === '"') i += 2;
        else if (c === q) { q = null; i++; }
        else i++;
        continue;
      }
      if (c === '"' || c === "'") { q = c; i++; continue; }
      if (open && c === open) depth++;
      else if (c === close) { depth--; if (depth === 0) { const inner = text.slice(start, i); i++; return inner; } }
      i++;
    }
    const inner = text.slice(start, n);
    i = n;
    return inner;
  };

  // Commands found inside `$(…)`, backticks, PS subexpressions and heredoc
  // bodies run in their own scope: a `cd` or assignment there never reaches
  // the enclosing command's cwd or variables.
  const nested = (inner) => {
    out.push({ type: 'open' });
    lex(inner, dialect, out);
    out.push({ type: 'close' });
  };

  const readVar = () => {
    // i points just after '$'
    let m;
    if (text[i] === '{') {
      i++;
      const inner = readBalanced('{', '}');
      m = /^([A-Za-z_][A-Za-z0-9_:]*)/.exec(inner);
      if (m && /^[A-Za-z_][A-Za-z0-9_:]*(:[-=?+].*|)$/.test(inner)) push({ var: m[1], raw: '${' + inner + '}' });
      else push({ sub: true, raw: '${' + inner + '}' });
      return;
    }
    if (text[i] === '(') {
      i++;
      const inner = readBalanced('(', ')');
      push({ sub: true, raw: '$(' + inner + ')' });
      nested(inner);
      return;
    }
    m = /^(env:[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)/.exec(text.slice(i, i + 80));
    if (m) { push({ var: m[1], raw: '$' + m[1] }); i += m[1].length; return; }
    m = /^[0-9@*#?$!_-]/.exec(text.slice(i, i + 1));
    if (m) { push({ sub: true, raw: '$' + m[0] }); i += 1; return; }
    push('$');
  };

  const readHeredocBodies = () => {
    // i points just after a newline; consume body lines for each pending delimiter.
    while (pendingHeredocs.length) {
      const delim = pendingHeredocs.shift();
      while (i < n) {
        let eol = text.indexOf('\n', i);
        if (eol < 0) eol = n;
        const line = text.slice(i, eol).replace(/\r$/, '');
        i = eol + 1;
        if (line.replace(/^\t+/, '') === delim) break;
        nested(line); // body lines are judged as commands, one at a time, in their own scope
      }
    }
    if (i > n) i = n;
  };

  while (i < n) {
    const c = text[i];
    const c2 = text[i + 1];

    if (c === '\n' || c === '\r') {
      i++;
      endCmd();
      expectRedirectTarget = false;
      if (c === '\n' && pendingHeredocs.length) readHeredocBodies();
      continue;
    }
    if (c === ' ' || c === '\t') { endWord(); i++; continue; }

    if (c === '#' && atCmdStart() && !ps) { while (i < n && text[i] !== '\n') i++; continue; }
    if (c === '#' && !inWord) { while (i < n && text[i] !== '\n') i++; continue; }

    if (c === "'") {
      i++;
      quoted = true;
      let s = '';
      while (i < n) {
        if (text[i] === "'") {
          if (ps && text[i + 1] === "'") { s += "'"; i += 2; continue; }
          break;
        }
        s += text[i++];
      }
      i++;
      push({ raw: "'" + s + "'" });
      parts.pop();
      push(s);
      continue;
    }
    if (c === '"') {
      i++;
      quoted = true;
      push({ raw: '"' });
      parts.pop();
      while (i < n && text[i] !== '"') {
        const d = text[i];
        if (!ps && d === '\\') {
          const e = text[i + 1];
          if (e === '"' || e === '\\' || e === '$' || e === '`') { push(e); i += 2; continue; }
          if (e === '\n') { i += 2; continue; }
          push('\\'); i++; continue;
        }
        if (ps && d === '`') {
          const e = text[i + 1];
          if (e === '\n') { i += 2; continue; }
          if (e === undefined) { i++; continue; }
          push(e === 'n' ? '\n' : e === 't' ? '\t' : e); i += 2; continue;
        }
        if (ps && d === '"' && text[i + 1] === '"') { push('"'); i += 2; continue; }
        if (d === '$') { i++; readVar(); continue; }
        if (!ps && d === '`') { i++; const inner = readBalanced(null, '`'); push({ sub: true, raw: '`' + inner + '`' }); nested(inner); continue; }
        push(d); i++;
      }
      i++;
      push({ raw: '"' });
      parts.pop();
      continue;
    }

    if (c === '\\' && !ps) {
      if (c2 === '\n') { i += 2; continue; }
      if (c2 === '\r' && text[i + 2] === '\n') { i += 3; continue; }
      if (c2 === undefined) { i++; continue; }
      push(c2); i += 2; continue;
    }
    if (c === '`' && ps) {
      if (c2 === '\n') { i += 2; continue; }
      if (c2 === undefined) { i++; continue; }
      push(c2); i += 2; continue;
    }
    if (c === '`' && !ps) {
      i++;
      const inner = readBalanced(null, '`');
      push({ sub: true, raw: '`' + inner + '`' });
      nested(inner);
      continue;
    }
    if (c === '$') {
      if (c2 === "'") { // $'…' ANSI-C string
        i += 2; quoted = true; let s = '';
        while (i < n && text[i] !== "'") { if (text[i] === '\\') { s += text[i + 1] || ''; i += 2; } else s += text[i++]; }
        i++; push(s); continue;
      }
      if (c2 === '"') { i++; continue; } // $"…" → treated as "…"
      i++;
      readVar();
      continue;
    }
    if (c === '~' && !inWord && !ps && (c2 === undefined || c2 === '/' || c2 === ' ' || c2 === '\t' || c2 === '\n' || c2 === ';' || c2 === '&' || c2 === '|' || c2 === ')')) {
      push({ home: true, raw: '~' }); i++; continue;
    }
    if (c === '~' && !inWord && ps && (c2 === undefined || c2 === '/' || c2 === '\\' || c2 === ' ')) {
      push({ home: true, raw: '~' }); i++; continue;
    }
    if (c === '@' && c2 === '(' && ps) { i += 2; const inner = readBalanced('(', ')'); push({ sub: true, raw: '@(' + inner + ')' }); nested(inner); continue; }

    // separators
    if (c === ';') { endCmd(); i++; continue; }
    if (c === '|') { endCmd(); i += (c2 === '|' || c2 === '&') ? 2 : 1; continue; }
    if (c === '&') {
      if (c2 === '>') { endWord(); i += 2; if (text[i] === '>') i++; expectRedirectTarget = true; continue; }
      endCmd(); i += c2 === '&' ? 2 : 1; continue;
    }
    if (c === '(') {
      if (atCmdStart()) { endCmd(); out.push({ type: 'open' }); i++; continue; }
      // mid-command: a subexpression (PS) or a function-def paren (bash)
      i++;
      const inner = readBalanced('(', ')');
      push({ sub: true, raw: '(' + inner + ')' });
      nested(inner);
      continue;
    }
    if (c === ')') { endCmd(); out.push({ type: 'close' }); i++; continue; }
    if (c === '{' || c === '}') {
      if (!inWord) { endWord(); i++; continue; }
      push(c); i++; continue;
    }
    if (c === '<' || c === '>') {
      // an fd number glued to the operator (2>&1) is not a word
      if (inWord && /^[0-9]+$/.test(raw) && parts.length === 1) { parts = []; raw = ''; inWord = false; }
      endWord();
      let op = c;
      i++;
      while (i < n && (text[i] === '<' || text[i] === '>' || text[i] === '&' || text[i] === '|' || text[i] === '-')) op += text[i++];
      if (op.startsWith('<<') && !op.startsWith('<<<')) { expectHeredocDelim = true; continue; }
      if (op.endsWith('&')) {
        // >&1 / 2>&1 / >&file: the following fd/word is not a target
        if (/^[0-9]+/.test(text.slice(i, i + 4))) { while (i < n && /[0-9]/.test(text[i])) i++; continue; }
        expectRedirectTarget = true; continue;
      }
      if (op.endsWith('|')) { /* >| */ }
      expectRedirectTarget = true;
      continue;
    }
    push(c);
    i++;
  }
  endCmd();
  return out;
}

function literalText(tok) {
  return tok.parts.map((p) => (typeof p === 'string' ? p : p.raw || '')).join('');
}

// ---------------------------------------------------------- resolution ----

function homeDir(env) {
  return env.HOME || env.USERPROFILE || null;
}

// → {text} | {multi: [text…]} | {unresolvable: true}
function tokenValue(tok, state) {
  let texts = [''];
  for (const p of tok.parts) {
    let vals;
    if (typeof p === 'string') vals = [p];
    else if (p.home) { const h = homeDir(state.env); if (h == null) return { unresolvable: true }; vals = [h]; }
    else if (p.var) {
      const v = lookupVar(p.var, state);
      if (v === undefined || v === null) return { unresolvable: true };
      vals = Array.isArray(v) ? v : [v];
    } else return { unresolvable: true };
    const next = [];
    for (const t of texts) for (const v of vals) next.push(t + v);
    texts = next.slice(0, 64);
  }
  return texts.length === 1 ? { text: texts[0] } : { multi: texts };
}

function lookupVar(name, state) {
  if (name === 'PWD' || name.toLowerCase() === 'pwd') return state.cwd;
  if (name === 'HOME' || name.toLowerCase() === 'home') return homeDir(state.env);
  const m = /^env:(.+)$/i.exec(name);
  if (m) return state.env[m[1]] !== undefined ? state.env[m[1]] : state.env[m[1].toUpperCase()];
  if (state.vars.has(name)) return state.vars.get(name);
  if (state.vars.has(name.toLowerCase())) return state.vars.get(name.toLowerCase());
  if (state.env[name] !== undefined) return state.env[name];
  if (/^[A-Z]/.test(name) && state.env[name.toUpperCase()] !== undefined) return state.env[name.toUpperCase()];
  return undefined;
}

function isAbsolute(p) {
  return /^(\/|\\\\|[A-Za-z]:[\\/])/.test(p);
}

// Forward slashes, Git Bash / WSL / cygwin drive prefixes → `c:/…`, `.`/`..`
// resolved, no trailing slash. Comparison is case-insensitive elsewhere.
function normalizePath(p) {
  let s = p.replace(/\\/g, '/');
  let m;
  if ((m = /^\/(?:mnt|cygdrive)\/([A-Za-z])(\/|$)/.exec(s))) s = m[1].toLowerCase() + ':/' + s.slice(m[0].length);
  else if ((m = /^\/([A-Za-z])(\/|$)/.exec(s))) s = m[1].toLowerCase() + ':/' + s.slice(m[0].length);
  else if ((m = /^([A-Za-z]):/.exec(s))) s = m[1].toLowerCase() + s.slice(1);
  const unc = s.startsWith('//');
  s = path.posix.normalize(s);
  if (unc && !s.startsWith('//')) s = '/' + s;
  if (s.length > 1 && s.endsWith('/') && !/^[a-z]:\/$/.test(s)) s = s.slice(0, -1);
  return s;
}

function joinPath(cwd, rel) {
  return normalizePath(cwd.replace(/\/$/, '') + '/' + rel);
}

// Split off a trailing glob: returns {dir, bare} where `bare` is true when the
// glob swallows everything in `dir` (`*`, `.*`, `**`), and `dir` is the deepest
// non-glob prefix. A glob with literal parts (`*.log`) counts as a child.
function splitGlob(p) {
  const segs = p.split('/');
  for (let k = 0; k < segs.length; k++) {
    if (/[*?[]/.test(segs[k])) {
      const bare = /^(\*+|\.\*|\*\.\*)$/.test(segs[k]);
      return { dir: segs.slice(0, k).join('/') || '/', bare, glob: true };
    }
  }
  return { dir: p, bare: false, glob: false };
}

// Where `abs` sits relative to .claude/worktrees: null (outside), or
// {depth, laneRoot, worktreesDir}. depth 0 = the worktrees dir, 1 = a lane root.
function locate(abs) {
  const segs = abs.split('/').filter((s, k) => s !== '' || k === 0);
  for (let k = 0; k + 1 < segs.length; k++) {
    if (segs[k].toLowerCase() === '.claude' && segs[k + 1].toLowerCase() === 'worktrees') {
      const depth = segs.length - (k + 2);
      return {
        depth,
        worktreesDir: segs.slice(0, k + 2).join('/'),
        laneRoot: depth >= 1 ? segs.slice(0, k + 3).join('/') : null,
      };
    }
  }
  return null;
}

function fsPath(abs) {
  // `c:/x` → `C:/x` for fs on Windows; posix paths unchanged.
  return /^[a-z]:\//.test(abs) ? abs[0].toUpperCase() + abs.slice(1) : abs;
}

function sameLane(a, b) {
  if (a.toLowerCase() === b.toLowerCase()) return true;
  try {
    const ra = fs.realpathSync.native(fsPath(a));
    const rb = fs.realpathSync.native(fsPath(b));
    return normalizePath(ra).toLowerCase() === normalizePath(rb).toLowerCase();
  } catch {
    return false;
  }
}

// Does `abs` hold the lanes (so removing/moving it takes them along)?
function holdsLanes(abs) {
  try {
    const base = fsPath(abs);
    const wt = /(^|\/)\.claude$/i.test(abs) ? path.join(base, 'worktrees') : path.join(base, '.claude', 'worktrees');
    if (!fs.statSync(wt).isDirectory()) return false;
    return fs.readdirSync(wt).length > 0;
  } catch {
    return false;
  }
}

function isDirectoryOnDisk(abs) {
  try { return fs.statSync(fsPath(abs)).isDirectory(); } catch { return false; }
}

// ------------------------------------------------------------ judgement ----

// role: 'remove' | 'move-src' | 'move-dest' | 'clean' | 'lane'
// contents: the verb deletes a filtered subset UNDER the path, never the path
// itself (`find lane -name '*.pyc' -delete`, `git clean lane`, `Remove-Item
// -Filter`), so a lane root is judged as "inside that lane", not as the lane.
function classify(abs, role, state, verb, rawTarget, contents) {
  const { dir, bare, glob } = splitGlob(abs);
  const target = glob && !bare ? dir + '/<glob>' : dir;
  const loc = locate(target);
  const show = rawTarget + (rawTarget === abs ? '' : ' → ' + abs);
  if (!loc) {
    if ((role === 'remove' || role === 'move-src' || role === 'clean') && holdsLanes(dir)) {
      return { deny: true, rule: 'ancestor', why: `${verb} ${show}: that directory holds .claude/worktrees/ and every lane in it` };
    }
    return { deny: false };
  }
  if (loc.depth === 0) return { deny: true, rule: 'worktrees-dir', why: `${verb} ${show}: that is the .claude/worktrees/ directory itself` };
  if (loc.depth === 1 && !(contents && !bare)) {
    if (role === 'move-dest') return { deny: true, rule: 'lane-root', why: `${verb} … ${show}: the destination is a lane root` };
    return { deny: true, rule: 'lane-root', why: `${verb} ${show}: that is a lane root (${bare ? 'its whole contents' : 'the lane itself'})` };
  }
  if (role === 'move-dest') return { deny: false };
  if (role === 'lane') return { deny: true, rule: 'lane-path', why: `${verb} ${show}: a path inside a lane` };
  // inside a lane: own-lane policy
  const cwdLoc = state.cwd ? locate(state.cwd) : null;
  const inside = cwdLoc && cwdLoc.depth >= 1 && sameLane(cwdLoc.laneRoot, loc.laneRoot);
  if (OWN_LANE === 'deny') return { deny: true, rule: 'inside-lane', why: `${verb} ${show}: inside a lane (policy: nothing under .claude/worktrees/ is deletable from a tool call)` };
  if (!inside) {
    return {
      deny: true,
      rule: 'other-lane',
      why: `${verb} ${show}: inside lane ${path.posix.basename(loc.laneRoot)}, but this command ${state.cwd ? 'runs from ' + state.cwd : 'runs from an unknown directory'} — only a command running inside that lane may delete there (cd into it first)`,
    };
  }
  if (OWN_LANE === 'files-only' && (glob || isDirectoryOnDisk(dir))) {
    return { deny: true, rule: 'own-lane-dir', why: `${verb} ${show}: a directory inside your own lane (policy: files only)` };
  }
  return { deny: false, own: true };
}

function judgeTarget(tok, role, state, verb, findings, opts) {
  opts = opts || {};
  const v = tokenValue(tok, state);
  const raw = tok.raw;
  if (v.unresolvable) {
    findings.push({ verb, raw, resolved: null, status: 'unresolvable', deny: state.namesWorktrees, rule: state.namesWorktrees ? 'unresolvable' : null, why: state.namesWorktrees ? `${verb} ${raw}: cannot resolve that path from this command, and the command names .claude/worktrees/ — failing closed` : null });
    return;
  }
  for (const text of v.multi || [v.text]) {
    if (text === '' || text === '-') continue;
    let abs;
    if (isAbsolute(text)) abs = normalizePath(text);
    else if (/^[A-Za-z]:/.test(text)) { // drive-relative `c:foo`
      findings.push({ verb, raw, resolved: null, status: 'unresolvable', deny: state.namesWorktrees, rule: state.namesWorktrees ? 'unresolvable' : null, why: state.namesWorktrees ? `${verb} ${raw}: drive-relative path, cannot resolve` : null });
      continue;
    } else if (opts.base || state.cwd) abs = joinPath(opts.base || state.cwd, text);
    else {
      // relative under an unknown cwd
      const norm = text.replace(/\\/g, '/');
      const climbs = /(^|\/)\.\.(\/|$)/.test(norm);
      const bareHere = /^(\.|\.\/|\*+|\.\*|\.\/\*+)$/.test(norm);
      const names = WORKTREES_TEXT.test(norm);
      if (climbs || bareHere || names) {
        findings.push({ verb, raw, resolved: null, status: 'unresolvable', deny: state.namesWorktrees, rule: state.namesWorktrees ? 'unresolvable' : null, why: state.namesWorktrees ? `${verb} ${raw}: relative to a directory this command changed to but the hook cannot resolve, and the command names .claude/worktrees/ — failing closed` : null });
      } else {
        findings.push({ verb, raw, resolved: null, status: 'relative-unknown-cwd', deny: false, rule: null, why: null });
      }
      continue;
    }
    const c = classify(abs, role, state, verb, text, !!opts.contents);
    findings.push({ verb, raw, resolved: abs, status: 'resolved', deny: c.deny, rule: c.rule || (c.own ? 'own-lane' : null), why: c.why || null });
  }
}

function cmdWord(tok, state) {
  const v = tokenValue(tok, state);
  if (v.unresolvable || v.multi) return null;
  let w = v.text.replace(/\\/g, '/');
  w = w.slice(w.lastIndexOf('/') + 1).toLowerCase();
  if (w.endsWith('.exe')) w = w.slice(0, -4);
  return w;
}

function isFlag(text, verb, dialect) {
  if (text.startsWith('-') && text !== '-') return true;
  if ((CMD_ONLY_VERBS.has(verb) || dialect === 'cmd') && /^\/[A-Za-z?]+$/.test(text)) return true;
  return false;
}

function pathArgs(words, verb, state, dialect) {
  const out = [];
  let noMoreFlags = false;
  for (let k = 0; k < words.length; k++) {
    const tok = words[k];
    const v = tokenValue(tok, state);
    const text = v.unresolvable ? tok.raw : (v.text !== undefined ? v.text : tok.raw);
    if (!noMoreFlags && !tok.quoted) {
      if (text === '--') { noMoreFlags = true; continue; }
      if (isFlag(text, verb, dialect)) {
        const low = text.toLowerCase();
        if (PS_VALUE_PARAMS.has(low)) k++;                       // -Filter *.log
        if (low === '-t' || low === '--target-directory') { if (words[k + 1]) out.push({ tok: words[k + 1], dest: true }); k++; }
        continue;
      }
    }
    out.push({ tok });
  }
  return out;
}

function evalCommand(words, state, findings, dialect, depth) {
  depth = depth || 0;
  if (depth > 6 || !words.length) return;
  words = words.slice();

  // leading bash assignments: NAME=value NAME2=value cmd …
  while (words.length) {
    const t = words[0];
    const m = /^([A-Za-z_][A-Za-z0-9_]*)(\+?=)/.exec(t.raw);
    if (!m || t.quoted && t.raw.indexOf(m[0]) !== 0) break;
    if (typeof t.parts[0] !== 'string' || !t.parts[0].startsWith(m[0])) break;
    assignFromToken(m[1], t, m[0].length, state);
    words.shift();
  }
  if (!words.length) return;

  // PowerShell assignment: $name = value   |   $name=value
  const first = words[0];
  if (first.parts.length >= 1 && typeof first.parts[0] === 'object' && first.parts[0].var) {
    const name = first.parts[0].var;
    const rest = first.parts.slice(1);
    if (rest.length && typeof rest[0] === 'string' && rest[0].startsWith('=')) {
      const valTok = { parts: [rest[0].slice(1), ...rest.slice(1)], quoted: first.quoted, raw: first.raw };
      state.vars.set(name.toLowerCase(), valueOrNull(valTok, state));
      return;
    }
    if (words[1] && words[1].raw === '=' ) {
      state.vars.set(name.toLowerCase(), words[2] ? valueOrNull(words[2], state) : '');
      return;
    }
  }

  // bash reserved words that prefix a command: `do rm …`, `then rm …`, `if rm …`
  while (words.length && !words[0].quoted && RESERVED.has(words[0].raw)) words.shift();
  if (!words.length) return;

  let verb = cmdWord(words[0], state);
  if (verb === null) return;

  // wrappers: sudo rm …, env X=y rm …, timeout 30 rm …
  while (WRAPPERS.has(verb) && words.length > 1) {
    words.shift();
    if (verb === 'timeout' && words.length && /^[0-9]/.test(words[0].raw)) words.shift();
    while (words.length && (words[0].raw.startsWith('-') || /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0].raw))) {
      if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0].raw) && verb === 'env') { const m = /^([A-Za-z_][A-Za-z0-9_]*)=/.exec(words[0].raw); assignFromToken(m[1], words[0], m[0].length, state); }
      words.shift();
    }
    if (!words.length) return;
    verb = cmdWord(words[0], state);
    if (verb === null) return;
  }
  const args = words.slice(1);

  if (ASSIGN_VERBS.has(verb)) {
    for (const t of args) { const m = /^([A-Za-z_][A-Za-z0-9_]*)=/.exec(t.raw); if (m) assignFromToken(m[1], t, m[0].length, state); }
    return;
  }
  if (verb === 'set-variable' || verb === 'sv') {
    const name = args[0] && tokenValue(args[0], state).text;
    if (name) state.vars.set(name.toLowerCase(), args[1] ? valueOrNull(args[1], state) : null);
    return;
  }
  if (verb === 'unset' || verb === 'read') { for (const t of args) if (!t.raw.startsWith('-')) state.vars.set(t.raw, null); return; }
  if (verb === 'for') {
    // for NAME in a b c
    const name = args[0] && args[0].raw;
    if (name && args[1] && args[1].raw === 'in') {
      const vals = [];
      for (const t of args.slice(2)) { const v = tokenValue(t, state); if (v.unresolvable) { state.vars.set(name, null); return; } vals.push(...(v.multi || [v.text])); }
      state.vars.set(name, vals);
    } else if (name) state.vars.set(name, null);
    return;
  }
  if (verb === 'foreach') { // PowerShell: foreach ($x in …)
    for (const t of args) { const m = /^\(\$([A-Za-z_][A-Za-z0-9_]*)\b/.exec(t.raw); if (m) state.vars.set(m[1].toLowerCase(), null); }
    return;
  }

  if (CD_VERBS.has(verb)) {
    let target = null;
    for (const t of args) {
      if (!t.quoted && t.raw.startsWith('-') && t.raw !== '-') continue;
      target = t; break;
    }
    if (!target) { state.cwd = homeDir(state.env) ? normalizePath(homeDir(state.env)) : null; return; }
    if (target.raw === '-') { state.cwd = null; return; }
    const v = tokenValue(target, state);
    if (v.unresolvable || v.multi) { state.cwd = null; return; }
    const text = v.text;
    if (text === '' ) { state.cwd = homeDir(state.env) ? normalizePath(homeDir(state.env)) : null; return; }
    if (isAbsolute(text)) state.cwd = normalizePath(text);
    else if (state.cwd) state.cwd = joinPath(state.cwd, text);
    else state.cwd = null;
    return;
  }
  if (POP_VERBS.has(verb)) { state.cwd = null; return; }

  // shells that re-run a string
  if (verb === 'bash' || verb === 'sh' || verb === 'zsh' || verb === 'dash' || verb === 'ksh') {
    const k = args.findIndex((t) => /^-[a-zA-Z]*c[a-zA-Z]*$/.test(t.raw));
    if (k >= 0 && args[k + 1]) { const v = tokenValue(args[k + 1], state); if (!v.unresolvable && v.text) evalItems(lex(v.text, 'bash'), cloneState(state), findings, 'bash', depth + 1); }
    return;
  }
  if (verb === 'eval') {
    const text = args.map((t) => { const v = tokenValue(t, state); return v.unresolvable ? t.raw : v.text; }).join(' ');
    evalItems(lex(text, dialect), state, findings, dialect, depth + 1);
    return;
  }
  if (verb === 'cmd') {
    const k = args.findIndex((t) => /^\/{1,2}[ck]$/i.test(t.raw));
    if (k >= 0) evalItems(lex(requote(args.slice(k + 1), state), 'cmd'), cloneState(state), findings, 'cmd', depth + 1);
    return;
  }
  if (verb === 'powershell' || verb === 'pwsh') {
    let k = args.findIndex((t) => /^-(c|command|encodedcommand)$/i.test(t.raw));
    if (k < 0) k = args.findIndex((t) => !t.raw.startsWith('-')) - 1;
    if (k >= -1 && args[k + 1]) {
      const text = args.length === k + 2 ? valueOrRaw(args[k + 1], state) : requote(args.slice(k + 1), state);
      if (text) evalItems(lex(text, 'ps'), cloneState(state), findings, 'ps', depth + 1);
    }
    return;
  }

  if (verb === 'git') return evalGit(args, state, findings, dialect);

  if (verb === 'find') {
    const hasDelete = args.some((t) => t.raw === '-delete');
    const execIdx = args.findIndex((t) => t.raw === '-exec' || t.raw === '-execdir' || t.raw === '-ok');
    const execVerb = execIdx >= 0 && args[execIdx + 1] ? cmdWord(args[execIdx + 1], state) : null;
    if (!hasDelete && !(execVerb && (REMOVE_VERBS.has(execVerb) || MOVE_VERBS.has(execVerb)))) return;
    const starts = [];
    for (const t of args) {
      if (/^-[HLPO]$/.test(t.raw) || /^-D/.test(t.raw)) continue;
      if (t.raw.startsWith('-') || t.raw === '(' || t.raw === '!' || t.raw === '\\(') break;
      starts.push(t);
    }
    if (!starts.length) starts.push({ parts: ['.'], quoted: false, raw: '.' });
    const filtered = args.some((t) => FIND_FILTERS.has(t.raw));
    for (const t of starts) judgeTarget(t, 'remove', state, 'find … ' + (hasDelete ? '-delete' : '-exec ' + execVerb), findings, { contents: filtered });
    return;
  }
  if (verb === 'xargs') {
    let k = 0;
    while (k < args.length && args[k].raw.startsWith('-')) { if (/^-(I|n|P|d|L|s|E|a)$/.test(args[k].raw)) k++; k++; }
    const inner = args[k] ? cmdWord(args[k], state) : null;
    if (inner && (REMOVE_VERBS.has(inner) || MOVE_VERBS.has(inner))) {
      evalCommand(args.slice(k), state, findings, dialect, depth + 1);
      findings.push({ verb: 'xargs ' + inner, raw: '<stdin>', resolved: null, status: 'unresolvable', deny: state.namesWorktrees, rule: state.namesWorktrees ? 'unresolvable' : null, why: state.namesWorktrees ? `xargs ${inner}: its targets come from stdin, and the command names .claude/worktrees/ — failing closed` : null });
    }
    return;
  }

  if (REMOVE_VERBS.has(verb)) {
    const contents = args.some((t) => /^-(filter|include)$/i.test(t.raw));
    for (const a of pathArgs(args, verb, state, dialect)) judgeTarget(a.tok, 'remove', state, verb, findings, { contents });
    return;
  }
  if (MOVE_VERBS.has(verb) || RENAME_VERBS.has(verb)) {
    const ps = pathArgs(args, verb, state, dialect);
    const explicitDest = ps.find((a) => a.dest);
    const positional = ps.filter((a) => !a.dest);
    let srcs = positional;
    let dest = explicitDest || null;
    if (!dest && positional.length >= 2) { srcs = positional.slice(0, -1); dest = positional[positional.length - 1]; }
    for (const a of srcs) judgeTarget(a.tok, 'move-src', state, verb, findings);
    if (dest && !RENAME_VERBS.has(verb)) judgeTarget(dest.tok, 'move-dest', state, verb, findings);
    return;
  }
}

function evalGit(args, state, findings, dialect) {
  let base = null;
  let k = 0;
  while (k < args.length && args[k].raw.startsWith('-')) {
    const r = args[k].raw;
    if (r === '-C' && args[k + 1]) {
      const v = tokenValue(args[k + 1], state);
      if (v.unresolvable || v.multi) base = 'unknown';
      else base = isAbsolute(v.text) ? normalizePath(v.text) : (state.cwd ? joinPath(state.cwd, v.text) : 'unknown');
      k += 2; continue;
    }
    if (r === '-c' || r === '--git-dir' || r === '--work-tree') { k += 2; continue; }
    k++;
  }
  const sub = args[k] ? args[k].raw : '';
  const rest = args.slice(k + 1);
  const scoped = base === 'unknown' ? { ...state, cwd: null } : (base ? { ...state, cwd: base } : state);

  if (sub === 'worktree') {
    const op = rest[0] ? rest[0].raw : '';
    const ops = rest.slice(1);
    if (op === 'remove') {
      for (const t of ops) if (!t.raw.startsWith('-')) judgeTarget(t, 'lane', scoped, 'git worktree remove', findings);
    } else if (op === 'move') {
      const pos = ops.filter((t) => !t.raw.startsWith('-'));
      if (pos[0]) judgeTarget(pos[0], 'lane', scoped, 'git worktree move', findings);
      if (pos[1]) judgeTarget(pos[1], 'move-dest', scoped, 'git worktree move', findings);
    } else if (op === 'add') {
      // the 2026-08-31 incident: `git worktree add "$UNSET" …` from inside a lane
      const cwdLoc = scoped.cwd ? locate(scoped.cwd) : null;
      if (cwdLoc && cwdLoc.depth >= 1) {
        let pathTok = null;
        for (let j = 0; j < ops.length; j++) {
          const r = ops[j].raw;
          if (r === '-b' || r === '-B' || r === '--orphan' || r === '--reason') { j++; continue; }
          if (r.startsWith('-')) continue;
          pathTok = ops[j]; break;
        }
        const v = pathTok ? tokenValue(pathTok, scoped) : null;
        const bareVar = pathTok && pathTok.parts.length === 1 && typeof pathTok.parts[0] === 'object';
        if (!pathTok || (v && v.unresolvable && bareVar) || (v && v.text === '')) {
          findings.push({ verb: 'git worktree add', raw: pathTok ? pathTok.raw : '<no path>', resolved: null, status: 'unresolvable', deny: true, rule: 'worktree-add-inside-lane', why: `git worktree add ${pathTok ? pathTok.raw : ''}: the path is ${pathTok ? 'a variable this command does not set' : 'missing'} and the command runs inside lane ${path.posix.basename(cwdLoc.laneRoot)} — an empty path here emptied a lane on 2026-08-31 (memory: worktree-add-empty-var-wipes-cwd). Run it from the primary checkout with a literal path.` });
        }
      }
    }
    return;
  }
  if (sub === 'clean') {
    // git removes nested repositories (what every lane is) only with -f given
    // twice, in any spelling: -ff, -fdf, -f -f, --force --force.
    let forces = 0;
    for (const t of rest) {
      if (t.raw === '--force') forces++;
      else if (/^-[a-zA-Z]+$/.test(t.raw)) forces += (t.raw.match(/f/g) || []).length;
    }
    const doubleForce = forces >= 2;
    const paths = rest.filter((t) => !t.raw.startsWith('-') && t.raw !== '--');
    if (paths.length) { for (const t of paths) judgeTarget(t, 'clean', scoped, 'git clean', findings, { contents: true }); return; }
    if (scoped.cwd) {
      const loc = locate(scoped.cwd);
      if (loc && loc.depth === 0) findings.push({ verb: 'git clean', raw: '.', resolved: scoped.cwd, status: 'resolved', deny: true, rule: 'worktrees-dir', why: 'git clean run inside .claude/worktrees/ itself' });
      else if (!loc && doubleForce && holdsLanes(scoped.cwd)) findings.push({ verb: 'git clean', raw: '.', resolved: scoped.cwd, status: 'resolved', deny: true, rule: 'ancestor', why: `git clean -ff… from ${scoped.cwd}: double --force removes nested repositories, which is what every lane under .claude/worktrees/ is` });
    }
  }
}

function cloneState(state) {
  return { ...state, vars: new Map(state.vars) };
}

function valueOrRaw(tok, state) {
  const v = tokenValue(tok, state);
  return v.unresolvable ? tok.raw : v.text;
}

// Re-assemble argument words into one command line for a nested lexer,
// keeping each quoted/space-bearing value a single word.
function requote(toks, state) {
  return toks.map((t) => {
    const v = tokenValue(t, state);
    if (v.unresolvable) return t.raw;
    const s = v.text || '';
    return t.quoted || /\s/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }).join(' ');
}

function valueOrNull(tok, state) {
  const v = tokenValue(tok, state);
  if (v.unresolvable) return null;
  return v.multi ? v.multi : v.text;
}

function assignFromToken(name, tok, prefixLen, state) {
  const parts = tok.parts.slice();
  if (typeof parts[0] === 'string') parts[0] = parts[0].slice(prefixLen); else return state.vars.set(name, null);
  state.vars.set(name, valueOrNull({ parts, quoted: tok.quoted, raw: tok.raw }, state));
}

function evalItems(items, state, findings, dialect, depth) {
  const stack = [];
  for (const it of items) {
    if (it.type === 'open') { stack.push(cloneState(state)); continue; }
    if (it.type === 'close') { const s = stack.pop(); if (s) { state.cwd = s.cwd; state.vars = s.vars; } continue; }
    try { evalCommand(it.words, state, findings, dialect, depth); } catch (e) { findings.push({ verb: '?', raw: '?', resolved: null, status: 'error', deny: state.namesWorktrees && OLD_DESTRUCTIVE.test(state.text), rule: 'parse-error', why: 'guard could not parse this command: ' + (e && e.message) }); }
  }
}

const OLD_DESTRUCTIVE = /\b(rm|rmdir|rd|del|mv)\b|Remove-Item|Move-Item/i;

// payload: the PreToolUse hook's stdin JSON (tool_name, tool_input.command, cwd)
function judge(payload, opts) {
  opts = opts || {};
  const cmd = (payload && payload.tool_input && payload.tool_input.command) || '';
  const tool = (payload && payload.tool_name) || 'Bash';
  const dialect = /powershell/i.test(tool) ? 'ps' : 'bash';
  const env = opts.env || process.env;
  const state = {
    cwd: payload && payload.cwd ? realCwd(String(payload.cwd)) : null,
    vars: new Map(),
    env,
    text: cmd,
    namesWorktrees: WORKTREES_TEXT.test(cmd),
  };
  const findings = [];
  let items;
  try {
    items = lex(cmd, dialect);
    evalItems(items, state, findings, dialect, 0);
  } catch (e) {
    // never crash a tool call: fall back to the text rule the guard had before
    const deny = state.namesWorktrees && OLD_DESTRUCTIVE.test(cmd);
    return { deny, findings: [{ verb: '?', raw: '?', resolved: null, status: 'error', deny, rule: 'parse-error', why: 'guard could not parse this command: ' + (e && e.message) }], reason: deny ? denyReason([{ why: 'the guard could not parse this command and it names .claude/worktrees/ beside a destructive verb' }]) : null };
  }
  const denied = findings.filter((f) => f.deny);
  return { deny: denied.length > 0, findings, reason: denied.length ? denyReason(denied) : null };
}

// The payload cwd may reach a lane through a junction, symlink or 8.3 short
// name; the on-disk path is what the lane comparison needs.
function realCwd(cwd) {
  const n = normalizePath(cwd);
  try { return normalizePath(fs.realpathSync.native(fsPath(n))); } catch { return n; }
}

function denyReason(denied) {
  const lines = denied.slice(0, 4).map((f) => '  - ' + f.why);
  return (
    'Blocked: this would delete or move something under .claude/worktrees/, which holds ' +
    'live uncommitted work from parallel feature lanes (see CLAUDE.md footgun 2).\n' +
    lines.join('\n') + (denied.length > 4 ? `\n  - … and ${denied.length - 4} more` : '') +
    '\nRun `git worktree list` to see the lanes. A lane root is never deletable from a tool call — ' +
    'if removal is really intended, ask Kent to do it directly. (Guard: .claude/hooks/block-worktree-mutation.js)'
  );
}

function main() {
  let data;
  try {
    data = JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch {
    process.exit(0);
  }
  const verdict = judge(data);
  if (verdict.deny) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: verdict.reason,
      },
    }));
  }
  process.exit(0);
}

if (require.main === module) main();

module.exports = { judge, lex, normalizePath, locate, OWN_LANE };
