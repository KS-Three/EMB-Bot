#!/usr/bin/env node
/**
 * spypoint-sync.mjs — pull your SpyPoint cameras (locations + status) and
 * photos to local disk, incrementally, via the same REST API the SpyPoint
 * app itself uses.
 *
 * UNOFFICIAL: endpoints mirrored from the community clients
 * hstern/pyspypoint and coloradude/spypoint-api-wrapper
 * (https://restapi.spypoint.com/api/v3). SpyPoint can change this API at any
 * time; when that happens this script fails loudly with a nonzero exit
 * instead of guessing.
 *
 * Zero dependencies. Node 20+.
 *
 *   SPYPOINT_EMAIL=you@example.com SPYPOINT_PASSWORD=... node spypoint-sync.mjs
 *
 * Options:
 *   --out DIR      output dir (default ./spypoint-data, or $SPYPOINT_OUT)
 *   --limit N      photos per API page (default 100)
 *   --max N        max new downloads per camera per run (default 500, 0 = all)
 *   --size S       large | medium | small (default large; falls back downward)
 *   --cameras A,B  only cameras whose name/id contains one of these
 *   --dry-run      show what would download; write nothing
 *   --inspect      dump raw field paths of one camera + one photo, then exit
 *   --quiet        errors and final summary only
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const API = 'https://restapi.spypoint.com/api/v3';
const FUTURE = '2100-01-01T00:00:00.000Z';

const argv = process.argv.slice(2);
const has = f => argv.includes(f);
const val = (f, d) => {
  const i = argv.indexOf(f);
  return i !== -1 && argv[i + 1] !== undefined ? argv[i + 1] : d;
};
const maxRaw = parseInt(val('--max', '500'), 10);
const OPT = {
  out: path.resolve(val('--out', process.env.SPYPOINT_OUT || './spypoint-data')),
  limit: Math.max(1, parseInt(val('--limit', '100'), 10) || 100),
  max: Number.isNaN(maxRaw) ? 500 : Math.max(0, maxRaw),
  size: val('--size', 'large'),
  cameras: val('--cameras', '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean),
  dryRun: has('--dry-run'),
  inspect: has('--inspect'),
  quiet: has('--quiet'),
};

const log = (...a) => { if (!OPT.quiet) console.log(...a); };
const warn = (...a) => console.error(...a);
const die = msg => { console.error(`\nERROR: ${msg}`); process.exit(1); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function api(method, route, { token, body } = {}) {
  await sleep(250); // no official rate limits exist, so stay deliberately slow
  for (let attempt = 1; ; attempt++) {
    let res;
    try {
      res = await fetch(API + route, {
        method,
        headers: {
          accept: 'application/json',
          ...(body ? { 'content-type': 'application/json' } : {}),
          ...(token ? { authorization: `Bearer ${token}` } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (err) {
      if (attempt < 3) { await sleep(1500 * attempt); continue; }
      throw new Error(`${method} ${route}: network failure after ${attempt} tries (${err.message})`);
    }
    if (res.status >= 500 && attempt < 3) { await sleep(1500 * attempt); continue; }
    if (!res.ok) {
      const text = (await res.text().catch(() => '')).slice(0, 300);
      const e = new Error(`${method} ${route} -> HTTP ${res.status}${text ? ` ${text}` : ''}`);
      e.status = res.status;
      throw e;
    }
    return res.json();
  }
}

// The camera/photo schemas are undocumented (both community clients pass the
// JSON through untouched), so extraction hunts by key name instead of
// hardcoding paths. Run --inspect to see what your account actually returns.
function* walk(obj, prefix = '') {
  if (obj === null || typeof obj !== 'object') {
    if (prefix) yield [prefix, obj];
    return;
  }
  if (Array.isArray(obj)) {
    if (prefix && obj.length > 0 && obj.every(x => typeof x === 'number')) yield [prefix, obj];
    for (let i = 0; i < obj.length; i++) yield* walk(obj[i], `${prefix}[${i}]`);
    return;
  }
  for (const [k, v] of Object.entries(obj)) yield* walk(v, prefix ? `${prefix}.${k}` : k);
}

const leafKey = p => p.replace(/\[\d+\]/g, '').split('.').pop();

function findFirst(obj, keyRe, pred = () => true) {
  for (const [p, v] of walk(obj)) {
    if (keyRe.test(leafKey(p)) && pred(v)) return { path: p, value: v };
  }
  return null;
}

const isNum = v => typeof v === 'number' && Number.isFinite(v);

function cameraSummary(cam) {
  const name = cam?.config?.name
    ?? findFirst(cam, /^name$/i, v => typeof v === 'string' && v.length > 0)?.value
    ?? String(cam?.id ?? 'camera');
  const lat = findFirst(cam, /^lat(itude)?$/i, isNum)?.value ?? null;
  const lng = findFirst(cam, /^(lng|lon|long|longitude)$/i, isNum)?.value ?? null;
  // Some models carry location as a bare 2-number array; [lng,lat] vs [lat,lng]
  // order is unverified — check one camera against the app map before trusting.
  const coords = (lat === null || lng === null)
    ? (findFirst(cam, /coord|position/i, v => Array.isArray(v) && v.length === 2)?.value ?? null)
    : null;
  return {
    id: String(cam?.id ?? ''),
    name,
    model: findFirst(cam, /^model$/i, v => typeof v === 'string')?.value ?? null,
    lat, lng, coords,
    battery: findFirst(cam, /batter/i, isNum)?.value ?? null,
    signal: findFirst(cam, /signal|cellular/i, isNum)?.value ?? null,
    lastSeen: findFirst(cam, /last.?(update|sync|comm|photo)/i, v => typeof v === 'string')?.value ?? null,
  };
}

const fmtLoc = r =>
  r.lat !== null && r.lng !== null ? `${r.lat},${r.lng}`
  : r.coords ? `${JSON.stringify(r.coords)} (order unverified)`
  : '?';

const DATE_KEYS = ['originDate', 'date', 'createDate', 'creationDate', 'dateTime'];
function photoDate(p) {
  for (const k of DATE_KEYS) {
    if (typeof p?.[k] === 'string' && !Number.isNaN(Date.parse(p[k]))) return p[k];
  }
  const hit = findFirst(p, /date|time/i, v => typeof v === 'string' && !Number.isNaN(Date.parse(v)));
  return hit?.value ?? null;
}

function photoUrl(p, prefer) {
  for (const size of [prefer, 'large', 'medium', 'small']) {
    const s = p?.[size];
    if (s?.host && s?.path) return `https://${s.host}/${s.path}`;
  }
  return null;
}

const q = v => {
  if (v === null || v === undefined) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const safe = s =>
  String(s).replace(/[^\w.-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60) || 'camera';

async function existingIds(root) {
  const ids = new Set();
  let names;
  try { names = await fs.readdir(root, { recursive: true }); } catch { return ids; }
  for (const n of names) {
    const ext = path.extname(n).toLowerCase();
    if (ext === '.jpg' || ext === '.jpeg') ids.add(path.basename(n, path.extname(n)));
  }
  return ids;
}

async function download(url, dest) {
  await sleep(150);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  await fs.mkdir(path.dirname(dest), { recursive: true });
  await fs.writeFile(dest, Buffer.from(await res.arrayBuffer()));
}

const fetchPage = (token, cameraId, dateEnd) =>
  api('POST', '/photo/all', {
    token,
    body: { camera: [cameraId], dateEnd, favorite: false, hd: false, limit: OPT.limit, tag: [] },
  });

function dumpPaths(label, obj) {
  console.log(`\n=== ${label} ===`);
  if (!obj) { console.log('  (nothing returned)'); return; }
  for (const [p, v] of walk(obj)) {
    let s = JSON.stringify(v);
    if (s && s.length > 80) s = s.slice(0, 77) + '...';
    console.log(`  ${p} = ${s}`);
  }
}

async function main() {
  const email = process.env.SPYPOINT_EMAIL;
  const password = process.env.SPYPOINT_PASSWORD;
  if (!email || !password) {
    die(`SPYPOINT_EMAIL and SPYPOINT_PASSWORD must be set (never hardcode them).
  PowerShell:  $env:SPYPOINT_EMAIL = "you@example.com"; $env:SPYPOINT_PASSWORD = "..."
  cmd:         set SPYPOINT_EMAIL=you@example.com
  bash:        export SPYPOINT_EMAIL=you@example.com`);
  }

  log(`Logging in as ${email} ...`);
  let auth;
  try {
    auth = await api('POST', '/user/login', { body: { username: email, password } });
  } catch (err) {
    if (err.status === 401 || err.status === 403) {
      die('SpyPoint rejected the login — check SPYPOINT_EMAIL / SPYPOINT_PASSWORD.');
    }
    throw err;
  }
  const token = auth?.token;
  if (!token) {
    die(`login response carried no token — the API may have changed. Keys seen: ${Object.keys(auth ?? {}).join(', ')}`);
  }

  const cameras = await api('GET', '/camera/all', { token });
  if (!Array.isArray(cameras)) die('camera/all did not return an array — the API may have changed.');
  log(`${cameras.length} camera(s) on the account.`);

  if (OPT.inspect) {
    dumpPaths('camera[0] raw fields', cameras[0]);
    if (cameras[0]?.id) {
      const page = await fetchPage(token, cameras[0].id, FUTURE);
      dumpPaths('photo[0] raw fields', (page?.photos ?? [])[0]);
    }
    console.log('\n(Trim anything you consider sensitive before sharing this output.)');
    return;
  }

  const rows = cameras.map(cameraSummary);
  const selected = OPT.cameras.length
    ? rows.filter(r => OPT.cameras.some(f =>
        r.name.toLowerCase().includes(f) || r.id.toLowerCase().includes(f)))
    : rows;
  for (const r of rows) {
    const mark = selected.includes(r) ? '' : '   (skipped by --cameras)';
    log(`  ${r.name}  model=${r.model ?? '?'}  loc=${fmtLoc(r)}  battery=${r.battery ?? '?'}  signal=${r.signal ?? '?'}  last=${r.lastSeen ?? '?'}${mark}`);
  }

  if (!OPT.dryRun) {
    await fs.mkdir(OPT.out, { recursive: true });
    await fs.writeFile(path.join(OPT.out, 'cameras.raw.json'), JSON.stringify(cameras, null, 2));
    const header = 'id,name,model,latitude,longitude,coords_raw,battery,signal,last_seen';
    const lines = rows.map(r => [
      r.id, q(r.name), q(r.model), r.lat ?? '', r.lng ?? '',
      r.coords ? q(JSON.stringify(r.coords)) : '', r.battery ?? '', r.signal ?? '', q(r.lastSeen),
    ].join(','));
    await fs.writeFile(path.join(OPT.out, 'cameras.csv'), [header, ...lines].join('\n') + '\n');
  }

  const photoRoot = path.join(OPT.out, 'photos');
  const seen = await existingIds(photoRoot); // the photos/ tree IS the sync state
  log(`${seen.size} photo(s) already on disk under ${photoRoot}`);

  let totalNew = 0;
  const meta = [];
  for (const cam of selected) {
    let dateEnd = FUTURE;
    let fetched = 0;
    let pages = 0;
    camloop: while (pages < 1000) {
      const page = await fetchPage(token, cam.id, dateEnd);
      const photos = page?.photos ?? [];
      pages++;
      if (photos.length === 0) break;
      let oldest = null;
      for (const p of photos) {
        const d = photoDate(p);
        if (d && (oldest === null || Date.parse(d) < Date.parse(oldest))) oldest = d;
        const id = String(p?.id ?? '');
        if (!id || seen.has(id)) continue;
        const url = photoUrl(p, OPT.size);
        if (!url) { warn(`  ${cam.name}: photo ${id} has no downloadable URL, skipped`); continue; }
        if (OPT.dryRun) {
          log(`  [dry] ${cam.name}  ${id}  ${d ?? 'date?'}`);
        } else {
          const dest = path.join(photoRoot, safe(cam.name), d ? safe(d.slice(0, 7)) : 'unknown-date', `${id}.jpg`);
          try {
            await download(url, dest);
          } catch (err) {
            warn(`  ${cam.name}: download failed for ${id} (${err.message}) — will retry next run`);
            continue;
          }
        }
        seen.add(id);
        meta.push(JSON.stringify({
          id, camera: cam.id, cameraName: cam.name, date: d,
          tags: p.tag ?? p.tags ?? [], url,
        }));
        fetched++; totalNew++;
        if (OPT.max && fetched >= OPT.max) {
          log(`  ${cam.name}: reached --max ${OPT.max}; older history remains (rerun, or --max 0 for full backfill)`);
          break camloop;
        }
      }
      if (photos.length < OPT.limit) break; // final page
      if (!oldest) break;                   // cannot page without dates
      const next = new Date(Date.parse(oldest) - 1).toISOString();
      if (Date.parse(next) >= Date.parse(dateEnd)) break; // cursor must move backward
      dateEnd = next;
    }
    log(`${cam.name}: ${fetched} new photo(s)`);
  }

  if (meta.length && !OPT.dryRun) {
    await fs.appendFile(path.join(OPT.out, 'photos.jsonl'), meta.join('\n') + '\n');
  }
  console.log(`Done: ${totalNew} new photo(s)${OPT.dryRun ? ' would be downloaded (dry run)' : ''}. Output: ${OPT.out}`);
}

main().catch(err => die(err.stack ?? String(err)));
