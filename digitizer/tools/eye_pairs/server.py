"""The picker: four routes, stdlib only, bound to localhost.

Served by WHITELIST. The page may fetch the public pair list and exactly the
images that list names; `arms.json`, `features.json` and `designs/` are in the
same directory and must never be reachable, because reading them un-blinds
the sitting. A pick is appended and fsynced BEFORE the reply is written.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .pairs import CHOICES, append_pick, load_picks

PORT = 8731

PAGE = """<!doctype html>
<meta charset="utf-8"><title>Eye pairs</title>
<style>
body{margin:0;background:#2b2b2b;color:#ddd;font:14px system-ui,sans-serif}
#bar{padding:8px 12px;display:flex;gap:12px;align-items:center}
#count{min-width:6em}
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
<button id="bu">u &middot; Undo</button></div>
<div id="row">
<div class="view" id="vl"><img id="il" alt=""></div>
<div id="art"><img id="ia" alt=""></div>
<div class="view" id="vr"><img id="ir" alt=""></div>
</div>
<script>
let pairs=[],queue=[],done=[],t0=0,zoom=false;
const $=id=>document.getElementById(id);
async function load(){
  const r=await (await fetch('/pairs')).json();
  pairs=r.pairs;const picked=new Set(r.picked);
  queue=pairs.filter(p=>!picked.has(p.pair));
  done=pairs.filter(p=>picked.has(p.pair)).map(p=>p.pair);
  show();
}
function show(){
  setZoom(false);
  $('count').textContent=(pairs.length-queue.length)+' / '+pairs.length;
  if(!queue.length){$('row').innerHTML='<p style="padding:40px">All pairs picked. Close this tab and run --reveal.</p>';return;}
  const p=queue[0];
  $('il').src='/img/'+p.left;$('ir').src='/img/'+p.right;$('ia').src='/img/'+p.art;
  t0=performance.now();
}
async function send(body){
  await fetch('/pick',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
}
async function pick(choice){
  if(!queue.length)return;
  const p=queue.shift();done.push(p.pair);
  await send({pair:p.pair,choice:choice,ms:Math.round(performance.now()-t0)});
  show();
}
async function undo(){
  if(!done.length)return;
  const id=done.pop();
  await send({pair:id,undo:true,ms:0});
  queue.unshift(pairs.find(p=>p.pair===id));
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
  if(e.key==='ArrowLeft')pick('L');
  else if(e.key==='ArrowRight')pick('R');
  else if(e.key===' '){e.preventDefault();pick('tie');}
  else if(e.key==='u')undo();
});
load();
</script>
"""


def make_server(out_dir, port: int = PORT, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    out = Path(out_dir)
    pairs = json.loads((out / "pairs.json").read_text(encoding="utf-8"))
    ids = {p["pair"] for p in pairs}
    allowed = {p[k] for p in pairs for k in ("left", "right", "art")}
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
                with lock:
                    picked = sorted(load_picks(log))
                body = json.dumps({"pairs": pairs, "picked": picked}).encode("utf-8")
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
                body = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._send(400, b"bad json", "text/plain")
                return
            pair, undo = body.get("pair"), bool(body.get("undo"))
            if pair not in ids or (not undo and body.get("choice") not in CHOICES):
                self._send(400, b"bad pick", "text/plain")
                return
            with lock:
                if undo:
                    append_pick(log, pair, None, 0, undo_of=pair)
                else:
                    append_pick(log, pair, body["choice"], int(body.get("ms") or 0))
            self._send(200, b'{"ok": true}', "application/json")

    return ThreadingHTTPServer((host, port), Handler)
