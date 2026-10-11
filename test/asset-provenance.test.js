// Every image / stitch file in the fixture and render folders must have an
// entry in docs/asset-provenance.json recording its source and licence status.
// The repo is public: a file nobody can account for is a publishing risk.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const ROOTS = ['digitizer/testdata/', 'app/e2e/fixtures/', 'app/src/lib/fixtures/',
  'app/public/', 'test/fixtures/', 'docs/renders/'];
const EXT = /\.(png|jpe?g|webp|gif|svg|bmp|tiff?|pes|dst|exp|jef|vp3|pdf)$/i;

const manifest = JSON.parse(readFileSync(new URL('../docs/asset-provenance.json', import.meta.url), 'utf8'));
const files = execFileSync('git', ['ls-files', ...ROOTS], { encoding: 'utf8', maxBuffer: 1 << 26 })
  .split('\n').filter((f) => f && EXT.test(f));

const matcher = (e) => {
  if (e.path) return (f) => f === e.path;
  if (e.prefix) return (f) => f.startsWith(e.prefix);
  const re = new RegExp('^' + e.prefix_ext.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*') + '$');
  return (f) => re.test(f);
};
const rules = manifest.entries.map((e) => ({ e, match: matcher(e) }));

test('manifest entries are well formed', () => {
  for (const { e } of rules) {
    assert.ok(e.path || e.prefix || e.prefix_ext, `entry without a path: ${JSON.stringify(e)}`);
    assert.ok(manifest.statuses.includes(e.status), `bad status "${e.status}"`);
    assert.ok(e.source && e.basis, `${e.path || e.prefix || e.prefix_ext}: source and basis required`);
  }
});

test('every image/stitch file has a provenance entry', () => {
  assert.ok(files.length > 100, 'file scan found suspiciously few files');
  const missing = files.filter((f) => !rules.some((r) => r.match(f)));
  assert.deepEqual(missing, [], `add these to docs/asset-provenance.json:\n${missing.join('\n')}`);
});

test('no fixture-root manifest entry is stale', () => {
  // docs/renders is output, so its entries may outlive a deleted directory.
  const stale = rules.filter((r) => !(r.e.prefix || '').startsWith('docs/renders/') && !files.some(r.match)).map((r) => r.e.path || r.e.prefix || r.e.prefix_ext);
  assert.deepEqual(stale, [], 'entries matching no tracked file');
});
