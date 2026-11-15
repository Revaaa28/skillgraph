"""SkillGraph — judge-facing live demo (stdlib only).

Serves a small web UI on port 8000 that talks to the REAL local HydraDB
node (HTTP API on 127.0.0.1:8443) through sg.py / demo.py. Every number
on every page comes from a live query issued while rendering that page;
the only fixed query set is the one below — visitors cannot run
arbitrary Cypher, and the node token never leaves the server.

Run (on the box, next to the node):
    HYDRA_TOKEN_FILE=<node token file> python3 webapp.py
"""
import html, json, os, sys, time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg import q, rows
import demo

PORT = int(os.environ.get("SG_WEB_PORT", "8000"))
TASKS = demo.TASKS

CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;
 background:#0b0f14;color:#e6edf3;line-height:1.5}
.wrap{max-width:980px;margin:0 auto;padding:24px 18px 60px}
a{color:#58a6ff} h1{font-size:28px;margin:8px 0} h2{margin-top:34px}
.card{background:#11161d;border:1px solid #26303c;border-radius:10px;
 padding:16px 18px;margin:14px 0}
.big{font-size:30px;font-weight:700}
table{border-collapse:collapse;width:100%;margin:8px 0}
td,th{border:1px solid #26303c;padding:6px 9px;text-align:left;vertical-align:top}
th{background:#161d26}
pre{background:#0d1117;border:1px solid #26303c;border-radius:8px;
 padding:12px;overflow:auto;font-size:12px;max-height:420px}
.pill{display:inline-block;background:#1c2733;border:1px solid #2f4152;
 border-radius:999px;padding:2px 10px;margin:2px 4px 2px 0;font-size:13px}
.cur{border-left:4px solid #3fb950}
code{background:#161d26;padding:1px 5px;border-radius:4px}
.small{color:#9fb0c1;font-size:13px}
"""

def esc(x):
    return html.escape(str(x))

def live_counts():
    kinds = {}
    for kind in ("Skill", "Tool", "MCPServer", "TaskType", "Entity", "Verdict"):
        kinds[kind] = len(rows(q(
            "MATCH (n) WHERE n.kind = '%s' RETURN n.id AS id" % kind)))
    edges = {}
    for et in ("NEEDS_SKILL", "USES_TOOL", "ABOUT", "HAS_VERDICT",
               "SUPERSEDES", "EXPOSED_VIA"):
        edges[et] = len(rows(q(
            "MATCH (a)-[r:%s]->(b) RETURN a.id AS id" % et)))
    return kinds, edges

def entity_names():
    return [r["name"] for r in rows(q(
        "MATCH (n) WHERE n.kind = 'Entity' RETURN n.name AS name"))]

def page(title, body):
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)}</title><style>{CSS}</style></head>"
            f"<body><div class='wrap'>{body}</div></body></html>")

def home():
    t0 = time.perf_counter()
    kinds, edges = live_counts()
    full = demo.full_catalog()
    preload = demo.bsize(full)
    ms = (time.perf_counter() - t0) * 1000
    task_links = " ".join(
        f"<a class='pill' href='/bundle?task={quote(t)}'>{esc(t)}</a>"
        for t in TASKS)
    ent_links = " ".join(
        f"<a class='pill' href='/chain?entity={quote(n)}'>{esc(n)}</a>"
        for n in entity_names())
    body = f"""
<h1>SkillGraph — the agent context layer on HydraDB</h1>
<p>An AI agent's skills, tools, MCP servers, the entities it works on and
<b>verified verdicts about those entities</b> live in one HydraDB graph.
For a task, the agent traverses only the subgraph it needs and assembles
a minimal context bundle — instead of preloading the whole catalog into
every prompt.</p>

<div class='card'><div class='big'>{sum(kinds.values())} nodes · {sum(edges.values())} edges</div>
<p class='small'>Counted live from the graph just now (page rendered in {ms:.0f} ms of query time):<br>
{" · ".join(f"{k}: {v}" for k, v in kinds.items())}<br>
{" · ".join(f"{k}: {v}" for k, v in edges.items())}</p></div>

<div class='card'><h2 style='margin-top:0'>The baseline this beats</h2>
<p>Preloading the entire catalog (every skill, tool, MCP server, task
type, entity and <i>all</i> verdicts including history) serializes to
<b>{preload:,} bytes</b> — and still goes stale the moment any verdict
changes. Try a task and compare its live bundle:</p>
<p>{task_links}</p></div>

<div class='card'><h2 style='margin-top:0'>Verdicts that learn: SUPERSEDES chains</h2>
<p>Verdicts accumulate with timestamps. A newer verdict
<code>SUPERSEDES</code> the older one; the current verdict is derived by
traversal — the chain vertex nobody supersedes — never by overwriting.
Pick an entity to inspect its chain:</p>
<p>{ent_links}</p>
<p class='small'>Start with <a href='/chain?entity={quote("Ink Koi (INKOI)")}'>Ink Koi</a>:
three real verdicts from the Mint RedCeh board's on-chain autocheck —
the free mint went from “243 slots left” to “free lane CLOSED” and the
graph's current answer tracked it.</p></div>

<p class='small'>Data: skills/tools are the agent's real playbooks;
entities + verdicts are the live Mint RedCeh free-mint board
(on-chain verification, BSC). Engine: self-hosted open-source HydraDB
(hydra-db/hydradb) running on this machine; this page queries it live.
Repo: github.com/Revaaa28/skillgraph</p>
"""
    return page("SkillGraph — live demo", body)

def bundle_page(task):
    if task not in TASKS:
        return None
    t0 = time.perf_counter()
    now = datetime.now(timezone.utc)
    bundle, stale = demo.assemble_bundle(task, stale_hours=24.0, now=now)
    full = demo.full_catalog()
    preload = demo.bsize(full)
    b = demo.bsize(bundle)
    ms = (time.perf_counter() - t0) * 1000
    saved = 100.0 * (1 - b / preload)
    skills = "".join(f"<tr><td>{esc(s['name'])}</td><td>{esc(s['purpose'])}</td></tr>"
                     for s in bundle["skills"])
    tools = " ".join(f"<span class='pill'>{esc(t['name'])}</span>" for t in bundle["tools"])
    ents = ""
    for e in bundle["entities"]:
        v = e.get("verdict")
        if v:
            vt = f"[{esc(v['label'])}] {esc(v['detail'])}<br><span class='small'>verdict ts {esc(v['ts'])} · {esc(v['provenance'])}</span>"
        elif "verdict_excluded" in e:
            vt = esc(e["verdict_excluded"])
        else:
            vt = "<i>no current verdict</i>"
        ents += f"<tr><td>{esc(e['name'])}</td><td>{vt}</td></tr>"
    ent_section = (f"<h2>Entities + current verdicts (derived via SUPERSEDES)</h2>"
                   f"<table><tr><th>Entity</th><th>Current verdict</th></tr>{ents}</table>"
                   if bundle["entities"] else "")
    body = f"""
<p><a href='/'>← all tasks</a></p>
<h1>Task bundle: {esc(task)}</h1>
<div class='card'><div class='big'>{b:,} bytes</div>
<p>assembled live by traversal in {ms:.0f} ms · baseline preload {preload:,} bytes ·
<b>{saved:.1f}% smaller</b> · stale verdicts excluded by the 24 h guard: {stale}</p></div>
<h2>Skills (TaskType → NEEDS_SKILL)</h2>
<table><tr><th>Skill</th><th>Purpose</th></tr>{skills}</table>
<h2>Tools (Skill → USES_TOOL)</h2><p>{tools}</p>
{ent_section}
<h2>The exact bundle JSON handed to the agent</h2>
<pre>{esc(json.dumps(bundle, indent=1, sort_keys=True))}</pre>
"""
    return page(f"SkillGraph bundle — {task}", body)

def chain_page(entity):
    names = entity_names()
    if entity not in names:
        return None
    t0 = time.perf_counter()
    vs = demo.verdicts_of(entity)
    sup = demo.superseded_ids(entity)
    cur = demo.current_verdict(entity)
    ms = (time.perf_counter() - t0) * 1000
    vs_sorted = sorted(vs, key=lambda v: v["ts"])
    rows_html = ""
    for v in vs_sorted:
        is_cur = cur and v["vid"] == cur["vid"]
        tag = " <b>← CURRENT (nobody supersedes it)</b>" if is_cur else (
            " <span class='small'>(superseded)</span>" if v["vid"] in sup else "")
        rows_html += (f"<tr{' class=cur' if is_cur else ''}><td>{esc(v['ts'])}</td>"
                      f"<td>{esc(v['label'])}{tag}</td><td>{esc(v['detail'])}</td>"
                      f"<td class='small'>{esc(v['provenance'])}</td></tr>")
    # time travel: verdict in force at each verdict's own moment, and now
    tt = ""
    for v in vs_sorted:
        at = demo.verdict_at(entity, v["ts"])
        tt += f"<tr><td>{esc(v['ts'])}</td><td>[{esc(at['label'])}] {esc(at['detail'])}</td></tr>"
    now_v = demo.current_verdict(entity)
    tt += (f"<tr><td>now</td><td>[{esc(now_v['label'])}] {esc(now_v['detail'])}</td></tr>"
           if now_v else "")
    body = f"""
<p><a href='/'>← home</a></p>
<h1>Verdict chain: {esc(entity)}</h1>
<p class='small'>Queried live in {ms:.0f} ms. Derivation rule: the current
verdict is the HAS_VERDICT vertex that no other verdict SUPERSEDES.
History is never overwritten — it stays traversable.</p>
<table><tr><th>Timestamp (UTC)</th><th>Label</th><th>Detail</th><th>Provenance</th></tr>{rows_html}</table>
<h2>Time travel — the verdict in force at each moment</h2>
<table><tr><th>At</th><th>Verdict then</th></tr>{tt}</table>
<p class='small'>A flat key-value store can only return the latest write.
The chain is what lets the agent answer “what did we believe on Nov 11 —
and why did it change?”</p>
"""
    return page(f"SkillGraph chain — {entity}", body)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, code=200):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        try:
            if u.path == "/healthz":
                self._send("ok")
            elif u.path == "/":
                self._send(home())
            elif u.path == "/bundle":
                p = bundle_page((qs.get("task") or [""])[0])
                self._send(p if p else page("not found", "<h1>Unknown task</h1>"), 200 if p else 404)
            elif u.path == "/chain":
                p = chain_page((qs.get("entity") or [""])[0])
                self._send(p if p else page("not found", "<h1>Unknown entity</h1>"), 200 if p else 404)
            else:
                self._send(page("not found", "<h1>404</h1>"), 404)
        except Exception as e:
            self._send(page("error", f"<h1>Live query failed</h1><pre>{esc(e)}</pre>"), 500)

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
