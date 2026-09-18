"""The picker: four routes, stdlib only, bound to localhost.

Served by WHITELIST. The page may fetch the public pair list and exactly the
images that list names; `arms.json`, `features.json` and `designs/` are in the
same directory and must never be reachable, because reading them un-blinds
the sitting. A pick is appended and fsynced BEFORE the reply is written.

The pair list is read once, at start. So the server records WHICH sitting it
read (the sealed map's hash, from `sitting.json`), refuses to start on one
that is torn, reports the hash on disk with every `/pairs` so the page can
see a `--pair` rebuild the sitting under it, and answers 409 to a pick once
that has happened.
"""
from __future__ import annotations

import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .pairs import CHOICES, append_pick, load_picks, sealed_hash

PORT = 8731
# A pick is under a hundred bytes. The cap keeps a wrong Content-Length from
# parking a handler thread on a read that nothing will satisfy.
MAX_BODY = 4096

PAGE = """<!doctype html>
<meta charset="utf-8"><title>Eye pairs</title>
<style>
body{margin:0;background:#2b2b2b;color:#ddd;font:14px system-ui,sans-serif}
#bar{padding:8px 12px;display:flex;gap:12px;align-items:center}
#count{min-width:6em}
#msg{color:#ffb454;min-height:1.2em}
#row{display:flex;gap:8px;align-items:flex-start;justify-content:center;padding:0 8px}
.view{flex:1 1 0;overflow:hidden;background:#fff;cursor:zoom-in;max-height:84vh}
.view img{width:100%;display:block;transform-origin:50% 50%}
#art{flex:0 0 13%;background:#fff}
#art img{width:100%;display:block}
button{font:inherit;padding:6px 14px}
</style>
<div id="bar"><span id="count"></span>
<button id="bl">&larr; Left</button>
<button id="bt">space &middot; Can't tell</button>
<button id="br">Right &rarr;</button>
<button id="bu">u &middot; Undo</button>
<span id="msg"></span></div>
<div id="row">
<div class="view" id="vl"><img id="il" alt=""></div>
<div id="art"><img id="ia" alt=""></div>
<div class="view" id="vr"><img id="ir" alt=""></div>
</div>
<script>
// `busy` is the latch: set while a pair's images are still loading and
// while a POST is in flight, so no keypress can act until the pair on
// screen is the pair the click is for. `done` is in CLICK order (the
// server reports picks that way), so Undo after a reload takes back the
// pair judged last, not the highest id. `stale` is set for good once the
// sitting on disk is no longer the one this page loaded: the ids on
// screen may now mean different pictures, so nothing more is recorded.
let pairs=[],queue=[],done=[],t0=0,zoom=false,busy=false,loading=0,stale=false,sitting=null;
const $=id=>document.getElementById(id);
async function load(){
  const r=await (await fetch('/pairs')).json();
  sitting=r.sitting;
  pairs=r.pairs;const picked=new Set(r.picked);
  queue=pairs.filter(p=>!picked.has(p.pair));
  done=r.picked.slice();
  show();
}
function rebuilt(){
  stale=true;
  $('msg').textContent='The sitting was rebuilt while this page was open - nothing more is recorded from this tab. Stop --serve, start it again, then reload.';
}
setInterval(async()=>{
  if(stale||sitting===null)return;
  try{const r=await (await fetch('/pairs')).json();if(r.sitting!==sitting)rebuilt();}catch(err){}
},5000);
function loaded(){
  loading=Math.max(0,loading-1);
  if(loading===0){busy=false;t0=performance.now();}
}
function show(){
  setZoom(false);
  $('count').textContent=(pairs.length-queue.length)+' / '+pairs.length;
  if(!queue.length){$('row').innerHTML='<p style="padding:40px">All pairs picked. Close this tab and run --reveal.</p>';return;}
  const p=queue[0];
  busy=true;loading=2;
  $('il').src='/img/'+p.left;$('ir').src='/img/'+p.right;$('ia').src='/img/'+p.art;
}
for(const id of ['il','ir']){$(id).addEventListener('load',loaded);$(id).addEventListener('error',loaded);}
async function send(body){
  const r=await fetch('/pick',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(r.status===409)rebuilt();
  if(!r.ok)throw new Error('HTTP '+r.status);
  return r;
}
async function pick(choice){
  if(busy||stale||!queue.length)return;
  busy=true;
  const p=queue[0];
  try{
    await send({pair:p.pair,choice:choice,ms:Math.round(performance.now()-t0)});
  }catch(err){
    if(!stale)$('msg').textContent='Not saved ('+err.message+') - the same pair is still showing; try again.';
    busy=false;return;
  }
  queue.shift();done.push(p.pair);
  $('msg').textContent='';
  show();
}
async function undo(){
  if(busy||stale||!done.length)return;
  busy=true;
  const id=done[done.length-1];
  try{
    await send({pair:id,undo:true,ms:0});
  }catch(err){
    if(!stale)$('msg').textContent='Undo not saved ('+err.message+'); try again.';
    busy=false;return;
  }
  done.pop();
  queue.unshift(pairs.find(p=>p.pair===id));
  $('msg').textContent='';
  show();
}
function setZoom(on,ox,oy){
  zoom=on;
  for(const id of ['il','ir']){
    const im=$(id);
    im.style.transformOrigin=(ox===undefined?50:ox)+'% '+(oy===undefined?50:oy)+'%';
    im.style.transform=on?'scale(3)':'scale(1)';
  }
  for(const id of ['vl','vr'])$(id).style.cursor=on?'zoom-out':'zoom-in';
}
function origin(e,el){
  const b=el.getBoundingClientRect();
  return [100*(e.clientX-b.left)/b.width,100*(e.clientY-b.top)/b.height];
}
for(const id of ['vl','vr']){
  const el=$(id);
  el.addEventListener('click',e=>{if(zoom){setZoom(false);}else{const o=origin(e,el);setZoom(true,o[0],o[1]);}});
  el.addEventListener('mousemove',e=>{if(zoom){const o=origin(e,el);setZoom(true,o[0],o[1]);}});
}
$('bl').onclick=()=>pick('L');$('br').onclick=()=>pick('R');
$('bt').onclick=()=>pick('tie');$('bu').onclick=undo;
document.addEventListener('keydown',e=>{
  if(e.repeat)return;
  if(e.key==='ArrowLeft')pick('L');
  else if(e.key==='ArrowRight')pick('R');
  else if(e.key===' '){e.preventDefault();pick('tie');}
  else if(e.key==='u')undo();
});
load();
</script>
"""


def sitting_on_disk(out: Path) -> str | None:
    """The sealed-map hash `--pair` last recorded, or None if unreadable
    (a `--pair` replacing the file this instant reads as 'changed', which
    is the safe answer)."""
    try:
        return json.loads((out / "sitting.json").read_text(encoding="utf-8")).get("sealed_sha256")
    except (OSError, ValueError):
        return None


def load_sitting(out: Path, pairs: list[dict]) -> str:
    """-> the hash of the sitting about to be served, or SystemExit.

    The pair list is read ONCE, so the server must know WHICH sitting it
    read. The public list cannot say — it is identical for any two sittings
    of one size, by design — so the identity is the sealed map's hash. The
    sealed map is hashed here and never served. A mismatch with
    `sitting.json` is a `--pair` that did not finish (review 2026-09-17).
    """
    loaded = sitting_on_disk(out)
    if loaded is None:
        raise SystemExit(f"REFUSED: no readable sitting.json in {out}. Run --pair first.")
    sealed = json.loads((out / "arms.json").read_text(encoding="utf-8"))
    n_pairs = json.loads((out / "sitting.json").read_text(encoding="utf-8")).get("n_pairs")
    if sealed_hash(sealed) != loaded or n_pairs != len(pairs) or set(sealed) != {p["pair"] for p in pairs}:
        raise SystemExit("REFUSED: pairs.json and arms.json are not the sitting that "
                         "sitting.json records - a --pair that did not finish? Run --pair again.")
    missing = sorted(p[k] for p in pairs for k in ("left", "right", "art")
                     if not (out / "img" / p[k]).exists())
    if missing:
        raise SystemExit(f"REFUSED: {len(missing)} image(s) listed in pairs.json are missing "
                         f"from img/ (first: {missing[0]}). Run --pair again.")
    return loaded


def make_server(out_dir, port: int = PORT, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    out = Path(out_dir)
    pairs = json.loads((out / "pairs.json").read_text(encoding="utf-8"))
    ids = {p["pair"] for p in pairs}
    allowed = {p[k] for p in pairs for k in ("left", "right", "art")}
    loaded = load_sitting(out, pairs)
    log = out / "picks.jsonl"
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):   # a name in a server log is a leak
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 - http.server's naming
            path = unquote(urlparse(self.path).path)
            if path == "/":
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/pairs":
                # Click order, not id order: `load_picks` keeps first-seen
                # order and an undo-then-repick moves a pair to the end,
                # which is exactly when it was judged last.
                with lock:
                    picked = list(load_picks(log))
                # `sitting` is re-read per request: the page polls this to
                # learn that a `--pair` rebuilt the sitting under it. A hash
                # names nothing, so it is safe to serve.
                body = json.dumps({"pairs": pairs, "picked": picked,
                                   "sitting": sitting_on_disk(out)}).encode("utf-8")
                self._send(200, body, "application/json")
            elif path.startswith("/img/") and path[len("/img/"):] in allowed:
                name = path[len("/img/"):]
                self._send(200, (out / "img" / name).read_bytes(),
                           "image/png" if name.endswith(".png") else "image/jpeg")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != "/pick":
                self._send(404, b"not found", "text/plain")
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if not 0 <= length <= MAX_BODY:
                    raise ValueError("unreasonable Content-Length")
                body = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._send(400, b"bad json", "text/plain")
                return
            # Everything below runs in the handler thread, where an uncaught
            # exception is a dropped connection and a banner that cannot say
            # why (review 2026-09-17). So the SHAPE is checked before use:
            # valid JSON need not be an object, and `ms` need not be a number.
            if not isinstance(body, dict):
                self._send(400, b"bad pick: not an object", "text/plain")
                return
            pair, undo, ms = body.get("pair"), bool(body.get("undo")), body.get("ms")
            if ms is None:
                ms = 0
            if (not isinstance(pair, str) or pair not in ids
                    or (not undo and body.get("choice") not in CHOICES)
                    or isinstance(ms, bool) or not isinstance(ms, (int, float))
                    or not math.isfinite(ms) or ms < 0):
                self._send(400, b"bad pick", "text/plain")
                return
            if sitting_on_disk(out) != loaded:
                # The click was made looking at the OLD sitting's pictures;
                # its id now means something else. The page polls for this,
                # but a click can land between polls.
                self._send(409, b"sitting rebuilt", "text/plain")
                return
            with lock:
                if undo:
                    append_pick(log, pair, None, 0, undo_of=pair)
                else:
                    append_pick(log, pair, body["choice"], int(ms))
            self._send(200, b'{"ok": true}', "application/json")

    return ThreadingHTTPServer((host, port), Handler)
